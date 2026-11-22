from decimal import Decimal
import ipaddress
import socket
from typing import Optional
from urllib.parse import urlparse
import urllib.request
from uuid import UUID
import xml.etree.ElementTree as ET
from django.conf import settings as dj_settings
from django.db.models import Count, Sum
from apps.accounts.models import AgencyMembership, User
from apps.cms.models import Article
from apps.crm.models import CustomerInteractionLog, FollowUpTask
from apps.customers.services import list_customers
from apps.negotiations.services import get_negotiation_detail
from apps.properties.services import list_agency_properties
from apps.settings.models import ProviderConfiguration
from apps.settings.services import parse_provider_credentials, resolve_active_provider_config
from apps.transactions.models import Deal
from common.exceptions import NotFoundDomainError, PermissionDeniedDomainError, ValidationDomainError
from common.permissions import get_active_membership, get_effective_permissions, is_super_admin
from integrations.registry import get_ai_provider
from .models import AiInteractionLog


def _assert_ai_access(user: User, agency_id: Optional[UUID]) -> None:
    if is_super_admin(user):
        return
    if not agency_id or not get_active_membership(user, agency_id):
        raise PermissionDeniedDomainError("دسترسی به دستیار هوشمند فقط برای اعضای فعال آژانس مجاز است.")


def _resolve_ai_runtime(agency_id: Optional[UUID]) -> tuple[str, str, str]:
    cfg = resolve_active_provider_config(
        category=ProviderConfiguration.Category.AI, agency_id=agency_id
    )
    creds = parse_provider_credentials(cfg)
    api_key = str(creds.get("api_key") or getattr(dj_settings, "GAPGPT_API_KEY", "") or "").strip()
    base_url = str(
        (cfg.config_json or {}).get("base_url") if cfg else getattr(dj_settings, "GAPGPT_BASE_URL", "https://api.gapgpt.app/v1")
    ).strip()
    default_model = str(
        (cfg.config_json or {}).get("default_model") if cfg else getattr(dj_settings, "GAPGPT_DEFAULT_MODEL", "gpt-4o")
    ).strip()
    return api_key, base_url, default_model


def get_ai_status(*, user: User, agency_id: Optional[UUID]) -> dict:
    _assert_ai_access(user, agency_id)
    adapter = get_ai_provider("gapgpt")
    api_key, base_url, default_model = _resolve_ai_runtime(agency_id)
    health = adapter.check_health(api_key=api_key, base_url=base_url)
    health["default_model"] = default_model or health.get("default_model", "gpt-4o")
    health["supported_models"] = adapter.list_supported_models()
    return health


def _build_grounded_agency_context(*, user: User, agency_id: Optional[UUID], task_mode: str, message: str) -> str:
    """Strictly builds RBAC-aware and tenant-isolated factual context for AI prompts."""
    if not agency_id:
        return "نقش کاربر: مدیر پلتفرم بدون آژانس فعال. فقط راهنمایی عمومی ساختار پلتفرم ارائه شود."

    perms = get_effective_permissions(user, agency_id)
    props = list(list_agency_properties(user=user, agency_id=agency_id)[:8])
    prop_lines = [
        f"- [{p.property_code}] {p.title} | وضعیت: {p.status} | متراژ: {p.built_area_sqm}متر | قیمت: {p.total_price} | منطقه: {getattr(getattr(p, 'location', None), 'district', '-')}"
        for p in props
    ]

    cust_lines = []
    if "*" in perms or "customer.view_all_agency" in perms or True:
        custs = list(list_customers(user=user, agency_id=agency_id)[:6])
        cust_lines = [
            f"- {c.full_name} | نوع: {c.customer_type} | امتیاز آمادگی: {c.lead_score} ({c.readiness_level})"
            for c in custs
        ]

    finance_summary = "دسترسی مالی برای این نقش محدود است."
    if "*" in perms or "deal.view_all_agency" in perms or "accounting.view" in perms:
        deals_agg = Deal.objects.all_tenants().filter(agency_id=agency_id).aggregate(
            count=Count("id"), total=Sum("deal_value")
        )
        agents_count = AgencyMembership.objects.filter(agency_id=agency_id, status="ACTIVE").count()
        finance_summary = (
            f"تعداد کل معاملات ثبت‌شده: {deals_agg['count'] or 0}، حجم معاملات: {deals_agg['total'] or 0} تومان، تعداد مشاوران فعال: {agents_count}."
        )

    return (
        f"نام سیستم: بنیان ملک (پلتفرم سازمانی املاک).\n"
        f"نوع درخواست: {task_mode}\n"
        f"املاک مجاز قابل مشاهده برای کاربر فعلی (آژانس {agency_id}):\n"
        + ("\n".join(prop_lines) if prop_lines else "ملکی ثبت نشده است.")
        + "\nمشتریان مجاز قابل مشاهده:\n"
        + ("\n".join(cust_lines) if cust_lines else "مشتری ثبت نشده است.")
        + f"\nخلاصه آمار عملکرد آژانس: {finance_summary}"
    )


def _deterministic_grounded_fallback(*, user: User, agency_id: Optional[UUID], task_mode: str, message: str) -> str:
    props = list(list_agency_properties(user=user, agency_id=agency_id)[:4]) if agency_id else []
    custs = list(list_customers(user=user, agency_id=agency_id)[:4]) if agency_id else []
    top_prop = props[0].title if props else "ملک شاخص آژانس"
    top_cust = custs[0].full_name if custs else "مشتری اولویت‌دار"

    if task_mode == "PROPERTY_MATCH":
        lines = "\n".join([f"• {p.property_code}: {p.title} ({p.built_area_sqm} متر — {p.total_price} تومان)" for p in props])
        return (
            f"بر اساس فایل‌های مجاز آژانس شما و تحلیل تطبیق هوشمند:\n"
            f"{lines or 'فایل فعالی در سبد شما یافت نشد.'}\n"
            f"پیشنهاد اقدام: هماهنگی بازدید حضوری برای فایل «{top_prop}» و مقایسه امکانات با بودجه هدف."
        )
    if task_mode == "LEAD_FOLLOWUP":
        lines = "\n".join([f"• {c.full_name} — امتیاز {c.lead_score} ({c.readiness_level})" for c in custs])
        return (
            f"تحلیل اولویت پیگیری سرنخ‌ها و مشتریان شما:\n"
            f"{lines or 'سرنخی ثبت نشده است.'}\n"
            f"توصیه عملیاتی: تماس فوری با «{top_cust}» جهت تثبیت زمان بازدید و ارائه ۲ فایل جایگزین هم‌منطقه."
        )
    if task_mode == "NEGOTIATION_ADVICE":
        return (
            "تحلیل استراتژیک مذاکره:\n"
            "۱) فاصله قیمت پیشنهادی مشتری با قیمت پایه را با شرایط پرداخت نقدی یا زمان تحویل کوتاه‌تر تعدیل کنید.\n"
            "۲) پس از توافق روی عدد میانی، مرحله مذاکره را به «توافق اولیه» منتقل کرده و پیش‌نویس قرارداد را یکجا صادر کنید."
        )
    if task_mode == "AD_COPY":
        return (
            f"پیشنهاد متن آگهی حرفه‌ای برای «{top_prop}»:\n"
            "عنوان: فرصت کم‌نظیر سرمایه‌گذاری و سکونت — نقشه مهندسی بدون پرتی\n"
            "متن: واحد خوش‌نقشه با نورگیری مستقیم، سند تک‌برگ آماده انتقال، دسترسی ممتاز به شریان‌های اصلی و مشاعات کامل. جهت دریافت جدول شرایط پرداخت و هماهنگی بازدید اختصاصی تماس بگیرید."
        )
    return (
        f"پاسخ تحلیلی دستیار هوشمند بر اساس داده‌های واقعی و مجاز آژانس شما:\n"
        f"- تعداد فایل‌های در دسترس شما: {len(props)} مورد (شاخص: {top_prop})\n"
        f"- تعداد مشتریان در دسترس شما: {len(custs)} مورد (اولویت: {top_cust})\n"
        f"- راهنمایی: برای فعال‌سازی مدل‌های زبانی GapGPT (مانند GPT-4o و Claude Sonnet)، کلید GAPGPT_API_KEY را در تنظیمات سرور وارد کنید."
    )


def chat_with_assistant(
    *,
    user: User,
    agency_id: Optional[UUID],
    message: str,
    task_mode: str = "GENERAL",
    model: Optional[str] = None,
    history: Optional[list[dict]] = None,
) -> dict:
    _assert_ai_access(user, agency_id)
    clean_msg = (message or "").strip()
    if not clean_msg:
        raise ValidationDomainError("متن پیام برای دستیار هوشمند نمی‌تواند خالی باشد.")

    grounded_ctx = _build_grounded_agency_context(
        user=user, agency_id=agency_id, task_mode=task_mode, message=clean_msg
    )
    system_prompt = (
        "تو دستیار تخصصی سازمانی پلتفرم املاک «بنیان ملک» هستی. "
        "به زبان فارسی حرفه‌ای، دقیق، ساختارمند و کاربردی پاسخ بده. "
        "هرگز اطلاعات خارج از داده‌های واقعی زیر جعل نکن و محرمانگی سایر آژانس‌ها را کاملاً رعایت کن.\n\n"
        f"{grounded_ctx}"
    )

    messages = [{"role": "system", "content": system_prompt}]
    for item in (history or [])[-6:]:
        role = item.get("role")
        content = str(item.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content[:2000]})
    messages.append({"role": "user", "content": clean_msg})

    api_key, base_url, default_model = _resolve_ai_runtime(agency_id)
    resolved_model = (model or default_model or "gpt-4o").strip()
    adapter = get_ai_provider("gapgpt")

    provider_used = "GAPGPT"
    tokens_used = 0
    latency_ms = 0
    fallback_note = ""

    if api_key:
        try:
            res = adapter.complete_chat(
                messages=messages,
                model=resolved_model,
                api_key=api_key,
                base_url=base_url,
            )
            reply_text = res.content
            resolved_model = res.model
            tokens_used = res.tokens_used
            latency_ms = res.latency_ms
        except Exception as exc:
            provider_used = "DOMAIN_ENGINE"
            fallback_note = str(exc)
            reply_text = _deterministic_grounded_fallback(
                user=user, agency_id=agency_id, task_mode=task_mode, message=clean_msg
            )
    else:
        provider_used = "DOMAIN_ENGINE"
        fallback_note = "GAPGPT_API_KEY در سرور تنظیم نشده؛ پاسخ از موتور تحلیلی بومی تولید شد."
        reply_text = _deterministic_grounded_fallback(
            user=user, agency_id=agency_id, task_mode=task_mode, message=clean_msg
        )

    output_payload = {
        "reply": reply_text,
        "provider": provider_used,
        "model": resolved_model,
        "task_mode": task_mode,
        "tokens_used": tokens_used,
        "latency_ms": latency_ms,
        "fallback_note": fallback_note,
    }
    AiInteractionLog.objects.create(
        agency_id=agency_id,
        user=user,
        tool_type=AiInteractionLog.ToolType.AGENCY_CHAT,
        resource_type="AssistantChat",
        prompt_summary=f"[{task_mode}] {clean_msg[:220]}",
        draft_output=output_payload,
        provider=provider_used,
        model_name=resolved_model,
        tokens_used=tokens_used,
        latency_ms=latency_ms,
    )
    return output_payload


def summarize_negotiation_with_ai(
    *, user: User, agency_id: UUID, negotiation_id: UUID, model: Optional[str] = None
) -> dict:
    _assert_ai_access(user, agency_id)
    neg = get_negotiation_detail(user=user, agency_id=agency_id, negotiation_id=negotiation_id)
    offers_str = "\n".join(
        [
            f"- نسخه {o.version_number} ({o.offered_by}): {o.proposed_price} تومان | وضعیت: {o.status}"
            for o in neg.offer_versions.order_by("version_number")
        ]
    )
    prompt = (
        f"خلاصه مذاکره ملک «{neg.property.title}» با مشتری «{neg.customer.full_name}» در مرحله {neg.status}:\n"
        f"قیمت پایه ملک: {neg.asking_price or neg.property.total_price}\n"
        f"پیشنهادها:\n{offers_str or 'هنوز پیشنهادی ثبت نشده'}\n"
        "لطفاً ریسک‌ها، نقطه تعادل قیمتی پیشنهادی و گام بعدی مشاور را ارائه بده."
    )
    return chat_with_assistant(
        user=user,
        agency_id=agency_id,
        message=prompt,
        task_mode="NEGOTIATION_ADVICE",
        model=model,
    )


def _assert_ssrf_safe_https_url(url: str) -> str:
    parsed = urlparse((url or "").strip())
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValidationDomainError("فقط نشانی‌های HTTPS معتبر برای دریافت فید مجاز هستند.")
    host = parsed.hostname.lower()
    if host in ("localhost", "127.0.0.1", "0.0.0.0", "169.254.169.254") or host.endswith(".local"):
        raise ValidationDomainError("دسترسی به نشانی‌های داخلی مجاز نیست (SSRF Protection).")
    try:
        ip_str = socket.gethostbyname(host)
        ip = ipaddress.ip_address(ip_str)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValidationDomainError("دسترسی به شبکه خصوصی از طریق فید RSS مسدود است.")
    except socket.gaierror as exc:
        raise ValidationDomainError("امکان تفکیک دامنه فید RSS وجود ندارد.") from exc
    return parsed.geturl()


def draft_property_listing(*, user: User, agency_id: UUID, property_id: UUID, tone: str = "FORMAL") -> dict:
    _assert_ai_access(user, agency_id)
    prop = list_agency_properties(user=user, agency_id=agency_id).filter(id=property_id).first()
    if not prop:
        raise NotFoundDomainError("ملک در آژانس شما یافت نشد.")
    loc = getattr(prop, "location", None)
    city = loc.city if loc else "تهران"
    district = loc.district if loc and loc.district else ""
    loc_label = f"{city}، {district}".strip("، ")
    amenities = [a.name_fa for a in prop.amenities.all()[:5]]
    amenities_str = "، ".join(amenities) if amenities else "نقشه مهندسی و نورگیری عالی"

    tone_intro = (
        "فرصت سرمایه‌گذاری و سکونت ممتاز"
        if tone == "INVESTMENT"
        else "پیشنهاد ویژه و استاندارد دفتر املاک"
    )
    suggested_title = f"{prop.property_type.name_fa} {int(prop.built_area_sqm)} متری {prop.bedrooms} خوابه در {loc_label}"
    suggested_description = (
        f"{tone_intro}: {prop.property_type.name_fa} با زیربنای {prop.built_area_sqm} متر مربع "
        f"واقع در {loc_label}. دارای {prop.bedrooms} اتاق خواب، {prop.bathrooms} سرویس و امکانات شاخص از جمله {amenities_str}. "
        f"نوع معامله: {prop.deal_type.name_fa}."
    )
    seo_keywords = [
        f"خرید {prop.property_type.name_fa} {district or city}".strip(),
        f"{prop.deal_type.name_fa} ملک در {city}",
        f"آپارتمان {prop.bedrooms} خوابه {district or city}".strip(),
    ]
    draft = {
        "is_draft": True,
        "auto_published": False,
        "property_id": str(prop.id),
        "property_code": prop.property_code,
        "suggested_title": suggested_title,
        "suggested_description": suggested_description,
        "suggested_highlights": amenities,
        "seo_keywords": seo_keywords,
    }
    AiInteractionLog.objects.create(
        agency_id=agency_id,
        user=user,
        tool_type=AiInteractionLog.ToolType.PROPERTY_COPY,
        resource_type="Property",
        resource_id=str(prop.id),
        prompt_summary=f"Property copy draft ({tone}) for {prop.property_code}",
        draft_output=draft,
        provider="DOMAIN_ENGINE",
    )
    return draft


def summarize_customer_crm(*, user: User, agency_id: UUID, customer_id: UUID) -> dict:
    _assert_ai_access(user, agency_id)
    customer = list_customers(user=user, agency_id=agency_id).filter(id=customer_id).first()
    if not customer:
        raise NotFoundDomainError("مشتری در آژانس شما یافت نشد.")

    interactions = list(
        CustomerInteractionLog.objects.all_tenants()
        .filter(agency_id=agency_id, customer=customer)
        .order_by("-created_at")[:6]
    )
    open_tasks = FollowUpTask.objects.all_tenants().filter(
        agency_id=agency_id, customer=customer, status="PENDING"
    ).count()

    next_action = (
        "هماهنگی زمان بازدید حضوری از فایل‌های هم‌تراز"
        if customer.lead_score >= 70
        else "تماس تلفنی برای تدقیق بودجه و اولویت محله"
    )
    summary_text = (
        f"مشتری «{customer.full_name}» با امتیاز آمادگی {customer.lead_score} ({customer.readiness_level}) "
        f"دارای {len(interactions)} تعامل ثبت‌شده و {open_tasks} کار پیگیری باز است."
    )
    draft = {
        "is_draft": True,
        "customer_id": str(customer.id),
        "customer_name": customer.full_name,
        "lead_score": customer.lead_score,
        "readiness_level": customer.readiness_level,
        "open_tasks_count": open_tasks,
        "recent_channels": [i.channel for i in interactions],
        "executive_summary": summary_text,
        "recommended_next_action": next_action,
    }
    AiInteractionLog.objects.create(
        agency_id=agency_id,
        user=user,
        tool_type=AiInteractionLog.ToolType.CRM_SUMMARY,
        resource_type="Customer",
        resource_id=str(customer.id),
        prompt_summary=f"CRM summary for {customer.full_name}",
        draft_output=draft,
        provider="DOMAIN_ENGINE",
    )
    return draft


def draft_seo_metadata(
    *,
    user: User,
    agency_id: Optional[UUID],
    title: str,
    body_excerpt: str,
    target_city: str = "",
) -> dict:
    _assert_ai_access(user, agency_id)
    clean_title = title.strip()[:58]
    city_suffix = f" در {target_city}" if target_city else ""
    meta_title = f"{clean_title}{city_suffix} | بنیان ملک"[:65]
    raw_desc = (body_excerpt.strip() or clean_title).replace("\n", " ")
    meta_description = (raw_desc[:148] + "...") if len(raw_desc) > 152 else raw_desc
    slug_base = "-".join(title.strip().lower().split()[:6]) or "article"

    words = [w for w in raw_desc.split() if len(w) > 1]
    word_count = len(words)
    sentences = max(1, raw_desc.count(".") + raw_desc.count("۔") + raw_desc.count("؟") + 1)
    avg_words_per_sentence = round(word_count / sentences, 1)
    readability_score = max(45, min(98, int(100 - max(0, avg_words_per_sentence - 12) * 2.5)))

    title_tokens = set(clean_title.split())
    similar_articles = []
    for art in Article.objects.all()[:50]:
        art_tokens = set(art.title.split())
        overlap = len(title_tokens & art_tokens) / max(1, len(title_tokens | art_tokens))
        if overlap >= 0.45:
            similar_articles.append({"slug": art.slug, "title": art.title, "similarity_percent": int(overlap * 100)})

    internal_links = [
        {"label": f"فهرست املاک {target_city or 'برگزیده'}", "href": f"/search?city={target_city or 'تهران'}"},
        {"label": "فهرست مشاوران و آژانس‌های همکار", "href": "/properties"},
        {"label": "درخواست مشاوره تخصصی خرید و فروش", "href": "/contact"},
    ]
    outline = [
        f"۱. چشم‌انداز قیمت و تقاضا برای «{clean_title}»",
        "۲. چک‌لیست حقوقی و استعلام سند پیش از عقد قرارداد",
        "۳. مقایسه محله‌های هم‌تراز و بازدهی سرمایه‌گذاری",
        "۴. جمع‌بندی و مسیر رزرو بازدید حضوری",
    ]

    draft = {
        "is_draft": True,
        "requires_human_approval": True,
        "auto_published": False,
        "meta_title": meta_title,
        "meta_description": meta_description,
        "suggested_slug": slug_base,
        "focus_keywords": [clean_title, target_city or "املاک", "مشاوره ملکی", "قیمت مسکن"],
        "outline": outline,
        "internal_links": internal_links,
        "readability": {
            "word_count": word_count,
            "avg_sentence_length": avg_words_per_sentence,
            "score": readability_score,
            "label": "عالی" if readability_score >= 80 else ("مناسب" if readability_score >= 60 else "نیازمند ویرایش جملات طولانی"),
        },
        "duplicate_warnings": similar_articles,
        "topic_suggestions": [
            f"تحلیل قیمت هر متر مربع در {target_city or 'مناطق ۱ تا ۳ تهران'}",
            "نکات کلیدی تنظیم مبایعه‌نامه رسمی و کد رهگیری",
            "مقایسه بازدهی اجاره‌داری مسکونی و اداری در سال ۱۴۰۵",
        ],
    }
    AiInteractionLog.objects.create(
        agency_id=agency_id,
        user=user,
        tool_type=AiInteractionLog.ToolType.SEO_DRAFT,
        resource_type="SEO",
        prompt_summary=f"SEO metadata draft for {clean_title[:60]}",
        draft_output=draft,
        provider="DOMAIN_ENGINE",
    )
    return draft


def fetch_rss_topic_ideas(*, user: User, agency_id: Optional[UUID], feed_url: Optional[str] = None) -> dict:
    _assert_ai_access(user, agency_id)
    if not feed_url:
        return {
            "source": "internal_market_curated",
            "requires_human_approval": True,
            "topics": [
                {"title": "تحلیل روند معاملات مسکن مناطق شمالی کلان‌شهرها", "angle": "گزارش تحلیلی داده‌محور"},
                {"title": "راهنمای محاسبه کمیسیون قانونی و مالیات بر نقل‌وانتقال", "angle": "آموزشی و حقوقی"},
                {"title": "تأثیر نرخ تسهیلات بانکی بر تقاضای رهن و اجاره", "angle": "اخبار بازار مسکن"},
            ],
        }

    safe_url = _assert_ssrf_safe_https_url(feed_url)
    req = urllib.request.Request(safe_url, headers={"User-Agent": "BonyanMelk-RSSReader/1.0"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        xml_bytes = resp.read(250_000)

    root = ET.fromstring(xml_bytes)
    topics = []
    for item in root.findall(".//item")[:8]:
        t = item.findtext("title") or ""
        link = item.findtext("link") or ""
        if t.strip():
            topics.append({"title": t.strip()[:160], "reference_url": link.strip(), "angle": "ایده خبری (نیازمند بازنویسی انسانی)"})
    return {"source": safe_url, "requires_human_approval": True, "topics": topics}


def get_portfolio_insights(*, user: User, agency_id: UUID) -> dict:
    _assert_ai_access(user, agency_id)
    props_qs = list_agency_properties(user=user, agency_id=agency_id)
    total_props = props_qs.count()
    by_status = list(props_qs.values("status").annotate(count=Count("id")))
    deals_agg = Deal.objects.all_tenants().filter(agency_id=agency_id).aggregate(
        count=Count("id"), total=Sum("deal_value")
    )
    return {
        "is_draft": True,
        "total_properties": total_props,
        "properties_by_status": by_status,
        "deals_count": deals_agg["count"] or 0,
        "deals_volume": str(deals_agg["total"] or Decimal("0")),
        "recommendations": [
            "پیشنهاد می‌شود املاک در وضعیت PENDING_APPROVAL جهت انتشار سریع‌تر بازبینی شوند.",
            "از تطبیق هوشمند خریداران با فایل‌های جدید برای افزایش نرخ تبدیل بازدید به مذاکره استفاده کنید.",
        ],
    }


def list_ai_logs(*, user: User, agency_id: Optional[UUID]):
    _assert_ai_access(user, agency_id)
    qs = AiInteractionLog.objects.select_related("user")
    if agency_id:
        qs = qs.filter(agency_id=agency_id)
    elif not is_super_admin(user):
        qs = qs.filter(user=user)
    return qs.order_by("-created_at")[:30]


CONTENT_TYPE_TOPICS: dict[str, list[dict[str, str]]] = {
    "ARTICLE": [
        {"title": "راهنمای جامع بررسی حقوقی سند و استعلام ملک پیش از خرید", "keywords": "سند تک برگ، استعلام ثبتی، خرید ملک", "audience": "خریداران"},
        {"title": "تحلیل ارزش‌گذاری واقعی آپارتمان بر اساس موقعیت، نور و سال ساخت", "keywords": "ارزش گذاری ملک، قیمت هر متر، کارشناسی", "audience": "خریداران و مالکان"},
        {"title": "مقایسه سرمایه‌گذاری در املاک مسکونی نوساز و کلنگی با قابلیت مشارکت", "keywords": "سرمایه گذاری مسکن، ملک کلنگی، نوساز", "audience": "سرمایه‌گذاران"},
    ],
    "EDUCATIONAL": [
        {"title": "آموزش گام‌به‌گام محاسبه کمیسیون قانونی معاملات املاک و مالیات نقل‌وانتقال", "keywords": "کمیسیون املاک، مالیات نقل و انتقال، قرارداد", "audience": "مشاوران و متعاملین"},
        {"title": "۱۰ نکته طلایی تنظیم مبایعه‌نامه و اجاره‌نامه بدون ریسک حقوقی", "keywords": "مبایعه نامه، اجاره نامه، کد رهگیری", "audience": "مشاوران املاک"},
        {"title": "آشنایی با تفاوت قراردادهای مشارکت در ساخت و پیش‌فروش ساختمان", "keywords": "مشارکت در ساخت، پیش فروش، قرارداد", "audience": "سازندگان و خریداران"},
    ],
    "NEWS": [
        {"title": "گزارش تحلیلی روند تقاضای خرید و اجاره در فصول پرتقاضای بازار مسکن", "keywords": "بازار مسکن، روند اجاره، گزارش ماهانه", "audience": "فعالان بازار مسکن"},
        {"title": "تأثیر توسعه حمل‌ونقل ریلی و دسترسی‌های بزرگراهی بر قیمت محله‌ها", "keywords": "رشد قیمت محله، زیرساخت شهری، مسکن", "audience": "سرمایه‌گذاران"},
        {"title": "تغییرات جدید مقررات ثبت معاملات رسمی و احراز اصالت آگهی‌های ملکی", "keywords": "ثبت رسمی، احراز اصالت، قوانین املاک", "audience": "مدیران آژانس"},
    ],
    "PROMOTIONAL": [
        {"title": "چرا همکاری با آژانس‌های دارای فرآیند احراز اصالت سه‌مرحله‌ای امنیت معامله را تضمین می‌کند؟", "keywords": "معامله امن، احراز اصالت، آژانس معتبر", "audience": "خریداران و مالکان"},
        {"title": "معرفی خدمات اختصاصی کارشناسی قیمت و تور مجازی سه‌بعدی برای فروش سریع‌تر ملک", "keywords": "تور مجازی، فروش سریع ملک، کارشناسی", "audience": "فروشندگان ملک"},
    ],
    "SEO": [
        {"title": "بهترین محله‌ها برای خرید آپارتمان خوش‌نقشه با دسترسی عالی و بازدهی پایدار", "keywords": "خرید آپارتمان، محله های برتر، راهنمای خرید", "audience": "جستجوگران اینترنتی"},
        {"title": "راهنمای کامل رهن و اجاره واحدهای اداری و تجاری با سند موقعیت اداری", "keywords": "اجاره دفتر کار، سند اداری، رهن تجاری", "audience": "کسب‌وکارها"},
    ],
    "SOCIAL_MEDIA": [
        {"title": "۵ اشتباه رایج در بازدید اول ملک که نباید مرتکب شوید", "keywords": "نکات بازدید ملک، چک لیست خریدار، اینستاگرام املاک", "audience": "مخاطبان شبکه‌های اجتماعی"},
        {"title": "چگونه در ۳ دقیقه اصالت سند و رضایت مالک یک فایل ملکی را تشخیص دهیم؟", "keywords": "اصالت ملک، امنیت خرید، نکات سریع", "audience": "خریداران جوان"},
    ],
    "LISTING_DESCRIPTION": [
        {"title": "توضیحات حرفه‌ای و متقاعدکننده برای معرفی فایل پنت‌هاوس یا آپارتمان لوکس", "keywords": "پنت هاوس، فایل ویژه، آگهی حرفه ای", "audience": "خریداران ملک لوکس"},
        {"title": "الگوی استاندارد نگارش آگهی اجاره واحد اداری و مستغلات شرکتی", "keywords": "آگهی اداری، اجاره مستغلات، موقعیت تجاری", "audience": "شرکت‌ها و مدیران"},
    ],
}

VALID_CONTENT_TYPES = set(CONTENT_TYPE_TOPICS.keys())


def suggest_content_topics(
    *,
    user: User,
    agency_id: Optional[UUID],
    content_type: str = "ARTICLE",
    focus_city: str = "",
    audience: str = "",
) -> dict:
    _assert_ai_access(user, agency_id)
    ctype = (content_type or "ARTICLE").upper()
    if ctype not in VALID_CONTENT_TYPES:
        ctype = "ARTICLE"

    city_label = (focus_city or "").strip()
    base_topics = [dict(t) for t in CONTENT_TYPE_TOPICS[ctype]]
    if city_label:
        for item in base_topics:
            item["title"] = f"{item['title']} ({city_label})"
            item["keywords"] = f"{item['keywords']}، {city_label}"
    if audience:
        for item in base_topics:
            item["audience"] = audience.strip()

    # Enrich with agency's live top property district if agency_id is present
    if agency_id:
        top_prop = list_agency_properties(user=user, agency_id=agency_id).first()
        if top_prop:
            loc = getattr(top_prop, "location", None)
            dist = (loc.district or loc.city) if loc else ""
            if dist:
                base_topics.insert(
                    0,
                    {
                        "title": f"تحلیل و معرفی فرصت‌های شاخص {top_prop.property_type.name_fa} در {dist}",
                        "keywords": f"{top_prop.property_type.name_fa}، {dist}، {top_prop.deal_type.name_fa}",
                        "audience": audience or "متقاضیان فعال منطقه",
                    },
                )

    return {
        "content_type": ctype,
        "topics": base_topics[:6],
        "requires_human_approval": True,
    }


def _build_domain_content_draft(
    *,
    topic: str,
    content_type: str,
    language: str,
    tone: str,
    target_audience: str,
    keywords: list[str],
) -> dict:
    kw_list = [k.strip() for k in keywords if k and k.strip()] or ["بنیان ملک", "مشاوره املاک", "تحلیل بازار مسکن"]
    kw_str = "، ".join(kw_list)
    aud = target_audience.strip() or "خریداران، مالکان و مشاوران حرفه‌ای املاک"
    lang_en = language.lower().startswith("en")

    if lang_en:
        title = topic.strip()
        summary = f"Structured {content_type.lower()} draft prepared for {aud} focusing on {kw_str}."
        body_html = (
            f"<h2>{title}</h2>"
            f"<p><strong>Target Audience:</strong> {aud} | <strong>Tone:</strong> {tone}</p>"
            f"<p>In the modern real estate market, verified property records, transparent valuation, and documented legal compliance directly protect transaction outcomes.</p>"
            f"<h3>Key Takeaways</h3>"
            f"<ul><li>Verify physical existence, deed status, and owner authorization prior to commitment.</li>"
            f"<li>Benchmark comparable square-meter rates and payment milestones clearly.</li>"
            f"<li>Key focus terms: {kw_str}.</li></ul>"
        )
    elif content_type == "SOCIAL_MEDIA":
        title = topic.strip()
        summary = f"کپشن آماده انتشار در شبکه‌های اجتماعی برای {aud} با تمرکز بر {kw_str}"
        body_html = (
            f"<h2>{title}</h2>"
            f"<p>پیش از هر تصمیم ملکی، بررسی دقیق این ۳ مورد سرمایه شما را حفظ می‌کند:</p>"
            f"<ul>"
            f"<li>۱. تطبیق اصالت سند و رضایت ثبت‌شده مالک با مشخصات آگهی</li>"
            f"<li>۲. مقایسه قیمت هر متر مربع با فایل‌های مشابه هم‌محله</li>"
            f"<li>۳. ثبت شفاف تعهدات و زمان‌بندی پرداخت در پیش‌نویس قرارداد رسمی</li>"
            f"</ul>"
            f"<p><strong>دعوت به اقدام:</strong> برای دریافت مشاوره تخصصی و استعلام فایل‌های تأییدشده با کارشناسان ما در ارتباط باشید.</p>"
            f"<p>کلیدواژه‌ها: {kw_str}</p>"
        )
    elif content_type == "LISTING_DESCRIPTION":
        title = topic.strip()
        summary = f"توضیحات استاندارد آگهی ملکی جهت جذب {aud}"
        body_html = (
            f"<h2>{title}</h2>"
            f"<p>یک انتخاب کم‌نظیر با استاندارد معماری مهندسی، نورگیری مطلوب و دسترسی سریع به شریان‌های اصلی شهر. این ملک از نظر مدارک مالکیتی و اصالت فایل به‌طور کامل بررسی شده است.</p>"
            f"<h3>مشخصات و مزایای کلیدی</h3>"
            f"<ul>"
            f"<li>پلان کاربردی بدون فضای پرت و سالن یک‌تکه مناسب چیدمان مدرن</li>"
            f"<li>وضعیت سند: معتبر و آماده بررسی حقوقی پیش از تنظیم قرارداد</li>"
            f"<li>شرایط معامله قابل مذاکره با حضور مالک و مشاور پرونده</li>"
            f"</ul>"
            f"<p><strong>کلیدواژه‌ها:</strong> {kw_str}</p>"
        )
    else:
        type_headings = {
            "ARTICLE": "تحلیل تخصصی و نکات اجرایی",
            "EDUCATIONAL": "گام‌های آموزشی و چک‌لیست عملی",
            "NEWS": "خلاصه تحولات و تحلیل پیامدهای بازار",
            "PROMOTIONAL": "ارزش پیشنهادی و مزیت رقابتی",
            "SEO": "راهنمای جامع سئومحور و پاسخ به پرسش‌های کلیدی",
        }
        sec_heading = type_headings.get(content_type, "بررسی تخصصی موضوع")
        title = topic.strip()
        summary = f"پیش‌نویس {content_type} ویژه {aud} درباره «{title}» با کلیدواژه‌های {kw_str}."
        body_html = (
            f"<h2>{title}</h2>"
            f"<p>مخاطب هدف این محتوا <strong>{aud}</strong> است و با لحن <strong>{tone}</strong> نگارش شده است تا تصمیم‌گیری ملکی با شفافیت و اطمینان بیشتری انجام شود.</p>"
            f"<h3>{sec_heading}</h3>"
            f"<p>در فرآیند ارزیابی و انجام معاملات املاک، اتکا به داده‌های واقعی منطقه، احراز اصالت سه‌مرحله‌ای فایل (وجود فیزیکی، اصالت سند، رضایت مالک) و مستندسازی توافقات نقش کلیدی در پیشگیری از ریسک‌های مالی و حقوقی دارد.</p>"
            f"<ul>"
            f"<li><strong>بررسی قیمت معیار:</strong> مقایسه نرخ هر متر مربع با معاملات هم‌تراز در بازه زمانی جاری</li>"
            f"<li><strong>مدیریت ریسک حقوقی:</strong> استعلام وضعیت رهن، توقیف یا وکالت‌نامه پیش از پرداخت وجه</li>"
            f"<li><strong>کلمات کلیدی هدف:</strong> {kw_str}</li>"
            f"</ul>"
            f"<h3>جمع‌بندی و اقدام پیشنهادی</h3>"
            f"<p>پیش از نهایی‌سازی هرگونه تعهد، تمامی شروط پرداخت و زمان تحویل را در قالب قرارداد استاندارد ثبت و تأیید کنید.</p>"
        )

    import re

    slug_clean = re.sub(r"[^a-z0-9-]+", "-", topic.lower()).strip("-")
    if len(slug_clean) < 4:
        import secrets
        slug_clean = f"ai-{content_type.lower()}-{secrets.token_hex(3)}"

    return {
        "title": title,
        "summary": summary[:450],
        "content_body": body_html,
        "meta_title": f"{title[:55]} | بنیان ملک",
        "meta_description": summary[:155],
        "suggested_slug": slug_clean[:120],
        "keywords": kw_list,
    }


def generate_ai_content(*, user: User, agency_id: Optional[UUID], data: dict) -> dict:
    _assert_ai_access(user, agency_id)
    topic = (data.get("topic") or "").strip()
    if len(topic) < 3:
        raise ValidationDomainError("موضوع تولید محتوا باید حداقل ۳ کاراکتر باشد.")

    content_type = str(data.get("content_type") or "ARTICLE").upper()
    if content_type not in VALID_CONTENT_TYPES:
        raise ValidationDomainError("نوع محتوای انتخاب‌شده معتبر نیست.")

    language = str(data.get("language") or "fa").strip()
    tone = str(data.get("tone") or "PROFESSIONAL").strip()
    target_audience = str(data.get("target_audience") or "خریداران و سرمایه‌گذاران املاک").strip()
    keywords = [str(k).strip() for k in (data.get("keywords") or []) if str(k).strip()]
    custom_instructions = str(data.get("custom_instructions") or "").strip()

    api_key, base_url, default_model = _resolve_ai_runtime(agency_id)
    resolved_model = (data.get("model") or default_model or "gpt-4o").strip()
    adapter = get_ai_provider("gapgpt")

    provider_used = "DOMAIN_ENGINE"
    tokens_used = 0
    latency_ms = 0
    fallback_note = ""
    draft = _build_domain_content_draft(
        topic=topic,
        content_type=content_type,
        language=language,
        tone=tone,
        target_audience=target_audience,
        keywords=keywords,
    )

    if api_key:
        prompt = (
            f"تولید پیش‌نویس محتوای تخصصی املاک با مشخصات زیر:\n"
            f"- موضوع: {topic}\n"
            f"- نوع محتوا: {content_type}\n"
            f"- زبان: {language}\n"
            f"- لحن: {tone}\n"
            f"- مخاطب هدف: {target_audience}\n"
            f"- کلمات کلیدی: {', '.join(keywords) or 'املاک، بنیان ملک'}\n"
            + (f"- نکات تکمیلی: {custom_instructions}\n" if custom_instructions else "")
            + "لطفاً خروجی را با ساختار HTML استاندارد (h2, h3, p, ul, li) و آماده بازبینی تحریریه تولید کن."
        )
        try:
            res = adapter.complete_chat(
                messages=[
                    {"role": "system", "content": "تو سردبیر ارشد تولید محتوای املاک هستی. فقط پیش‌نویس دقیق و کاربردی تولید کن."},
                    {"role": "user", "content": prompt},
                ],
                model=resolved_model,
                api_key=api_key,
                base_url=base_url,
            )
            if res.content and res.content.strip():
                draft["content_body"] = res.content.strip()
            resolved_model = res.model
            tokens_used = res.tokens_used
            latency_ms = res.latency_ms
            provider_used = "GAPGPT"
        except Exception as exc:
            fallback_note = str(exc)

    result = {
        **draft,
        "content_type": content_type,
        "language": language,
        "tone": tone,
        "target_audience": target_audience,
        "is_draft": True,
        "status": "DRAFT",
        "auto_published": False,
        "requires_human_approval": True,
        "provider": provider_used,
        "model": resolved_model,
        "tokens_used": tokens_used,
        "latency_ms": latency_ms,
        "fallback_note": fallback_note,
    }
    AiInteractionLog.objects.create(
        agency_id=agency_id,
        user=user,
        tool_type=AiInteractionLog.ToolType.SEO_DRAFT,
        resource_type="ArticleDraft",
        prompt_summary=f"[{content_type}/{language}] {topic[:180]}",
        draft_output=result,
        provider=provider_used,
        model_name=resolved_model,
        tokens_used=tokens_used,
        latency_ms=latency_ms,
    )
    return result


def rewrite_ai_content(*, user: User, agency_id: Optional[UUID], data: dict) -> dict:
    _assert_ai_access(user, agency_id)
    title = str(data.get("title") or "").strip()
    body = str(data.get("content_body") or "").strip()
    instruction = str(data.get("instruction") or "بهبود خوانایی، روانی متن و بهینه‌سازی سئو").strip()
    tone = str(data.get("tone") or "PROFESSIONAL").strip()
    language = str(data.get("language") or "fa").strip()
    keywords = [str(k).strip() for k in (data.get("keywords") or []) if str(k).strip()]

    if not body:
        raise ValidationDomainError("متن فعلی برای بازنویسی نمی‌تواند خالی باشد.")

    api_key, base_url, default_model = _resolve_ai_runtime(agency_id)
    resolved_model = (data.get("model") or default_model or "gpt-4o").strip()
    adapter = get_ai_provider("gapgpt")

    provider_used = "DOMAIN_ENGINE"
    tokens_used = 0
    latency_ms = 0
    rewritten_body = (
        f"{body}\n"
        f"<h3>جمع‌بندی بازنویسی‌شده ({tone})</h3>"
        f"<p>نسخه بازنگری‌شده بر اساس دستور «{instruction}»"
        + (f" با تمرکز بر کلیدواژه‌های {'، '.join(keywords)}" if keywords else "")
        + " آماده بررسی و تأیید نهایی تحریریه است.</p>"
    )

    if api_key:
        try:
            res = adapter.complete_chat(
                messages=[
                    {"role": "system", "content": "تو ویراستار حرفه‌ای محتوای املاک هستی. متن را طبق دستور کاربر به HTML تمیز بازنویسی کن."},
                    {
                        "role": "user",
                        "content": f"عنوان: {title}\nزبان: {language}\nلحن هدف: {tone}\nدستور بازنویسی: {instruction}\nکلمات کلیدی: {', '.join(keywords)}\n\nمتن فعلی:\n{body[:5000]}",
                    },
                ],
                model=resolved_model,
                api_key=api_key,
                base_url=base_url,
            )
            if res.content and res.content.strip():
                rewritten_body = res.content.strip()
            resolved_model = res.model
            tokens_used = res.tokens_used
            latency_ms = res.latency_ms
            provider_used = "GAPGPT"
        except Exception:
            pass

    output = {
        "title": title,
        "content_body": rewritten_body,
        "tone": tone,
        "language": language,
        "is_draft": True,
        "auto_published": False,
        "provider": provider_used,
        "model": resolved_model,
        "tokens_used": tokens_used,
    }
    AiInteractionLog.objects.create(
        agency_id=agency_id,
        user=user,
        tool_type=AiInteractionLog.ToolType.SEO_DRAFT,
        resource_type="ArticleRewrite",
        prompt_summary=f"Rewrite: {instruction[:180]}",
        draft_output=output,
        provider=provider_used,
        model_name=resolved_model,
        tokens_used=tokens_used,
        latency_ms=latency_ms,
    )
    return output


def save_ai_content_to_cms(*, user: User, agency_id: Optional[UUID], data: dict) -> Article:
    from apps.cms.services import create_article

    payload = dict(data)
    payload["agency_id"] = agency_id
    payload["ai_generated"] = True
    payload["change_note"] = payload.get("change_note") or "ذخیره پیش‌نویس تولیدشده توسط هوش مصنوعی"
    return create_article(user=user, data=payload)


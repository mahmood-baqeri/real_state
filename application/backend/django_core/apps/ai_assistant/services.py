# Path: backend/django_core/apps/ai_assistant/services.py

from decimal import Decimal
from typing import Optional
from uuid import UUID
from django.db.models import Count, Sum
from apps.accounts.models import User
from apps.crm.models import CustomerInteractionLog, FollowUpTask
from apps.customers.services import list_customers
from apps.properties.services import list_agency_properties
from apps.transactions.models import Deal
from common.exceptions import NotFoundDomainError, PermissionDeniedDomainError
from common.permissions import get_active_membership, is_super_admin
from .models import AiInteractionLog


def _assert_ai_access(user: User, agency_id: Optional[UUID]) -> None:
    if is_super_admin(user):
        return
    if not agency_id or not get_active_membership(user, agency_id):
        raise PermissionDeniedDomainError("دسترسی به دستیار هوشمند فقط برای اعضای فعال آژانس مجاز است.")


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


def draft_seo_metadata(*, user: User, agency_id: Optional[UUID], title: str, body_excerpt: str, target_city: str = "") -> dict:
    _assert_ai_access(user, agency_id)
    clean_title = title.strip()[:58]
    city_suffix = f" در {target_city}" if target_city else ""
    meta_title = f"{clean_title}{city_suffix} | بنیان ملک"[:65]
    raw_desc = (body_excerpt.strip() or clean_title).replace("\n", " ")
    meta_description = (raw_desc[:148] + "...") if len(raw_desc) > 152 else raw_desc
    slug_base = "-".join(title.strip().lower().split()[:6]) or "article"
    draft = {
        "is_draft": True,
        "auto_published": False,
        "meta_title": meta_title,
        "meta_description": meta_description,
        "suggested_slug": slug_base,
        "focus_keywords": [clean_title, target_city or "املاک", "مشاوره ملکی"],
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


def get_portfolio_insights(*, user: User, agency_id: UUID) -> dict:
    _assert_ai_access(user, agency_id)
    props_qs = list_agency_properties(user=user, agency_id=agency_id)
    total_props = props_qs.count()
    by_status = list(props_qs.values("status").annotate(count=Count("id")))
    deals_agg = Deal.objects.all_tenants().filter(agency_id=agency_id).aggregate(
        count=Count("id"), total=Sum("deal_value")
    )
    draft = {
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
    return draft


def list_ai_logs(*, user: User, agency_id: Optional[UUID]):
    _assert_ai_access(user, agency_id)
    qs = AiInteractionLog.objects.select_related("user")
    if agency_id:
        qs = qs.filter(agency_id=agency_id)
    elif not is_super_admin(user):
        qs = qs.filter(user=user)
    return qs.order_by("-created_at")[:30]

import secrets
from typing import Optional
from uuid import UUID
from django.db import models, transaction
from django.utils import timezone
from apps.accounts.models import User
from apps.accounts.services import register_user
from apps.agencies.services import create_agency
from apps.audit.services import record_audit_event
from common.exceptions import (
    ConflictDomainError,
    NotFoundDomainError,
    PermissionDeniedDomainError,
    ValidationDomainError,
)
from common.permissions import is_super_admin
from common.sanitizer import sanitize_html
from .models import (
    AgencyCooperationRequest,
    Article,
    AuthorProfile,
    ContactInquiry,
    ContentCategory,
    ContentVersion,
    FaqItem,
    JobOpening,
    LegalAcceptanceRecord,
    LegalDocument,
    LegalDocumentVersion,
    RedirectRule,
    Tag,
)

ARTICLE_TRANSITIONS = {
    Article.Status.DRAFT: {Article.Status.REVIEW, Article.Status.ARCHIVED},
    Article.Status.REVIEW: {Article.Status.APPROVED, Article.Status.DRAFT, Article.Status.ARCHIVED},
    Article.Status.APPROVED: {Article.Status.PUBLISHED, Article.Status.SCHEDULED, Article.Status.DRAFT},
    Article.Status.SCHEDULED: {Article.Status.PUBLISHED, Article.Status.DRAFT, Article.Status.ARCHIVED},
    Article.Status.PUBLISHED: {Article.Status.ARCHIVED, Article.Status.DRAFT},
    Article.Status.ARCHIVED: {Article.Status.DRAFT},
}

LEGAL_TRANSITIONS = {
    LegalDocument.Status.DRAFT: {LegalDocument.Status.REVIEW, LegalDocument.Status.PUBLISHED, LegalDocument.Status.ARCHIVED},
    LegalDocument.Status.REVIEW: {LegalDocument.Status.APPROVED, LegalDocument.Status.DRAFT, LegalDocument.Status.ARCHIVED},
    LegalDocument.Status.APPROVED: {LegalDocument.Status.PUBLISHED, LegalDocument.Status.DRAFT, LegalDocument.Status.ARCHIVED},
    LegalDocument.Status.PUBLISHED: {LegalDocument.Status.DRAFT, LegalDocument.Status.ARCHIVED},
    LegalDocument.Status.ARCHIVED: {LegalDocument.Status.DRAFT},
}


def _normalize_legal_sections(raw_sections: Optional[list]) -> list[dict]:
    if not raw_sections:
        return []
    cleaned: list[dict] = []
    for idx, item in enumerate(raw_sections, start=1):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        body_html = sanitize_html(str(item.get("body_html") or ""))
        if not title and not body_html:
            continue
        cleaned.append(
            {
                "id": str(item.get("id") or f"sec-{idx}"),
                "title": title or f"بخش {idx}",
                "body_html": body_html,
                "sort_order": int(item.get("sort_order") or idx),
            }
        )
    cleaned.sort(key=lambda s: s["sort_order"])
    return cleaned


def _render_sections_html(sections: list[dict]) -> str:
    if not sections:
        return ""
    parts = []
    for s in sections:
        parts.append(f"<h3>{s['title']}</h3>{s['body_html']}")
    return "".join(parts)


def _assert_cms_editor(user: Optional[User]) -> None:
    if not user or not user.is_authenticated:
        raise PermissionDeniedDomainError("احراز هویت الزامی است.")
    if is_super_admin(user):
        return
    raise PermissionDeniedDomainError("مدیریت محتوای سامانه فقط برای مدیر کل مجاز است.")


def _assert_cms_approver(user: Optional[User]) -> None:
    if not user or not user.is_authenticated or not is_super_admin(user):
        raise PermissionDeniedDomainError("تأیید نهایی و انتشار عمومی در پرتال فقط توسط مدیر کل سامانه مجاز است.")


def _assert_legal_admin(user: Optional[User]) -> None:
    if not user or not user.is_authenticated or not is_super_admin(user):
        raise PermissionDeniedDomainError("مدیریت قوانین، حریم خصوصی و اسناد حقوقی فقط توسط مدیر کل مجاز است.")


# ==============================================================================
# Legal, Governance & Policy Document CMS
# ==============================================================================


def list_legal_documents(*, user: Optional[User] = None, doc_type: Optional[str] = None, published_only: bool = True):
    qs = LegalDocument.objects.prefetch_related("versions")
    if published_only:
        qs = qs.filter(status=LegalDocument.Status.PUBLISHED)
    elif not is_super_admin(user):
        raise PermissionDeniedDomainError("فقط مدیر کل مجاز به مشاهده پیش‌نویس‌های اسناد حقوقی است.")
    if doc_type:
        qs = qs.filter(doc_type=doc_type.upper())
    return list(qs.order_by("sort_order", "slug"))


def get_public_legal_document(*, slug: str, user: Optional[User] = None) -> tuple[LegalDocument, bool]:
    clean_slug = slug.strip().lower()
    doc = LegalDocument.objects.filter(slug=clean_slug, status=LegalDocument.Status.PUBLISHED).first()
    if not doc:
        raise NotFoundDomainError("سند حقوقی یا صفحه مقررات مورد نظر یافت نشد.")
    accepted = False
    if user and user.is_authenticated:
        accepted = LegalAcceptanceRecord.objects.filter(
            document=doc, version_number=doc.version_number, user=user
        ).exists()
    return doc, accepted


def get_legal_document_admin(*, user: User, doc_id: UUID) -> LegalDocument:
    _assert_legal_admin(user)
    doc = LegalDocument.objects.prefetch_related("versions__edited_by").filter(id=doc_id).first()
    if not doc:
        raise NotFoundDomainError("سند حقوقی یافت نشد.")
    return doc


@transaction.atomic
def upsert_legal_document(*, user: User, slug: Optional[str], data: dict) -> LegalDocument:
    _assert_legal_admin(user)
    clean_slug = (slug or data.get("slug") or "").strip().lower()
    if not clean_slug:
        raise ValidationDomainError("شناسه یکتا (slug) سند الزامی است.")

    sections = _normalize_legal_sections(data.get("sections_json")) if "sections_json" in data else None
    raw_body = str(data.get("body_html") or "")
    sanitized_body = sanitize_html(raw_body)
    if sections is not None and (sections or not sanitized_body):
        sanitized_body = _render_sections_html(sections) or sanitized_body
    existing = LegalDocument.objects.filter(slug=clean_slug).first()

    if existing is None:
        final_sections = sections or (
            [{"id": f"{clean_slug}-sec-1", "title": str(data["title_fa"]).strip(), "body_html": sanitized_body, "sort_order": 1}]
            if sanitized_body
            else []
        )
        doc = LegalDocument.objects.create(
            slug=clean_slug,
            doc_type=str(data.get("doc_type") or "LEGAL").upper(),
            title_fa=str(data["title_fa"]).strip(),
            title_en=str(data.get("title_en") or "").strip(),
            summary=str(data.get("summary") or "").strip(),
            body_html=sanitized_body,
            sections_json=final_sections,
            status=str(data.get("status") or LegalDocument.Status.DRAFT),
            version_number=1,
            requires_acceptance=bool(data.get("requires_acceptance", False)),
            effective_at=data.get("effective_at"),
            published_at=timezone.now() if data.get("status") == LegalDocument.Status.PUBLISHED else None,
            meta_title=str(data.get("meta_title") or data["title_fa"])[:160],
            meta_description=str(data.get("meta_description") or data.get("summary") or "")[:320],
            sort_order=int(data.get("sort_order", 100)),
            is_system_doc=bool(data.get("is_system_doc", False)),
            created_by=user,
            updated_by=user,
        )
        LegalDocumentVersion.objects.create(
            document=doc,
            version_number=1,
            title_fa=doc.title_fa,
            summary=doc.summary,
            body_html=doc.body_html,
            sections_json=doc.sections_json,
            change_note=str(data.get("change_note") or "ایجاد نسخه اولیه")[:240],
            edited_by=user,
            created_by=user,
        )
    else:
        doc = existing
        for f in ("title_fa", "title_en", "summary", "doc_type", "requires_acceptance", "effective_at", "meta_title", "meta_description", "sort_order"):
            if f in data and data[f] is not None:
                setattr(doc, f, data[f])
        new_status = str(data.get("status") or "").strip()
        if new_status and new_status in LegalDocument.Status.values and new_status != doc.status:
            doc.status = new_status
            if new_status == LegalDocument.Status.PUBLISHED:
                doc.published_at = doc.published_at or timezone.now()
                doc.effective_at = doc.effective_at or timezone.now()
        if sections is not None:
            doc.sections_json = sections
            if sections:
                doc.body_html = _render_sections_html(sections)
            elif "body_html" in data and data["body_html"] is not None:
                doc.body_html = sanitized_body
        elif "body_html" in data and data["body_html"] is not None:
            doc.body_html = sanitized_body
        doc.version_number += 1
        doc.updated_by = user
        doc.save()
        LegalDocumentVersion.objects.create(
            document=doc,
            version_number=doc.version_number,
            title_fa=doc.title_fa,
            summary=doc.summary,
            body_html=doc.body_html,
            sections_json=doc.sections_json or [],
            change_note=str(data.get("change_note") or f"ویرایش نسخه {doc.version_number}")[:240],
            edited_by=user,
            created_by=user,
        )

    record_audit_event(
        action="LEGAL_DOCUMENT_UPSERTED",
        resource_type="LegalDocument",
        resource_id=doc.slug,
        actor=user,
        after_state={"version": doc.version_number, "status": doc.status},
    )
    from apps.settings.services import invalidate_public_bootstrap_cache

    invalidate_public_bootstrap_cache()
    return doc


@transaction.atomic
def transition_legal_status(*, user: User, doc_id: UUID, to_status: str) -> LegalDocument:
    _assert_legal_admin(user)
    doc = LegalDocument.objects.filter(id=doc_id).first()
    if not doc:
        raise NotFoundDomainError("سند حقوقی یافت نشد.")
    if to_status not in LegalDocument.Status.values:
        raise ValidationDomainError("وضعیت انتخاب‌شده برای سند حقوقی نامعتبر است.")

    allowed = LEGAL_TRANSITIONS.get(doc.status, set())
    if doc.status != to_status and to_status not in allowed:
        raise ValidationDomainError(f"انتقال وضعیت سند حقوقی از {doc.status} به {to_status} مجاز نیست (سند منتشرشده فقط قابل بایگانی است).")

    prev = doc.status
    doc.status = to_status
    if to_status == LegalDocument.Status.PUBLISHED:
        doc.published_at = doc.published_at or timezone.now()
        doc.effective_at = doc.effective_at or timezone.now()
    doc.updated_by = user
    doc.save()

    record_audit_event(
        action="LEGAL_DOCUMENT_STATUS_CHANGED",
        resource_type="LegalDocument",
        resource_id=doc.slug,
        actor=user,
        before_state={"status": prev},
        after_state={"status": to_status},
    )
    from apps.settings.services import invalidate_public_bootstrap_cache

    invalidate_public_bootstrap_cache()
    return doc


@transaction.atomic
def restore_legal_version(*, user: User, doc_id: UUID, version_number: int) -> LegalDocument:
    _assert_legal_admin(user)
    doc = LegalDocument.objects.filter(id=doc_id).first()
    if not doc:
        raise NotFoundDomainError("سند حقوقی یافت نشد.")
    ver = LegalDocumentVersion.objects.filter(document=doc, version_number=version_number).first()
    if not ver:
        raise NotFoundDomainError("نسخه انتخاب‌شده یافت نشد.")

    doc.title_fa = ver.title_fa
    doc.summary = ver.summary
    doc.body_html = sanitize_html(ver.body_html)
    doc.sections_json = ver.sections_json or []
    doc.version_number += 1
    doc.updated_by = user
    doc.save()

    LegalDocumentVersion.objects.create(
        document=doc,
        version_number=doc.version_number,
        title_fa=doc.title_fa,
        summary=doc.summary,
        body_html=doc.body_html,
        sections_json=doc.sections_json or [],
        change_note=f"بازگردانی از نسخه {version_number}",
        edited_by=user,
        created_by=user,
    )
    record_audit_event(
        action="LEGAL_DOCUMENT_VERSION_RESTORED",
        resource_type="LegalDocument",
        resource_id=doc.slug,
        actor=user,
        after_state={"restored_from": version_number, "new_version": doc.version_number},
    )
    return doc


@transaction.atomic
def accept_legal_document(
    *, user: User, slug: str, ip_address: Optional[str] = None, user_agent: str = ""
) -> LegalAcceptanceRecord:
    doc = LegalDocument.objects.filter(slug=slug.strip().lower(), status=LegalDocument.Status.PUBLISHED).first()
    if not doc:
        raise NotFoundDomainError("سند حقوقی منتشرشده یافت نشد.")
    rec, created = LegalAcceptanceRecord.objects.get_or_create(
        document=doc,
        version_number=doc.version_number,
        user=user,
        defaults={
            "ip_address": ip_address,
            "user_agent": (user_agent or "")[:255],
            "created_by": user,
        },
    )
    if created:
        record_audit_event(
            action="LEGAL_DOCUMENT_ACCEPTED",
            resource_type="LegalDocument",
            resource_id=doc.slug,
            actor=user,
            ip_address=ip_address,
            after_state={"version_number": doc.version_number},
        )
    return rec


def list_legal_acceptances(*, user: User, doc_id: Optional[UUID] = None) -> list[LegalAcceptanceRecord]:
    _assert_legal_admin(user)
    qs = LegalAcceptanceRecord.objects.select_related("document", "user")
    if doc_id:
        qs = qs.filter(document_id=doc_id)
    return list(qs.order_by("-accepted_at")[:200])


# ==============================================================================
# Articles, Categories, Redirects, Inquiries, FAQs, Jobs
# ==============================================================================


def list_categories():
    return ContentCategory.objects.all()


@transaction.atomic
def create_category(*, user: User, name: str, slug: str, description: str = "", sort_order: int = 1) -> ContentCategory:
    _assert_cms_approver(user)
    clean_slug = slug.strip().lower()
    if ContentCategory.objects.filter(slug=clean_slug).exists():
        raise ConflictDomainError("شناسه دسته‌بندی تکراری است.")
    return ContentCategory.objects.create(
        name=name.strip(),
        slug=clean_slug,
        description=description.strip(),
        sort_order=sort_order,
        created_by=user,
    )


def list_public_articles(*, category_slug: Optional[str] = None, article_type: Optional[str] = None, q: Optional[str] = None):
    now = timezone.now()
    qs = (
        Article.objects.select_related("category", "author")
        .prefetch_related("tags")
        .filter(
            models.Q(status=Article.Status.PUBLISHED)
            | models.Q(status=Article.Status.SCHEDULED, scheduled_for__lte=now)
        )
    )
    if category_slug:
        qs = qs.filter(category__slug=category_slug)
    if article_type:
        qs = qs.filter(article_type=article_type)
    if q:
        qs = qs.filter(models.Q(title__icontains=q) | models.Q(summary__icontains=q) | models.Q(content_body__icontains=q))
    return qs.order_by("-published_at", "-created_at")


def get_public_article(*, slug: str) -> Article:
    art = list_public_articles().filter(slug=slug).first()
    if not art:
        raise NotFoundDomainError("مقاله یا خبر مورد نظر یافت نشد.")
    Article.objects.filter(id=art.id).update(view_count=models.F("view_count") + 1)
    return art


def list_cms_articles(*, user: User, status_filter: Optional[str] = None):
    _assert_cms_editor(user)
    qs = Article.objects.select_related("category", "author").prefetch_related("tags", "versions")
    if not is_super_admin(user):
        qs = qs.filter(models.Q(created_by=user) | models.Q(status=Article.Status.PUBLISHED))
    if status_filter:
        qs = qs.filter(status=status_filter)
    return qs.order_by("-updated_at")


@transaction.atomic
def create_article(*, user: User, data: dict) -> Article:
    _assert_cms_editor(user)
    clean_slug = data["slug"].strip().lower()
    if Article.objects.filter(slug=clean_slug).exists():
        raise ConflictDomainError("شناسه (slug) مقاله تکراری است.")

    author, _ = AuthorProfile.objects.get_or_create(
        user=user, defaults={"display_name": user.full_name, "role_title": "نویسنده تحریریه"}
    )
    category = None
    if data.get("category_id"):
        category = ContentCategory.objects.filter(id=data["category_id"]).first()

    body = sanitize_html(data["content_body"].strip())
    reading_mins = max(1, len(body.split()) // 160)

    art = Article.objects.create(
        agency_id=data.get("agency_id"),
        title=data["title"].strip(),
        slug=clean_slug,
        article_type=data.get("article_type", Article.ArticleType.ARTICLE),
        category=category,
        author=author,
        summary=data.get("summary", "").strip(),
        content_body=body,
        cover_image_url=data.get("cover_image_url", "").strip(),
        status=Article.Status.DRAFT,
        language=str(data.get("language") or "fa").strip()[:12],
        tone=str(data.get("tone") or "PROFESSIONAL").strip()[:40],
        target_audience=str(data.get("target_audience") or "").strip()[:120],
        keywords=list(data.get("keywords") or []),
        ai_generated=bool(data.get("ai_generated", False)),
        ai_model=str(data.get("ai_model") or "")[:64],
        ai_tokens_used=int(data.get("ai_tokens_used") or 0),
        meta_title=data.get("meta_title", "").strip() or data["title"].strip()[:160],
        meta_description=data.get("meta_description", "").strip() or data.get("summary", "")[:300],
        canonical_url=data.get("canonical_url", "").strip(),
        reading_time_minutes=reading_mins,
        created_by=user,
    )
    for tag_name in data.get("tags") or []:
        t_slug = str(tag_name).strip().lower().replace(" ", "-")
        if t_slug:
            tag, _ = Tag.objects.get_or_create(slug=t_slug, defaults={"name": str(tag_name).strip()})
            art.tags.add(tag)

    ContentVersion.objects.create(
        article=art,
        version_number=1,
        title=art.title,
        content_body=art.content_body,
        edited_by=user,
        change_note=data.get("change_note") or "ایجاد پیش‌نویس اولیه",
        created_by=user,
    )
    record_audit_event(action="CMS_ARTICLE_CREATED", resource_type="Article", resource_id=str(art.id), actor=user)
    return art


@transaction.atomic
def update_article(*, user: User, article_id: UUID, data: dict) -> Article:
    _assert_cms_editor(user)
    art = Article.objects.filter(id=article_id).first()
    if not art:
        raise NotFoundDomainError("مقاله یافت نشد.")
    if not is_super_admin(user) and art.created_by_id != user.id:
        raise PermissionDeniedDomainError("شما فقط مجاز به ویرایش مقالات خود هستید.")

    for field in (
        "title",
        "summary",
        "cover_image_url",
        "meta_title",
        "meta_description",
        "canonical_url",
        "article_type",
        "language",
        "tone",
        "target_audience",
        "keywords",
    ):
        if field in data and data[field] is not None:
            setattr(art, field, data[field])
    if "content_body" in data and data["content_body"] is not None:
        art.content_body = sanitize_html(data["content_body"])
        art.reading_time_minutes = max(1, len(art.content_body.split()) // 160)
    if "category_id" in data and data["category_id"] is not None:
        art.category_id = data["category_id"]
    art.updated_by = user
    art.save()

    next_ver = (art.versions.aggregate(m=models.Max("version_number"))["m"] or 0) + 1
    ContentVersion.objects.create(
        article=art,
        version_number=next_ver,
        title=art.title,
        content_body=art.content_body,
        edited_by=user,
        change_note=data.get("change_note", "به‌روزرسانی محتوا"),
        created_by=user,
    )
    return art


@transaction.atomic
def delete_article(*, user: User, article_id: UUID) -> dict:
    _assert_cms_editor(user)
    art = Article.objects.filter(id=article_id).first()
    if not art:
        raise NotFoundDomainError("مقاله یا محتوا یافت نشد.")
    if not is_super_admin(user):
        if art.created_by_id != user.id:
            raise PermissionDeniedDomainError("شما فقط مجاز به حذف پیش‌نویس‌های خود هستید.")
        if art.status == Article.Status.PUBLISHED:
            raise PermissionDeniedDomainError("حذف محتوای منتشرشده فقط توسط مدیر کل مجاز است.")
    title_snap = art.title
    art.delete()
    record_audit_event(
        action="CMS_ARTICLE_DELETED",
        resource_type="Article",
        resource_id=str(article_id),
        actor=user,
        after_state={"title": title_snap},
    )
    return {"deleted": True, "id": str(article_id)}


@transaction.atomic
def transition_article_status(*, user: User, article_id: UUID, to_status: str, scheduled_for=None) -> Article:
    art = Article.objects.filter(id=article_id).first()
    if not art:
        raise NotFoundDomainError("مقاله یافت نشد.")

    if to_status in (Article.Status.APPROVED, Article.Status.PUBLISHED, Article.Status.SCHEDULED, Article.Status.ARCHIVED):
        _assert_cms_approver(user)
    else:
        _assert_cms_editor(user)

    allowed = ARTICLE_TRANSITIONS.get(art.status, set())
    if to_status not in allowed and art.status != to_status:
        raise ValidationDomainError(f"تغییر وضعیت از {art.status} به {to_status} مجاز نیست.")

    prev = art.status
    art.status = to_status
    if to_status == Article.Status.PUBLISHED and not art.published_at:
        art.published_at = timezone.now()
    if to_status == Article.Status.SCHEDULED:
        if not scheduled_for:
            raise ValidationDomainError("زمان انتشار برنامه‌ریزی‌شده الزامی است.")
        art.scheduled_for = scheduled_for
    art.updated_by = user
    art.save()

    record_audit_event(
        action="CMS_ARTICLE_STATUS_CHANGED",
        resource_type="Article",
        resource_id=str(art.id),
        actor=user,
        before_state={"status": prev},
        after_state={"status": to_status},
    )
    return art


def list_redirects(*, active_only: bool = False):
    qs = RedirectRule.objects.all()
    if active_only:
        qs = qs.filter(is_active=True)
    return qs


@transaction.atomic
def create_redirect(*, user: User, from_path: str, to_path: str, status_code: int = 301) -> RedirectRule:
    _assert_cms_approver(user)
    if status_code not in (301, 302):
        raise ValidationDomainError("کد ریدایرکت باید ۳۰۱ یا ۳۰۲ باشد.")
    clean_from = "/" + from_path.strip().lstrip("/")
    clean_to = to_path.strip()
    if RedirectRule.objects.filter(from_path=clean_from).exists():
        raise ConflictDomainError("مسیر مبدأ ریدایرکت تکراری است.")
    return RedirectRule.objects.create(
        from_path=clean_from, to_path=clean_to, status_code=status_code, created_by=user
    )


@transaction.atomic
def submit_contact_inquiry(*, data: dict) -> ContactInquiry:
    code = f"REQ-1405-{secrets.randbelow(9000) + 1000}"
    while ContactInquiry.objects.filter(tracking_code=code).exists():
        code = f"REQ-1405-{secrets.randbelow(9000) + 1000}"
    return ContactInquiry.objects.create(
        tracking_code=code,
        full_name=data["full_name"].strip(),
        phone_number=data["phone_number"].strip(),
        email=data.get("email", "").strip(),
        inquiry_type=data.get("inquiry_type", ContactInquiry.InquiryType.GENERAL),
        subject=data["subject"].strip(),
        message=data["message"].strip(),
    )


def track_contact_inquiry(*, tracking_code: str, phone_number: str) -> ContactInquiry:
    inq = ContactInquiry.objects.filter(
        tracking_code=tracking_code.strip().upper(), phone_number=phone_number.strip()
    ).first()
    if not inq:
        raise NotFoundDomainError("درخواستی با این کد رهگیری و شماره تماس یافت نشد.")
    return inq


def list_contact_inquiries(*, user: User):
    _assert_cms_approver(user)
    return ContactInquiry.objects.all()


@transaction.atomic
def update_contact_inquiry(*, user: User, inquiry_id: UUID, status_value: str, staff_response: str = "") -> ContactInquiry:
    _assert_cms_approver(user)
    inq = ContactInquiry.objects.filter(id=inquiry_id).first()
    if not inq:
        raise NotFoundDomainError("درخواست یافت نشد.")
    inq.status = status_value
    if staff_response:
        inq.staff_response = staff_response.strip()
    inq.updated_by = user
    inq.save()
    return inq


@transaction.atomic
def submit_cooperation_request(*, data: dict) -> AgencyCooperationRequest:
    code = f"COOP-1405-{secrets.randbelow(9000) + 1000}"
    while AgencyCooperationRequest.objects.filter(tracking_code=code).exists():
        code = f"COOP-1405-{secrets.randbelow(9000) + 1000}"
    return AgencyCooperationRequest.objects.create(
        tracking_code=code,
        agency_name=data["agency_name"].strip(),
        city=data["city"].strip(),
        manager_name=data["manager_name"].strip(),
        manager_phone=data["manager_phone"].strip(),
        email=data.get("email", "").strip(),
        agents_count=int(data.get("agents_count", 5)),
        license_number=data.get("license_number", "").strip(),
        notes=data.get("notes", "").strip(),
    )


def list_cooperation_requests(*, user: User):
    _assert_cms_approver(user)
    return AgencyCooperationRequest.objects.all()


@transaction.atomic
def review_cooperation_request(*, user: User, request_id: UUID, decision: str) -> AgencyCooperationRequest:
    _assert_cms_approver(user)
    req = AgencyCooperationRequest.objects.filter(id=request_id).first()
    if not req:
        raise NotFoundDomainError("درخواست همکاری آژانس یافت نشد.")
    if decision not in (AgencyCooperationRequest.Status.APPROVED, AgencyCooperationRequest.Status.REJECTED, AgencyCooperationRequest.Status.UNDER_REVIEW):
        raise ValidationDomainError("تصمیم نامعتبر است.")

    if decision == AgencyCooperationRequest.Status.APPROVED and not req.approved_agency_id:
        manager = User.objects.filter(phone_number=req.manager_phone).first()
        if not manager:
            parts = req.manager_name.split(" ", 1)
            manager = register_user(
                phone_number=req.manager_phone,
                password=f"Bonyan@{secrets.randbelow(9000) + 1000}",
                first_name=parts[0],
                last_name=parts[1] if len(parts) > 1 else "",
                email=req.email or None,
            )
            manager.platform_role = User.PlatformRole.AGENCY_USER
            manager.save(update_fields=["platform_role"])
        slug_candidate = f"agency-{req.tracking_code.lower()}"
        agency = create_agency(
            owner=manager,
            name=req.agency_name,
            slug=slug_candidate,
            registration_number=req.license_number,
            phone=req.manager_phone,
            email=req.email,
            description=f"آژانس همکار در شهر {req.city}",
        )
        agency.status = "ACTIVE"
        agency.save(update_fields=["status", "updated_at"])
        req.approved_agency_id = agency.id

    req.status = decision
    req.updated_by = user
    req.save()
    record_audit_event(
        action="AGENCY_COOPERATION_REVIEWED",
        resource_type="AgencyCooperationRequest",
        resource_id=str(req.id),
        actor=user,
        after_state={"status": decision, "approved_agency_id": str(req.approved_agency_id) if req.approved_agency_id else None},
    )
    return req


def list_public_jobs():
    return JobOpening.objects.filter(is_active=True)


def list_public_faqs():
    return FaqItem.objects.filter(is_active=True)

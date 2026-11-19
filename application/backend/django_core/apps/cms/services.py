# Path: backend/django_core/apps/cms/services.py

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
from .models import (
    AgencyCooperationRequest,
    Article,
    AuthorProfile,
    ContactInquiry,
    ContentCategory,
    ContentVersion,
    FaqItem,
    JobOpening,
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


def _assert_cms_editor(user: Optional[User]) -> None:
    if not user or not user.is_authenticated:
        raise PermissionDeniedDomainError("احراز هویت الزامی است.")
    if is_super_admin(user):
        return
    if user.memberships.filter(status="ACTIVE", role__code="AGENCY_MANAGER").exists():
        return
    raise PermissionDeniedDomainError("مدیریت محتوای CMS فقط برای ادمین پلتفرم یا مدیر آژانس مجاز است.")


def _assert_cms_approver(user: Optional[User]) -> None:
    if not user or not user.is_authenticated or not is_super_admin(user):
        raise PermissionDeniedDomainError("تأیید نهایی و انتشار عمومی در پرتال فقط توسط مدیر کل سامانه مجاز است.")


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

    body = data["content_body"].strip()
    reading_mins = max(1, len(body.split()) // 160)

    art = Article.objects.create(
        title=data["title"].strip(),
        slug=clean_slug,
        article_type=data.get("article_type", Article.ArticleType.ARTICLE),
        category=category,
        author=author,
        summary=data.get("summary", "").strip(),
        content_body=body,
        cover_image_url=data.get("cover_image_url", "").strip(),
        status=Article.Status.DRAFT,
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
        change_note="ایجاد پیش‌نویس اولیه",
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

    for field in ("title", "summary", "content_body", "cover_image_url", "meta_title", "meta_description", "canonical_url", "article_type"):
        if field in data and data[field] is not None:
            setattr(art, field, data[field])
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

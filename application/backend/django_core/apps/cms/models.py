from django.conf import settings
from django.db import models
from common.models import BaseModel


class ContentCategory(BaseModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True, default="")
    sort_order = models.PositiveSmallIntegerField(default=1)

    class Meta:
        db_table = "cms_category"
        ordering = ["sort_order", "name"]


class Tag(BaseModel):
    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=80, unique=True)

    class Meta:
        db_table = "cms_tag"
        ordering = ["name"]


class AuthorProfile(BaseModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="author_profile"
    )
    display_name = models.CharField(max_length=120)
    role_title = models.CharField(max_length=120, blank=True, default="تحریریه تخصصی بنیان ملک")
    bio = models.TextField(blank=True, default="")

    class Meta:
        db_table = "cms_author_profile"


class Article(BaseModel):
    class ArticleType(models.TextChoices):
        ARTICLE = "ARTICLE", "Article / Guide"
        NEWS = "NEWS", "News / Market Report"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        REVIEW = "REVIEW", "In Review"
        APPROVED = "APPROVED", "Approved"
        PUBLISHED = "PUBLISHED", "Published"
        SCHEDULED = "SCHEDULED", "Scheduled"
        ARCHIVED = "ARCHIVED", "Archived"

    title = models.CharField(max_length=240)
    slug = models.SlugField(max_length=240, unique=True)
    article_type = models.CharField(max_length=16, choices=ArticleType.choices, default=ArticleType.ARTICLE)
    category = models.ForeignKey(ContentCategory, null=True, blank=True, on_delete=models.SET_NULL, related_name="articles")
    author = models.ForeignKey(AuthorProfile, null=True, blank=True, on_delete=models.SET_NULL, related_name="articles")
    summary = models.TextField(blank=True, default="")
    content_body = models.TextField()
    cover_image_url = models.CharField(max_length=500, blank=True, default="")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT, db_index=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    meta_title = models.CharField(max_length=160, blank=True, default="")
    meta_description = models.CharField(max_length=320, blank=True, default="")
    canonical_url = models.CharField(max_length=300, blank=True, default="")
    reading_time_minutes = models.PositiveSmallIntegerField(default=4)
    view_count = models.PositiveIntegerField(default=0)
    tags = models.ManyToManyField(Tag, blank=True, related_name="articles")

    class Meta:
        db_table = "cms_article"
        ordering = ["-published_at", "-created_at"]


class ContentVersion(BaseModel):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="versions")
    version_number = models.PositiveIntegerField()
    title = models.CharField(max_length=240)
    content_body = models.TextField()
    edited_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    change_note = models.CharField(max_length=240, blank=True, default="")

    class Meta:
        db_table = "cms_content_version"
        unique_together = ("article", "version_number")
        ordering = ["-version_number"]


class RedirectRule(BaseModel):
    from_path = models.CharField(max_length=300, unique=True)
    to_path = models.CharField(max_length=300)
    status_code = models.PositiveSmallIntegerField(default=301)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "cms_redirect_rule"
        ordering = ["from_path"]


class ContactInquiry(BaseModel):
    class InquiryType(models.TextChoices):
        BUY_CONSULT = "BUY_CONSULT", "Buy Consultation"
        SELL_PROPERTY = "SELL_PROPERTY", "Sell / List Property"
        ENTERPRISE_DEMO = "ENTERPRISE_DEMO", "Enterprise Demo"
        GENERAL = "GENERAL", "General Inquiry"

    class Status(models.TextChoices):
        NEW = "NEW", "New"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        RESOLVED = "RESOLVED", "Resolved"
        CLOSED = "CLOSED", "Closed"

    tracking_code = models.CharField(max_length=32, unique=True, db_index=True)
    full_name = models.CharField(max_length=140)
    phone_number = models.CharField(max_length=24, db_index=True)
    email = models.EmailField(blank=True, default="")
    inquiry_type = models.CharField(max_length=24, choices=InquiryType.choices, default=InquiryType.GENERAL)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW, db_index=True)
    staff_response = models.TextField(blank=True, default="")

    class Meta:
        db_table = "cms_contact_inquiry"
        ordering = ["-created_at"]


class AgencyCooperationRequest(BaseModel):
    class Status(models.TextChoices):
        NEW = "NEW", "New"
        UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    tracking_code = models.CharField(max_length=32, unique=True, db_index=True)
    agency_name = models.CharField(max_length=160)
    city = models.CharField(max_length=100)
    manager_name = models.CharField(max_length=140)
    manager_phone = models.CharField(max_length=24)
    email = models.EmailField(blank=True, default="")
    agents_count = models.PositiveIntegerField(default=5)
    license_number = models.CharField(max_length=80, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW, db_index=True)
    approved_agency_id = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = "cms_agency_cooperation_request"
        ordering = ["-created_at"]


class JobOpening(BaseModel):
    title = models.CharField(max_length=160)
    department = models.CharField(max_length=100)
    location = models.CharField(max_length=100, default="تهران / هیبرید")
    employment_type = models.CharField(max_length=60, default="تمام‌وقت")
    description = models.TextField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "cms_job_opening"
        ordering = ["-created_at"]


class FaqItem(BaseModel):
    category = models.CharField(max_length=100, default="عمومی")
    question = models.CharField(max_length=320)
    answer = models.TextField()
    sort_order = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "cms_faq_item"
        ordering = ["sort_order", "created_at"]

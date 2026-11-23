from django.conf import settings
from django.db import models
from django.utils import timezone
from common.models import BaseModel
from .tour import Scene, VirtualTour


class CaptureSession(BaseModel):
    class Status(models.TextChoices):
        CREATED = "created", "ایجادشده"
        CAPTURING = "capturing", "در حال عکاسی"
        VALIDATING = "validating", "در حال بررسی کیفیت"
        NEEDS_RETAKE = "needs_retake", "نیاز به عکاسی مجدد"
        READY = "ready", "آماده پردازش"
        COMPLETED = "completed", "تکمیل‌شده"
        CANCELLED = "cancelled", "لغوشده"

    tour = models.ForeignKey(
        VirtualTour,
        on_delete=models.CASCADE,
        related_name="capture_sessions",
    )
    scene = models.ForeignKey(
        Scene,
        on_delete=models.CASCADE,
        related_name="capture_sessions",
    )
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.CREATED,
        db_index=True,
    )
    device_info = models.JSONField(default=dict, blank=True)
    capture_config = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "virtual_tours_capture_session"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["scene", "status"])]


class CaptureImage(BaseModel):
    class Status(models.TextChoices):
        UPLOADED = "uploaded", "بارگذاری‌شده"
        PASSED = "passed", "تأیید کیفیت"
        WARNING = "warning", "هشدار کیفیت"
        REJECTED = "rejected", "ردشده"
        REPLACED = "replaced", "جایگزین‌شده"

    session = models.ForeignKey(
        CaptureSession,
        on_delete=models.CASCADE,
        related_name="images",
    )
    scene = models.ForeignKey(
        Scene,
        on_delete=models.CASCADE,
        related_name="capture_images",
    )
    storage_key = models.CharField(max_length=500)
    filename = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=80, default="image/jpeg")
    sequence = models.PositiveSmallIntegerField()
    size_bytes = models.PositiveIntegerField(default=0)
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UPLOADED,
        db_index=True,
    )
    analysis = models.JSONField(default=dict, blank=True)
    yaw = models.FloatField(default=0.0)
    pitch = models.FloatField(default=0.0)
    captured_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "virtual_tours_capture_image"
        ordering = ["sequence", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "sequence"],
                name="uq_capture_image_session_sequence",
            )
        ]


class CaptureGuideStep(BaseModel):
    class State(models.TextChoices):
        PENDING = "pending", "در انتظار"
        CAPTURED = "captured", "ثبت‌شده"
        PASSED = "passed", "تأییدشده"
        NEEDS_RETAKE = "needs_retake", "نیاز به تکرار"
        SKIPPED = "skipped", "ردشده"

    session = models.ForeignKey(
        CaptureSession,
        on_delete=models.CASCADE,
        related_name="guide_steps",
    )
    sequence = models.PositiveSmallIntegerField()
    yaw = models.FloatField(default=0.0)
    pitch = models.FloatField(default=0.0)
    label = models.CharField(max_length=80)
    required = models.BooleanField(default=True)
    expected_overlap_percent = models.FloatField(default=35.0)
    state = models.CharField(
        max_length=20,
        choices=State.choices,
        default=State.PENDING,
    )
    image = models.ForeignKey(
        CaptureImage,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="guide_steps",
    )
    guidance = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "virtual_tours_capture_guide_step"
        ordering = ["sequence"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "sequence"],
                name="uq_capture_step_session_sequence",
            )
        ]


class PanoramaVersion(BaseModel):
    class State(models.TextChoices):
        PROCESSING = "processing", "در حال پردازش"
        REVIEW = "review", "نیازمند بازبینی"
        APPROVED = "approved", "تأییدشده"
        REJECTED = "rejected", "ردشده"
        SUPERSEDED = "superseded", "نسخه جایگزین‌شده"
        FAILED = "failed", "ناموفق"

    scene = models.ForeignKey(
        Scene,
        on_delete=models.CASCADE,
        related_name="panorama_versions",
    )
    capture_session = models.ForeignKey(
        CaptureSession,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="panorama_versions",
    )
    version = models.PositiveIntegerField(default=1)
    state = models.CharField(
        max_length=20,
        choices=State.choices,
        default=State.PROCESSING,
        db_index=True,
    )
    storage_key = models.CharField(max_length=500, blank=True, default="")
    thumbnail_key = models.CharField(max_length=500, blank=True, default="")
    projection = models.CharField(max_length=32, default="equirectangular")
    width_px = models.PositiveIntegerField(default=0)
    height_px = models.PositiveIntegerField(default=0)
    source_image_count = models.PositiveIntegerField(default=0)
    engine = models.CharField(max_length=64, default="opencv_stitcher")
    quality_report = models.JSONField(default=dict, blank=True)
    is_current = models.BooleanField(default=False, db_index=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_panoramas",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default="")

    class Meta:
        db_table = "virtual_tours_panorama_version"
        ordering = ["-version", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["scene", "version"],
                name="uq_panorama_scene_version",
            )
        ]


class SceneLink(BaseModel):
    tour = models.ForeignKey(
        VirtualTour,
        on_delete=models.CASCADE,
        related_name="links",
    )
    source_scene = models.ForeignKey(
        Scene,
        on_delete=models.CASCADE,
        related_name="outgoing_links",
    )
    target_scene = models.ForeignKey(
        Scene,
        on_delete=models.CASCADE,
        related_name="incoming_links",
    )
    yaw = models.FloatField(default=0.0)
    pitch = models.FloatField(default=-5.0)
    title = models.CharField(max_length=120, blank=True, default="")
    bidirectional = models.BooleanField(default=True)
    reverse_yaw = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = "virtual_tours_scene_link"
        ordering = ["created_at"]
        indexes = [models.Index(fields=["tour", "source_scene"])]


class Hotspot(BaseModel):
    class Kind(models.TextChoices):
        INFO = "info", "توضیحات فضا"
        NAVIGATION = "navigation", "انتقال به اتاق"
        FEATURE = "feature", "ویژگی ملک"
        FURNITURE = "furniture", "مبلمان و تجهیزات"
        MATERIAL = "material", "معرفی متریال"
        MEDIA = "media", "تصویر تکمیلی"
        MEASUREMENT = "measurement", "اندازه‌گیری"

    scene = models.ForeignKey(
        Scene,
        on_delete=models.CASCADE,
        related_name="hotspots",
    )
    kind = models.CharField(max_length=24, choices=Kind.choices, default=Kind.INFO)
    title = models.CharField(max_length=140)
    body = models.TextField(blank=True, default="")
    yaw = models.FloatField(default=0.0)
    pitch = models.FloatField(default=0.0)
    target_scene = models.ForeignKey(
        Scene,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="hotspot_targets",
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "virtual_tours_hotspot"
        ordering = ["created_at"]
        indexes = [models.Index(fields=["scene", "kind"])]


class ProcessingJob(BaseModel):
    class JobType(models.TextChoices):
        PANORAMA_STITCH = "panorama_stitch", "دوخت پانوراما"
        PANORAMA_REPROCESS = "panorama_reprocess", "پردازش مجدد پانوراما"
        MODEL_BUILD = "model_build", "ساخت مدل سه‌بعدی"
        SCAN_PROCESS = "scan_process", "پردازش فایل اسکن"
        QUALITY_AUDIT = "quality_audit", "ممیزی کیفیت تور"

    class State(models.TextChoices):
        QUEUED = "queued", "در صف"
        RUNNING = "running", "در حال اجرا"
        SUCCEEDED = "succeeded", "تکمیل‌شده"
        FAILED = "failed", "ناموفق"
        CANCELLED = "cancelled", "لغوشده"

    tour = models.ForeignKey(
        VirtualTour,
        on_delete=models.CASCADE,
        related_name="processing_jobs",
    )
    scene = models.ForeignKey(
        Scene,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="processing_jobs",
    )
    job_type = models.CharField(max_length=32, choices=JobType.choices, db_index=True)
    state = models.CharField(max_length=20, choices=State.choices, default=State.QUEUED, db_index=True)
    progress = models.PositiveSmallIntegerField(default=0)
    current_step = models.CharField(max_length=120, blank=True, default="")
    celery_task_id = models.CharField(max_length=128, blank=True, default="")
    idempotency_key = models.CharField(max_length=128, blank=True, default="", db_index=True)
    input_params = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True, default="")
    result = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    retry_count = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "virtual_tours_processing_job"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["tour", "state", "job_type"])]

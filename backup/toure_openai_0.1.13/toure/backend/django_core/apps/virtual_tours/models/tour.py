from decimal import Decimal
import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone
from common.models import BaseModel, TenantScopedModel


class VirtualTour(TenantScopedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "پیش‌نویس"
        CAPTURING = "capturing", "در حال عکاسی"
        PROCESSING = "processing", "در حال پردازش"
        REVIEW = "review", "نیازمند بازبینی"
        EDITING = "editing", "در حال ویرایش"
        READY = "ready", "آماده انتشار"
        PUBLISHED = "published", "منتشرشده"
        ARCHIVED = "archived", "آرشیوشده"
        FAILED = "failed", "دارای خطا"

    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.CASCADE,
        related_name="virtual_tours",
    )
    branch = models.ForeignKey(
        "branches.Branch",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="virtual_tours",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    settings_override = models.JSONField(default=dict, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "virtual_tours_tour"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["property"],
                condition=~Q(status="archived"),
                name="uq_active_virtual_tour_per_property",
            )
        ]
        indexes = [
            models.Index(fields=["agency", "status"]),
            models.Index(fields=["property", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.property_id})"


class Floor(BaseModel):
    tour = models.ForeignKey(
        VirtualTour,
        on_delete=models.CASCADE,
        related_name="floors",
    )
    title = models.CharField(max_length=120)
    order = models.PositiveSmallIntegerField(default=0)
    elevation_m = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    description = models.TextField(blank=True, default="")

    class Meta:
        db_table = "virtual_tours_floor"
        ordering = ["order", "created_at"]
        indexes = [models.Index(fields=["tour", "order"])]

    def __str__(self) -> str:
        return f"{self.title} - {self.tour_id}"


class Scene(BaseModel):
    DEFAULT_ROOM_TYPES = [
        ("living_room", "پذیرایی"),
        ("sitting_room", "نشیمن"),
        ("bedroom", "اتاق خواب"),
        ("kitchen", "آشپزخانه"),
        ("bathroom", "حمام"),
        ("restroom", "سرویس بهداشتی"),
        ("dining_room", "غذاخوری"),
        ("hallway", "راهرو"),
        ("balcony", "بالکن"),
        ("terrace", "تراس"),
        ("yard", "حیاط"),
        ("parking", "پارکینگ"),
        ("storage", "انباری"),
        ("office", "دفتر کار"),
        ("other", "سایر فضاها"),
    ]

    tour = models.ForeignKey(
        VirtualTour,
        on_delete=models.CASCADE,
        related_name="scenes",
    )
    floor = models.ForeignKey(
        Floor,
        on_delete=models.CASCADE,
        related_name="scenes",
    )
    title = models.CharField(max_length=140)
    room_type = models.CharField(max_length=64, default="living_room")
    description = models.TextField(blank=True, default="")
    order = models.PositiveSmallIntegerField(default=0)
    is_start_scene = models.BooleanField(default=False)
    active = models.BooleanField(default=True, db_index=True)
    initial_yaw = models.FloatField(default=0.0)
    initial_pitch = models.FloatField(default=0.0)
    thumbnail_storage_key = models.CharField(max_length=500, blank=True, default="")
    width_m = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    length_m = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    height_m = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    polygon_json = models.JSONField(default=list, blank=True)
    geometry_source = models.CharField(max_length=32, default="none")

    class Meta:
        db_table = "virtual_tours_scene"
        ordering = ["floor__order", "order", "created_at"]
        indexes = [models.Index(fields=["tour", "floor", "active", "order"])]

    def __str__(self) -> str:
        return f"{self.title} ({self.room_type})"


class TourPublication(BaseModel):
    tour = models.ForeignKey(
        VirtualTour,
        on_delete=models.CASCADE,
        related_name="publications",
    )
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True, db_index=True)
    public_slug = models.CharField(
        max_length=120,
        unique=True,
        default="",
    )
    snapshot_json = models.JSONField(default=dict, blank=True)
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="published_virtual_tours",
    )
    published_at = models.DateTimeField(default=timezone.now)
    unpublished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "virtual_tours_publication"
        ordering = ["-version", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["tour", "version"], name="uq_tour_publication_version")
        ]

    def save(self, *args, **kwargs):
        if not self.public_slug:
            self.public_slug = f"vt-{uuid.uuid4().hex[:12]}"
        super().save(*args, **kwargs)


class TourQualityReport(BaseModel):
    tour = models.ForeignKey(
        VirtualTour,
        on_delete=models.CASCADE,
        related_name="quality_reports",
    )
    report_data = models.JSONField(default=dict, blank=True)
    is_ready_to_publish = models.BooleanField(default=False)
    blocking_issues_count = models.PositiveSmallIntegerField(default=0)
    warning_issues_count = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "virtual_tours_quality_report"
        ordering = ["-created_at"]

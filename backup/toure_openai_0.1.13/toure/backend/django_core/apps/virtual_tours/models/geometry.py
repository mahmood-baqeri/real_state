from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone
from common.models import BaseModel
from .tour import Floor, Scene, VirtualTour


class FloorPlanAsset(BaseModel):
    tour = models.ForeignKey(
        VirtualTour,
        on_delete=models.CASCADE,
        related_name="floorplans",
    )
    floor = models.ForeignKey(
        Floor,
        on_delete=models.CASCADE,
        related_name="floorplans",
    )
    file_type = models.CharField(max_length=16, default="png")
    storage_key = models.CharField(max_length=500)
    preview_storage_key = models.CharField(max_length=500, blank=True, default="")
    filename = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=80, default="image/png")
    size_bytes = models.PositiveIntegerField(default=0)
    width_px = models.PositiveIntegerField(default=0)
    height_px = models.PositiveIntegerField(default=0)
    scale_m_per_px = models.FloatField(null=True, blank=True)
    calibration_data = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "virtual_tours_floorplan_asset"
        ordering = ["floor__order", "-created_at"]
        indexes = [models.Index(fields=["tour", "floor", "is_active"])]


class RoomGeometry(BaseModel):
    tour = models.ForeignKey(
        VirtualTour,
        on_delete=models.CASCADE,
        related_name="room_geometries",
    )
    floor = models.ForeignKey(
        Floor,
        on_delete=models.CASCADE,
        related_name="room_geometries",
    )
    scene = models.ForeignKey(
        Scene,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="room_geometries",
    )
    floorplan = models.ForeignKey(
        FloorPlanAsset,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="rooms",
    )
    label = models.CharField(max_length=140)
    room_type = models.CharField(max_length=64, default="living_room")
    polygon_points = models.JSONField(default=list, blank=True)
    area_sqm = models.DecimalField(max_digits=9, decimal_places=2, default=Decimal("0.00"))
    perimeter_m = models.DecimalField(max_digits=9, decimal_places=2, default=Decimal("0.00"))
    height_m = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("2.90"))
    source = models.CharField(max_length=32, default="floorplan_2d")
    color_hex = models.CharField(max_length=16, default="#0F766E")

    class Meta:
        db_table = "virtual_tours_room_geometry"
        ordering = ["floor__order", "created_at"]
        indexes = [models.Index(fields=["tour", "floor"])]


class WallSegment(BaseModel):
    tour = models.ForeignKey(
        VirtualTour,
        on_delete=models.CASCADE,
        related_name="wall_segments",
    )
    floor = models.ForeignKey(
        Floor,
        on_delete=models.CASCADE,
        related_name="wall_segments",
    )
    floorplan = models.ForeignKey(
        FloorPlanAsset,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="wall_segments",
    )
    start_x = models.FloatField()
    start_y = models.FloatField()
    end_x = models.FloatField()
    end_y = models.FloatField()
    thickness_m = models.FloatField(default=0.18)
    height_m = models.FloatField(default=2.90)
    is_exterior = models.BooleanField(default=False)

    class Meta:
        db_table = "virtual_tours_wall_segment"
        ordering = ["floor__order", "created_at"]
        indexes = [models.Index(fields=["tour", "floor"])]


class WallOpening(BaseModel):
    class Kind(models.TextChoices):
        DOOR = "door", "درب"
        WINDOW = "window", "پنجره"
        ARCH = "arch", "طاق یا قوس"
        BALCONY = "balcony", "درب بالکن"

    wall = models.ForeignKey(
        WallSegment,
        on_delete=models.CASCADE,
        related_name="openings",
    )
    kind = models.CharField(max_length=24, choices=Kind.choices, default=Kind.DOOR)
    offset_ratio = models.FloatField(default=0.5)
    width_m = models.FloatField(default=0.95)
    height_m = models.FloatField(default=2.10)
    sill_height_m = models.FloatField(default=0.0)

    class Meta:
        db_table = "virtual_tours_wall_opening"
        ordering = ["offset_ratio", "created_at"]


class RoomMeasurement(BaseModel):
    room = models.ForeignKey(
        RoomGeometry,
        on_delete=models.CASCADE,
        related_name="measurements",
    )
    label = models.CharField(max_length=120)
    start_point = models.JSONField(default=list, blank=True)
    end_point = models.JSONField(default=list, blank=True)
    distance_m = models.DecimalField(max_digits=8, decimal_places=3, default=Decimal("0.000"))
    source = models.CharField(max_length=32, default="calibrated_floorplan")

    class Meta:
        db_table = "virtual_tours_room_measurement"
        ordering = ["created_at"]


class BuildingGeometry(BaseModel):
    tour = models.OneToOneField(
        VirtualTour,
        on_delete=models.CASCADE,
        related_name="building_geometry",
    )
    default_wall_height_m = models.FloatField(default=2.90)
    default_wall_thickness_m = models.FloatField(default=0.18)
    slab_thickness_m = models.FloatField(default=0.22)
    footprint_bounds = models.JSONField(default=dict, blank=True)
    total_area_sqm = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    geometry_source = models.CharField(max_length=48, default="floorplan_2d_extrusion")

    class Meta:
        db_table = "virtual_tours_building_geometry"


class GeneratedModelAsset(BaseModel):
    class State(models.TextChoices):
        PROCESSING = "processing", "در حال ساخت"
        READY = "ready", "آماده بازبینی"
        APPROVED = "approved", "تأییدشده"
        REJECTED = "rejected", "ردشده"
        SUPERSEDED = "superseded", "نسخه جایگزین‌شده"
        FAILED = "failed", "ناموفق"

    tour = models.ForeignKey(
        VirtualTour,
        on_delete=models.CASCADE,
        related_name="generated_models",
    )
    version = models.PositiveIntegerField(default=1)
    format = models.CharField(max_length=16, default="glb")
    state = models.CharField(
        max_length=20,
        choices=State.choices,
        default=State.READY,
        db_index=True,
    )
    geometry_source = models.CharField(max_length=48, default="floorplan_2d_extrusion")
    estimated_accuracy = models.CharField(
        max_length=180,
        default="تقریبی (برگرفته از پلان دو‌بعدی کالیبره‌شده)",
    )
    total_area_sqm = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    storage_key = models.CharField(max_length=500, blank=True, default="")
    size_bytes = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    is_current = models.BooleanField(default=False, db_index=True)

    class Meta:
        db_table = "virtual_tours_generated_model_asset"
        ordering = ["-version", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tour", "version"],
                name="uq_tour_generated_model_version",
            )
        ]


class ModelReview(BaseModel):
    class Decision(models.TextChoices):
        APPROVED = "approved", "تأییدشده"
        REJECTED = "rejected", "ردشده"

    model_asset = models.ForeignKey(
        GeneratedModelAsset,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    decision = models.CharField(max_length=20, choices=Decision.choices)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="virtual_tour_model_reviews",
    )
    reason = models.TextField(blank=True, default="")
    reviewed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "virtual_tours_model_review"
        ordering = ["-reviewed_at"]

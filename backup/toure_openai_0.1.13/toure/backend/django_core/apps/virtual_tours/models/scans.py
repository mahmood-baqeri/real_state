from django.db import models
from common.models import BaseModel
from .capture import ProcessingJob
from .tour import Floor, Scene, VirtualTour


class ScanAsset(BaseModel):
    class Format(models.TextChoices):
        PLY = "ply", "PLY Point Cloud"
        PCD = "pcd", "PCD Point Cloud"
        XYZ = "xyz", "XYZ ASCII Cloud"
        PTS = "pts", "PTS Point Cloud"
        NPY = "npy", "NumPy Array (.npy)"
        NPZ = "npz", "NumPy Archive (.npz)"
        OBJ = "obj", "Wavefront OBJ Mesh"
        GLB = "glb", "glTF Binary (.glb)"
        LAS = "las", "LAS LiDAR Archive"
        DEPTH_PNG = "depth_png", "Depth Map PNG"
        DEPTH_TIFF = "depth_tiff", "Depth Map TIFF"

    class Status(models.TextChoices):
        UPLOADED = "uploaded", "بارگذاری‌شده"
        PROCESSING = "processing", "در حال پردازش"
        VALIDATED = "validated", "اعتبارسنجی و پردازش‌شده"
        FAILED = "failed", "ناموفق"

    class SourceDevice(models.TextChoices):
        LIDAR_IOS = "lidar_ios", "اسکنر LiDAR آیفون / آیپد"
        DEPTH_ANDROID = "depth_android", "حسگر عمق Android (ARCore / ToF)"
        PHOTOGRAMMETRY = "photogrammetry", "فتوگرامتری"
        LASER_SCANNER = "laser_scanner", "اسکنر لیزری حرفه‌ای"
        OTHER = "other", "سایر منابع سه‌بعدی"

    tour = models.ForeignKey(
        VirtualTour,
        on_delete=models.CASCADE,
        related_name="scans",
    )
    floor = models.ForeignKey(
        Floor,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="scans",
    )
    scene = models.ForeignKey(
        Scene,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="scans",
    )
    format = models.CharField(max_length=20, choices=Format.choices, db_index=True)
    filename = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=100, default="application/octet-stream")
    size_bytes = models.BigIntegerField(default=0)
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.UPLOADED,
        db_index=True,
    )
    source_device = models.CharField(
        max_length=32,
        choices=SourceDevice.choices,
        default=SourceDevice.LIDAR_IOS,
    )
    storage_key = models.CharField(max_length=500)
    preview_glb_key = models.CharField(max_length=500, blank=True, default="")
    density_map_key = models.CharField(max_length=500, blank=True, default="")
    points_count = models.BigIntegerField(default=0)
    bounding_box = models.JSONField(default=dict, blank=True)
    processing_notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "virtual_tours_scan_asset"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["tour", "status"])]


class ScanProcessingResult(BaseModel):
    scan = models.OneToOneField(
        ScanAsset,
        on_delete=models.CASCADE,
        related_name="processing_result",
    )
    job = models.ForeignKey(
        ProcessingJob,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="scan_results",
    )
    raw_points_count = models.BigIntegerField(default=0)
    downsampled_points_count = models.BigIntegerField(default=0)
    outlier_points_count = models.BigIntegerField(default=0)
    estimated_footprint_sqm = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    point_density_per_sqm = models.FloatField(default=0.0)
    height_stats = models.JSONField(default=dict, blank=True)
    metrics = models.JSONField(default=dict, blank=True)
    engine = models.CharField(max_length=64, default="numpy_trimesh_geometry")
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "virtual_tours_scan_processing_result"
        ordering = ["-created_at"]

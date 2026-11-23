from django.db import models
from common.models import BaseModel
from .capture import Hotspot
from .tour import Scene, VirtualTour


class TourAnalyticsEvent(BaseModel):
    class EventType(models.TextChoices):
        TOUR_OPEN = "tour_open", "ورود به تور"
        SCENE_ENTER = "scene_enter", "ورود به اتاق"
        HOTSPOT_CLICK = "hotspot_click", "تعامل با نقطه تعاملی"
        DOLLHOUSE_OPEN = "dollhouse_open", "باز کردن مدل سه‌بعدی"
        FLOORPLAN_OPEN = "floorplan_open", "باز کردن پلان"
        TOUR_COMPLETE = "tour_complete", "تکمیل بازدید تور"
        DURATION_PING = "duration_ping", "ثبت مدت زمان"

    tour = models.ForeignKey(
        VirtualTour,
        on_delete=models.CASCADE,
        related_name="analytics_events",
    )
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.CASCADE,
        related_name="virtual_tour_analytics",
    )
    agency = models.ForeignKey(
        "agencies.Agency",
        on_delete=models.CASCADE,
        related_name="virtual_tour_analytics",
    )
    scene = models.ForeignKey(
        Scene,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    hotspot = models.ForeignKey(
        Hotspot,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    visitor_hash = models.CharField(max_length=64, db_index=True)
    session_key = models.CharField(max_length=64, db_index=True)
    event_type = models.CharField(max_length=24, choices=EventType.choices, db_index=True)
    device_type = models.CharField(max_length=24, default="desktop")
    duration_sec = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "virtual_tours_analytics_event"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tour", "event_type", "created_at"]),
            models.Index(fields=["agency", "created_at"]),
        ]

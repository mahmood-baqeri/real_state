import hashlib
from typing import Any, Optional
from uuid import UUID
from django.db.models import Avg, Count
from apps.virtual_tours.models import TourAnalyticsEvent, VirtualTour
from apps.virtual_tours.policies.access import is_property_publicly_publishable
from apps.virtual_tours.selectors import get_tour_for_user
from common.exceptions import NotFoundDomainError, ValidationDomainError


def record_tour_analytics_event(
    *,
    tour_id: UUID,
    event_type: str,
    session_key: str,
    scene_id: Optional[UUID] = None,
    hotspot_id: Optional[UUID] = None,
    device_type: str = "desktop",
    duration_sec: int = 0,
    client_ip: str = "",
    user_agent: str = "",
) -> TourAnalyticsEvent:
    tour = VirtualTour.objects.all_tenants().select_related("property").filter(id=tour_id).first()
    if not tour or tour.status != VirtualTour.Status.PUBLISHED or not is_property_publicly_publishable(tour.property):
        raise NotFoundDomainError("تور مجازی منتشرشده یافت نشد.")

    valid_events = {e for e, _ in TourAnalyticsEvent.EventType.choices}
    if event_type not in valid_events:
        raise ValidationDomainError("نوع رویداد آمار نامعتبر است.")

    raw_visitor = f"{tour.id}:{client_ip}:{user_agent[:120]}"
    visitor_hash = hashlib.sha256(raw_visitor.encode("utf-8")).hexdigest()

    return TourAnalyticsEvent.objects.create(
        tour=tour,
        property=tour.property,
        agency=tour.agency,
        scene_id=scene_id,
        hotspot_id=hotspot_id,
        visitor_hash=visitor_hash,
        session_key=(session_key or visitor_hash)[:64],
        event_type=event_type,
        device_type=(device_type or "desktop")[:24],
        duration_sec=max(0, min(86400, int(duration_sec))),
    )


def get_tour_analytics_summary(*, user, agency_id: Optional[UUID], tour_id: UUID) -> dict[str, Any]:
    tour = get_tour_for_user(user=user, agency_id=agency_id, tour_id=tour_id, require_edit=False)
    qs = TourAnalyticsEvent.objects.filter(tour=tour)

    total_opens = qs.filter(event_type=TourAnalyticsEvent.EventType.TOUR_OPEN).count()
    unique_visitors = qs.values("visitor_hash").distinct().count()
    completed_sessions = qs.filter(event_type=TourAnalyticsEvent.EventType.TOUR_COMPLETE).values("session_key").distinct().count()
    total_sessions = qs.values("session_key").distinct().count()
    avg_duration = qs.filter(duration_sec__gt=0).aggregate(avg=Avg("duration_sec"))["avg"] or 0

    scene_stats = list(
        qs.filter(event_type=TourAnalyticsEvent.EventType.SCENE_ENTER, scene__isnull=False)
        .values("scene_id", "scene__title")
        .annotate(visits=Count("id"))
        .order_by("-visits")[:10]
    )
    hotspot_clicks = qs.filter(event_type=TourAnalyticsEvent.EventType.HOTSPOT_CLICK).count()
    dollhouse_opens = qs.filter(event_type=TourAnalyticsEvent.EventType.DOLLHOUSE_OPEN).count()
    floorplan_opens = qs.filter(event_type=TourAnalyticsEvent.EventType.FLOORPLAN_OPEN).count()
    devices = list(
        qs.values("device_type").annotate(count=Count("id")).order_by("-count")
    )

    return {
        "tour_id": str(tour.id),
        "total_views": total_opens,
        "unique_visitors": unique_visitors,
        "total_sessions": total_sessions,
        "completed_sessions": completed_sessions,
        "completion_rate_percent": round((completed_sessions / max(1, total_sessions)) * 100, 1) if total_sessions else 0.0,
        "avg_duration_seconds": round(float(avg_duration), 1),
        "hotspot_clicks": hotspot_clicks,
        "dollhouse_opens": dollhouse_opens,
        "floorplan_opens": floorplan_opens,
        "popular_scenes": [
            {"scene_id": str(row["scene_id"]), "title": row["scene__title"], "visits": row["visits"]}
            for row in scene_stats
        ],
        "device_breakdown": devices,
    }

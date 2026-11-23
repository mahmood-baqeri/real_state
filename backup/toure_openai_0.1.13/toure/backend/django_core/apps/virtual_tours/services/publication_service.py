from typing import Any, Optional
from uuid import UUID
from django.db import transaction
from django.utils import timezone
from apps.accounts.models import User
from apps.audit.services import record_audit_event
from apps.virtual_tours.models import PanoramaVersion, TourPublication, VirtualTour
from apps.virtual_tours.policies.access import (
    assert_tour_publish_access,
    build_private_file_url,
    is_property_publicly_publishable,
)
from apps.virtual_tours.selectors import get_property_active_tour, get_tour_for_user
from apps.virtual_tours.services.quality_service import generate_tour_quality_report
from common.exceptions import NotFoundDomainError, ValidationDomainError


def _build_publication_snapshot(tour: VirtualTour) -> dict[str, Any]:
    floors_data = []
    for f in tour.floors.order_by("order"):
        floors_data.append({
            "id": str(f.id),
            "title": f.title,
            "order": f.order,
            "elevation_m": str(f.elevation_m),
        })

    scenes_data = []
    for s in tour.scenes.filter(active=True).select_related("floor").order_by("floor__order", "order"):
        pano = (
            s.panorama_versions.filter(is_current=True, state=PanoramaVersion.State.APPROVED).first()
            or s.panorama_versions.filter(is_current=True).first()
        )
        if not pano:
            continue
        links_out = [
            {
                "id": str(lnk.id),
                "target_scene_id": str(lnk.target_scene_id),
                "target_scene_title": lnk.target_scene.title,
                "yaw": lnk.yaw,
                "pitch": lnk.pitch,
                "title": lnk.title or lnk.target_scene.title,
            }
            for lnk in s.outgoing_links.select_related("target_scene").all()
        ]
        hotspots_list = [
            {
                "id": str(hs.id),
                "kind": hs.kind,
                "title": hs.title,
                "body": hs.body,
                "yaw": hs.yaw,
                "pitch": hs.pitch,
                "target_scene_id": str(hs.target_scene_id) if hs.target_scene_id else None,
                "metadata": hs.metadata,
            }
            for hs in s.hotspots.all()
        ]
        scenes_data.append({
            "id": str(s.id),
            "floor_id": str(s.floor_id),
            "floor_title": s.floor.title,
            "title": s.title,
            "room_type": s.room_type,
            "description": s.description,
            "is_start_scene": s.is_start_scene,
            "initial_yaw": s.initial_yaw,
            "initial_pitch": s.initial_pitch,
            "panorama_version_id": str(pano.id),
            "panorama_url": build_private_file_url(kind="panorama", object_id=str(pano.id), tour_id=str(tour.id), signed=False),
            "thumbnail_url": build_private_file_url(kind="panorama-thumb", object_id=str(pano.id), tour_id=str(tour.id), signed=False),
            "width_px": pano.width_px,
            "height_px": pano.height_px,
            "links": links_out,
            "hotspots": hotspots_list,
        })

    from apps.virtual_tours.models import GeneratedModelAsset

    floorplans_data = [
        {
            "id": str(fp.id),
            "tour_id": str(tour.id),
            "floor_id": str(fp.floor_id),
            "floor_title": fp.floor.title,
            "file_type": fp.file_type,
            "filename": fp.filename,
            "width_px": fp.width_px,
            "height_px": fp.height_px,
            "scale_m_per_px": fp.scale_m_per_px,
            "calibration_data": fp.calibration_data or {},
            "file_url": build_private_file_url(kind="floorplan-preview", object_id=str(fp.id), tour_id=str(tour.id), signed=False),
            "created_at": fp.created_at.isoformat(),
        }
        for fp in tour.floorplans.filter(is_active=True).select_related("floor").order_by("floor__order")
    ]

    rooms_data = [
        {
            "id": str(r.id),
            "tour_id": str(tour.id),
            "floor_id": str(r.floor_id),
            "scene_id": str(r.scene_id) if r.scene_id else None,
            "scene_title": r.scene.title if r.scene else None,
            "label": r.label,
            "room_type": r.room_type,
            "polygon_points": r.polygon_points or [],
            "area_sqm": str(r.area_sqm),
            "perimeter_m": str(r.perimeter_m),
            "height_m": str(r.height_m),
            "source": r.source,
            "color_hex": r.color_hex,
        }
        for r in tour.room_geometries.select_related("scene").order_by("floor__order", "created_at")
    ]

    dollhouse_model = (
        tour.generated_models.filter(is_current=True, state=GeneratedModelAsset.State.APPROVED).first()
        or tour.generated_models.filter(is_current=True, state=GeneratedModelAsset.State.READY).first()
    )
    dollhouse_data = (
        {
            "id": str(dollhouse_model.id),
            "tour_id": str(tour.id),
            "version": dollhouse_model.version,
            "format": dollhouse_model.format,
            "state": dollhouse_model.state,
            "geometry_source": dollhouse_model.geometry_source,
            "estimated_accuracy": dollhouse_model.estimated_accuracy,
            "total_area_sqm": str(dollhouse_model.total_area_sqm),
            "file_url": build_private_file_url(
                kind="model-glb", object_id=str(dollhouse_model.id), tour_id=str(tour.id), signed=False
            ),
            "size_bytes": dollhouse_model.size_bytes,
            "metadata": dollhouse_model.metadata or {},
            "is_current": dollhouse_model.is_current,
            "created_at": dollhouse_model.created_at.isoformat(),
        }
        if dollhouse_model and dollhouse_model.storage_key
        else None
    )

    return {
        "tour_id": str(tour.id),
        "property_id": str(tour.property_id),
        "title": tour.title,
        "description": tour.description,
        "floors": floors_data,
        "scenes": scenes_data,
        "floorplans": floorplans_data,
        "rooms": rooms_data,
        "dollhouse": dollhouse_data,
    }


@transaction.atomic
def publish_virtual_tour(
    *,
    user: User,
    agency_id: Optional[UUID],
    tour_id: UUID,
) -> TourPublication:
    tour = get_tour_for_user(user=user, agency_id=agency_id, tour_id=tour_id, require_edit=False)
    assert_tour_publish_access(user=user, agency_id=agency_id, prop=tour.property)

    report = generate_tour_quality_report(tour, actor=user)
    if not report.is_ready_to_publish:
        first_msg = (report.report_data.get("blocking_issues") or [{}])[0].get("message", "شرایط انتشار تور تکمیل نشده است.")
        raise ValidationDomainError(f"تور هنوز آماده انتشار نیست: {first_msg}")

    snapshot = _build_publication_snapshot(tour)
    if not snapshot["scenes"]:
        raise ValidationDomainError("هیچ صحنه دارای پانورامای معتبر برای انتشار وجود ندارد.")

    next_ver = (tour.publications.order_by("-version").values_list("version", flat=True).first() or 0) + 1
    tour.publications.filter(is_active=True).update(is_active=False, unpublished_at=timezone.now())
    pub = TourPublication.objects.create(
        tour=tour,
        version=next_ver,
        is_active=True,
        snapshot_json=snapshot,
        published_by=user,
        published_at=timezone.now(),
        created_by=user,
        updated_by=user,
    )

    tour.status = VirtualTour.Status.PUBLISHED
    tour.published_at = pub.published_at
    tour.updated_by = user
    tour.save(update_fields=["status", "published_at", "updated_by", "updated_at"])

    record_audit_event(
        action="virtual_tour.publish",
        resource_type="TourPublication",
        resource_id=str(pub.id),
        actor=user,
        agency_id=tour.agency_id,
        after_state={"tour_id": str(tour.id), "version": pub.version, "scenes_count": len(snapshot["scenes"])},
    )
    return pub


@transaction.atomic
def unpublish_virtual_tour(
    *,
    user: User,
    agency_id: Optional[UUID],
    tour_id: UUID,
) -> VirtualTour:
    tour = get_tour_for_user(user=user, agency_id=agency_id, tour_id=tour_id, require_edit=False)
    assert_tour_publish_access(user=user, agency_id=agency_id, prop=tour.property)

    tour.publications.filter(is_active=True).update(is_active=False, unpublished_at=timezone.now())
    tour.status = VirtualTour.Status.READY
    tour.updated_by = user
    tour.save(update_fields=["status", "updated_by", "updated_at"])

    record_audit_event(
        action="virtual_tour.unpublish",
        resource_type="VirtualTour",
        resource_id=str(tour.id),
        actor=user,
        agency_id=tour.agency_id,
        after_state={"status": tour.status},
    )
    return tour


def get_public_virtual_tour_by_slug(*, public_slug: str) -> dict[str, Any]:
    """Resolve a published tour using its shareable publication slug."""
    pub = (
        TourPublication.objects.select_related("tour", "tour__property")
        .filter(public_slug=public_slug, is_active=True, tour__status=VirtualTour.Status.PUBLISHED)
        .first()
    )
    if not pub or not is_property_publicly_publishable(pub.tour.property):
        raise NotFoundDomainError("تور عمومی مورد نظر یافت نشد یا دیگر منتشرشده نیست.")
    return {
        "tour_id": str(pub.tour_id),
        "property_id": str(pub.tour.property_id),
        "publication_version": pub.version,
        "public_slug": pub.public_slug,
        "published_at": pub.published_at.isoformat(),
        **(pub.snapshot_json or {}),
    }


def get_public_property_virtual_tour(*, property_id: UUID) -> dict[str, Any]:
    """
    Strictly enforces both property public eligibility AND published tour publication snapshot.
    Never leaks raw captures or private draft tours.
    """
    tour = get_property_active_tour(property_id=property_id)
    if not tour or tour.status != VirtualTour.Status.PUBLISHED:
        raise NotFoundDomainError("تور مجازی منتشرشده‌ای برای این ملک وجود ندارد.")
    if not is_property_publicly_publishable(tour.property):
        raise NotFoundDomainError("ملک در پورتال عمومی منتشر نشده است و تور آن در دسترس عموم نیست.")

    pub = tour.publications.filter(is_active=True).order_by("-version").first()
    if not pub:
        raise NotFoundDomainError("نسخه منتشرشده فعال برای تور یافت نشد.")

    return {
        "tour_id": str(tour.id),
        "property_id": str(tour.property_id),
        "publication_version": pub.version,
        "public_slug": pub.public_slug,
        "published_at": pub.published_at.isoformat(),
        **pub.snapshot_json,
    }

from typing import Optional
from uuid import UUID
from apps.accounts.models import User
from apps.virtual_tours.models import (
    CaptureSession,
    Floor,
    FloorPlanAsset,
    GeneratedModelAsset,
    Hotspot,
    ProcessingJob,
    RoomGeometry,
    ScanAsset,
    Scene,
    SceneLink,
    VirtualTour,
    WallOpening,
    WallSegment,
)
from apps.virtual_tours.policies.access import (
    assert_tour_edit_access,
    assert_tour_view_access,
)
from common.exceptions import NotFoundDomainError


def get_property_active_tour(*, property_id: UUID) -> Optional[VirtualTour]:
    return (
        VirtualTour.objects.all_tenants()
        .select_related("property", "agency", "branch")
        .filter(property_id=property_id)
        .exclude(status=VirtualTour.Status.ARCHIVED)
        .first()
    )


def get_tour_for_user(
    *,
    user: Optional[User],
    agency_id: Optional[UUID],
    tour_id: UUID,
    require_edit: bool = False,
) -> VirtualTour:
    tour = (
        VirtualTour.objects.all_tenants()
        .select_related("property", "agency", "branch")
        .filter(id=tour_id)
        .first()
    )
    if not tour:
        raise NotFoundDomainError("تور مجازی مورد نظر یافت نشد.")
    if require_edit:
        assert_tour_edit_access(user=user, agency_id=agency_id, prop=tour.property)
    else:
        assert_tour_view_access(user=user, agency_id=agency_id, prop=tour.property)
    return tour


def get_floor_for_user(
    *,
    user: Optional[User],
    agency_id: Optional[UUID],
    floor_id: UUID,
    require_edit: bool = False,
) -> Floor:
    floor = Floor.objects.select_related("tour", "tour__property", "tour__agency").filter(id=floor_id).first()
    if not floor:
        raise NotFoundDomainError("طبقه مورد نظر یافت نشد.")
    if require_edit:
        assert_tour_edit_access(user=user, agency_id=agency_id, prop=floor.tour.property)
    else:
        assert_tour_view_access(user=user, agency_id=agency_id, prop=floor.tour.property)
    return floor


def get_scene_for_user(
    *,
    user: Optional[User],
    agency_id: Optional[UUID],
    scene_id: UUID,
    require_edit: bool = False,
) -> Scene:
    scene = Scene.objects.select_related("tour", "tour__property", "tour__agency", "floor").filter(id=scene_id).first()
    if not scene:
        raise NotFoundDomainError("اتاق یا صحنه مورد نظر یافت نشد.")
    if require_edit:
        assert_tour_edit_access(user=user, agency_id=agency_id, prop=scene.tour.property)
    else:
        assert_tour_view_access(user=user, agency_id=agency_id, prop=scene.tour.property)
    return scene


def get_capture_session_for_user(
    *,
    user: Optional[User],
    agency_id: Optional[UUID],
    session_id: UUID,
    require_edit: bool = False,
) -> CaptureSession:
    session = (
        CaptureSession.objects.select_related("tour", "tour__property", "scene", "scene__floor")
        .filter(id=session_id)
        .first()
    )
    if not session:
        raise NotFoundDomainError("جلسه عکاسی مورد نظر یافت نشد.")
    if require_edit:
        assert_tour_edit_access(user=user, agency_id=agency_id, prop=session.tour.property)
    else:
        assert_tour_view_access(user=user, agency_id=agency_id, prop=session.tour.property)
    return session


def get_link_for_user(
    *,
    user: Optional[User],
    agency_id: Optional[UUID],
    link_id: UUID,
    require_edit: bool = False,
) -> SceneLink:
    link = (
        SceneLink.objects.select_related("tour", "tour__property", "source_scene", "target_scene")
        .filter(id=link_id)
        .first()
    )
    if not link:
        raise NotFoundDomainError("لینک بین اتاق‌ها یافت نشد.")
    if require_edit:
        assert_tour_edit_access(user=user, agency_id=agency_id, prop=link.tour.property)
    else:
        assert_tour_view_access(user=user, agency_id=agency_id, prop=link.tour.property)
    return link


def get_hotspot_for_user(
    *,
    user: Optional[User],
    agency_id: Optional[UUID],
    hotspot_id: UUID,
    require_edit: bool = False,
) -> Hotspot:
    hs = Hotspot.objects.select_related("scene", "scene__tour", "scene__tour__property").filter(id=hotspot_id).first()
    if not hs:
        raise NotFoundDomainError("نقطه تعاملی (Hotspot) مورد نظر یافت نشد.")
    if require_edit:
        assert_tour_edit_access(user=user, agency_id=agency_id, prop=hs.scene.tour.property)
    else:
        assert_tour_view_access(user=user, agency_id=agency_id, prop=hs.scene.tour.property)
    return hs


def get_processing_job_for_user(
    *,
    user: Optional[User],
    agency_id: Optional[UUID],
    job_id: UUID,
    require_edit: bool = False,
) -> ProcessingJob:
    job = ProcessingJob.objects.select_related("tour", "tour__property", "scene").filter(id=job_id).first()
    if not job:
        raise NotFoundDomainError("پردازش (Job) مورد نظر یافت نشد.")
    if require_edit:
        assert_tour_edit_access(user=user, agency_id=agency_id, prop=job.tour.property)
    else:
        assert_tour_view_access(user=user, agency_id=agency_id, prop=job.tour.property)
    return job


def get_floorplan_for_user(
    *,
    user: Optional[User],
    agency_id: Optional[UUID],
    floorplan_id: UUID,
    require_edit: bool = False,
) -> FloorPlanAsset:
    fp = FloorPlanAsset.objects.select_related("tour", "tour__property", "floor").filter(id=floorplan_id).first()
    if not fp:
        raise NotFoundDomainError("فایل پلان مورد نظر یافت نشد.")
    if require_edit:
        assert_tour_edit_access(user=user, agency_id=agency_id, prop=fp.tour.property)
    else:
        assert_tour_view_access(user=user, agency_id=agency_id, prop=fp.tour.property)
    return fp


def get_room_geometry_for_user(
    *,
    user: Optional[User],
    agency_id: Optional[UUID],
    room_id: UUID,
    require_edit: bool = False,
) -> RoomGeometry:
    room = RoomGeometry.objects.select_related("tour", "tour__property", "floor", "scene").filter(id=room_id).first()
    if not room:
        raise NotFoundDomainError("هندسه اتاق مورد نظر یافت نشد.")
    if require_edit:
        assert_tour_edit_access(user=user, agency_id=agency_id, prop=room.tour.property)
    else:
        assert_tour_view_access(user=user, agency_id=agency_id, prop=room.tour.property)
    return room


def get_wall_segment_for_user(
    *,
    user: Optional[User],
    agency_id: Optional[UUID],
    wall_id: UUID,
    require_edit: bool = False,
) -> WallSegment:
    wall = WallSegment.objects.select_related("tour", "tour__property", "floor").filter(id=wall_id).first()
    if not wall:
        raise NotFoundDomainError("قطعه دیوار مورد نظر یافت نشد.")
    if require_edit:
        assert_tour_edit_access(user=user, agency_id=agency_id, prop=wall.tour.property)
    else:
        assert_tour_view_access(user=user, agency_id=agency_id, prop=wall.tour.property)
    return wall


def get_wall_opening_for_user(
    *,
    user: Optional[User],
    agency_id: Optional[UUID],
    opening_id: UUID,
    require_edit: bool = False,
) -> WallOpening:
    opening = (
        WallOpening.objects.select_related("wall", "wall__tour", "wall__tour__property")
        .filter(id=opening_id)
        .first()
    )
    if not opening:
        raise NotFoundDomainError("بازشوی دیوار (درب/پنجره) یافت نشد.")
    if require_edit:
        assert_tour_edit_access(user=user, agency_id=agency_id, prop=opening.wall.tour.property)
    else:
        assert_tour_view_access(user=user, agency_id=agency_id, prop=opening.wall.tour.property)
    return opening


def get_model_asset_for_user(
    *,
    user: Optional[User],
    agency_id: Optional[UUID],
    model_id: UUID,
    require_edit: bool = False,
) -> GeneratedModelAsset:
    asset = GeneratedModelAsset.objects.select_related("tour", "tour__property").filter(id=model_id).first()
    if not asset:
        raise NotFoundDomainError("نسخه مدل سه‌بعدی مورد نظر یافت نشد.")
    if require_edit:
        assert_tour_edit_access(user=user, agency_id=agency_id, prop=asset.tour.property)
    else:
        assert_tour_view_access(user=user, agency_id=agency_id, prop=asset.tour.property)
    return asset


def get_scan_asset_for_user(
    *,
    user: Optional[User],
    agency_id: Optional[UUID],
    scan_id: UUID,
    require_edit: bool = False,
) -> ScanAsset:
    scan = ScanAsset.objects.select_related("tour", "tour__property", "floor", "scene").filter(id=scan_id).first()
    if not scan:
        raise NotFoundDomainError("فایل اسکن مورد نظر یافت نشد.")
    if require_edit:
        assert_tour_edit_access(user=user, agency_id=agency_id, prop=scan.tour.property)
    else:
        assert_tour_view_access(user=user, agency_id=agency_id, prop=scan.tour.property)
    return scan

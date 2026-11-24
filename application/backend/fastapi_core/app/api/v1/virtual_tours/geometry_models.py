from uuid import UUID
from fastapi import APIRouter, Depends, File, Form, UploadFile
from app.core.django_bridge import run_django
from app.dependencies.auth import RequestContext, require_agency_context
from app.schemas.common import ok
from app.schemas.virtual_tours import (
    FloorPlanCalibrateBody,
    GenerateDollhouseBody,
    ModelRejectBody,
    RoomGeometryUpsertBody,
    RoomMeasurementCreateBody,
    WallOpeningCreateBody,
    WallSegmentCreateBody,
)
from .serializers import (
    serialize_floorplan,
    serialize_generated_model_asset,
    serialize_processing_job,
    serialize_room_geometry,
    serialize_wall_opening,
    serialize_wall_segment,
)

from app.core.uploads import read_upload_limited

router = APIRouter(tags=["Virtual Tours Floorplan & 3D Dollhouse"])


@router.get("/virtual-tours/{tour_id}/floorplans")
async def list_floorplans_endpoint(
    tour_id: UUID,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.selectors import get_tour_for_user

        tour = get_tour_for_user(user=ctx.user, agency_id=ctx.agency_id, tour_id=tour_id, require_edit=False)
        fps = list(tour.floorplans.filter(is_active=True).select_related("floor").order_by("floor__order", "-created_at"))
        return [serialize_floorplan(fp) for fp in fps]

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/virtual-tours/{tour_id}/floorplans", status_code=201)
async def upload_floorplan_endpoint(
    tour_id: UUID,
    floor_id: UUID = Form(...),
    file: UploadFile = File(...),
    ctx: RequestContext = Depends(require_agency_context),
):
    raw_bytes = await read_upload_limited(file)

    def _op():
        from apps.virtual_tours.services import geometry_service

        fp = geometry_service.upload_floorplan(
            user=ctx.user,
            agency_id=ctx.agency_id,
            tour_id=tour_id,
            floor_id=floor_id,
            filename=file.filename or "floorplan.png",
            content_type=file.content_type or "image/png",
            content=raw_bytes,
        )
        return serialize_floorplan(fp)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/floorplans/{floorplan_id}/calibrate")
async def calibrate_floorplan_endpoint(
    floorplan_id: UUID,
    body: FloorPlanCalibrateBody,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import geometry_service

        fp = geometry_service.calibrate_floorplan(
            user=ctx.user,
            agency_id=ctx.agency_id,
            floorplan_id=floorplan_id,
            point_a=body.point_a,
            point_b=body.point_b,
            real_distance_m=body.real_distance_m,
        )
        return serialize_floorplan(fp)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/virtual-tours/{tour_id}/rooms", status_code=201)
async def create_room_geometry_endpoint(
    tour_id: UUID,
    body: RoomGeometryUpsertBody,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import geometry_service

        rm = geometry_service.create_or_update_room_geometry(
            user=ctx.user,
            agency_id=ctx.agency_id,
            tour_id=tour_id,
            data=body.model_dump(),
        )
        return serialize_room_geometry(rm)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.patch("/rooms/{room_id}")
async def update_room_geometry_endpoint(
    room_id: UUID,
    body: RoomGeometryUpsertBody,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.selectors import get_room_geometry_for_user
        from apps.virtual_tours.services import geometry_service

        existing = get_room_geometry_for_user(user=ctx.user, agency_id=ctx.agency_id, room_id=room_id, require_edit=True)
        rm = geometry_service.create_or_update_room_geometry(
            user=ctx.user,
            agency_id=ctx.agency_id,
            tour_id=existing.tour_id,
            data=body.model_dump(),
            room_id=room_id,
        )
        return serialize_room_geometry(rm)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.delete("/rooms/{room_id}")
async def delete_room_geometry_endpoint(
    room_id: UUID,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import geometry_service

        return geometry_service.delete_room_geometry(user=ctx.user, agency_id=ctx.agency_id, room_id=room_id)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/rooms/{room_id}/measurements", status_code=201)
async def create_room_measurement_endpoint(
    room_id: UUID,
    body: RoomMeasurementCreateBody,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import geometry_service

        m = geometry_service.create_room_measurement(
            user=ctx.user,
            agency_id=ctx.agency_id,
            room_id=room_id,
            label=body.label,
            start_point=body.start_point,
            end_point=body.end_point,
        )
        return {
            "id": str(m.id),
            "room_id": str(m.room_id),
            "label": m.label,
            "start_point": m.start_point,
            "end_point": m.end_point,
            "distance_m": str(m.distance_m),
            "source": m.source,
        }

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/virtual-tours/{tour_id}/walls", status_code=201)
async def create_wall_segment_endpoint(
    tour_id: UUID,
    body: WallSegmentCreateBody,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import geometry_service

        wall = geometry_service.create_wall_segment(
            user=ctx.user,
            agency_id=ctx.agency_id,
            tour_id=tour_id,
            data=body.model_dump(),
        )
        return serialize_wall_segment(wall)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.delete("/walls/{wall_id}")
async def delete_wall_segment_endpoint(
    wall_id: UUID,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import geometry_service

        return geometry_service.delete_wall_segment(user=ctx.user, agency_id=ctx.agency_id, wall_id=wall_id)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/walls/{wall_id}/openings", status_code=201)
async def create_wall_opening_endpoint(
    wall_id: UUID,
    body: WallOpeningCreateBody,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import geometry_service

        op = geometry_service.create_wall_opening(
            user=ctx.user,
            agency_id=ctx.agency_id,
            wall_id=wall_id,
            data=body.model_dump(),
        )
        return serialize_wall_opening(op)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.delete("/openings/{opening_id}")
async def delete_wall_opening_endpoint(
    opening_id: UUID,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import geometry_service

        return geometry_service.delete_wall_opening(user=ctx.user, agency_id=ctx.agency_id, opening_id=opening_id)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/virtual-tours/{tour_id}/generate-3d", status_code=202)
async def generate_dollhouse_3d_endpoint(
    tour_id: UUID,
    body: GenerateDollhouseBody = GenerateDollhouseBody(),
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import geometry_service

        job = geometry_service.enqueue_dollhouse_build(
            user=ctx.user,
            agency_id=ctx.agency_id,
            tour_id=tour_id,
            wall_height_m=body.wall_height_m,
            wall_thickness_m=body.wall_thickness_m,
        )
        return {
            "job": serialize_processing_job(job),
            "job_id": str(job.id),
        }

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.get("/virtual-tours/{tour_id}/model/current")
async def get_current_dollhouse_model_endpoint(
    tour_id: UUID,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.selectors import get_tour_for_user

        tour = get_tour_for_user(user=ctx.user, agency_id=ctx.agency_id, tour_id=tour_id, require_edit=False)
        asset = tour.generated_models.filter(is_current=True).first() or tour.generated_models.order_by("-version").first()
        return serialize_generated_model_asset(asset) if asset else None

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.get("/virtual-tours/{tour_id}/models")
async def list_dollhouse_models_endpoint(
    tour_id: UUID,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.selectors import get_tour_for_user

        tour = get_tour_for_user(user=ctx.user, agency_id=ctx.agency_id, tour_id=tour_id, require_edit=False)
        return [serialize_generated_model_asset(m) for m in tour.generated_models.order_by("-version")]

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/models/{model_id}/approve")
async def approve_dollhouse_model_endpoint(
    model_id: UUID,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import geometry_service

        asset = geometry_service.review_generated_model(
            user=ctx.user,
            agency_id=ctx.agency_id,
            model_id=model_id,
            approve=True,
        )
        return serialize_generated_model_asset(asset)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/models/{model_id}/reject")
async def reject_dollhouse_model_endpoint(
    model_id: UUID,
    body: ModelRejectBody,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import geometry_service

        asset = geometry_service.review_generated_model(
            user=ctx.user,
            agency_id=ctx.agency_id,
            model_id=model_id,
            approve=False,
            reason=body.reason,
        )
        return serialize_generated_model_asset(asset)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/models/{model_id}/restore")
async def restore_dollhouse_model_endpoint(
    model_id: UUID,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import geometry_service

        asset = geometry_service.restore_generated_model(
            user=ctx.user,
            agency_id=ctx.agency_id,
            model_id=model_id,
        )
        return serialize_generated_model_asset(asset)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, File, Form, UploadFile
from app.core.django_bridge import run_django
from app.dependencies.auth import RequestContext, require_agency_context
from app.schemas.common import ok
from .serializers import serialize_processing_job, serialize_scan_asset

router = APIRouter(tags=["Virtual Tours 3D Scans & LiDAR"])


@router.get("/virtual-tours/{tour_id}/scans")
async def list_tour_scans_endpoint(
    tour_id: UUID,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.selectors import get_tour_for_user

        tour = get_tour_for_user(user=ctx.user, agency_id=ctx.agency_id, tour_id=tour_id, require_edit=False)
        scans = list(tour.scans.select_related("floor", "scene", "processing_result").order_by("-created_at"))
        return [serialize_scan_asset(s) for s in scans]

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/virtual-tours/{tour_id}/scans", status_code=201)
async def upload_tour_scan_endpoint(
    tour_id: UUID,
    file: UploadFile = File(...),
    source_device: str = Form(default="lidar_ios"),
    floor_id: Optional[UUID] = Form(default=None),
    scene_id: Optional[UUID] = Form(default=None),
    ctx: RequestContext = Depends(require_agency_context),
):
    raw_bytes = await file.read()

    def _op():
        from apps.virtual_tours.services import scan_service

        scan = scan_service.upload_scan_asset(
            user=ctx.user,
            agency_id=ctx.agency_id,
            tour_id=tour_id,
            filename=file.filename or "scan.ply",
            content_type=file.content_type or "application/octet-stream",
            content=raw_bytes,
            source_device=source_device,
            floor_id=floor_id,
            scene_id=scene_id,
        )
        return serialize_scan_asset(scan)

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.get("/scans/{scan_id}")
async def get_scan_detail_endpoint(
    scan_id: UUID,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.selectors import get_scan_asset_for_user

        scan = get_scan_asset_for_user(user=ctx.user, agency_id=ctx.agency_id, scan_id=scan_id, require_edit=False)
        return serialize_scan_asset(scan)

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/scans/{scan_id}/process", status_code=202)
async def process_scan_endpoint(
    scan_id: UUID,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import scan_service

        job = scan_service.enqueue_scan_process(
            user=ctx.user,
            agency_id=ctx.agency_id,
            scan_id=scan_id,
        )
        return {
            "job": serialize_processing_job(job),
            "job_id": str(job.id),
        }

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.delete("/scans/{scan_id}")
async def delete_scan_endpoint(
    scan_id: UUID,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import scan_service

        scan_service.delete_scan_asset(user=ctx.user, agency_id=ctx.agency_id, scan_id=scan_id)
        return {"deleted": True, "scan_id": str(scan_id)}

    return ok(await run_django(_op, agency_id=ctx.agency_id))

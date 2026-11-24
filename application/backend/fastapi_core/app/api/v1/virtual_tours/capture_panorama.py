from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, File, Form, Header, UploadFile
from app.core.django_bridge import run_django
from app.dependencies.auth import RequestContext, require_agency_context
from app.schemas.common import ok
from app.schemas.virtual_tours import (
    CaptureSessionCreateBody,
    PanoramaApproveBody,
    PanoramaRejectBody,
    ProcessSceneBody,
)
from .serializers import (
    serialize_capture_guide_step,
    serialize_capture_image,
    serialize_capture_session,
    serialize_panorama_version,
    serialize_processing_job,
)

from app.core.uploads import read_upload_limited

router = APIRouter(tags=["Virtual Tours Capture & Panorama"])


@router.post("/scenes/{scene_id}/capture-sessions", status_code=201)
async def create_capture_session_endpoint(
    scene_id: UUID,
    body: CaptureSessionCreateBody,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import capture_service

        session = capture_service.start_capture_session(
            user=ctx.user,
            agency_id=ctx.agency_id,
            scene_id=scene_id,
            device_info=body.device_info,
            allow_partial_stitch=body.allow_partial_stitch,
        )
        return serialize_capture_session(session)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.get("/scenes/{scene_id}/capture-sessions")
async def list_scene_capture_sessions_endpoint(
    scene_id: UUID,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.selectors import get_scene_for_user

        scene = get_scene_for_user(user=ctx.user, agency_id=ctx.agency_id, scene_id=scene_id, require_edit=False)
        return [serialize_capture_session(s) for s in scene.capture_sessions.order_by("-created_at")[:10]]

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.get("/capture-sessions/{session_id}")
async def get_capture_session_endpoint(
    session_id: UUID,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.selectors import get_capture_session_for_user

        session = get_capture_session_for_user(
            user=ctx.user, agency_id=ctx.agency_id, session_id=session_id, require_edit=False
        )
        return serialize_capture_session(session)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.get("/capture-sessions/{session_id}/guide")
async def get_capture_guide_endpoint(
    session_id: UUID,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.selectors import get_capture_session_for_user
        from apps.virtual_tours.services.quality_service import evaluate_capture_session_quality

        session = get_capture_session_for_user(
            user=ctx.user, agency_id=ctx.agency_id, session_id=session_id, require_edit=False
        )
        tour_id = str(session.tour_id)
        return {
            "session_id": str(session.id),
            "status": session.status,
            "summary": evaluate_capture_session_quality(session),
            "steps": [
                serialize_capture_guide_step(st, tour_id=tour_id)
                for st in session.guide_steps.select_related("image").order_by("sequence")
            ],
        }

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/capture-sessions/{session_id}/images", status_code=201)
async def upload_capture_image_endpoint(
    session_id: UUID,
    file: UploadFile = File(...),
    sequence: int = Form(...),
    yaw: Optional[float] = Form(default=None),
    pitch: Optional[float] = Form(default=None),
    ctx: RequestContext = Depends(require_agency_context),
):
    content = await read_upload_limited(file)

    def _op():
        from apps.virtual_tours.services import capture_service

        img, summary = capture_service.upload_capture_image(
            user=ctx.user,
            agency_id=ctx.agency_id,
            session_id=session_id,
            filename=file.filename or f"frame-{sequence}.jpg",
            content_type=file.content_type or "",
            content=content,
            sequence=sequence,
            yaw=yaw,
            pitch=pitch,
        )
        return {
            "image": serialize_capture_image(img, tour_id=str(img.session.tour_id)),
            "session_summary": summary,
        }

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.get("/capture-sessions/{session_id}/images")
async def list_capture_images_endpoint(
    session_id: UUID,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.models import CaptureImage
        from apps.virtual_tours.selectors import get_capture_session_for_user

        session = get_capture_session_for_user(
            user=ctx.user, agency_id=ctx.agency_id, session_id=session_id, require_edit=False
        )
        tour_id = str(session.tour_id)
        return [
            serialize_capture_image(img, tour_id=tour_id)
            for img in session.images.exclude(status=CaptureImage.Status.REPLACED).order_by("sequence")
        ]

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/capture-sessions/{session_id}/steps/{sequence}/skip")
async def skip_capture_step_endpoint(
    session_id: UUID,
    sequence: int,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import capture_service

        step = capture_service.skip_capture_step(
            user=ctx.user, agency_id=ctx.agency_id, session_id=session_id, sequence=sequence
        )
        return serialize_capture_guide_step(step, tour_id=str(step.session.tour_id))

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/capture-sessions/{session_id}/complete")
async def complete_capture_session_endpoint(
    session_id: UUID,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import capture_service

        session, summary = capture_service.complete_capture_session(
            user=ctx.user, agency_id=ctx.agency_id, session_id=session_id
        )
        return {
            "session": serialize_capture_session(session),
            "summary": summary,
        }

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/capture-sessions/{session_id}/cancel")
async def cancel_capture_session_endpoint(
    session_id: UUID,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import capture_service

        session = capture_service.cancel_capture_session(
            user=ctx.user, agency_id=ctx.agency_id, session_id=session_id
        )
        return {"session_id": str(session.id), "status": session.status}

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


# Panorama Processing, Direct Upload, Review & Versioning
@router.post("/scenes/{scene_id}/process", status_code=202)
async def process_scene_panorama_endpoint(
    scene_id: UUID,
    body: Optional[ProcessSceneBody] = None,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    ctx: RequestContext = Depends(require_agency_context),
):
    req = body or ProcessSceneBody()

    def _op():
        from apps.virtual_tours.services import panorama_service

        job = panorama_service.enqueue_scene_panorama_processing(
            user=ctx.user,
            agency_id=ctx.agency_id,
            scene_id=scene_id,
            session_id=req.session_id,
            reprocess=req.reprocess,
            idempotency_key=idempotency_key,
        )
        return serialize_processing_job(job)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/scenes/{scene_id}/reprocess", status_code=202)
async def reprocess_scene_panorama_endpoint(
    scene_id: UUID,
    body: Optional[ProcessSceneBody] = None,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    ctx: RequestContext = Depends(require_agency_context),
):
    req = body or ProcessSceneBody(reprocess=True)

    def _op():
        from apps.virtual_tours.services import panorama_service

        job = panorama_service.enqueue_scene_panorama_processing(
            user=ctx.user,
            agency_id=ctx.agency_id,
            scene_id=scene_id,
            session_id=req.session_id,
            reprocess=True,
            idempotency_key=idempotency_key,
        )
        return serialize_processing_job(job)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/scenes/{scene_id}/panoramas/upload", status_code=201)
async def upload_direct_panorama_endpoint(
    scene_id: UUID,
    file: UploadFile = File(...),
    ctx: RequestContext = Depends(require_agency_context),
):
    content = await read_upload_limited(file)

    def _op():
        from apps.virtual_tours.services import panorama_service

        pano = panorama_service.upload_direct_equirectangular_panorama(
            user=ctx.user,
            agency_id=ctx.agency_id,
            scene_id=scene_id,
            filename=file.filename or "panorama.jpg",
            content_type=file.content_type or "",
            content=content,
        )
        return serialize_panorama_version(pano, tour_id=str(pano.scene.tour_id))

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.get("/scenes/{scene_id}/panoramas")
async def list_scene_panoramas_endpoint(
    scene_id: UUID,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.selectors import get_scene_for_user

        scene = get_scene_for_user(user=ctx.user, agency_id=ctx.agency_id, scene_id=scene_id, require_edit=False)
        tour_id = str(scene.tour_id)
        return [
            serialize_panorama_version(p, tour_id=tour_id)
            for p in scene.panorama_versions.select_related("approved_by").order_by("-version")
        ]

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/scenes/{scene_id}/approve-panorama")
async def approve_panorama_endpoint(
    scene_id: UUID,
    body: Optional[PanoramaApproveBody] = None,
    ctx: RequestContext = Depends(require_agency_context),
):
    req = body or PanoramaApproveBody()

    def _op():
        from apps.virtual_tours.services import panorama_service

        pano = panorama_service.approve_scene_panorama(
            user=ctx.user,
            agency_id=ctx.agency_id,
            scene_id=scene_id,
            panorama_version_id=req.panorama_version_id,
        )
        return serialize_panorama_version(pano, tour_id=str(pano.scene.tour_id))

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/scenes/{scene_id}/reject-panorama")
async def reject_panorama_endpoint(
    scene_id: UUID,
    body: PanoramaRejectBody,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import panorama_service

        pano = panorama_service.reject_scene_panorama(
            user=ctx.user,
            agency_id=ctx.agency_id,
            scene_id=scene_id,
            reason=body.reason,
            panorama_version_id=body.panorama_version_id,
        )
        return serialize_panorama_version(pano, tour_id=str(pano.scene.tour_id))

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/scenes/{scene_id}/panoramas/{version_id}/restore")
async def restore_panorama_version_endpoint(
    scene_id: UUID,
    version_id: UUID,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import panorama_service

        pano = panorama_service.restore_panorama_version(
            user=ctx.user,
            agency_id=ctx.agency_id,
            scene_id=scene_id,
            version_id=version_id,
        )
        return serialize_panorama_version(pano, tour_id=str(pano.scene.tour_id))

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))

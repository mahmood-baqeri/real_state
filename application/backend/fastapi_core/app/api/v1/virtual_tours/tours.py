from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from app.core.django_bridge import run_django
from app.dependencies.auth import RequestContext, require_agency_context
from app.schemas.common import ok
from app.schemas.virtual_tours import (
    FloorCreateBody,
    FloorPatchBody,
    HotspotCreateBody,
    HotspotPatchBody,
    SceneCreateBody,
    SceneLinkCreateBody,
    ScenePatchBody,
    VirtualTourCreateBody,
    VirtualTourPatchBody,
)
from .serializers import (
    serialize_floor,
    serialize_hotspot,
    serialize_processing_job,
    serialize_publication,
    serialize_quality_report,
    serialize_scene,
    serialize_scene_link,
    serialize_virtual_tour_detail,
)

router = APIRouter(tags=["Virtual Tours Core"])


@router.get("/properties/{property_id}/virtual-tour")
async def get_property_virtual_tour_endpoint(
    property_id: UUID,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import tour_service
        from apps.virtual_tours.services.settings_service import (
            get_capture_policy,
            get_room_types_catalog,
            get_tour_limits,
        )

        tour = tour_service.get_tour_for_property(
            user=ctx.user,
            agency_id=ctx.agency_id,
            property_id=property_id,
        )
        if not tour:
            return {
                "tour": None,
                "config": {
                    "room_types": get_room_types_catalog(ctx.agency_id),
                    "capture_policy": get_capture_policy(agency_id=ctx.agency_id),
                    "limits": get_tour_limits(agency_id=ctx.agency_id),
                },
            }
        return serialize_virtual_tour_detail(tour)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/properties/{property_id}/virtual-tour", status_code=201)
async def create_property_virtual_tour_endpoint(
    property_id: UUID,
    body: VirtualTourCreateBody,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import tour_service

        tour = tour_service.create_virtual_tour(
            user=ctx.user,
            agency_id=ctx.agency_id,
            property_id=property_id,
            title=body.title,
            description=body.description,
            create_default_floor=body.create_default_floor,
        )
        return serialize_virtual_tour_detail(tour)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.get("/virtual-tours/{tour_id}")
async def get_virtual_tour_endpoint(
    tour_id: UUID,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.selectors import get_tour_for_user

        tour = get_tour_for_user(
            user=ctx.user,
            agency_id=ctx.agency_id,
            tour_id=tour_id,
            require_edit=False,
        )
        return serialize_virtual_tour_detail(tour)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.patch("/virtual-tours/{tour_id}")
async def patch_virtual_tour_endpoint(
    tour_id: UUID,
    body: VirtualTourPatchBody,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import tour_service

        tour = tour_service.update_virtual_tour(
            user=ctx.user,
            agency_id=ctx.agency_id,
            tour_id=tour_id,
            data=body.model_dump(exclude_none=True),
        )
        return serialize_virtual_tour_detail(tour)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.delete("/virtual-tours/{tour_id}")
async def archive_virtual_tour_endpoint(
    tour_id: UUID,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import tour_service

        tour = tour_service.archive_virtual_tour(
            user=ctx.user,
            agency_id=ctx.agency_id,
            tour_id=tour_id,
        )
        return {"archived": True, "tour_id": str(tour.id), "status": tour.status}

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


# Floors
@router.get("/virtual-tours/{tour_id}/floors")
async def list_floors_endpoint(
    tour_id: UUID,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import tour_service

        return [
            serialize_floor(f)
            for f in tour_service.list_floors(user=ctx.user, agency_id=ctx.agency_id, tour_id=tour_id)
        ]

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/virtual-tours/{tour_id}/floors", status_code=201)
async def create_floor_endpoint(
    tour_id: UUID,
    body: FloorCreateBody,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import tour_service

        f = tour_service.create_floor(
            user=ctx.user,
            agency_id=ctx.agency_id,
            tour_id=tour_id,
            title=body.title,
            order=body.order,
            elevation_m=Decimal(str(body.elevation_m)),
            description=body.description,
        )
        return serialize_floor(f)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.patch("/floors/{floor_id}")
async def patch_floor_endpoint(
    floor_id: UUID,
    body: FloorPatchBody,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import tour_service

        f = tour_service.update_floor(
            user=ctx.user,
            agency_id=ctx.agency_id,
            floor_id=floor_id,
            data=body.model_dump(exclude_none=True),
        )
        return serialize_floor(f)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.delete("/floors/{floor_id}")
async def delete_floor_endpoint(
    floor_id: UUID,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import tour_service

        tour_service.delete_floor(user=ctx.user, agency_id=ctx.agency_id, floor_id=floor_id)
        return {"deleted": True}

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


# Scenes
@router.get("/virtual-tours/{tour_id}/scenes")
async def list_scenes_endpoint(
    tour_id: UUID,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import tour_service

        return [
            serialize_scene(s, include_details=True)
            for s in tour_service.list_scenes(user=ctx.user, agency_id=ctx.agency_id, tour_id=tour_id)
        ]

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/virtual-tours/{tour_id}/scenes", status_code=201)
async def create_scene_endpoint(
    tour_id: UUID,
    body: SceneCreateBody,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import tour_service

        s = tour_service.create_scene(
            user=ctx.user,
            agency_id=ctx.agency_id,
            tour_id=tour_id,
            floor_id=body.floor_id,
            title=body.title,
            room_type=body.room_type,
            description=body.description,
            order=body.order,
            is_start_scene=body.is_start_scene,
            initial_yaw=body.initial_yaw,
            initial_pitch=body.initial_pitch,
        )
        return serialize_scene(s, include_details=True)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.get("/scenes/{scene_id}")
async def get_scene_endpoint(
    scene_id: UUID,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.selectors import get_scene_for_user

        s = get_scene_for_user(user=ctx.user, agency_id=ctx.agency_id, scene_id=scene_id, require_edit=False)
        return serialize_scene(s, include_details=True)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.patch("/scenes/{scene_id}")
async def patch_scene_endpoint(
    scene_id: UUID,
    body: ScenePatchBody,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import tour_service

        s = tour_service.update_scene(
            user=ctx.user,
            agency_id=ctx.agency_id,
            scene_id=scene_id,
            data=body.model_dump(exclude_none=True),
        )
        return serialize_scene(s, include_details=True)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.delete("/scenes/{scene_id}")
async def delete_scene_endpoint(
    scene_id: UUID,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import tour_service

        tour_service.delete_scene(user=ctx.user, agency_id=ctx.agency_id, scene_id=scene_id)
        return {"deleted": True}

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


# Navigation Links & Hotspots
@router.get("/virtual-tours/{tour_id}/links")
async def list_links_endpoint(
    tour_id: UUID,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import navigation_service

        return [
            serialize_scene_link(l)
            for l in navigation_service.list_tour_links(user=ctx.user, agency_id=ctx.agency_id, tour_id=tour_id)
        ]

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/virtual-tours/{tour_id}/links", status_code=201)
async def create_link_endpoint(
    tour_id: UUID,
    body: SceneLinkCreateBody,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import navigation_service

        lnk = navigation_service.create_scene_link(
            user=ctx.user,
            agency_id=ctx.agency_id,
            tour_id=tour_id,
            source_scene_id=body.source_scene_id,
            target_scene_id=body.target_scene_id,
            yaw=body.yaw,
            pitch=body.pitch,
            title=body.title,
            bidirectional=body.bidirectional,
        )
        return serialize_scene_link(lnk)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.delete("/links/{link_id}")
async def delete_link_endpoint(
    link_id: UUID,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import navigation_service

        navigation_service.delete_scene_link(user=ctx.user, agency_id=ctx.agency_id, link_id=link_id)
        return {"deleted": True}

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.get("/scenes/{scene_id}/hotspots")
async def list_hotspots_endpoint(
    scene_id: UUID,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import navigation_service

        return [
            serialize_hotspot(hs)
            for hs in navigation_service.list_scene_hotspots(user=ctx.user, agency_id=ctx.agency_id, scene_id=scene_id)
        ]

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/scenes/{scene_id}/hotspots", status_code=201)
async def create_hotspot_endpoint(
    scene_id: UUID,
    body: HotspotCreateBody,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import navigation_service

        hs = navigation_service.create_hotspot(
            user=ctx.user,
            agency_id=ctx.agency_id,
            scene_id=scene_id,
            kind=body.kind,
            title=body.title,
            body=body.body,
            yaw=body.yaw,
            pitch=body.pitch,
            target_scene_id=body.target_scene_id,
            metadata=body.metadata,
        )
        return serialize_hotspot(hs)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.patch("/hotspots/{hotspot_id}")
async def patch_hotspot_endpoint(
    hotspot_id: UUID,
    body: HotspotPatchBody,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import navigation_service

        hs = navigation_service.update_hotspot(
            user=ctx.user,
            agency_id=ctx.agency_id,
            hotspot_id=hotspot_id,
            data=body.model_dump(exclude_unset=True),
        )
        return serialize_hotspot(hs)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.delete("/hotspots/{hotspot_id}")
async def delete_hotspot_endpoint(
    hotspot_id: UUID,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import navigation_service

        navigation_service.delete_hotspot(user=ctx.user, agency_id=ctx.agency_id, hotspot_id=hotspot_id)
        return {"deleted": True}

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


# Processing Jobs Monitoring
@router.get("/virtual-tours/{tour_id}/jobs")
async def list_jobs_endpoint(
    tour_id: UUID,
    state: str | None = Query(default=None),
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.selectors import get_tour_for_user

        tour = get_tour_for_user(user=ctx.user, agency_id=ctx.agency_id, tour_id=tour_id, require_edit=False)
        qs = tour.processing_jobs.select_related("scene").order_by("-created_at")
        if state:
            qs = qs.filter(state=state)
        return [serialize_processing_job(j) for j in qs[:50]]

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.get("/processing-jobs/{job_id}")
async def get_processing_job_endpoint(
    job_id: UUID,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.selectors import get_processing_job_for_user

        job = get_processing_job_for_user(user=ctx.user, agency_id=ctx.agency_id, job_id=job_id, require_edit=False)
        return serialize_processing_job(job)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/processing-jobs/{job_id}/retry")
async def retry_processing_job_endpoint(
    job_id: UUID,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import panorama_service

        job = panorama_service.retry_processing_job(user=ctx.user, agency_id=ctx.agency_id, job_id=job_id)
        return serialize_processing_job(job)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/processing-jobs/{job_id}/cancel")
async def cancel_processing_job_endpoint(
    job_id: UUID,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import panorama_service

        job = panorama_service.cancel_processing_job(user=ctx.user, agency_id=ctx.agency_id, job_id=job_id)
        return serialize_processing_job(job)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


# Quality Report, Publication & Internal Analytics Summary
@router.get("/virtual-tours/{tour_id}/quality-report")
async def get_quality_report_endpoint(
    tour_id: UUID,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.selectors import get_tour_for_user
        from apps.virtual_tours.services.quality_service import generate_tour_quality_report

        tour = get_tour_for_user(user=ctx.user, agency_id=ctx.agency_id, tour_id=tour_id, require_edit=False)
        report = generate_tour_quality_report(tour, actor=ctx.user)
        return serialize_quality_report(report)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/virtual-tours/{tour_id}/publish")
async def publish_virtual_tour_endpoint(
    tour_id: UUID,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import publication_service

        pub = publication_service.publish_virtual_tour(user=ctx.user, agency_id=ctx.agency_id, tour_id=tour_id)
        return serialize_publication(pub)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/virtual-tours/{tour_id}/unpublish")
async def unpublish_virtual_tour_endpoint(
    tour_id: UUID,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import publication_service

        tour = publication_service.unpublish_virtual_tour(user=ctx.user, agency_id=ctx.agency_id, tour_id=tour_id)
        return {"tour_id": str(tour.id), "status": tour.status}

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.get("/virtual-tours/{tour_id}/publication")
async def get_publication_status_endpoint(
    tour_id: UUID,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.selectors import get_tour_for_user

        tour = get_tour_for_user(user=ctx.user, agency_id=ctx.agency_id, tour_id=tour_id, require_edit=False)
        pubs = list(tour.publications.select_related("published_by").order_by("-version")[:10])
        active_pub = next((p for p in pubs if p.is_active), None)
        return {
            "tour_id": str(tour.id),
            "status": tour.status,
            "active_publication": serialize_publication(active_pub) if active_pub else None,
            "history": [serialize_publication(p) for p in pubs],
        }

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.get("/virtual-tours/{tour_id}/analytics")
async def get_tour_analytics_endpoint(
    tour_id: UUID,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.virtual_tours.services import analytics_service

        return analytics_service.get_tour_analytics_summary(
            user=ctx.user,
            agency_id=ctx.agency_id,
            tour_id=tour_id,
        )

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))

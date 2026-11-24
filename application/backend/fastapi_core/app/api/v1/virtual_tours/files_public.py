from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request, Response
from app.core.django_bridge import run_django
from app.dependencies.auth import RequestContext, get_optional_context
from app.schemas.common import ok
from app.schemas.virtual_tours import TourAnalyticsEventBody

router = APIRouter(tags=["Virtual Tours Public & Gated Assets"])


@router.get("/public/virtual-tours/{public_slug}")
async def get_public_virtual_tour_by_slug_endpoint(public_slug: str):
    def _op():
        from apps.virtual_tours.services import publication_service

        return publication_service.get_public_virtual_tour_by_slug(public_slug=public_slug)

    return ok(await run_django(_op))


@router.get("/public/properties/{property_id}/virtual-tour")
async def get_public_property_virtual_tour_endpoint(property_id: UUID):
    def _op():
        from apps.virtual_tours.services import publication_service

        return publication_service.get_public_property_virtual_tour(property_id=property_id)

    return ok(await run_django(_op))


@router.post("/public/virtual-tours/{tour_id}/analytics", status_code=201)
async def record_public_tour_analytics_endpoint(
    tour_id: UUID,
    body: TourAnalyticsEventBody,
    request: Request,
):
    client_ip = request.client.host if request.client else ""
    user_agent = request.headers.get("user-agent", "")

    def _op():
        from apps.virtual_tours.services import analytics_service

        ev = analytics_service.record_tour_analytics_event(
            tour_id=tour_id,
            event_type=body.event_type,
            session_key=body.session_key,
            scene_id=body.scene_id,
            hotspot_id=body.hotspot_id,
            device_type=body.device_type,
            duration_sec=body.duration_sec,
            client_ip=client_ip,
            user_agent=user_agent,
        )
        return {"recorded": True, "id": str(ev.id)}

    return ok(await run_django(_op))


@router.get("/virtual-tours/files/{kind}/{object_id}")
async def serve_virtual_tour_file_endpoint(
    kind: str,
    object_id: UUID,
    token: Optional[str] = Query(default=None),
    ctx: RequestContext = Depends(get_optional_context),
):
    """
    Gated binary asset endpoint for virtual tours.
    - Raw capture frames ('capture') NEVER leak publicly: requires authenticated tenant access OR short-lived signed HMAC token.
    - 'panorama' / 'panorama-thumb': allows signed token, authenticated tenant access, OR public access ONLY if tour & property are both publicly published and panorama is current & approved.
    """
    def _op():
        from apps.virtual_tours.models import CaptureImage, PanoramaVersion, VirtualTour
        from apps.virtual_tours.policies.access import (
            assert_tour_view_access,
            is_property_publicly_publishable,
            verify_asset_access_token,
        )
        from apps.virtual_tours.services.settings_service import get_tour_limits
        from common.exceptions import NotFoundDomainError, PermissionDeniedDomainError
        from integrations.registry import get_storage_provider

        storage = get_storage_provider()

        if kind == "capture":
            img = (
                CaptureImage.objects.select_related("session", "session__tour", "session__tour__property")
                .filter(id=object_id)
                .first()
            )
            if not img:
                raise NotFoundDomainError("تصویر خام مورد نظر یافت نشد.")
            tour = img.session.tour
            has_token = bool(
                token
                and verify_asset_access_token(
                    token=token, kind="capture", object_id=str(object_id), tour_id=str(tour.id)
                )
            )
            if not has_token:
                if not ctx.is_authenticated:
                    raise PermissionDeniedDomainError("دسترسی به تصاویر خام بدون احراز هویت مجاز نیست.")
                assert_tour_view_access(user=ctx.user, agency_id=ctx.agency_id, prop=tour.property)

            data = storage.get_bytes(file_key=img.storage_key)
            return data, img.mime_type or "image/jpeg", img.filename or "capture.jpg", "private, max-age=300"

        if kind in ("panorama", "panorama-thumb"):
            pano = (
                PanoramaVersion.objects.select_related("scene", "scene__tour", "scene__tour__property")
                .filter(id=object_id)
                .first()
            )
            if not pano:
                raise NotFoundDomainError("فایل پانورامای مورد نظر یافت نشد.")
            tour = pano.scene.tour
            storage_key = pano.thumbnail_key if kind == "panorama-thumb" else pano.storage_key
            if not storage_key:
                raise NotFoundDomainError("فایل تصویر برای این نسخه پانوراما موجود نیست.")

            has_token = bool(
                token
                and verify_asset_access_token(
                    token=token, kind=kind, object_id=str(object_id), tour_id=str(tour.id)
                )
            )
            if not has_token:
                if ctx.is_authenticated and ctx.agency_id:
                    assert_tour_view_access(user=ctx.user, agency_id=ctx.agency_id, prop=tour.property)
                else:
                    limits = get_tour_limits(agency_id=tour.agency_id, tour=tour)
                    state_ok = pano.state == PanoramaVersion.State.APPROVED or (
                        not limits["require_manager_approval"] and pano.state == PanoramaVersion.State.REVIEW
                    )
                    if not (
                        tour.status == VirtualTour.Status.PUBLISHED
                        and is_property_publicly_publishable(tour.property)
                        and pano.is_current
                        and state_ok
                    ):
                        raise PermissionDeniedDomainError("دسترسی عمومی به این پانوراما مجاز نیست.")

            data = storage.get_bytes(file_key=storage_key)
            fname = f"panorama-{pano.version}{'-thumb' if kind == 'panorama-thumb' else ''}.jpg"
            cache_ctrl = "public, max-age=600" if tour.status == VirtualTour.Status.PUBLISHED else "private, max-age=120"
            return data, "image/jpeg", fname, cache_ctrl

        if kind in ("floorplan", "floorplan-preview"):
            from apps.virtual_tours.models import FloorPlanAsset

            fp = (
                FloorPlanAsset.objects.select_related("tour", "tour__property")
                .filter(id=object_id)
                .first()
            )
            if not fp:
                raise NotFoundDomainError("فایل پلان مورد نظر یافت نشد.")
            tour = fp.tour
            storage_key = (fp.preview_storage_key or fp.storage_key) if kind == "floorplan-preview" else fp.storage_key
            mime_out = "image/png" if (kind == "floorplan-preview" and fp.file_type == "pdf") else (fp.mime_type or "image/png")

            has_token = bool(
                token
                and verify_asset_access_token(
                    token=token, kind=kind, object_id=str(object_id), tour_id=str(tour.id)
                )
            )
            if not has_token:
                if ctx.is_authenticated and ctx.agency_id:
                    assert_tour_view_access(user=ctx.user, agency_id=ctx.agency_id, prop=tour.property)
                else:
                    if not (
                        tour.status == VirtualTour.Status.PUBLISHED
                        and is_property_publicly_publishable(tour.property)
                        and fp.is_active
                    ):
                        raise PermissionDeniedDomainError("دسترسی عمومی به پلان این ملک مجاز نیست.")

            data = storage.get_bytes(file_key=storage_key)
            cache_ctrl = "public, max-age=600" if tour.status == VirtualTour.Status.PUBLISHED else "private, max-age=120"
            return data, mime_out, fp.filename or "floorplan.png", cache_ctrl

        if kind == "model-glb":
            from apps.virtual_tours.models import GeneratedModelAsset

            model_asset = (
                GeneratedModelAsset.objects.select_related("tour", "tour__property")
                .filter(id=object_id)
                .first()
            )
            if not model_asset or not model_asset.storage_key:
                raise NotFoundDomainError("فایل مدل سه‌بعدی مورد نظر یافت نشد.")
            tour = model_asset.tour

            has_token = bool(
                token
                and verify_asset_access_token(
                    token=token, kind=kind, object_id=str(object_id), tour_id=str(tour.id)
                )
            )
            if not has_token:
                if ctx.is_authenticated and ctx.agency_id:
                    assert_tour_view_access(user=ctx.user, agency_id=ctx.agency_id, prop=tour.property)
                else:
                    state_ok = model_asset.state in (
                        GeneratedModelAsset.State.APPROVED,
                        GeneratedModelAsset.State.READY,
                    )
                    if not (
                        tour.status == VirtualTour.Status.PUBLISHED
                        and is_property_publicly_publishable(tour.property)
                        and model_asset.is_current
                        and state_ok
                    ):
                        raise PermissionDeniedDomainError("دسترسی عمومی به مدل سه‌بعدی این ملک مجاز نیست.")

            data = storage.get_bytes(file_key=model_asset.storage_key)
            fname = f"dollhouse-v{model_asset.version}.glb"
            cache_ctrl = "public, max-age=600" if tour.status == VirtualTour.Status.PUBLISHED else "private, max-age=120"
            return data, "model/gltf-binary", fname, cache_ctrl

        if kind in ("scan-raw", "scan-preview-glb", "scan-density-map"):
            from apps.virtual_tours.models import ScanAsset

            scan = (
                ScanAsset.objects.select_related("tour", "tour__property")
                .filter(id=object_id)
                .first()
            )
            if not scan:
                raise NotFoundDomainError("فایل اسکن سه‌بعدی یافت نشد.")
            tour = scan.tour
            has_token = bool(
                token
                and verify_asset_access_token(
                    token=token, kind=kind, object_id=str(object_id), tour_id=str(tour.id)
                )
            )
            if not has_token:
                if not ctx.is_authenticated:
                    raise PermissionDeniedDomainError("دسترسی عمومی به فایل‌های اسکن سه‌بعدی بدون توکن مجاز نیست.")
                assert_tour_view_access(user=ctx.user, agency_id=ctx.agency_id, prop=tour.property)

            if kind == "scan-raw":
                storage_key = scan.storage_key
                mime_out = scan.mime_type or "application/octet-stream"
                fname_out = scan.filename or f"scan.{scan.format}"
            elif kind == "scan-preview-glb":
                storage_key = scan.preview_glb_key
                mime_out = "model/gltf-binary"
                fname_out = f"scan-{scan.id}-preview.glb"
            else:
                storage_key = scan.density_map_key
                mime_out = "image/png"
                fname_out = f"scan-{scan.id}-density.png"

            if not storage_key:
                raise NotFoundDomainError("خروجی پردازش برای این اسکن هنوز آماده نشده است.")
            data = storage.get_bytes(file_key=storage_key)
            return data, mime_out, fname_out, "private, max-age=300"

        raise NotFoundDomainError("نوع فایل درخواستی پشتیبانی نمی‌شود.")

    raw_bytes, mime, filename, cache_ctrl = await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None)
    return Response(
        content=raw_bytes,
        media_type=mime,
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": cache_ctrl,
            "X-Content-Type-Options": "nosniff",
        },
    )

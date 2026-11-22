import asyncio
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
import jwt
from app.core.django_bridge import run_django
from app.core.security import decode_jwt_token

router = APIRouter(tags=["Realtime WebSocket"])


@router.websocket("/ws/notifications")
async def notifications_ws(websocket: WebSocket, token: str = Query(default="")):
    try:
        payload = decode_jwt_token(token, expected_type="access")
        user_id = str(payload.get("user_id") or "")
        if not user_id:
            await websocket.close(code=4001)
            return
    except jwt.PyJWTError:
        await websocket.close(code=4001)
        return

    await websocket.accept()
    try:
        while True:
            def _fetch():
                from apps.notifications.models import NotificationMessage

                qs = NotificationMessage.objects.filter(recipient_id=user_id, is_read=False)
                latest = qs.order_by("-created_at")[:5]
                return {
                    "unread_count": qs.count(),
                    "latest": [
                        {
                            "id": str(n.id),
                            "title": n.title,
                            "body": n.body,
                            "created_at": n.created_at.isoformat(),
                        }
                        for n in latest
                    ],
                }

            snap = await run_django(_fetch)
            await websocket.send_json({"event": "notification_snapshot", "data": snap})
            await asyncio.sleep(15)
    except WebSocketDisconnect:
        return


@router.websocket("/ws/virtual-tours/{tour_id}/jobs")
async def virtual_tour_jobs_ws(
    websocket: WebSocket,
    tour_id: str,
    token: str = Query(default=""),
    agency_id: str = Query(default=""),
):
    from uuid import UUID

    try:
        payload = decode_jwt_token(token, expected_type="access")
        user_id = str(payload.get("user_id") or "")
        tour_uuid = UUID(tour_id)
        parsed_agency_id = UUID(agency_id) if agency_id else None
        if not user_id:
            await websocket.close(code=4001)
            return
    except (jwt.PyJWTError, ValueError):
        await websocket.close(code=4001)
        return

    def _authorize():
        from apps.accounts.models import AgencyMembership, User
        from apps.virtual_tours.selectors import get_tour_for_user

        user = User.objects.filter(id=user_id, is_active=True).first()
        if not user:
            return None
        resolved_agency = parsed_agency_id
        if not resolved_agency:
            m = AgencyMembership.objects.filter(
                user=user, status=AgencyMembership.Status.ACTIVE
            ).first()
            resolved_agency = m.agency_id if m else None
        try:
            tour = get_tour_for_user(
                user=user,
                agency_id=resolved_agency,
                tour_id=tour_uuid,
                require_edit=False,
            )
            return resolved_agency, str(tour.id)
        except Exception:
            return None

    auth_res = await run_django(_authorize)
    if not auth_res:
        await websocket.close(code=4003)
        return

    resolved_agency, _ = auth_res
    await websocket.accept()
    try:
        while True:
            def _fetch_jobs():
                from apps.virtual_tours.models import ProcessingJob, VirtualTour
                from app.api.v1.virtual_tours.serializers import serialize_processing_job

                tour = VirtualTour.objects.filter(id=tour_uuid).first()
                if not tour:
                    return None
                jobs = list(tour.processing_jobs.select_related("scene").order_by("-created_at")[:25])
                has_active = any(
                    j.state in (ProcessingJob.State.QUEUED, ProcessingJob.State.RUNNING) for j in jobs
                )
                return {
                    "tour_id": str(tour.id),
                    "tour_status": tour.status,
                    "has_active_jobs": has_active,
                    "jobs": [serialize_processing_job(j) for j in jobs],
                }

            snap = await run_django(_fetch_jobs, agency_id=resolved_agency)
            if snap is None:
                await websocket.close(code=4004)
                return
            await websocket.send_json({"event": "tour_jobs_snapshot", "data": snap})
            await asyncio.sleep(2 if snap["has_active_jobs"] else 8)
    except WebSocketDisconnect:
        return


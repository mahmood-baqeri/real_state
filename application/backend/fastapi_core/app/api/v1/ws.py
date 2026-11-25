"""ارتباط زندهٔ اعلان‌ها و وضعیت پردازش تور با بلیت یک‌بارمصرف."""

import asyncio
from uuid import UUID
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import jwt

from app.core.config import settings
from app.core.django_bridge import run_django
from app.core.security import decode_jwt_token

router = APIRouter(tags=["Realtime WebSocket"])


async def _wait_for_disconnect(websocket: WebSocket) -> None:
    """قطع اتصال مشتری را حتی در نبود پیام خروجی تشخیص می‌دهد."""
    while (await websocket.receive())["type"] != "websocket.disconnect":
        pass


async def _socket_session_is_active(*, user_id: UUID, session_jti: str, agency_id: UUID | None) -> bool:
    def _check():
        from django.utils import timezone
        from apps.accounts.models import User, UserSession
        user = User.objects.filter(id=user_id, is_active=True, status=User.Status.ACTIVE).first()
        session = UserSession.objects.filter(
            user_id=user_id, jti=session_jti, revoked_at__isnull=True
        ).first()
        return bool(user and session and (not session.expires_at or session.expires_at > timezone.now()))
    return await run_django(_check, agency_id=agency_id, user_id=user_id)


def _ticket_from_protocols(websocket: WebSocket) -> str:
    protocols = websocket.headers.get("sec-websocket-protocol", "")
    for protocol in protocols.split(","):
        protocol = protocol.strip()
        if protocol.startswith("ticket."):
            return protocol[len("ticket."):]
    return ""


async def _authenticate_socket(websocket: WebSocket):
    origin = websocket.headers.get("origin")
    if origin and origin not in settings.CORS_ALLOWED_ORIGINS:
        await websocket.close(code=4003)
        return None
    ticket_token = _ticket_from_protocols(websocket)
    if not ticket_token:
        await websocket.close(code=4001)
        return None
    try:
        payload = decode_jwt_token(ticket_token, expected_type="ws_ticket")
        user_id = UUID(str(payload.get("user_id")))
        ticket_id = UUID(str(payload.get("ticket_id")))
        agency_id = UUID(str(payload.get("agency_id"))) if payload.get("agency_id") else None
        session_jti = str(payload.get("session_jti") or "")
        if not session_jti:
            raise ValueError("missing session")
    except (jwt.PyJWTError, ValueError, TypeError):
        await websocket.close(code=4001)
        return None

    def _consume_ticket():
        from django.db import transaction
        from django.utils import timezone
        from apps.accounts.models import User, UserSession, WebSocketTicket
        with transaction.atomic():
            ticket = WebSocketTicket.objects.select_for_update().filter(
                id=ticket_id,
                ticket_jti=ticket_id,
                user_id=user_id,
                session_jti=session_jti,
                agency_id=agency_id,
                used_at__isnull=True,
                expires_at__gt=timezone.now(),
            ).first()
            if not ticket:
                return False
            user = User.objects.filter(id=user_id, is_active=True, status=User.Status.ACTIVE).first()
            session = UserSession.objects.filter(
                user_id=user_id, jti=session_jti, revoked_at__isnull=True
            ).first()
            if not user or not session or (session.expires_at and session.expires_at <= timezone.now()):
                return False
            ticket.used_at = timezone.now()
            ticket.save(update_fields=["used_at"])
            return True

    valid = await run_django(_consume_ticket, agency_id=agency_id, user_id=user_id)
    if not valid:
        await websocket.close(code=4001)
        return None
    return payload


@router.websocket("/ws/notifications")
async def notifications_ws(websocket: WebSocket):
    """اعلان‌های کاربر را تا قطع اتصال یا انقضای نشست ارسال می‌کند."""
    payload = await _authenticate_socket(websocket)
    if not payload:
        return
    user_id = UUID(str(payload["user_id"]))
    session_jti = str(payload["session_jti"])
    agency_id = UUID(str(payload["agency_id"])) if payload.get("agency_id") else None
    await websocket.accept(subprotocol="bonyan.auth")
    import redis.asyncio as redis_async
    client = redis_async.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = client.pubsub()
    channel = f"bonyan:notifications:{user_id}"
    disconnect = asyncio.create_task(_wait_for_disconnect(websocket))
    try:
        def _snapshot():
            from apps.notifications.models import NotificationMessage
            def _read():
                qs = NotificationMessage.objects.filter(recipient_id=user_id, is_read=False)
                latest = list(qs.order_by("-created_at")[:5])
                return {"unread_count": qs.count(), "latest": [
                    {"id": str(n.id), "title": n.title, "body": n.body, "created_at": n.created_at.isoformat()}
                    for n in latest
                ]}
            if agency_id:
                return _read()
            from common.tenant.context import tenant_bypass
            with tenant_bypass(reason="notification_websocket_snapshot"):
                return _read()
        await pubsub.subscribe(channel)
        snap = await run_django(_snapshot, agency_id=agency_id, user_id=user_id)
        await websocket.send_json({"event": "notification_snapshot", "data": snap})
        last_session_check = asyncio.get_running_loop().time()
        while not disconnect.done():
            if asyncio.get_running_loop().time() - last_session_check >= 60:
                if not await _socket_session_is_active(user_id=user_id, session_jti=session_jti, agency_id=agency_id):
                    await websocket.close(code=4001, reason="Session revoked or expired")
                    return
                last_session_check = asyncio.get_running_loop().time()
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message.get("type") == "message":
                snap = await run_django(_snapshot, agency_id=agency_id, user_id=user_id)
                await websocket.send_json({"event": "notification_snapshot", "data": snap})
    except WebSocketDisconnect:
        return
    finally:
        disconnect.cancel()
        await asyncio.gather(disconnect, return_exceptions=True)
        try:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()
            await client.aclose()
        except Exception:
            pass


@router.websocket("/ws/virtual-tours/{tour_id}/jobs")
async def virtual_tour_jobs_ws(websocket: WebSocket, tour_id: str):
    """وضعیت پردازش تور مجاز را تا قطع اتصال به‌روز می‌کند."""
    payload = await _authenticate_socket(websocket)
    if not payload:
        return
    try:
        tour_uuid = UUID(tour_id)
        user_id = UUID(str(payload["user_id"]))
        session_jti = str(payload["session_jti"])
        agency_id = UUID(str(payload["agency_id"])) if payload.get("agency_id") else None
    except (ValueError, TypeError):
        await websocket.close(code=4001)
        return

    def _authorize():
        from apps.accounts.models import User
        from apps.virtual_tours.selectors import get_tour_for_user
        user = User.objects.filter(id=user_id, is_active=True).first()
        if not user:
            return None
        try:
            tour = get_tour_for_user(
                user=user, agency_id=agency_id, tour_id=tour_uuid, require_edit=False
            )
            return str(tour.id)
        except Exception:
            return None

    authorized_tour = await run_django(_authorize, agency_id=agency_id, user_id=user_id)
    if not authorized_tour:
        await websocket.close(code=4003)
        return
    await websocket.accept(subprotocol="bonyan.auth")
    disconnect = asyncio.create_task(_wait_for_disconnect(websocket))
    try:
        while not disconnect.done():
            if not await _socket_session_is_active(user_id=user_id, session_jti=session_jti, agency_id=agency_id):
                await websocket.close(code=4001, reason="Session revoked or expired")
                return
            def _fetch_jobs():
                from apps.virtual_tours.models import ProcessingJob, VirtualTour
                from app.api.v1.virtual_tours.serializers import serialize_processing_job
                tour = VirtualTour.objects.filter(id=tour_uuid).first()
                if not tour:
                    return None
                jobs = list(tour.processing_jobs.select_related("scene").order_by("-created_at")[:25])
                has_active = any(
                    job.state in (ProcessingJob.State.QUEUED, ProcessingJob.State.RUNNING)
                    for job in jobs
                )
                return {
                    "tour_id": str(tour.id),
                    "tour_status": tour.status,
                    "has_active_jobs": has_active,
                    "jobs": [serialize_processing_job(job) for job in jobs],
                }
            snap = await run_django(_fetch_jobs, agency_id=agency_id, user_id=user_id)
            if snap is None:
                await websocket.close(code=4004)
                return
            await websocket.send_json({"event": "tour_jobs_snapshot", "data": snap})
            await asyncio.wait({disconnect}, timeout=2 if snap["has_active_jobs"] else 8)
    except WebSocketDisconnect:
        return
    finally:
        disconnect.cancel()
        await asyncio.gather(disconnect, return_exceptions=True)

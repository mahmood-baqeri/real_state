# Path: backend/fastapi_core/app/api/v1/notifications.py

from uuid import UUID
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from app.core.django_bridge import run_django
from app.dependencies.auth import RequestContext, get_current_context
from app.schemas.common import ok

router = APIRouter(prefix="/notifications", tags=["Notifications & Messaging"])


class NotificationCreateBody(BaseModel):
    recipient_user_id: UUID
    title: str
    body: str
    channel: str = "IN_APP"


def _ser_notif(n) -> dict:
    return {
        "id": str(n.id),
        "agency_id": str(n.agency_id) if n.agency_id else None,
        "agency_name": n.agency.name if n.agency else None,
        "channel": n.channel,
        "title": n.title,
        "body": n.body,
        "delivery_status": n.delivery_status,
        "is_read": n.is_read,
        "read_at": n.read_at.isoformat() if n.read_at else None,
        "created_at": n.created_at.isoformat(),
    }


@router.get("")
async def list_notifications_endpoint(
    unread_only: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    ctx: RequestContext = Depends(get_current_context),
):
    def _op():
        from apps.notifications.services import list_notifications_for_user
        from common.pagination import paginate_queryset

        qs = list_notifications_for_user(user=ctx.user, unread_only=unread_only)
        return paginate_queryset(qs, page=page, page_size=page_size, serializer_fn=_ser_notif)

    items, meta = await run_django(_op)
    return ok(items, meta=meta)


@router.post("", status_code=201)
async def send_notification_endpoint(
    body: NotificationCreateBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.notifications.services import send_notification

        msg = send_notification(
            recipient_user_id=body.recipient_user_id,
            title=body.title,
            body=body.body,
            channel=body.channel,
            agency_id=ctx.agency_id,
            actor=ctx.user,
        )
        return _ser_notif(msg)

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/{notification_id}/read")
async def read_notification_endpoint(
    notification_id: UUID, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.notifications.services import mark_notification_read

        msg = mark_notification_read(user=ctx.user, notification_id=notification_id)
        return _ser_notif(msg)

    return ok(await run_django(_op))


@router.post("/read-all")
async def read_all_notifications_endpoint(ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.notifications.services import mark_all_notifications_read

        count = mark_all_notifications_read(user=ctx.user)
        return {"marked_count": count}

    return ok(await run_django(_op))

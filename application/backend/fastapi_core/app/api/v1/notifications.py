from typing import Optional
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


class SmsTemplateUpsertBody(BaseModel):
    key: str
    event_type: str = "GENERAL"
    name_fa: str
    body_template: str
    sample_tokens: list[str] = []
    provider_template_id: str = ""
    is_active: bool = True


class SmsTestBody(BaseModel):
    phone_number: str
    template_key: Optional[str] = None
    message: Optional[str] = None


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


def _ser_sms_template(t) -> dict:
    return {
        "id": str(t.id),
        "key": t.key,
        "event_type": t.event_type,
        "name_fa": t.name_fa,
        "body_template": t.body_template,
        "sample_tokens": t.sample_tokens or [],
        "provider_template_id": t.provider_template_id,
        "is_active": t.is_active,
        "updated_at": t.updated_at.isoformat(),
    }


def _ser_sms_log(l) -> dict:
    return {
        "id": str(l.id),
        "recipient_masked": l.recipient_masked,
        "event_type": l.event_type,
        "template_key": l.template_key,
        "provider_key": l.provider_key,
        "status": l.status,
        "message_id": l.message_id,
        "cost_amount": str(l.cost_amount),
        "error_message": l.error_message,
        "agency_name": l.agency.name if l.agency else None,
        "actor_name": l.actor.full_name if l.actor else None,
        "created_at": l.created_at.isoformat(),
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


@router.get("/sms/templates")
async def list_sms_templates_endpoint(ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.notifications.services import list_sms_templates

        return [_ser_sms_template(t) for t in list_sms_templates(user=ctx.user)]

    return ok(await run_django(_op))


@router.post("/sms/templates", status_code=201)
async def upsert_sms_template_endpoint(
    body: SmsTemplateUpsertBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.notifications.services import upsert_sms_template

        return _ser_sms_template(upsert_sms_template(user=ctx.user, data=body.model_dump()))

    return ok(await run_django(_op))


@router.get("/sms/logs")
async def list_sms_logs_endpoint(
    event_type: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    ctx: RequestContext = Depends(get_current_context),
):
    def _op():
        from apps.notifications.services import list_sms_logs
        from common.pagination import paginate_queryset

        qs = list_sms_logs(
            user=ctx.user, agency_id=ctx.agency_id, event_type=event_type, status_filter=status
        )
        return paginate_queryset(qs, page=page, page_size=page_size, serializer_fn=_ser_sms_log)

    items, meta = await run_django(_op, agency_id=ctx.agency_id)
    return ok(items, meta=meta)


@router.get("/sms/settings")
async def get_sms_settings_endpoint(ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.notifications.services import get_sms_settings_and_stats

        return get_sms_settings_and_stats(user=ctx.user, agency_id=ctx.agency_id)

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/sms/test")
async def send_test_sms_endpoint(
    body: SmsTestBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.notifications.services import send_test_sms

        return send_test_sms(
            user=ctx.user,
            agency_id=ctx.agency_id,
            phone_number=body.phone_number,
            template_key=body.template_key,
            message=body.message,
        )

    return ok(await run_django(_op, agency_id=ctx.agency_id))

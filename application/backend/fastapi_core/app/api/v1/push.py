# Path: backend/fastapi_core/app/api/v1/push.py

from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.core.django_bridge import run_django
from app.dependencies.auth import RequestContext, get_current_context
from app.schemas.common import ok

router = APIRouter(prefix="/push", tags=["Web Push & Notification Preferences"])


class PushSubscribeBody(BaseModel):
    endpoint: str
    p256dh: str
    auth: str
    device_label: str = "Web Browser"


class PushUnsubscribeBody(BaseModel):
    endpoint: str


class NotificationPreferencePatchBody(BaseModel):
    in_app_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None


@router.get("/vapid-public-key")
async def vapid_public_key_endpoint():
    def _op():
        from apps.notifications.services import get_vapid_public_key

        return {"public_key": get_vapid_public_key()}

    return ok(await run_django(_op))


@router.get("/subscriptions")
async def list_subscriptions_endpoint(ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.notifications.services import list_user_push_subscriptions

        return [
            {
                "id": str(s.id),
                "endpoint": s.endpoint,
                "device_label": s.device_label,
                "is_active": s.is_active,
                "last_used_at": s.last_used_at.isoformat() if s.last_used_at else None,
                "created_at": s.created_at.isoformat(),
            }
            for s in list_user_push_subscriptions(user=ctx.user)
        ]

    return ok(await run_django(_op))


@router.post("/subscribe", status_code=201)
async def subscribe_push_endpoint(body: PushSubscribeBody, ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.notifications.services import register_push_subscription

        sub = register_push_subscription(
            user=ctx.user,
            agency_id=ctx.agency_id,
            endpoint=body.endpoint,
            p256dh=body.p256dh,
            auth=body.auth,
            device_label=body.device_label,
        )
        return {"id": str(sub.id), "device_label": sub.device_label, "is_active": sub.is_active}

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/unsubscribe")
async def unsubscribe_push_endpoint(body: PushUnsubscribeBody, ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.notifications.services import unregister_push_subscription

        count = unregister_push_subscription(user=ctx.user, endpoint=body.endpoint)
        return {"deactivated": count}

    return ok(await run_django(_op))


@router.get("/preferences")
async def get_preferences_endpoint(ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.notifications.services import get_or_create_preferences

        p = get_or_create_preferences(user=ctx.user)
        return {
            "in_app_enabled": p.in_app_enabled,
            "push_enabled": p.push_enabled,
            "sms_enabled": p.sms_enabled,
            "email_enabled": p.email_enabled,
            "quiet_hours_start": p.quiet_hours_start,
            "quiet_hours_end": p.quiet_hours_end,
        }

    return ok(await run_django(_op))


@router.patch("/preferences")
async def patch_preferences_endpoint(
    body: NotificationPreferencePatchBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.notifications.services import update_preferences

        p = update_preferences(user=ctx.user, updates=body.model_dump(exclude_none=True))
        return {
            "in_app_enabled": p.in_app_enabled,
            "push_enabled": p.push_enabled,
            "sms_enabled": p.sms_enabled,
            "email_enabled": p.email_enabled,
            "quiet_hours_start": p.quiet_hours_start,
            "quiet_hours_end": p.quiet_hours_end,
        }

    return ok(await run_django(_op))


@router.post("/test")
async def test_push_endpoint(ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.notifications.services import send_notification

        msg = send_notification(
            recipient_user_id=ctx.user.id,
            title="تست اعلان لحظه‌ای بنیان ملک",
            body="سرویس اعلان مرورگر و پوش نوتیفیکیشن با موفقیت پیکربندی شده است.",
            channel="PUSH",
            agency_id=ctx.agency_id,
            actor=ctx.user,
        )
        return {"id": str(msg.id), "delivery_status": msg.delivery_status}

    return ok(await run_django(_op, agency_id=ctx.agency_id))

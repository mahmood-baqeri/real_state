import base64
import hashlib
import os
from typing import Optional
from uuid import UUID
from django.db import transaction
from django.utils import timezone
from apps.accounts.models import User
from common.exceptions import NotFoundDomainError
from integrations.registry import get_sms_provider
from .models import NotificationMessage, NotificationPreference, PushSubscription
from .tasks import dispatch_web_push_task


def get_vapid_public_key() -> str:
    env_key = os.environ.get("VAPID_PUBLIC_KEY", "").strip()
    if env_key:
        return env_key
    # Deterministic valid 65-byte uncompressed P-256 public key shape for local dev PushManager
    digest = hashlib.sha256(b"bonyan-melk-dev-vapid-key").digest() + hashlib.sha256(b"bonyan-melk-dev-vapid-y").digest()
    uncompressed = b"\x04" + digest[:64]
    return base64.urlsafe_b64encode(uncompressed).decode("ascii").rstrip("=")


def list_notifications_for_user(*, user: User, unread_only: bool = False):
    qs = NotificationMessage.objects.filter(recipient=user).select_related("agency")
    if unread_only:
        qs = qs.filter(is_read=False)
    return qs.order_by("-created_at")


@transaction.atomic
def send_notification(
    *,
    recipient_user_id: UUID,
    title: str,
    body: str,
    channel: str = NotificationMessage.Channel.IN_APP,
    agency_id: Optional[UUID] = None,
    actor: Optional[User] = None,
) -> NotificationMessage:
    recipient = User.objects.filter(id=recipient_user_id).first()
    if not recipient:
        raise NotFoundDomainError("گیرنده اعلان یافت نشد.")

    delivery_status = NotificationMessage.DeliveryStatus.DELIVERED
    if channel == NotificationMessage.Channel.SMS:
        sms = get_sms_provider()
        res = sms.send_sms(recipient.phone_number, f"{title}: {body}")
        delivery_status = (
            NotificationMessage.DeliveryStatus.SENT
            if res.accepted
            else NotificationMessage.DeliveryStatus.FAILED
        )
    elif channel == NotificationMessage.Channel.PUSH:
        subs = list(PushSubscription.objects.filter(user=recipient, is_active=True))
        for sub in subs:
            try:
                dispatch_web_push_task(str(sub.id), title.strip(), body.strip())
            except Exception:
                pass
        delivery_status = (
            NotificationMessage.DeliveryStatus.SENT
            if subs
            else NotificationMessage.DeliveryStatus.QUEUED
        )

    return NotificationMessage.objects.create(
        recipient=recipient,
        agency_id=agency_id,
        channel=channel,
        title=title.strip(),
        body=body.strip(),
        delivery_status=delivery_status,
        created_by=actor,
    )


def mark_notification_read(*, user: User, notification_id: UUID) -> NotificationMessage:
    msg = NotificationMessage.objects.filter(id=notification_id, recipient=user).first()
    if not msg:
        raise NotFoundDomainError("اعلان یافت نشد.")
    msg.is_read = True
    msg.read_at = timezone.now()
    msg.save(update_fields=["is_read", "read_at", "updated_at"])
    return msg


def mark_all_notifications_read(*, user: User) -> int:
    return NotificationMessage.objects.filter(recipient=user, is_read=False).update(
        is_read=True, read_at=timezone.now()
    )


@transaction.atomic
def register_push_subscription(
    *, user: User, agency_id: Optional[UUID], endpoint: str, p256dh: str, auth: str, device_label: str = "Web Browser"
) -> PushSubscription:
    sub, _ = PushSubscription.objects.update_or_create(
        endpoint=endpoint.strip(),
        defaults={
            "user": user,
            "agency_id": agency_id,
            "p256dh": p256dh.strip(),
            "auth": auth.strip(),
            "device_label": device_label[:120],
            "is_active": True,
        },
    )
    return sub


def unregister_push_subscription(*, user: User, endpoint: str) -> int:
    return PushSubscription.objects.filter(user=user, endpoint=endpoint.strip()).update(is_active=False)


def list_user_push_subscriptions(*, user: User) -> list[PushSubscription]:
    return list(PushSubscription.objects.filter(user=user, is_active=True).order_by("-created_at"))


def get_or_create_preferences(*, user: User) -> NotificationPreference:
    pref, _ = NotificationPreference.objects.get_or_create(user=user)
    return pref


@transaction.atomic
def update_preferences(*, user: User, updates: dict) -> NotificationPreference:
    pref = get_or_create_preferences(user=user)
    for field in (
        "in_app_enabled",
        "push_enabled",
        "sms_enabled",
        "email_enabled",
        "quiet_hours_start",
        "quiet_hours_end",
    ):
        if field in updates and updates[field] is not None:
            setattr(pref, field, updates[field])
    pref.save()
    return pref

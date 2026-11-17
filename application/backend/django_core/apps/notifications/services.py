from typing import Optional
from uuid import UUID
from django.db import transaction
from django.utils import timezone
from apps.accounts.models import User
from common.exceptions import NotFoundDomainError, PermissionDeniedDomainError
from integrations.registry import get_sms_provider
from .models import NotificationMessage


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

from datetime import timedelta
from celery import shared_task
from django.utils import timezone
from integrations.registry import get_email_provider, get_push_provider, get_sms_provider


@shared_task(name="apps.notifications.tasks.dispatch_web_push_task")
def dispatch_web_push_task(subscription_id: str, title: str, body: str, url: str = "/dashboard/notifications") -> dict:
    from .models import PushSubscription

    sub = PushSubscription.objects.filter(id=subscription_id, is_active=True).first()
    if not sub:
        return {"status": "SKIPPED", "reason": "subscription_not_found"}

    provider = get_push_provider()
    res = provider.send_web_push(
        endpoint=sub.endpoint,
        p256dh=sub.p256dh,
        auth=sub.auth,
        title=title,
        body=body,
        url=url,
    )
    sub.last_used_at = timezone.now()
    sub.save(update_fields=["last_used_at", "updated_at"])
    return {
        "status": "DISPATCHED",
        "subscription_id": str(sub.id),
        "provider": res.provider_key,
        "title": title,
        "url": url,
    }


@shared_task(name="apps.notifications.tasks.send_email_notification_task")
def send_email_notification_task(to_email: str, subject: str, body_text: str) -> dict:
    provider = get_email_provider()
    res = provider.send_email(to_email=to_email, subject=subject, body_text=body_text)
    return {"accepted": res.accepted, "provider": res.provider_key, "id": res.provider_message_id}


@shared_task(name="apps.notifications.tasks.send_sms_notification_task")
def send_sms_notification_task(phone_number: str, message: str) -> dict:
    provider = get_sms_provider()
    res = provider.send_sms(phone_number=phone_number, message=message)
    return {"accepted": res.accepted, "provider": res.provider_key, "id": res.provider_message_id}


@shared_task(name="apps.notifications.tasks.check_expiring_contracts_and_cheques_task")
def check_expiring_contracts_and_cheques_task() -> dict:
    from apps.accounting.models import ChequeInstrument
    from apps.contracts.models import Contract
    from common.tenant.context import tenant_bypass

    soon = timezone.now() + timedelta(days=7)
    with tenant_bypass():
        cheques_count = ChequeInstrument.objects.all_tenants().filter(
            status=ChequeInstrument.Status.HELD, due_date__lte=soon
        ).count()
        contracts_count = Contract.objects.all_tenants().filter(
            status=Contract.Status.ACTIVE, end_date__lte=soon.date()
        ).count()
    return {"cheques_due_soon": cheques_count, "contracts_expiring_soon": contracts_count}

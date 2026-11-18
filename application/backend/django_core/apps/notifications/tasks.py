from celery import shared_task
from django.utils import timezone


@shared_task(name="apps.notifications.tasks.dispatch_web_push_task")
def dispatch_web_push_task(subscription_id: str, title: str, body: str, url: str = "/dashboard/notifications") -> dict:
    from .models import PushSubscription

    sub = PushSubscription.objects.filter(id=subscription_id, is_active=True).first()
    if not sub:
        return {"status": "SKIPPED", "reason": "subscription_not_found"}

    sub.last_used_at = timezone.now()
    sub.save(update_fields=["last_used_at", "updated_at"])
    return {
        "status": "DISPATCHED",
        "subscription_id": str(sub.id),
        "title": title,
        "url": url,
    }

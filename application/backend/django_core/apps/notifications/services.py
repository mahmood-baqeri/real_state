import base64
from datetime import timedelta
from decimal import Decimal
import hashlib
import os
from typing import Optional
from uuid import UUID
from django.db import models, transaction
from django.utils import timezone
from common.tenant.context import tenant_bypass
from apps.accounts.models import User
from apps.audit.services import record_audit_event
from apps.settings.models import ProviderConfiguration
from apps.settings.services import get_setting_value, parse_provider_credentials
from common.exceptions import NotFoundDomainError, PermissionDeniedDomainError, ValidationDomainError
from common.permissions import has_agency_permission, is_super_admin
from integrations.registry import SMS_PROVIDERS, get_sms_provider
from .models import (
    NotificationMessage,
    NotificationPreference,
    PushSubscription,
    SmsDeliveryLog,
    SmsTemplate,
)
from .tasks import dispatch_web_push_task


def get_vapid_public_key() -> str:
    env_key = os.environ.get("VAPID_PUBLIC_KEY", "").strip()
    if env_key:
        return env_key
    digest = hashlib.sha256(b"bonyan-melk-dev-vapid-key").digest() + hashlib.sha256(b"bonyan-melk-dev-vapid-y").digest()
    uncompressed = b"\x04" + digest[:64]
    return base64.urlsafe_b64encode(uncompressed).decode("ascii").rstrip("=")


def mask_phone_number(phone: str) -> str:
    clean = (phone or "").strip()
    if len(clean) <= 6:
        return "***"
    return f"{clean[:4]}***{clean[-4:]}"


def hash_phone_number(phone: str) -> str:
    return hashlib.sha256((phone or "").strip().encode("utf-8")).hexdigest()


def render_sms_template(body_template: str, tokens: Optional[dict] = None) -> str:
    rendered = body_template or ""
    for k, v in (tokens or {}).items():
        rendered = rendered.replace(f"{{{{{k}}}}}", str(v))
        rendered = rendered.replace(f"{{{k}}}", str(v))
    return rendered


def list_sms_templates(*, user: User) -> list[SmsTemplate]:
    if not is_super_admin(user):
        raise PermissionDeniedDomainError("فقط مدیر کل مجاز به مشاهده و مدیریت الگوهای پیامک است.")
    return list(SmsTemplate.objects.all().order_by("event_type", "key"))


@transaction.atomic
def upsert_sms_template(*, user: User, data: dict) -> SmsTemplate:
    if not is_super_admin(user):
        raise PermissionDeniedDomainError("فقط مدیر کل مجاز به ویرایش الگوهای پیامک است.")
    key = str(data["key"]).strip().lower()
    if not key:
        raise ValidationDomainError("شناسه الگوی پیامک الزامی است.")
    tpl, _ = SmsTemplate.objects.update_or_create(
        key=key,
        defaults={
            "event_type": str(data.get("event_type") or SmsTemplate.EventType.GENERAL),
            "name_fa": str(data["name_fa"]).strip(),
            "body_template": str(data["body_template"]).strip(),
            "sample_tokens": list(data.get("sample_tokens") or []),
            "provider_template_id": str(data.get("provider_template_id") or "").strip(),
            "is_active": bool(data.get("is_active", True)),
            "updated_by": user,
        },
    )
    record_audit_event(
        action="SMS_TEMPLATE_UPDATED",
        resource_type="SmsTemplate",
        resource_id=tpl.key,
        actor=user,
        after_state={"event_type": tpl.event_type, "is_active": tpl.is_active},
    )
    return tpl


def list_sms_logs(
    *, user: User, agency_id: Optional[UUID] = None, event_type: Optional[str] = None, status_filter: Optional[str] = None
):
    if not (is_super_admin(user) or (agency_id and has_agency_permission(user, agency_id, "agency.manage_policy"))):
        raise PermissionDeniedDomainError("عدم دسترسی به گزارش ارسال پیامک.")
    qs = SmsDeliveryLog.objects.select_related("agency", "actor")
    if not is_super_admin(user):
        qs = qs.filter(agency_id=agency_id)
    elif agency_id:
        qs = qs.filter(agency_id=agency_id)
    if event_type:
        qs = qs.filter(event_type=event_type)
    if status_filter:
        qs = qs.filter(status=status_filter)
    return qs.order_by("-created_at")


def get_sms_settings_and_stats(*, user: User, agency_id: Optional[UUID] = None) -> dict:
    if not (is_super_admin(user) or (agency_id and has_agency_permission(user, agency_id, "agency.manage_policy"))):
        raise PermissionDeniedDomainError("عدم دسترسی به آمار و تنظیمات پیامک.")
    now = timezone.now()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = day_start - timedelta(days=30)

    qs = SmsDeliveryLog.objects.all()
    if not is_super_admin(user) and agency_id:
        qs = qs.filter(agency_id=agency_id)

    today_sent = qs.filter(created_at__gte=day_start, status=SmsDeliveryLog.DeliveryStatus.SENT).count()
    month_sent = qs.filter(created_at__gte=month_start, status=SmsDeliveryLog.DeliveryStatus.SENT).count()
    month_failed = qs.filter(created_at__gte=month_start, status=SmsDeliveryLog.DeliveryStatus.FAILED).count()
    month_cost = qs.filter(created_at__gte=month_start).aggregate(s=models.Sum("cost_amount"))["s"] or Decimal("0.00")

    return {
        "enabled": bool(get_setting_value("sms.enabled", True, agency_id=agency_id)),
        "daily_cap": int(get_setting_value("sms.daily_cap", 5000, agency_id=agency_id) or 5000),
        "cost_per_segment": str(get_setting_value("sms.cost_per_segment", "950", agency_id=agency_id)),
        "fallback_enabled": bool(get_setting_value("sms.fallback_enabled", True, agency_id=agency_id)),
        "event_toggles": {
            "OTP_LOGIN": bool(get_setting_value("sms.event.otp_login", True, agency_id=agency_id)),
            "REGISTER": bool(get_setting_value("sms.event.register", True, agency_id=agency_id)),
            "PASSWORD_RESET": bool(get_setting_value("sms.event.password_reset", True, agency_id=agency_id)),
            "NOTIFICATION": bool(get_setting_value("sms.event.notification", True, agency_id=agency_id)),
            "APPOINTMENT": bool(get_setting_value("sms.event.appointment", True, agency_id=agency_id)),
            "CRM_FOLLOWUP": bool(get_setting_value("sms.event.crm_followup", True, agency_id=agency_id)),
            "DEAL_CONTRACT": bool(get_setting_value("sms.event.deal_contract", True, agency_id=agency_id)),
            "PAYMENT_FINANCE": bool(get_setting_value("sms.event.payment_finance", True, agency_id=agency_id)),
            "ADMIN_ALERT": bool(get_setting_value("sms.event.admin_alert", True, agency_id=agency_id)),
        },
        "stats": {
            "today_sent": today_sent,
            "month_sent": month_sent,
            "month_failed": month_failed,
            "month_estimated_cost": str(month_cost),
        },
    }


def _resolve_sms_provider_chain(agency_id: Optional[UUID] = None) -> list[tuple[str, dict, str]]:
    """درگاه‌های فعالِ آژانس و پیش‌فرض‌های سراسری پیامک را به ترتیب اولویت می‌خواند."""
    query = ProviderConfiguration.objects.filter(
        category=ProviderConfiguration.Category.SMS, is_active=True,
    ).order_by("priority", "-updated_at")
    configs = list(query.filter(agency_id=agency_id)) if agency_id else []
    with tenant_bypass(reason="system_configuration"):
        configs.extend(query.filter(agency__isnull=True))
    configs.sort(key=lambda cfg: (cfg.priority, -cfg.updated_at.timestamp()))
    chain: list[tuple[str, dict, str]] = []
    seen = set()
    for cfg in configs:
        if cfg.provider_key in SMS_PROVIDERS and cfg.provider_key not in seen:
            seen.add(cfg.provider_key)
            creds = parse_provider_credentials(cfg)
            sender_line = str((cfg.config_json or {}).get("sender_line") or creds.get("sender_line") or "")
            chain.append((cfg.provider_key, creds, sender_line))
    if not chain:
        chain.append(("console", {}, ""))
    elif bool(get_setting_value("sms.fallback_enabled", True, agency_id=agency_id)) and "console" not in seen:
        chain.append(("console", {}, ""))
    return chain


@transaction.atomic
def dispatch_sms_with_policy(
    *,
    phone_number: str,
    event_type: str = "GENERAL",
    template_key: Optional[str] = None,
    tokens: Optional[dict] = None,
    message: Optional[str] = None,
    is_otp: bool = False,
    agency_id: Optional[UUID] = None,
    actor: Optional[User] = None,
) -> dict:
    clean_phone = (phone_number or "").strip()
    masked = mask_phone_number(clean_phone)
    phone_hash = hash_phone_number(clean_phone)

    global_enabled = bool(get_setting_value("sms.enabled", True, agency_id=agency_id))
    event_setting_key = f"sms.event.{event_type.lower()}"
    event_enabled = bool(get_setting_value(event_setting_key, True, agency_id=agency_id))

    if not global_enabled or not event_enabled:
        SmsDeliveryLog.objects.create(
            recipient_masked=masked,
            recipient_hash=phone_hash,
            event_type=event_type,
            template_key=template_key or "",
            provider_key="policy-guard",
            status=SmsDeliveryLog.DeliveryStatus.BLOCKED_BY_TOGGLE,
            error_message="ارسال پیامک برای این رویداد یا در کل سامانه غیرفعال شده است.",
            agency_id=agency_id,
            actor=actor,
        )
        return {
            "accepted": False,
            "blocked": True,
            "status": SmsDeliveryLog.DeliveryStatus.BLOCKED_BY_TOGGLE,
            "provider_key": "policy-guard",
            "message_id": "",
            "error_message": "ارسال پیامک غیرفعال است.",
        }

    daily_cap = int(get_setting_value("sms.daily_cap", 5000, agency_id=agency_id) or 5000)
    day_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_cnt = SmsDeliveryLog.objects.filter(
        created_at__gte=day_start, status=SmsDeliveryLog.DeliveryStatus.SENT
    ).count()
    if today_cnt >= daily_cap:
        SmsDeliveryLog.objects.create(
            recipient_masked=masked,
            recipient_hash=phone_hash,
            event_type=event_type,
            template_key=template_key or "",
            provider_key="rate-cap",
            status=SmsDeliveryLog.DeliveryStatus.RATE_LIMITED,
            error_message="سقف ارسال روزانه پیامک پر شده است.",
            agency_id=agency_id,
            actor=actor,
        )
        return {
            "accepted": False,
            "blocked": True,
            "status": SmsDeliveryLog.DeliveryStatus.RATE_LIMITED,
            "provider_key": "rate-cap",
            "message_id": "",
            "error_message": "سقف ارسال روزانه پیامک تکمیل شد.",
        }

    tpl = None
    if template_key:
        with tenant_bypass(reason="system_configuration"):
            tpl = SmsTemplate.objects.filter(key=template_key, is_active=True).first()
    rendered_body = message or (render_sms_template(tpl.body_template, tokens) if tpl else "اعلان سامانه بنیان ملک")
    seg_cost = Decimal(str(get_setting_value("sms.cost_per_segment", "950", agency_id=agency_id) or "950"))

    chain = _resolve_sms_provider_chain(agency_id=agency_id)
    last_err = ""
    for provider_key, creds, sender_line in chain:
        adapter = get_sms_provider(provider_key)
        if is_otp:
            lookup_tpl = (tpl.provider_template_id if tpl and tpl.provider_template_id else (template_key or "otp"))
            res = adapter.send_otp(clean_phone, lookup_tpl, tokens or {}, credentials=creds)
        else:
            res = adapter.send_sms(clean_phone, rendered_body, sender_line=sender_line or None, credentials=creds)

        if res.accepted:
            SmsDeliveryLog.objects.create(
                recipient_masked=masked,
                recipient_hash=phone_hash,
                event_type=event_type,
                template_key=template_key or "",
                provider_key=res.provider_key,
                status=SmsDeliveryLog.DeliveryStatus.SENT,
                message_id=res.provider_message_id,
                cost_amount=seg_cost,
                agency_id=agency_id,
                actor=actor,
            )
            return {
                "accepted": True,
                "blocked": False,
                "status": SmsDeliveryLog.DeliveryStatus.SENT,
                "provider_key": res.provider_key,
                "message_id": res.provider_message_id,
                "rendered_message": rendered_body,
                "error_message": "",
            }
        last_err = res.error_message

    SmsDeliveryLog.objects.create(
        recipient_masked=masked,
        recipient_hash=phone_hash,
        event_type=event_type,
        template_key=template_key or "",
        provider_key=chain[0][0],
        status=SmsDeliveryLog.DeliveryStatus.FAILED,
        error_message=(last_err or "ارسال از طریق ارائه‌دهندگان پیامک ناموفق بود.")[:255],
        agency_id=agency_id,
        actor=actor,
    )
    return {
        "accepted": False,
        "blocked": False,
        "status": SmsDeliveryLog.DeliveryStatus.FAILED,
        "provider_key": chain[0][0],
        "message_id": "",
        "error_message": last_err or "خطا در ارسال پیامک",
    }


def send_test_sms(
    *, user: User, agency_id: Optional[UUID], phone_number: str, template_key: Optional[str] = None, message: Optional[str] = None
) -> dict:
    if not (is_super_admin(user) or (agency_id and has_agency_permission(user, agency_id, "agency.manage_policy"))):
        raise PermissionDeniedDomainError("عدم مجوز ارسال پیامک آزمایشی.")
    if not phone_number or len(phone_number.strip()) < 7:
        raise ValidationDomainError("شماره موبایل گیرنده معتبر نیست.")
    res = dispatch_sms_with_policy(
        phone_number=phone_number.strip(),
        event_type="ADMIN_ALERT",
        template_key=template_key,
        tokens={"code": "482910", "name": user.full_name, "agency": "بنیان ملک"},
        message=message or f"پیامک آزمایشی مرکز تنظیمات بنیان ملک — کاربر: {user.full_name}",
        is_otp=False,
        agency_id=agency_id,
        actor=user,
    )
    record_audit_event(
        action="SMS_TEST_DISPATCHED",
        resource_type="SmsDeliveryLog",
        resource_id=res.get("message_id") or "test",
        actor=user,
        agency_id=agency_id,
        after_state={"accepted": res.get("accepted"), "provider_key": res.get("provider_key")},
    )
    return res


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
    err_msg = ""
    if channel == NotificationMessage.Channel.SMS:
        res = dispatch_sms_with_policy(
            phone_number=recipient.phone_number,
            event_type="NOTIFICATION",
            message=f"{title}: {body}",
            is_otp=False,
            agency_id=agency_id,
            actor=actor,
        )
        delivery_status = (
            NotificationMessage.DeliveryStatus.SENT
            if res.get("accepted")
            else NotificationMessage.DeliveryStatus.FAILED
        )
        err_msg = str(res.get("error_message") or "")
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

    message = NotificationMessage.objects.create(
        recipient=recipient,
        agency_id=agency_id,
        channel=channel,
        title=title.strip(),
        body=body.strip(),
        delivery_status=delivery_status,
        error_message=err_msg,
        created_by=actor,
    )
    try:
        import redis
        client = redis.Redis.from_url(os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0"), socket_connect_timeout=0.5)
        client.publish(f"bonyan:notifications:{recipient.id}", "new_notification")
        client.close()
    except Exception:
        pass
    return message


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

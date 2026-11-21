from decimal import Decimal
from django.conf import settings
from django.db import models
from common.models import BaseModel


class NotificationMessage(BaseModel):
    class Channel(models.TextChoices):
        IN_APP = "IN_APP", "In App"
        EMAIL = "EMAIL", "Email"
        SMS = "SMS", "SMS"
        PUSH = "PUSH", "Browser Push"

    class DeliveryStatus(models.TextChoices):
        QUEUED = "QUEUED", "Queued"
        SENT = "SENT", "Sent"
        DELIVERED = "DELIVERED", "Delivered"
        FAILED = "FAILED", "Failed"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    agency = models.ForeignKey(
        "agencies.Agency", null=True, blank=True, on_delete=models.CASCADE
    )
    channel = models.CharField(max_length=16, choices=Channel.choices, default=Channel.IN_APP)
    title = models.CharField(max_length=160)
    body = models.TextField()
    delivery_status = models.CharField(
        max_length=16, choices=DeliveryStatus.choices, default=DeliveryStatus.QUEUED
    )
    error_message = models.TextField(blank=True, default="")
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "notifications_message"
        ordering = ["-created_at"]


class PushSubscription(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="push_subscriptions"
    )
    agency = models.ForeignKey(
        "agencies.Agency", null=True, blank=True, on_delete=models.CASCADE
    )
    endpoint = models.CharField(max_length=500, unique=True)
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=255)
    device_label = models.CharField(max_length=120, blank=True, default="Web Browser")
    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "notifications_push_subscription"
        ordering = ["-created_at"]


class NotificationPreference(BaseModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_preference"
    )
    in_app_enabled = models.BooleanField(default=True)
    push_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=True)
    email_enabled = models.BooleanField(default=True)
    quiet_hours_start = models.CharField(max_length=5, blank=True, default="")
    quiet_hours_end = models.CharField(max_length=5, blank=True, default="")

    class Meta:
        db_table = "notifications_preference"


class SmsTemplate(BaseModel):
    class EventType(models.TextChoices):
        OTP_LOGIN = "OTP_LOGIN", "OTP Login"
        REGISTER = "REGISTER", "Register"
        PASSWORD_RESET = "PASSWORD_RESET", "Password Reset"
        NOTIFICATION = "NOTIFICATION", "Notification"
        APPOINTMENT = "APPOINTMENT", "Appointment"
        CRM_FOLLOWUP = "CRM_FOLLOWUP", "CRM Follow-up"
        DEAL_CONTRACT = "DEAL_CONTRACT", "Deal & Contract"
        PAYMENT_FINANCE = "PAYMENT_FINANCE", "Payment & Finance"
        ADMIN_ALERT = "ADMIN_ALERT", "Admin Alert"
        GENERAL = "GENERAL", "General"

    key = models.CharField(max_length=64, unique=True)
    event_type = models.CharField(
        max_length=24, choices=EventType.choices, default=EventType.GENERAL, db_index=True
    )
    name_fa = models.CharField(max_length=120)
    body_template = models.TextField()
    sample_tokens = models.JSONField(default=list, blank=True)
    provider_template_id = models.CharField(max_length=80, blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "notifications_sms_template"
        ordering = ["event_type", "key"]


class SmsDeliveryLog(BaseModel):
    class DeliveryStatus(models.TextChoices):
        SENT = "SENT", "Sent"
        FAILED = "FAILED", "Failed"
        BLOCKED_BY_TOGGLE = "BLOCKED_BY_TOGGLE", "Blocked By Toggle"
        RATE_LIMITED = "RATE_LIMITED", "Rate Limited"

    recipient_masked = models.CharField(max_length=32)
    recipient_hash = models.CharField(max_length=64, db_index=True)
    event_type = models.CharField(max_length=24, db_index=True, default="GENERAL")
    template_key = models.CharField(max_length=64, blank=True, default="")
    provider_key = models.CharField(max_length=48, default="console")
    status = models.CharField(
        max_length=24, choices=DeliveryStatus.choices, default=DeliveryStatus.SENT, db_index=True
    )
    message_id = models.CharField(max_length=128, blank=True, default="")
    error_message = models.CharField(max_length=255, blank=True, default="")
    cost_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    agency = models.ForeignKey(
        "agencies.Agency", null=True, blank=True, on_delete=models.SET_NULL
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        db_table = "notifications_sms_delivery_log"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["event_type", "status", "-created_at"])]


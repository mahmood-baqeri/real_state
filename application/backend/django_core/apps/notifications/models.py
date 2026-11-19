# Path: backend/django_core/apps/notifications/models.py

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

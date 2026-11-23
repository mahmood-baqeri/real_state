import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class AuditLog(models.Model):
    """Append-only immutable audit trail for sensitive operations and access checks."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency_id = models.UUIDField(null=True, blank=True, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_events",
    )
    action = models.CharField(max_length=120, db_index=True)
    resource_type = models.CharField(max_length=80, db_index=True)
    resource_id = models.CharField(max_length=64, blank=True, default="", db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True, default="")
    before_state = models.JSONField(null=True, blank=True)
    after_state = models.JSONField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False, db_index=True)

    class Meta:
        db_table = "audit_log"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["agency_id", "created_at"]),
            models.Index(fields=["resource_type", "resource_id"]),
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise PermissionError("AuditLog entries are immutable and cannot be modified.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("AuditLog entries are immutable and cannot be deleted.")

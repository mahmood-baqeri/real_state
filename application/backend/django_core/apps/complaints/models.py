# Path: backend/django_core/apps/complaints/models.py

from django.conf import settings
from django.db import models
from common.models import BaseModel


class Complaint(BaseModel):
    class TargetType(models.TextChoices):
        AGENCY = "AGENCY", "Agency"
        AGENT = "AGENT", "Agent"
        PROPERTY = "PROPERTY", "Property Listing"
        PLATFORM = "PLATFORM", "Platform"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        ESCALATED = "ESCALATED", "Escalated"
        RESOLVED = "RESOLVED", "Resolved"
        CLOSED = "CLOSED", "Closed"

    tracking_code = models.CharField(max_length=32, unique=True)
    complainant_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="filed_complaints",
    )
    complainant_name = models.CharField(max_length=120)
    complainant_phone = models.CharField(max_length=24)
    agency = models.ForeignKey(
        "agencies.Agency", null=True, blank=True, on_delete=models.SET_NULL, related_name="complaints"
    )
    target_type = models.CharField(max_length=20, choices=TargetType.choices, default=TargetType.AGENCY)
    target_title = models.CharField(max_length=160, blank=True, default="")
    subject = models.CharField(max_length=200)
    description = models.TextField()
    is_confidential = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    assigned_to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_complaints",
    )
    resolution_summary = models.TextField(blank=True, default="")
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "complaints_complaint"
        ordering = ["-created_at"]


class ComplaintNote(BaseModel):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="notes")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="complaint_notes"
    )
    note = models.TextField()
    is_confidential = models.BooleanField(default=True)

    class Meta:
        db_table = "complaints_note"
        ordering = ["-created_at"]

from django.conf import settings
from django.db import models
from common.models import BaseModel


class Ticket(BaseModel):
    class Scope(models.TextChoices):
        PLATFORM = "PLATFORM", "Platform Support"
        AGENCY = "AGENCY", "Agency Internal Support"

    class Category(models.TextChoices):
        TECHNICAL = "TECHNICAL", "Technical"
        BILLING = "BILLING", "Billing"
        ACCOUNT = "ACCOUNT", "Account"
        AGENCY_OPS = "AGENCY_OPS", "Agency Operations"
        GENERAL = "GENERAL", "General"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        NORMAL = "NORMAL", "Normal"
        HIGH = "HIGH", "High"
        URGENT = "URGENT", "Urgent"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        WAITING_USER = "WAITING_USER", "Waiting for User"
        RESOLVED = "RESOLVED", "Resolved"
        CLOSED = "CLOSED", "Closed"

    ticket_number = models.CharField(max_length=32, unique=True)
    scope = models.CharField(max_length=16, choices=Scope.choices, default=Scope.AGENCY)
    agency = models.ForeignKey(
        "agencies.Agency", null=True, blank=True, on_delete=models.CASCADE, related_name="tickets"
    )
    created_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_tickets"
    )
    assigned_to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_tickets",
    )
    category = models.CharField(max_length=24, choices=Category.choices, default=Category.GENERAL)
    priority = models.CharField(max_length=16, choices=Priority.choices, default=Priority.NORMAL)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    subject = models.CharField(max_length=200)
    sla_due_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    satisfaction_rating = models.PositiveSmallIntegerField(null=True, blank=True)
    satisfaction_comment = models.TextField(blank=True, default="")

    class Meta:
        db_table = "support_ticket"
        ordering = ["-created_at"]


class TicketMessage(BaseModel):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="ticket_messages"
    )
    body = models.TextField()
    is_internal_note = models.BooleanField(default=False)

    class Meta:
        db_table = "support_ticket_message"
        ordering = ["created_at"]


class TicketAttachment(BaseModel):
    message = models.ForeignKey(TicketMessage, on_delete=models.CASCADE, related_name="attachments")
    file_name = models.CharField(max_length=255)
    file_url = models.CharField(max_length=500)
    mime_type = models.CharField(max_length=120, default="application/octet-stream")
    file_size_bytes = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "support_ticket_attachment"


class TicketStatusHistory(BaseModel):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="status_history")
    from_status = models.CharField(max_length=16, blank=True, default="")
    to_status = models.CharField(max_length=16)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    note = models.TextField(blank=True, default="")

    class Meta:
        db_table = "support_ticket_status_history"
        ordering = ["-created_at"]


class CannedReply(BaseModel):
    agency = models.ForeignKey(
        "agencies.Agency", null=True, blank=True, on_delete=models.CASCADE, related_name="canned_replies"
    )
    title = models.CharField(max_length=120)
    category = models.CharField(max_length=24, choices=Ticket.Category.choices, default=Ticket.Category.GENERAL)
    body = models.TextField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "support_canned_reply"
        ordering = ["title"]

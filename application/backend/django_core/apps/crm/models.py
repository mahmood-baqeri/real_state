# Path: backend/django_core/apps/crm/models.py

from django.db import models
from common.models import TenantScopedModel


class PipelineStage(TenantScopedModel):
    code = models.CharField(max_length=48)
    name = models.CharField(max_length=80)
    sort_order = models.PositiveSmallIntegerField(default=1)
    is_terminal_won = models.BooleanField(default=False)
    is_terminal_lost = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "crm_pipeline_stage"
        ordering = ["sort_order"]
        unique_together = ("agency", "code")


class CustomerPipelineItem(TenantScopedModel):
    customer = models.OneToOneField(
        "customers.Customer", on_delete=models.CASCADE, related_name="pipeline_item"
    )
    stage = models.ForeignKey(PipelineStage, on_delete=models.PROTECT, related_name="items")
    assigned_membership = models.ForeignKey(
        "accounts.AgencyMembership", null=True, blank=True, on_delete=models.SET_NULL
    )
    property = models.ForeignKey(
        "properties.Property", null=True, blank=True, on_delete=models.SET_NULL
    )
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "crm_pipeline_item"


class CustomerInteractionLog(TenantScopedModel):
    class Channel(models.TextChoices):
        CALL = "CALL", "Phone Call"
        MEETING = "MEETING", "In-Person Meeting"
        MESSAGE = "MESSAGE", "Message"
        NOTE = "NOTE", "Private Note"

    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.CASCADE, related_name="interactions"
    )
    membership = models.ForeignKey(
        "accounts.AgencyMembership", null=True, on_delete=models.SET_NULL
    )
    channel = models.CharField(max_length=16, choices=Channel.choices, default=Channel.NOTE)
    summary = models.TextField()
    is_private = models.BooleanField(default=True)

    class Meta:
        db_table = "crm_interaction_log"
        ordering = ["-created_at"]


class FollowUpTask(TenantScopedModel):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.CASCADE, related_name="tasks"
    )
    assigned_membership = models.ForeignKey(
        "accounts.AgencyMembership", on_delete=models.CASCADE, related_name="follow_up_tasks"
    )
    title = models.CharField(max_length=160)
    due_at = models.DateTimeField(db_index=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "crm_follow_up_task"
        ordering = ["due_at"]

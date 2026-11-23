from django.core.exceptions import ValidationError
from django.db import models, transaction
from common.models import TenantScopedModel


class ViewingAppointment(TenantScopedModel):
    class Status(models.TextChoices):
        REQUESTED = "REQUESTED", "Requested"
        CONFIRMED = "CONFIRMED", "Confirmed"
        RESCHEDULED = "RESCHEDULED", "Rescheduled"
        CANCELLED = "CANCELLED", "Cancelled"
        REJECTED = "REJECTED", "Rejected"
        COMPLETED = "COMPLETED", "Completed"
        NO_SHOW = "NO_SHOW", "No Show"

    property = models.ForeignKey(
        "properties.Property", on_delete=models.PROTECT, related_name="appointments"
    )
    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.PROTECT, related_name="appointments"
    )
    agent_membership = models.ForeignKey(
        "accounts.AgencyMembership", on_delete=models.PROTECT, related_name="appointments"
    )
    scheduled_start = models.DateTimeField(db_index=True)
    scheduled_end = models.DateTimeField(db_index=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.REQUESTED)
    customer_feedback = models.TextField(blank=True, default="")
    agent_report = models.TextField(blank=True, default="")

    class Meta:
        db_table = "appointments_viewing"
        ordering = ["scheduled_start"]
        indexes = [
            models.Index(fields=["agent_membership", "scheduled_start", "scheduled_end"]),
        ]

    @classmethod
    def check_conflict(cls, *, agent_membership_id, property_id, start_at, end_at, exclude_id=None):
        if end_at <= start_at:
            raise ValidationError("End time must be after start time.")
        active_statuses = [cls.Status.CONFIRMED, cls.Status.RESCHEDULED]
        overlap_q = models.Q(scheduled_start__lt=end_at) & models.Q(scheduled_end__gt=start_at)
        agent_conflict = (
            cls.objects.all_tenants()
            .filter(agent_membership_id=agent_membership_id, status__in=active_statuses)
            .filter(overlap_q)
        )
        prop_conflict = (
            cls.objects.all_tenants()
            .filter(property_id=property_id, status__in=active_statuses)
            .filter(overlap_q)
        )
        if exclude_id:
            agent_conflict = agent_conflict.exclude(id=exclude_id)
            prop_conflict = prop_conflict.exclude(id=exclude_id)
        if agent_conflict.exists():
            raise ValidationError("Agent already has an overlapping confirmed viewing appointment.")
        if prop_conflict.exists():
            raise ValidationError("Property already has an overlapping confirmed viewing appointment.")

    @classmethod
    @transaction.atomic
    def schedule_safely(cls, **kwargs):
        cls.check_conflict(
            agent_membership_id=kwargs["agent_membership"].id,
            property_id=kwargs["property"].id,
            start_at=kwargs["scheduled_start"],
            end_at=kwargs["scheduled_end"],
        )
        return cls.objects.create(**kwargs)

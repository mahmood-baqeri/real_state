# Path: backend/django_core/apps/leads/models.py

from django.db import models
from common.models import TenantScopedModel


class Lead(TenantScopedModel):
    class Status(models.TextChoices):
        NEW = "NEW", "New"
        CONTACTED = "CONTACTED", "Contacted"
        QUALIFIED = "QUALIFIED", "Qualified"
        CONVERTED = "CONVERTED", "Converted to Customer"
        DISQUALIFIED = "DISQUALIFIED", "Disqualified"

    full_name = models.CharField(max_length=160)
    phone_number = models.CharField(max_length=24, db_index=True)
    request_type = models.CharField(max_length=32, default="BUY")
    property = models.ForeignKey(
        "properties.Property", null=True, blank=True, on_delete=models.SET_NULL
    )
    source = models.CharField(max_length=48, default="PORTAL")
    assigned_membership = models.ForeignKey(
        "accounts.AgencyMembership", null=True, blank=True, on_delete=models.SET_NULL
    )
    converted_customer = models.ForeignKey(
        "customers.Customer", null=True, blank=True, on_delete=models.SET_NULL
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.NEW)
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "leads_lead"
        ordering = ["-created_at"]

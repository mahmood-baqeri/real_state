# Path: backend/django_core/apps/subscriptions/models.py

from decimal import Decimal
from django.db import models
from common.models import BaseModel


class SubscriptionPlan(BaseModel):
    code = models.CharField(max_length=32, unique=True)  # FREE, BASIC, PRO, ENTERPRISE
    name_fa = models.CharField(max_length=80)
    name_en = models.CharField(max_length=80)
    currency = models.ForeignKey("settings.Currency", on_delete=models.PROTECT, default="IRT")
    monthly_price = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    annual_price = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    max_agents = models.PositiveIntegerField(default=5)
    max_branches = models.PositiveIntegerField(default=1)
    max_active_listings = models.PositiveIntegerField(default=50)
    features_json = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "subscriptions_plan"


class AgencySubscription(BaseModel):
    class Status(models.TextChoices):
        TRIAL = "TRIAL", "Trial"
        ACTIVE = "ACTIVE", "Active"
        PAST_DUE = "PAST_DUE", "Past Due"
        EXPIRED = "EXPIRED", "Expired"
        CANCELLED = "CANCELLED", "Cancelled"

    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="subscriptions"
    )
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT)
    billing_cycle = models.CharField(
        max_length=16, choices=[("MONTHLY", "Monthly"), ("ANNUAL", "Annual")], default="MONTHLY"
    )
    starts_at = models.DateTimeField()
    expires_at = models.DateTimeField(db_index=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.TRIAL)

    class Meta:
        db_table = "subscriptions_agency_subscription"
        ordering = ["-expires_at"]

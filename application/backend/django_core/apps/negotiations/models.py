from decimal import Decimal
from django.db import models
from common.models import BaseModel, TenantScopedModel


class Negotiation(TenantScopedModel):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        COUNTER_OFFERED = "COUNTER_OFFERED", "Counter Offered"
        ACCEPTED = "ACCEPTED", "Accepted"
        REJECTED = "REJECTED", "Rejected"
        WITHDRAWN = "WITHDRAWN", "Withdrawn"
        EXPIRED = "EXPIRED", "Expired"

    property = models.ForeignKey(
        "properties.Property", on_delete=models.PROTECT, related_name="negotiations"
    )
    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.PROTECT, related_name="negotiations"
    )
    agent_membership = models.ForeignKey(
        "accounts.AgencyMembership", on_delete=models.PROTECT, related_name="negotiations"
    )
    deal_type = models.ForeignKey("properties.DealType", on_delete=models.PROTECT)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.OPEN)
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "negotiations_negotiation"
        ordering = ["-created_at"]


class NegotiationOfferVersion(BaseModel):
    class OfferedBy(models.TextChoices):
        BUYER = "BUYER", "Buyer/Tenant"
        SELLER = "SELLER", "Seller/Owner"
        AGENT = "AGENT", "Agent Mediation"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACCEPTED = "ACCEPTED", "Accepted"
        REJECTED = "REJECTED", "Rejected"
        SUPERSEDED = "SUPERSEDED", "Superseded"

    negotiation = models.ForeignKey(
        Negotiation, on_delete=models.CASCADE, related_name="offer_versions"
    )
    version_number = models.PositiveIntegerField()
    offered_by = models.CharField(max_length=16, choices=OfferedBy.choices)
    currency = models.ForeignKey("settings.Currency", on_delete=models.PROTECT, default="IRT")
    proposed_price = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    proposed_deposit = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    proposed_rent = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    discount_amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    payment_terms = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    valid_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "negotiations_offer_version"
        unique_together = ("negotiation", "version_number")
        ordering = ["-version_number"]

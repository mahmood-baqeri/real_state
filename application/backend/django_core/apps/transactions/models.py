from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models
from common.models import TenantScopedModel


class Deal(TenantScopedModel):
    class Status(models.TextChoices):
        INITIATED = "INITIATED", "Initiated"
        CONTRACT_ACTIVE = "CONTRACT_ACTIVE", "Contract Active"
        SETTLING = "SETTLING", "Settlement In Progress"
        CLOSED_WON = "CLOSED_WON", "Closed Won"
        VOIDED = "VOIDED", "Voided / Terminated"

    deal_code = models.CharField(max_length=48)
    contract = models.OneToOneField(
        "contracts.Contract", on_delete=models.PROTECT, related_name="deal"
    )
    property = models.ForeignKey(
        "properties.Property", on_delete=models.PROTECT, related_name="deals"
    )
    negotiation = models.OneToOneField(
        "negotiations.Negotiation",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="deal",
    )
    primary_agent = models.ForeignKey(
        "accounts.AgencyMembership", on_delete=models.PROTECT, related_name="primary_deals"
    )
    co_agent = models.ForeignKey(
        "accounts.AgencyMembership",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="co_deals",
    )
    currency = models.ForeignKey("settings.Currency", on_delete=models.PROTECT, default="IRT")
    deal_value = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.INITIATED)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "transactions_deal"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["agency", "deal_code"], name="uq_deal_code_per_agency"
            )
        ]

    def delete(self, *args, **kwargs):
        raise ValidationError("Deals with financial history cannot be deleted.")

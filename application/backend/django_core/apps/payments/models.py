from django.db import models
from common.models import BaseModel


class PaymentGatewayTransaction(BaseModel):
    class Status(models.TextChoices):
        INITIATED = "INITIATED", "Initiated"
        PAID = "PAID", "Paid"
        FAILED = "FAILED", "Failed"
        REFUNDED = "REFUNDED", "Refunded"

    agency = models.ForeignKey(
        "agencies.Agency", null=True, blank=True, on_delete=models.PROTECT
    )
    subscription = models.ForeignKey(
        "subscriptions.AgencySubscription", null=True, blank=True, on_delete=models.PROTECT
    )
    provider_key = models.CharField(max_length=32, default="sandbox")
    authority = models.CharField(max_length=128, unique=True)
    reference_id = models.CharField(max_length=128, blank=True, default="")
    currency = models.ForeignKey("settings.Currency", on_delete=models.PROTECT, default="IRT")
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.INITIATED)
    raw_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "payments_gateway_transaction"

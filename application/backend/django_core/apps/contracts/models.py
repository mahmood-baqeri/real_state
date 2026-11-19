# Path: backend/django_core/apps/contracts/models.py

from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from common.models import BaseModel, TenantScopedModel


class ContractTemplate(BaseModel):
    agency = models.ForeignKey(
        "agencies.Agency",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="contract_templates",
    )
    country = models.ForeignKey("settings.Country", on_delete=models.PROTECT, default="IR")
    contract_type = models.CharField(max_length=32)
    title = models.CharField(max_length=160)
    body_template = models.TextField()
    legal_disclaimer = models.TextField(
        default="متن حقوقی پیش‌نویس بوده و پیش از رسمیت نیازمند بررسی و تأیید مدیر آژانس است."
    )
    is_manager_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "contracts_template"


class Contract(TenantScopedModel):
    class ContractType(models.TextChoices):
        SALE = "SALE", "Buy & Sell"
        RENT = "RENT", "Rent"
        MORTGAGE_RENT = "MORTGAGE_RENT", "Deposit & Rent"
        PARTNERSHIP = "PARTNERSHIP", "Construction Partnership"
        PRESALE = "PRESALE", "Pre-Sale"
        EXCLUSIVE_LISTING = "EXCLUSIVE_LISTING", "Exclusive Listing"
        AGENT_COOPERATION = "AGENT_COOPERATION", "Agent Cooperation"
        CUSTOM = "CUSTOM", "Custom"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PENDING_REVIEW = "PENDING_REVIEW", "Pending Review"
        PENDING_PARTIES_APPROVAL = "PENDING_PARTIES_APPROVAL", "Pending Parties Approval"
        SIGNED = "SIGNED", "Signed"
        ACTIVE = "ACTIVE", "Active"
        COMPLETED = "COMPLETED", "Completed"
        TERMINATED = "TERMINATED", "Terminated"
        EXPIRED = "EXPIRED", "Expired"
        ARCHIVED = "ARCHIVED", "Archived"

    contract_number = models.CharField(max_length=48)
    internal_tracking_code = models.CharField(max_length=64, db_index=True)
    contract_type = models.CharField(
        max_length=24, choices=ContractType.choices, default=ContractType.SALE
    )
    property = models.ForeignKey(
        "properties.Property", on_delete=models.PROTECT, related_name="contracts"
    )
    deal_type = models.ForeignKey("properties.DealType", on_delete=models.PROTECT)
    template = models.ForeignKey(
        ContractTemplate, null=True, blank=True, on_delete=models.PROTECT
    )

    currency = models.ForeignKey("settings.Currency", on_delete=models.PROTECT, default="IRT")
    amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    deposit_amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    rent_amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    advance_payment = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    remaining_amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    payment_method = models.CharField(max_length=120, blank=True, default="")

    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    terms_snapshot = models.TextField(blank=True, default="")
    obligations_json = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.DRAFT)

    class Meta:
        db_table = "contracts_contract"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["agency", "contract_number"], name="uq_contract_number_per_agency"
            )
        ]

    def delete(self, *args, **kwargs):
        raise ValidationError("Contracts cannot be hard-deleted; use TERMINATED or ARCHIVED status.")


class ContractParty(BaseModel):
    class Role(models.TextChoices):
        OWNER = "OWNER", "Owner / Seller / Landlord"
        COUNTERPARTY = "COUNTERPARTY", "Buyer / Tenant"
        GUARANTOR = "GUARANTOR", "Guarantor"
        WITNESS = "WITNESS", "Witness"

    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name="parties")
    customer = models.ForeignKey(
        "customers.Customer", null=True, blank=True, on_delete=models.PROTECT
    )
    full_name = models.CharField(max_length=160)
    party_role = models.CharField(max_length=20, choices=Role.choices)
    signed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "contracts_party"


class ContractStatusHistory(models.Model):
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name="status_history")
    from_status = models.CharField(max_length=32)
    to_status = models.CharField(max_length=32)
    reason = models.CharField(max_length=255, blank=True, default="")
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "contracts_status_history"

# Path: backend/django_core/apps/commissions/models.py

from decimal import Decimal
from django.db import models
from django.utils import timezone
from common.models import BaseModel, TenantScopedModel


class CommissionPolicy(TenantScopedModel):
    name = models.CharField(max_length=120)
    deal_type = models.ForeignKey("properties.DealType", on_delete=models.PROTECT)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "commissions_policy"
        unique_together = ("agency", "deal_type", "name")


class CommissionPolicyVersion(BaseModel):
    class FormulaType(models.TextChoices):
        PERCENT = "PERCENT", "Percentage of Deal Value"
        FIXED = "FIXED", "Fixed Amount"
        TIERED = "TIERED", "Tiered Brackets"

    policy = models.ForeignKey(
        CommissionPolicy, on_delete=models.CASCADE, related_name="versions"
    )
    version_number = models.PositiveIntegerField()
    effective_from = models.DateTimeField(default=timezone.now)
    formula_type = models.CharField(
        max_length=16, choices=FormulaType.choices, default=FormulaType.PERCENT
    )
    gross_rate_percent = models.DecimalField(
        max_digits=8, decimal_places=4, default=Decimal("1.0000")
    )
    fixed_amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    tax_rate_percent = models.DecimalField(
        max_digits=8, decimal_places=4, default=Decimal("10.0000")
    )
    platform_share_percent = models.DecimalField(
        max_digits=8, decimal_places=4, default=Decimal("0.0000")
    )
    agency_house_percent = models.DecimalField(
        max_digits=8, decimal_places=4, default=Decimal("50.0000")
    )
    primary_agent_percent = models.DecimalField(
        max_digits=8, decimal_places=4, default=Decimal("50.0000")
    )
    co_agent_split_ratio = models.DecimalField(
        max_digits=8, decimal_places=4, default=Decimal("50.0000")
    )
    rules_json = models.JSONField(default=dict, blank=True)
    is_published = models.BooleanField(default=True)

    class Meta:
        db_table = "commissions_policy_version"
        unique_together = ("policy", "version_number")
        ordering = ["-version_number"]


class DealCommission(TenantScopedModel):
    class Status(models.TextChoices):
        CALCULATED = "CALCULATED", "Calculated"
        MANAGER_APPROVED = "MANAGER_APPROVED", "Manager Approved"
        FINANCE_APPROVED = "FINANCE_APPROVED", "Finance Approved"
        SETTLED = "SETTLED", "Settled"
        REVERSED = "REVERSED", "Reversed"

    deal = models.OneToOneField(
        "transactions.Deal", on_delete=models.PROTECT, related_name="commission"
    )
    policy_version = models.ForeignKey(CommissionPolicyVersion, on_delete=models.PROTECT)
    currency = models.ForeignKey("settings.Currency", on_delete=models.PROTECT, default="IRT")

    base_amount = models.DecimalField(max_digits=20, decimal_places=2)
    gross_commission = models.DecimalField(max_digits=20, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    tax_amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    net_distributable = models.DecimalField(max_digits=20, decimal_places=2)
    calculation_snapshot = models.JSONField(default=dict)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.CALCULATED)

    class Meta:
        db_table = "commissions_deal_commission"


class CommissionShare(TenantScopedModel):
    class BeneficiaryType(models.TextChoices):
        PLATFORM = "PLATFORM", "Platform"
        AGENCY = "AGENCY", "Agency House"
        CO_AGENCY = "CO_AGENCY", "Co-Broker Agency"
        MANAGER = "MANAGER", "Manager Override"
        REFERRER = "REFERRER", "Referrer"
        AGENT = "AGENT", "Real Estate Agent"

    deal_commission = models.ForeignKey(
        DealCommission, on_delete=models.CASCADE, related_name="shares"
    )
    beneficiary_type = models.CharField(max_length=16, choices=BeneficiaryType.choices)
    beneficiary_membership = models.ForeignKey(
        "accounts.AgencyMembership",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="commission_shares",
    )
    share_percent_of_net = models.DecimalField(max_digits=8, decimal_places=4)
    calculated_amount = models.DecimalField(max_digits=20, decimal_places=2)
    is_included_in_payroll = models.BooleanField(default=False)

    class Meta:
        db_table = "commissions_share"

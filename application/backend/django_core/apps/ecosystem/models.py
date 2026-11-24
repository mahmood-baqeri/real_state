from django.conf import settings
from django.db import models
from common.models import BaseModel

class AfterDealCase(BaseModel):
    class Status(models.TextChoices):
        OPEN = "OPEN", "باز"
        IN_PROGRESS = "IN_PROGRESS", "در حال پیگیری"
        WAITING = "WAITING", "در انتظار پاسخ"
        RESOLVED = "RESOLVED", "حل‌شده"
        CANCELLED = "CANCELLED", "لغوشده"
    class Priority(models.TextChoices):
        LOW = "LOW", "عادی"
        MEDIUM = "MEDIUM", "متوسط"
        HIGH = "HIGH", "زیاد"
        URGENT = "URGENT", "فوری"
    agency = models.ForeignKey("agencies.Agency", on_delete=models.CASCADE, related_name="after_deal_cases")
    customer = models.ForeignKey("customers.Customer", on_delete=models.PROTECT, related_name="after_deal_cases")
    contract_id = models.UUIDField(null=True, blank=True, db_index=True)
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True, default="")
    category = models.CharField(max_length=40, default="GENERAL")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN, db_index=True)
    priority = models.CharField(max_length=12, choices=Priority.choices, default=Priority.MEDIUM)
    due_at = models.DateTimeField(null=True, blank=True, db_index=True)
    assigned_membership = models.ForeignKey("accounts.AgencyMembership", null=True, blank=True, on_delete=models.SET_NULL)
    resolved_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        db_table = "ecosystem_after_deal_case"
        ordering = ["-created_at"]

class AfterDealUpdate(BaseModel):
    case = models.ForeignKey(AfterDealCase, on_delete=models.CASCADE, related_name="updates")
    body = models.TextField()
    status_from = models.CharField(max_length=20, blank=True, default="")
    status_to = models.CharField(max_length=20, blank=True, default="")
    class Meta:
        db_table = "ecosystem_after_deal_update"
        ordering = ["-created_at"]


class CooperationPropertyShare(BaseModel):
    """Explicit, revocable consent to expose a provider agency listing to its partner."""
    cooperation = models.ForeignKey(
        "agencies.AgencyCooperation", on_delete=models.CASCADE, related_name="property_shares"
    )
    property = models.ForeignKey(
        "properties.Property", on_delete=models.CASCADE, related_name="cooperation_shares"
    )
    shared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="ecosystem_shared_properties"
    )
    is_active = models.BooleanField(default=True, db_index=True)
    consented_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "ecosystem_cooperation_property_share"
        constraints = [
            models.UniqueConstraint(fields=["cooperation", "property"], name="uq_ecosystem_coop_property")
        ]


class CooperationSettlement(BaseModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "پیش‌نویس"
        PENDING_APPROVAL = "PENDING_APPROVAL", "در انتظار تأیید"
        APPROVED = "APPROVED", "تأییدشده"
        PAID = "PAID", "پرداخت‌شده"
        CANCELLED = "CANCELLED", "لغوشده"

    cooperation = models.ForeignKey(
        "agencies.AgencyCooperation", on_delete=models.PROTECT, related_name="settlements"
    )
    contract = models.ForeignKey(
        "contracts.Contract", null=True, blank=True, on_delete=models.PROTECT,
        related_name="cooperation_settlements"
    )
    payer_agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.PROTECT, related_name="cooperation_payables"
    )
    payee_agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.PROTECT, related_name="cooperation_receivables"
    )
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    currency_code = models.CharField(max_length=10)
    split_percent = models.DecimalField(max_digits=6, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    description = models.CharField(max_length=300, blank=True, default="")
    external_reference = models.CharField(max_length=120, blank=True, default="")
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="ecosystem_approved_settlements"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "ecosystem_cooperation_settlement"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(check=models.Q(amount__gt=0), name="ck_ecosystem_settlement_amount_positive"),
            models.CheckConstraint(check=models.Q(split_percent__gte=0, split_percent__lte=100), name="ck_ecosystem_settlement_split_range"),
        ]


class TrustScoreSnapshot(BaseModel):
    agency = models.ForeignKey("agencies.Agency", on_delete=models.CASCADE, related_name="trust_score_snapshots")
    score = models.PositiveSmallIntegerField(null=True, blank=True)
    methodology_version = models.CharField(max_length=24, default="1.0")
    components = models.JSONField(default=dict, blank=True)
    evidence = models.JSONField(default=dict, blank=True)
    coverage = models.PositiveSmallIntegerField(default=0)
    is_public = models.BooleanField(default=False)

    class Meta:
        db_table = "ecosystem_trust_score_snapshot"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["agency", "-created_at"])]


class OwnerReportSnapshot(BaseModel):
    agency = models.ForeignKey("agencies.Agency", on_delete=models.CASCADE, related_name="owner_reports")
    owner_customer = models.ForeignKey("customers.Customer", on_delete=models.PROTECT, related_name="owner_reports")
    period_start = models.DateField()
    period_end = models.DateField()
    report_data = models.JSONField(default=dict, blank=True)
    generated_at = models.DateTimeField()
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="ecosystem_owner_reports"
    )

    class Meta:
        db_table = "ecosystem_owner_report_snapshot"
        ordering = ["-generated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["agency", "owner_customer", "period_start", "period_end"],
                name="uq_ecosystem_owner_report_period"
            )
        ]

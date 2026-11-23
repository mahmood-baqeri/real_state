from decimal import Decimal
from django.db import models
from common.models import BaseModel, TenantScopedModel


class Negotiation(TenantScopedModel):
    class Status(models.TextChoices):
        CREATED = "CREATED", "مذاکره ایجاد شده"
        AWAITING_BUYER_OFFER = "AWAITING_BUYER_OFFER", "در انتظار پیشنهاد مشتری"
        BUYER_OFFERED = "BUYER_OFFERED", "پیشنهاد مشتری ثبت شده"
        AWAITING_OWNER_RESPONSE = "AWAITING_OWNER_RESPONSE", "در انتظار پاسخ مالک"
        OWNER_COUNTERED = "OWNER_COUNTERED", "پیشنهاد مالک ثبت شده"
        BARGAINING = "BARGAINING", "در حال چانه‌زنی"
        PRE_AGREEMENT = "PRE_AGREEMENT", "توافق اولیه"
        AWAITING_FINAL_APPROVAL = "AWAITING_FINAL_APPROVAL", "در انتظار تأیید نهایی"
        ACCEPTED = "ACCEPTED", "موفق"
        REJECTED = "REJECTED", "ناموفق"
        PAUSED = "PAUSED", "متوقف شده"
        CANCELLED = "CANCELLED", "لغو شده"
        # Legacy aliases preserved for backward compatibility
        OPEN = "OPEN", "Open"
        COUNTER_OFFERED = "COUNTER_OFFERED", "Counter Offered"
        WITHDRAWN = "WITHDRAWN", "Withdrawn"
        EXPIRED = "EXPIRED", "Expired"

    property = models.ForeignKey(
        "properties.Property", on_delete=models.PROTECT, related_name="negotiations"
    )
    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.PROTECT, related_name="negotiations"
    )
    owner_customer = models.ForeignKey(
        "customers.Customer",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="owner_negotiations",
    )
    agent_membership = models.ForeignKey(
        "accounts.AgencyMembership", on_delete=models.PROTECT, related_name="negotiations"
    )
    deal_type = models.ForeignKey("properties.DealType", on_delete=models.PROTECT)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.CREATED, db_index=True)
    asking_price = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    initial_proposed_price = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    latest_proposed_price = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    agreed_price = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    next_followup_at = models.DateTimeField(null=True, blank=True, db_index=True)
    next_action = models.CharField(max_length=200, blank=True, default="")
    last_activity_at = models.DateTimeField(null=True, blank=True)
    outcome_reason = models.CharField(max_length=255, blank=True, default="")
    converted_contract = models.ForeignKey(
        "contracts.Contract",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="source_negotiations",
    )
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
    recipient_role = models.CharField(max_length=16, default="SELLER")
    currency = models.ForeignKey("settings.Currency", on_delete=models.PROTECT, default="IRT")
    proposed_price = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    proposed_deposit = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    proposed_rent = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    discount_amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    payment_terms = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True, default="")
    response_note = models.TextField(blank=True, default="")
    responded_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    valid_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "negotiations_offer_version"
        unique_together = ("negotiation", "version_number")
        ordering = ["-version_number"]


class NegotiationActivity(BaseModel):
    class ActivityType(models.TextChoices):
        CALL = "CALL", "تماس تلفنی"
        MEETING = "MEETING", "جلسه حضوری"
        MESSAGE = "MESSAGE", "مکاتبه / پیام"
        INTERNAL_NOTE = "INTERNAL_NOTE", "یادداشت داخلی"
        OFFER = "OFFER", "ثبت پیشنهاد قیمتی"
        STATUS_CHANGE = "STATUS_CHANGE", "تغییر وضعیت"
        CONTRACT_CONVERTED = "CONTRACT_CONVERTED", "تبدیل به قرارداد"

    negotiation = models.ForeignKey(
        Negotiation, on_delete=models.CASCADE, related_name="activities"
    )
    activity_type = models.CharField(max_length=24, choices=ActivityType.choices, default=ActivityType.INTERNAL_NOTE)
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True, default="")
    outcome = models.CharField(max_length=160, blank=True, default="")
    next_action = models.CharField(max_length=200, blank=True, default="")
    next_action_due_at = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=True)
    assigned_membership = models.ForeignKey(
        "accounts.AgencyMembership",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="negotiation_activities",
    )

    class Meta:
        db_table = "negotiations_activity"
        ordering = ["-created_at"]

# Path: backend/django_core/apps/customers/models.py

from decimal import Decimal
from django.conf import settings
from django.db import models
from common.encryption import decrypt_sensitive_value, encrypt_sensitive_value
from common.models import BaseModel, SoftDeleteMixin, TenantScopedModel


class Customer(TenantScopedModel, SoftDeleteMixin):
    class CustomerType(models.TextChoices):
        BUYER = "BUYER", "Buyer"
        SELLER = "SELLER", "Seller"
        TENANT = "TENANT", "Tenant"
        LANDLORD = "LANDLORD", "Landlord"
        INVESTOR = "INVESTOR", "Investor"
        OWNER = "OWNER", "Owner"
        PARTNERSHIP = "PARTNERSHIP", "Construction Partnership"
        PROSPECT = "PROSPECT", "Prospect"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="customer_profiles",
    )
    customer_type = models.CharField(
        max_length=24, choices=CustomerType.choices, default=CustomerType.BUYER
    )
    full_name = models.CharField(max_length=160)
    primary_phone = models.CharField(max_length=24, db_index=True)
    secondary_phone = models.CharField(max_length=24, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    national_id_encrypted = models.TextField(blank=True, default="")
    source = models.CharField(max_length=64, blank=True, default="PORTAL")
    assigned_membership = models.ForeignKey(
        "accounts.AgencyMembership",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_customers",
    )
    lead_score = models.PositiveSmallIntegerField(default=50)
    readiness_level = models.CharField(
        max_length=24,
        choices=[("LOW", "Low"), ("MEDIUM", "Medium"), ("HIGH", "High"), ("HOT", "Hot")],
        default="MEDIUM",
    )
    tags = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "customers_customer"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["agency", "primary_phone"], name="uq_customer_phone_per_agency"
            )
        ]

    def set_national_id(self, raw: str) -> None:
        self.national_id_encrypted = encrypt_sensitive_value(raw)

    def get_national_id(self) -> str:
        return decrypt_sensitive_value(self.national_id_encrypted)


class CustomerShare(BaseModel):
    class AccessLevel(models.TextChoices):
        VIEW = "VIEW", "View Only"
        EDIT = "EDIT", "View & Edit"

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="shares")
    membership = models.ForeignKey(
        "accounts.AgencyMembership", on_delete=models.CASCADE, related_name="shared_customers"
    )
    access_level = models.CharField(
        max_length=12, choices=AccessLevel.choices, default=AccessLevel.VIEW
    )
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "customers_share"
        unique_together = ("customer", "membership")


class CustomerRequirement(TenantScopedModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="requirements")
    deal_type = models.ForeignKey("properties.DealType", on_delete=models.PROTECT)
    property_type = models.ForeignKey("properties.PropertyType", on_delete=models.PROTECT)
    target_city = models.CharField(max_length=80, blank=True, default="")
    target_districts = models.JSONField(default=list, blank=True)
    min_area_sqm = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    max_area_sqm = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("99999.00"))
    currency = models.ForeignKey("settings.Currency", on_delete=models.PROTECT, default="IRT")
    min_budget = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    max_budget = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    min_bedrooms = models.PositiveSmallIntegerField(default=0)
    required_amenities = models.JSONField(default=list, blank=True)
    priority = models.CharField(max_length=16, default="NORMAL")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "customers_requirement"

from decimal import Decimal
from django.conf import settings
from django.db import models
from common.models import BaseModel, SoftDeleteMixin


class Agency(BaseModel, SoftDeleteMixin):
    class Status(models.TextChoices):
        PENDING_REVIEW = "PENDING_REVIEW", "Pending Review"
        APPROVED = "APPROVED", "Approved"
        ACTIVE = "ACTIVE", "Active"
        SUSPENDED = "SUSPENDED", "Suspended"
        ARCHIVED = "ARCHIVED", "Archived"

    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=160, unique=True)
    registration_number = models.CharField(max_length=64, blank=True, default="")
    tax_id = models.CharField(max_length=64, blank=True, default="")
    phone = models.CharField(max_length=32, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    logo_url = models.URLField(blank=True, default="")
    description = models.TextField(blank=True, default="")

    country = models.ForeignKey(
        "settings.Country", on_delete=models.PROTECT, default="IR", related_name="agencies"
    )
    default_currency = models.ForeignKey(
        "settings.Currency", on_delete=models.PROTECT, default="IRT", related_name="agencies"
    )
    default_calendar = models.CharField(
        max_length=16, choices=[("jalali", "Jalali"), ("gregorian", "Gregorian")], default="jalali"
    )
    timezone = models.CharField(max_length=64, default="Asia/Tehran")
    area_unit = models.CharField(
        max_length=16, choices=[("SQM", "Square Meter"), ("SQFT", "Square Feet")], default="SQM"
    )

    owner_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="owned_agencies"
    )
    status = models.CharField(
        max_length=24, choices=Status.choices, default=Status.PENDING_REVIEW, db_index=True
    )

    class Meta:
        db_table = "agencies_agency"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name


class AgencyAccessPolicy(BaseModel):
    """
    Independent agency-level access policy settings covering all 10 mandated domains,
    enforced strictly at Backend ORM / Serializer / Service layers.
    """

    class PropertyViewScope(models.TextChoices):
        OWN_AND_SHARED = "OWN_AND_SHARED", "Own & Explicitly Shared"
        PUBLIC_AGENCY = "PUBLIC_AGENCY", "Own + Agency Public Listings"
        ALL_AGENCY = "ALL_AGENCY", "All Agency Listings (Permissioned)"

    class PropertyEditScope(models.TextChoices):
        ASSIGNED_ONLY = "ASSIGNED_ONLY", "Assigned Agent Only"
        BRANCH = "BRANCH", "Branch Authorized Staff"
        ALL_WITH_PERMISSION = "ALL_WITH_PERMISSION", "All With Explicit Permission"

    class CustomerViewScope(models.TextChoices):
        ASSIGNED_AND_SHARED = "ASSIGNED_AND_SHARED", "Assigned & Shared Only"
        BRANCH = "BRANCH", "Branch Managers"
        ALL_WITH_PERMISSION = "ALL_WITH_PERMISSION", "All With Explicit Permission"

    class CustomerEditScope(models.TextChoices):
        ASSIGNED_ONLY = "ASSIGNED_ONLY", "Assigned Agent Only"
        SHARED_EDITORS = "SHARED_EDITORS", "Assigned & Shared Editors"
        ALL_WITH_PERMISSION = "ALL_WITH_PERMISSION", "All With Explicit Permission"

    class OwnerPIIVisibility(models.TextChoices):
        ASSIGNED_AND_MANAGER = "ASSIGNED_AND_MANAGER", "Assigned Agent & Agency Manager"
        MANAGERS_ONLY = "MANAGERS_ONLY", "Agency Managers Only"
        PERMISSION_BASED = "PERMISSION_BASED", "Explicit Permission Required"

    class StandardVisibility(models.TextChoices):
        ASSIGNED_ONLY = "ASSIGNED_ONLY", "Assigned Only"
        MANAGERS_AND_FINANCE = "MANAGERS_AND_FINANCE", "Managers & Finance"
        PERMISSION_BASED = "PERMISSION_BASED", "Permission Based"

    class CommissionVisibility(models.TextChoices):
        OWN_ONLY = "OWN_ONLY", "Own Commission Only"
        TEAM_LEAD = "TEAM_LEAD", "Own + Team"
        ALL_WITH_PERMISSION = "ALL_WITH_PERMISSION", "All With Permission"

    class PerformanceVisibility(models.TextChoices):
        OWN_ONLY = "OWN_ONLY", "Own Performance Only"
        RANKING_ONLY = "RANKING_ONLY", "Anonymized Ranking"
        FULL_TEAM = "FULL_TEAM", "Full Team Metrics"

    agency = models.OneToOneField(Agency, on_delete=models.CASCADE, related_name="access_policy")

    property_view_scope = models.CharField(
        max_length=32, choices=PropertyViewScope.choices, default=PropertyViewScope.PUBLIC_AGENCY
    )
    property_edit_scope = models.CharField(
        max_length=32, choices=PropertyEditScope.choices, default=PropertyEditScope.ASSIGNED_ONLY
    )
    customer_view_scope = models.CharField(
        max_length=32,
        choices=CustomerViewScope.choices,
        default=CustomerViewScope.ASSIGNED_AND_SHARED,
    )
    customer_edit_scope = models.CharField(
        max_length=32, choices=CustomerEditScope.choices, default=CustomerEditScope.SHARED_EDITORS
    )
    owner_pii_visibility = models.CharField(
        max_length=32,
        choices=OwnerPIIVisibility.choices,
        default=OwnerPIIVisibility.ASSIGNED_AND_MANAGER,
    )
    negotiation_visibility = models.CharField(
        max_length=32,
        choices=StandardVisibility.choices,
        default=StandardVisibility.ASSIGNED_ONLY,
    )
    contract_visibility = models.CharField(
        max_length=32,
        choices=StandardVisibility.choices,
        default=StandardVisibility.ASSIGNED_ONLY,
    )
    financial_visibility = models.CharField(
        max_length=32,
        choices=StandardVisibility.choices,
        default=StandardVisibility.MANAGERS_AND_FINANCE,
    )
    commission_visibility = models.CharField(
        max_length=32,
        choices=CommissionVisibility.choices,
        default=CommissionVisibility.OWN_ONLY,
    )
    agent_performance_visibility = models.CharField(
        max_length=32,
        choices=PerformanceVisibility.choices,
        default=PerformanceVisibility.OWN_ONLY,
    )

    class Meta:
        db_table = "agencies_access_policy"


class AgencyCooperation(BaseModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACTIVE = "ACTIVE", "Active"
        REVOKED = "REVOKED", "Revoked"

    requester_agency = models.ForeignKey(
        Agency, on_delete=models.CASCADE, related_name="cooperation_requests"
    )
    provider_agency = models.ForeignKey(
        Agency, on_delete=models.CASCADE, related_name="cooperation_grants"
    )
    default_split_percent = models.DecimalField(
        max_digits=6, decimal_places=2, default=Decimal("50.00")
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)

    class Meta:
        db_table = "agencies_cooperation"
        unique_together = ("requester_agency", "provider_agency")

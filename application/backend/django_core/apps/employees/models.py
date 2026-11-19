# Path: backend/django_core/apps/employees/models.py

from decimal import Decimal
from django.db import models
from common.models import TenantScopedModel


class EmployeeProfile(TenantScopedModel):
    class EmploymentType(models.TextChoices):
        FULL_TIME = "FULL_TIME", "Full Time"
        COMMISSION_AGENT = "COMMISSION_AGENT", "Commission Agent"
        CONTRACTOR = "CONTRACTOR", "Contractor"

    membership = models.OneToOneField(
        "accounts.AgencyMembership", on_delete=models.CASCADE, related_name="employee_profile"
    )
    employee_code = models.CharField(max_length=32)
    job_title = models.CharField(max_length=100, default="مشاور املاک")
    employment_type = models.CharField(
        max_length=24, choices=EmploymentType.choices, default=EmploymentType.COMMISSION_AGENT
    )
    hire_date = models.DateField()
    monthly_sales_target = models.DecimalField(
        max_digits=20, decimal_places=2, default=Decimal("0.00")
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "employees_profile"
        unique_together = ("agency", "employee_code")


class CompensationPlan(TenantScopedModel):
    class ModelType(models.TextChoices):
        FIXED = "FIXED", "Fixed Salary"
        FIXED_PLUS_COMMISSION = "FIXED_PLUS_COMMISSION", "Fixed + Commission"
        PURE_COMMISSION = "PURE_COMMISSION", "Pure Commission"
        TIERED_COMMISSION = "TIERED_COMMISSION", "Tiered Commission"
        PERFORMANCE_BASED = "PERFORMANCE_BASED", "Performance Based"
        TEAM_OVERRIDE = "TEAM_OVERRIDE", "Team Group Commission"
        CUSTOM = "CUSTOM", "Custom"

    employee = models.ForeignKey(
        EmployeeProfile, on_delete=models.CASCADE, related_name="compensation_plans"
    )
    model_type = models.CharField(
        max_length=32, choices=ModelType.choices, default=ModelType.FIXED_PLUS_COMMISSION
    )
    currency = models.ForeignKey("settings.Currency", on_delete=models.PROTECT, default="IRT")
    base_salary = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    commission_multiplier = models.DecimalField(
        max_digits=6, decimal_places=4, default=Decimal("1.0000")
    )
    tiered_rules_json = models.JSONField(default=list, blank=True)
    effective_from = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "employees_compensation_plan"

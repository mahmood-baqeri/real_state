from decimal import Decimal
from django.db import models
from common.models import BaseModel, TenantScopedModel


class PayrollCycle(TenantScopedModel):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        CALCULATED = "CALCULATED", "Calculated"
        APPROVED = "APPROVED", "Approved"
        PAID = "PAID", "Paid"
        CANCELLED = "CANCELLED", "Cancelled"

    title = models.CharField(max_length=80)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)

    class Meta:
        db_table = "payroll_cycle"
        unique_together = ("agency", "title")


class Payslip(TenantScopedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        APPROVED = "APPROVED", "Approved"
        PAID = "PAID", "Paid"
        CANCELLED = "CANCELLED", "Cancelled"

    cycle = models.ForeignKey(PayrollCycle, on_delete=models.PROTECT, related_name="payslips")
    employee = models.ForeignKey(
        "employees.EmployeeProfile", on_delete=models.PROTECT, related_name="payslips"
    )
    currency = models.ForeignKey("settings.Currency", on_delete=models.PROTECT, default="IRT")
    base_salary_amount = models.DecimalField(
        max_digits=20, decimal_places=2, default=Decimal("0.00")
    )
    commission_amount = models.DecimalField(
        max_digits=20, decimal_places=2, default=Decimal("0.00")
    )
    bonus_amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    deductions_amount = models.DecimalField(
        max_digits=20, decimal_places=2, default=Decimal("0.00")
    )
    tax_amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    net_payable = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)

    class Meta:
        db_table = "payroll_payslip"
        unique_together = ("cycle", "employee")


class PayslipLineItem(BaseModel):
    class ItemType(models.TextChoices):
        BASE_SALARY = "BASE_SALARY", "Base Salary"
        COMMISSION = "COMMISSION", "Commission"
        BONUS = "BONUS", "Bonus"
        OVERTIME = "OVERTIME", "Overtime"
        DEDUCTION = "DEDUCTION", "Deduction"
        ADVANCE = "ADVANCE", "Advance"
        TAX = "TAX", "Tax"

    payslip = models.ForeignKey(Payslip, on_delete=models.CASCADE, related_name="items")
    item_type = models.CharField(max_length=16, choices=ItemType.choices)
    description = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    commission_share = models.OneToOneField(
        "commissions.CommissionShare",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="payslip_item",
    )

    class Meta:
        db_table = "payroll_payslip_item"

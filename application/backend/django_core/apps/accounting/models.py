from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models
from common.models import BaseModel, TenantScopedModel


class FiscalYear(TenantScopedModel):
    title = models.CharField(max_length=64)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_closed = models.BooleanField(default=False)

    class Meta:
        db_table = "accounting_fiscal_year"
        unique_together = ("agency", "title")


class FiscalPeriod(TenantScopedModel):
    fiscal_year = models.ForeignKey(
        FiscalYear, on_delete=models.PROTECT, related_name="periods"
    )
    name = models.CharField(max_length=64)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_closed = models.BooleanField(default=False)

    class Meta:
        db_table = "accounting_fiscal_period"
        unique_together = ("fiscal_year", "name")


class ChartOfAccount(TenantScopedModel):
    class AccountType(models.TextChoices):
        ASSET = "ASSET", "Asset"
        LIABILITY = "LIABILITY", "Liability"
        EQUITY = "EQUITY", "Equity"
        REVENUE = "REVENUE", "Revenue"
        EXPENSE = "EXPENSE", "Expense"

    class Level(models.TextChoices):
        CLASS = "CLASS", "Group"
        GENERAL = "GENERAL", "General Ledger"
        SUBSIDIARY = "SUBSIDIARY", "Subsidiary"
        DETAIL = "DETAIL", "Detail"

    code = models.CharField(max_length=32)
    name = models.CharField(max_length=160)
    account_type = models.CharField(max_length=16, choices=AccountType.choices)
    level = models.CharField(max_length=16, choices=Level.choices, default=Level.SUBSIDIARY)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "accounting_coa"
        unique_together = ("agency", "code")
        ordering = ["code"]


class CostCenter(TenantScopedModel):
    code = models.CharField(max_length=32)
    name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "accounting_cost_center"
        unique_together = ("agency", "code")


class JournalEntry(TenantScopedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        POSTED = "POSTED", "Posted"
        REVERSED = "REVERSED", "Reversed"

    fiscal_period = models.ForeignKey(FiscalPeriod, on_delete=models.PROTECT)
    entry_number = models.CharField(max_length=40)
    entry_date = models.DateTimeField()
    description = models.CharField(max_length=255)
    currency = models.ForeignKey("settings.Currency", on_delete=models.PROTECT, default="IRT")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    source_type = models.CharField(max_length=48, blank=True, default="MANUAL")
    source_id = models.CharField(max_length=64, blank=True, default="")
    reversed_entry = models.OneToOneField(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="reversal_entry"
    )

    class Meta:
        db_table = "accounting_journal_entry"
        unique_together = ("agency", "entry_number")
        ordering = ["-entry_date", "-created_at"]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            prev = JournalEntry.objects.all_tenants().filter(pk=self.pk).values("status").first()
            if prev and prev["status"] == self.Status.POSTED and self.status != self.Status.REVERSED:
                raise ValidationError("Posted journal entries are immutable and cannot be edited.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Journal entries cannot be deleted; issue a reversal entry instead.")


class JournalEntryLine(BaseModel):
    journal_entry = models.ForeignKey(
        JournalEntry, on_delete=models.CASCADE, related_name="lines"
    )
    account = models.ForeignKey(ChartOfAccount, on_delete=models.PROTECT, related_name="lines")
    cost_center = models.ForeignKey(
        CostCenter, null=True, blank=True, on_delete=models.PROTECT
    )
    description = models.CharField(max_length=255, blank=True, default="")
    debit = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    credit = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        db_table = "accounting_journal_entry_line"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(debit__gte=0) & models.Q(credit__gte=0),
                name="chk_journal_line_non_negative",
            )
        ]


class BankAccount(TenantScopedModel):
    bank_name = models.CharField(max_length=120)
    account_number = models.CharField(max_length=64)
    iban = models.CharField(max_length=40, blank=True, default="")
    currency = models.ForeignKey("settings.Currency", on_delete=models.PROTECT, default="IRT")
    coa_account = models.ForeignKey(ChartOfAccount, on_delete=models.PROTECT)
    current_balance = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "accounting_bank_account"


class CashBox(TenantScopedModel):
    name = models.CharField(max_length=120)
    currency = models.ForeignKey("settings.Currency", on_delete=models.PROTECT, default="IRT")
    coa_account = models.ForeignKey(ChartOfAccount, on_delete=models.PROTECT)
    current_balance = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "accounting_cash_box"


class ChequeInstrument(TenantScopedModel):
    class Direction(models.TextChoices):
        RECEIVABLE = "RECEIVABLE", "Receivable"
        PAYABLE = "PAYABLE", "Payable"

    class Status(models.TextChoices):
        HELD = "HELD", "Held"
        CLEARED = "CLEARED", "Cleared"
        BOUNCED = "BOUNCED", "Bounced"
        CANCELLED = "CANCELLED", "Cancelled"

    direction = models.CharField(max_length=16, choices=Direction.choices)
    cheque_number = models.CharField(max_length=48)
    bank_name = models.CharField(max_length=100)
    due_date = models.DateTimeField(db_index=True)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    currency = models.ForeignKey("settings.Currency", on_delete=models.PROTECT, default="IRT")
    deal = models.ForeignKey(
        "transactions.Deal", null=True, blank=True, on_delete=models.PROTECT
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.HELD)

    class Meta:
        db_table = "accounting_cheque"


class DealFinancialLedger(TenantScopedModel):
    class SettlementStatus(models.TextChoices):
        OPEN = "OPEN", "Open"
        PARTIAL = "PARTIAL", "Partially Settled"
        SETTLED = "SETTLED", "Settled"

    deal = models.OneToOneField(
        "transactions.Deal", on_delete=models.PROTECT, related_name="financial_ledger"
    )
    currency = models.ForeignKey("settings.Currency", on_delete=models.PROTECT, default="IRT")
    deal_amount = models.DecimalField(max_digits=20, decimal_places=2)
    total_received = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    total_paid = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    gross_commission = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    agency_share = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    agents_share = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    related_expenses = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    tax_deductions = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    net_profit = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    settlement_status = models.CharField(
        max_length=16, choices=SettlementStatus.choices, default=SettlementStatus.OPEN
    )

    class Meta:
        db_table = "accounting_deal_ledger"

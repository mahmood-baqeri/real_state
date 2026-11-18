from decimal import Decimal
from typing import Iterable, Optional
from uuid import UUID
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from apps.accounts.models import User
from apps.audit.services import record_audit_event
from common.exceptions import (
    ConflictDomainError,
    NotFoundDomainError,
    PermissionDeniedDomainError,
    ValidationDomainError,
)
from common.localization.currency import quantize_amount
from common.permissions import has_agency_permission, is_super_admin
from .models import (
    BankAccount,
    CashBox,
    ChartOfAccount,
    ChequeInstrument,
    DealFinancialLedger,
    FiscalPeriod,
    JournalEntry,
    JournalEntryLine,
)


def assert_accounting_view(user: User, agency_id: UUID) -> None:
    if not (is_super_admin(user) or has_agency_permission(user, agency_id, "accounting.view")):
        raise PermissionDeniedDomainError("دسترسی به دفاتر حسابداری مجاز نیست.")


def assert_accounting_post(user: User, agency_id: UUID) -> None:
    if not (is_super_admin(user) or has_agency_permission(user, agency_id, "accounting.post")):
        raise PermissionDeniedDomainError("عدم مجوز ثبت یا تغییر اسناد حسابداری.")


@transaction.atomic
def create_and_post_journal_entry(
    *,
    agency,
    fiscal_period: FiscalPeriod,
    entry_number: str,
    description: str,
    lines: Iterable[dict],
    currency_id: str = "IRT",
    source_type: str = "MANUAL",
    source_id: str = "",
    actor=None,
) -> JournalEntry:
    """
    Atomically validates double-entry balance (SUM(debit) == SUM(credit)),
    verifies open fiscal period, and posts an immutable JournalEntry.
    """
    locked_period = FiscalPeriod.objects.all_tenants().select_for_update().get(pk=fiscal_period.pk)
    if locked_period.is_closed or locked_period.fiscal_year.is_closed:
        raise ValidationError("Cannot post journal entries into a closed fiscal period.")

    line_list = list(lines)
    if len(line_list) < 2:
        raise ValidationError("A double-entry journal must have at least 2 lines.")

    total_debit = Decimal("0.00")
    total_credit = Decimal("0.00")
    normalized_lines = []

    for item in line_list:
        debit = quantize_amount(Decimal(item.get("debit", "0")), currency_id)
        credit = quantize_amount(Decimal(item.get("credit", "0")), currency_id)
        if debit < 0 or credit < 0:
            raise ValidationError("Debit and credit amounts must be non-negative.")
        if debit > 0 and credit > 0:
            raise ValidationError("A single journal line cannot have both debit and credit > 0.")
        if debit == 0 and credit == 0:
            raise ValidationError("A journal line must have either debit or credit > 0.")
        total_debit += debit
        total_credit += credit
        normalized_lines.append({**item, "debit": debit, "credit": credit})

    if total_debit != total_credit:
        raise ValidationError(
            f"Unbalanced journal entry: total_debit ({total_debit}) != total_credit ({total_credit})."
        )

    entry = JournalEntry.objects.create(
        agency=agency,
        fiscal_period=locked_period,
        entry_number=entry_number,
        entry_date=timezone.now(),
        description=description,
        currency_id=currency_id,
        status=JournalEntry.Status.POSTED,
        source_type=source_type,
        source_id=str(source_id),
        created_by=actor,
    )

    for line in normalized_lines:
        account = line.get("account") or line.get("account_id")
        if isinstance(account, (str, UUID)):
            account = ChartOfAccount.objects.all_tenants().get(pk=account, agency=agency)
        JournalEntryLine.objects.create(
            journal_entry=entry,
            account=account,
            cost_center=line.get("cost_center"),
            description=line.get("description", ""),
            debit=line["debit"],
            credit=line["credit"],
            created_by=actor,
        )

    return entry


@transaction.atomic
def reverse_journal_entry(
    *, original_entry: JournalEntry, reversal_number: str, actor=None
) -> JournalEntry:
    locked = JournalEntry.objects.all_tenants().select_for_update().get(pk=original_entry.pk)
    if locked.status != JournalEntry.Status.POSTED:
        raise ValidationError("Only POSTED journal entries can be reversed.")

    reversed_lines = [
        {
            "account": line.account,
            "cost_center": line.cost_center,
            "description": f"Reversal: {line.description}",
            "debit": line.credit,
            "credit": line.debit,
        }
        for line in locked.lines.all()
    ]

    reversal = create_and_post_journal_entry(
        agency=locked.agency,
        fiscal_period=locked.fiscal_period,
        entry_number=reversal_number,
        description=f"Reversal of {locked.entry_number}",
        lines=reversed_lines,
        currency_id=locked.currency_id,
        source_type="REVERSAL",
        source_id=str(locked.id),
        actor=actor,
    )
    reversal.reversed_entry = locked
    JournalEntry.objects.all_tenants().filter(pk=locked.pk).update(
        status=JournalEntry.Status.REVERSED
    )
    return reversal


def list_coa(*, user: User, agency_id: UUID) -> list[ChartOfAccount]:
    assert_accounting_view(user, agency_id)
    return list(
        ChartOfAccount.objects.all_tenants()
        .filter(agency_id=agency_id, is_active=True)
        .order_by("code")
    )


@transaction.atomic
def create_coa_account(*, user: User, agency_id: UUID, data: dict) -> ChartOfAccount:
    assert_accounting_post(user, agency_id)
    if ChartOfAccount.objects.all_tenants().filter(agency_id=agency_id, code=data["code"]).exists():
        raise ConflictDomainError("کد حساب در کدینگ آژانس تکراری است.")
    return ChartOfAccount.objects.all_tenants().create(
        agency_id=agency_id,
        code=data["code"].strip(),
        name=data["name"].strip(),
        account_type=data["account_type"],
        level=data.get("level", ChartOfAccount.Level.SUBSIDIARY),
        parent_id=data.get("parent_id"),
        created_by=user,
    )


def list_journal_entries(*, user: User, agency_id: UUID):
    assert_accounting_view(user, agency_id)
    return (
        JournalEntry.objects.all_tenants()
        .filter(agency_id=agency_id)
        .select_related("fiscal_period", "currency")
        .prefetch_related("lines__account")
        .order_by("-entry_date", "-created_at")
    )


def post_journal_entry_service(*, user: User, agency_id: UUID, data: dict) -> JournalEntry:
    assert_accounting_post(user, agency_id)
    period = (
        FiscalPeriod.objects.all_tenants()
        .filter(agency_id=agency_id, is_closed=False)
        .first()
    )
    if not period:
        raise ValidationDomainError("دوره مالی باز در این آژانس یافت نشد.")
    try:
        entry = create_and_post_journal_entry(
            agency=period.agency,
            fiscal_period=period,
            entry_number=data["entry_number"],
            description=data["description"],
            lines=data["lines"],
            currency_id=data.get("currency_id", "IRT"),
            source_type=data.get("source_type", "MANUAL"),
            actor=user,
        )
    except ValidationError as exc:
        raise ValidationDomainError(str(exc.message if hasattr(exc, "message") else exc))
    record_audit_event(
        action="JOURNAL_ENTRY_POSTED",
        resource_type="JournalEntry",
        resource_id=str(entry.id),
        actor=user,
        agency_id=agency_id,
    )
    return entry


def reverse_journal_entry_service(*, user: User, agency_id: UUID, entry_id: UUID) -> JournalEntry:
    assert_accounting_post(user, agency_id)
    entry = JournalEntry.objects.all_tenants().filter(id=entry_id, agency_id=agency_id).first()
    if not entry:
        raise NotFoundDomainError("سند حسابداری یافت نشد.")
    try:
        rev = reverse_journal_entry(
            original_entry=entry, reversal_number=f"REV-{entry.entry_number}", actor=user
        )
    except ValidationError as exc:
        raise ValidationDomainError(str(exc.message if hasattr(exc, "message") else exc))
    record_audit_event(
        action="JOURNAL_ENTRY_REVERSED",
        resource_type="JournalEntry",
        resource_id=str(rev.id),
        actor=user,
        agency_id=agency_id,
    )
    return rev


def list_treasury_and_cheques(*, user: User, agency_id: UUID) -> dict:
    assert_accounting_view(user, agency_id)
    return {
        "bank_accounts": list(
            BankAccount.objects.all_tenants().filter(agency_id=agency_id, is_active=True)
        ),
        "cash_boxes": list(
            CashBox.objects.all_tenants().filter(agency_id=agency_id, is_active=True)
        ),
        "cheques": list(
            ChequeInstrument.objects.all_tenants()
            .filter(agency_id=agency_id)
            .select_related("deal")
            .order_by("due_date")
        ),
        "deal_ledgers": list(
            DealFinancialLedger.objects.all_tenants()
            .filter(agency_id=agency_id)
            .select_related("deal")
        ),
    }


@transaction.atomic
def create_cheque(*, user: User, agency_id: UUID, data: dict) -> ChequeInstrument:
    assert_accounting_post(user, agency_id)
    return ChequeInstrument.objects.all_tenants().create(
        agency_id=agency_id,
        direction=data["direction"],
        cheque_number=data["cheque_number"],
        bank_name=data["bank_name"],
        due_date=data["due_date"],
        amount=Decimal(data["amount"]),
        currency_id=data.get("currency_id", "IRT"),
        deal_id=data.get("deal_id"),
        created_by=user,
    )


@transaction.atomic
def update_cheque_status(
    *, user: User, agency_id: UUID, cheque_id: UUID, status_value: str
) -> ChequeInstrument:
    assert_accounting_post(user, agency_id)
    cheque = (
        ChequeInstrument.objects.all_tenants()
        .filter(id=cheque_id, agency_id=agency_id)
        .first()
    )
    if not cheque:
        raise NotFoundDomainError("چک یافت نشد.")
    cheque.status = status_value
    cheque.updated_by = user
    cheque.save(update_fields=["status", "updated_by", "updated_at"])
    return cheque


def get_trial_balance(
    *, user: User, agency_id: UUID, fiscal_period_id: Optional[UUID] = None
) -> dict:
    assert_accounting_view(user, agency_id)
    accounts = list(
        ChartOfAccount.objects.all_tenants()
        .filter(agency_id=agency_id, is_active=True)
        .order_by("code")
    )
    line_qs = JournalEntryLine.objects.filter(
        journal_entry__agency_id=agency_id,
        journal_entry__status=JournalEntry.Status.POSTED,
    )
    if fiscal_period_id:
        line_qs = line_qs.filter(journal_entry__fiscal_period_id=fiscal_period_id)

    aggregates = {
        row["account_id"]: row
        for row in line_qs.values("account_id").annotate(
            debit_sum=Sum("debit"), credit_sum=Sum("credit")
        )
    }

    rows = []
    grand_debit = Decimal("0.00")
    grand_credit = Decimal("0.00")
    grand_net_debit = Decimal("0.00")
    grand_net_credit = Decimal("0.00")

    for acct in accounts:
        agg = aggregates.get(acct.id)
        debit_total = (agg["debit_sum"] if agg else None) or Decimal("0.00")
        credit_total = (agg["credit_sum"] if agg else None) or Decimal("0.00")
        diff = debit_total - credit_total
        net_debit = diff if diff > 0 else Decimal("0.00")
        net_credit = -diff if diff < 0 else Decimal("0.00")
        grand_debit += debit_total
        grand_credit += credit_total
        grand_net_debit += net_debit
        grand_net_credit += net_credit
        rows.append(
            {
                "account_id": str(acct.id),
                "code": acct.code,
                "name": acct.name,
                "account_type": acct.account_type,
                "debit_turnover": str(debit_total),
                "credit_turnover": str(credit_total),
                "balance_debit": str(net_debit),
                "balance_credit": str(net_credit),
            }
        )

    return {
        "rows": rows,
        "totals": {
            "debit_turnover": str(grand_debit),
            "credit_turnover": str(grand_credit),
            "balance_debit": str(grand_net_debit),
            "balance_credit": str(grand_net_credit),
            "is_balanced": grand_debit == grand_credit and grand_net_debit == grand_net_credit,
        },
    }


def get_financial_statements(*, user: User, agency_id: UUID) -> dict:
    tb = get_trial_balance(user=user, agency_id=agency_id)
    assets = []
    liabilities = []
    equities = []
    revenues = []
    expenses = []

    total_assets = Decimal("0.00")
    total_liabilities = Decimal("0.00")
    total_equity = Decimal("0.00")
    total_revenue = Decimal("0.00")
    total_expense = Decimal("0.00")

    for r in tb["rows"]:
        debit = Decimal(r["debit_turnover"])
        credit = Decimal(r["credit_turnover"])
        atype = r["account_type"]
        if atype == ChartOfAccount.AccountType.ASSET:
            bal = debit - credit
            total_assets += bal
            assets.append({**r, "balance": str(bal)})
        elif atype == ChartOfAccount.AccountType.LIABILITY:
            bal = credit - debit
            total_liabilities += bal
            liabilities.append({**r, "balance": str(bal)})
        elif atype == ChartOfAccount.AccountType.EQUITY:
            bal = credit - debit
            total_equity += bal
            equities.append({**r, "balance": str(bal)})
        elif atype == ChartOfAccount.AccountType.REVENUE:
            bal = credit - debit
            total_revenue += bal
            revenues.append({**r, "balance": str(bal)})
        elif atype == ChartOfAccount.AccountType.EXPENSE:
            bal = debit - credit
            total_expense += bal
            expenses.append({**r, "balance": str(bal)})

    net_income = total_revenue - total_expense
    total_liabilities_and_equity = total_liabilities + total_equity + net_income

    return {
        "income_statement": {
            "revenues": revenues,
            "expenses": expenses,
            "total_revenue": str(total_revenue),
            "total_expense": str(total_expense),
            "net_income": str(net_income),
        },
        "balance_sheet": {
            "assets": assets,
            "liabilities": liabilities,
            "equities": equities,
            "current_net_income": str(net_income),
            "total_assets": str(total_assets),
            "total_liabilities": str(total_liabilities),
            "total_equity_and_income": str(total_equity + net_income),
            "total_liabilities_and_equity": str(total_liabilities_and_equity),
            "is_balanced": total_assets == total_liabilities_and_equity,
        },
    }


def get_general_ledger(*, user: User, agency_id: UUID, account_id: UUID) -> dict:
    assert_accounting_view(user, agency_id)
    acct = (
        ChartOfAccount.objects.all_tenants()
        .filter(id=account_id, agency_id=agency_id)
        .first()
    )
    if not acct:
        raise NotFoundDomainError("حساب انتخابی یافت نشد.")

    lines = (
        JournalEntryLine.objects.filter(
            journal_entry__agency_id=agency_id,
            journal_entry__status=JournalEntry.Status.POSTED,
            account=acct,
        )
        .select_related("journal_entry")
        .order_by("journal_entry__entry_date", "created_at")
    )

    running = Decimal("0.00")
    entries = []
    debit_normal = acct.account_type in (
        ChartOfAccount.AccountType.ASSET,
        ChartOfAccount.AccountType.EXPENSE,
    )
    for line in lines:
        if debit_normal:
            running += line.debit - line.credit
        else:
            running += line.credit - line.debit
        entries.append(
            {
                "id": str(line.id),
                "entry_id": str(line.journal_entry_id),
                "entry_number": line.journal_entry.entry_number,
                "entry_date": line.journal_entry.entry_date.isoformat(),
                "description": line.description or line.journal_entry.description,
                "debit": str(line.debit),
                "credit": str(line.credit),
                "running_balance": str(running),
            }
        )

    return {
        "account": {
            "id": str(acct.id),
            "code": acct.code,
            "name": acct.name,
            "account_type": acct.account_type,
        },
        "closing_balance": str(running),
        "lines": entries,
    }


def list_fiscal_periods(*, user: User, agency_id: UUID) -> list[FiscalPeriod]:
    assert_accounting_view(user, agency_id)
    return list(
        FiscalPeriod.objects.all_tenants()
        .filter(agency_id=agency_id)
        .select_related("fiscal_year")
        .order_by("-start_date")
    )


@transaction.atomic
def close_fiscal_period(*, user: User, agency_id: UUID, period_id: UUID) -> FiscalPeriod:
    assert_accounting_post(user, agency_id)
    period = (
        FiscalPeriod.objects.all_tenants()
        .select_for_update()
        .filter(id=period_id, agency_id=agency_id)
        .first()
    )
    if not period:
        raise NotFoundDomainError("دوره مالی یافت نشد.")
    if period.is_closed:
        raise ConflictDomainError("این دوره مالی قبلاً بسته شده است.")
    period.is_closed = True
    period.updated_by = user
    period.save(update_fields=["is_closed", "updated_by", "updated_at"])
    record_audit_event(
        action="FISCAL_PERIOD_CLOSED",
        resource_type="FiscalPeriod",
        resource_id=str(period.id),
        actor=user,
        agency_id=agency_id,
    )
    return period

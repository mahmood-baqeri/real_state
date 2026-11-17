from decimal import Decimal
from typing import Iterable
from uuid import UUID
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from apps.accounts.models import User
from apps.audit.services import record_audit_event
from common.exceptions import ConflictDomainError, NotFoundDomainError, PermissionDeniedDomainError, ValidationDomainError
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
def reverse_journal_entry(*, original_entry: JournalEntry, reversal_number: str, actor=None) -> JournalEntry:
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
    return list(ChartOfAccount.objects.all_tenants().filter(agency_id=agency_id, is_active=True).order_by("code"))


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
    period = FiscalPeriod.objects.all_tenants().filter(agency_id=agency_id, is_closed=False).first()
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
        rev = reverse_journal_entry(original_entry=entry, reversal_number=f"REV-{entry.entry_number}", actor=user)
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
        "bank_accounts": list(BankAccount.objects.all_tenants().filter(agency_id=agency_id, is_active=True)),
        "cash_boxes": list(CashBox.objects.all_tenants().filter(agency_id=agency_id, is_active=True)),
        "cheques": list(ChequeInstrument.objects.all_tenants().filter(agency_id=agency_id).select_related("deal").order_by("due_date")),
        "deal_ledgers": list(DealFinancialLedger.objects.all_tenants().filter(agency_id=agency_id).select_related("deal")),
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
def update_cheque_status(*, user: User, agency_id: UUID, cheque_id: UUID, status_value: str) -> ChequeInstrument:
    assert_accounting_post(user, agency_id)
    cheque = ChequeInstrument.objects.all_tenants().filter(id=cheque_id, agency_id=agency_id).first()
    if not cheque:
        raise NotFoundDomainError("چک یافت نشد.")
    cheque.status = status_value
    cheque.updated_by = user
    cheque.save(update_fields=["status", "updated_by", "updated_at"])
    return cheque

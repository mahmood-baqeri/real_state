from decimal import Decimal
from typing import Optional
from uuid import UUID
from django.db import models, transaction
from django.utils import timezone
from apps.accounts.models import User
from apps.agencies.models import AgencyAccessPolicy
from apps.audit.services import record_audit_event
from apps.accounting.models import DealFinancialLedger
from apps.commissions.models import CommissionPolicy
from apps.commissions.services import calculate_deal_commission
from apps.documents.models import Document
from apps.transactions.models import Deal
from common.exceptions import (
    ConflictDomainError,
    NotFoundDomainError,
    PermissionDeniedDomainError,
    ValidationDomainError,
)
from common.permissions import get_active_membership, get_agency_policy, has_agency_permission, is_super_admin
from .models import Contract, ContractAmendment, ContractParty, ContractStatusHistory, ContractTemplate

EDITABLE_CONTRACT_STATUSES = {
    Contract.Status.DRAFT,
    Contract.Status.PENDING_REVIEW,
    Contract.Status.PENDING_PARTIES_APPROVAL,
}

LOCKED_CONTRACT_STATUSES = {
    Contract.Status.SIGNED,
    Contract.Status.ACTIVE,
    Contract.Status.COMPLETED,
}

VALID_CONTRACT_TRANSITIONS = {
    Contract.Status.DRAFT: {
        Contract.Status.PENDING_REVIEW,
        Contract.Status.PENDING_PARTIES_APPROVAL,
        Contract.Status.SIGNED,
        Contract.Status.ACTIVE,
        Contract.Status.TERMINATED,
        Contract.Status.ARCHIVED,
    },
    Contract.Status.PENDING_REVIEW: {
        Contract.Status.DRAFT,
        Contract.Status.PENDING_PARTIES_APPROVAL,
        Contract.Status.SIGNED,
        Contract.Status.ACTIVE,
        Contract.Status.TERMINATED,
        Contract.Status.ARCHIVED,
    },
    Contract.Status.PENDING_PARTIES_APPROVAL: {
        Contract.Status.DRAFT,
        Contract.Status.PENDING_REVIEW,
        Contract.Status.SIGNED,
        Contract.Status.ACTIVE,
        Contract.Status.TERMINATED,
        Contract.Status.ARCHIVED,
    },
    Contract.Status.SIGNED: {
        Contract.Status.ACTIVE,
        Contract.Status.COMPLETED,
        Contract.Status.TERMINATED,
    },
    Contract.Status.ACTIVE: {
        Contract.Status.COMPLETED,
        Contract.Status.TERMINATED,
        Contract.Status.EXPIRED,
    },
    Contract.Status.COMPLETED: {
        Contract.Status.ARCHIVED,
    },
    Contract.Status.TERMINATED: {
        Contract.Status.ARCHIVED,
    },
    Contract.Status.EXPIRED: {
        Contract.Status.ARCHIVED,
    },
    Contract.Status.ARCHIVED: set(),
}


def list_contract_templates(agency_id: Optional[UUID]) -> list[ContractTemplate]:
    qs = ContractTemplate.objects.filter(is_active=True)
    if agency_id:
        qs = qs.filter(models.Q(agency_id=agency_id) | models.Q(agency__isnull=True))
    else:
        qs = qs.filter(agency__isnull=True)
    return list(qs.order_by("-created_at"))


@transaction.atomic
def create_contract_template(*, user: User, agency_id: Optional[UUID], data: dict) -> ContractTemplate:
    if not agency_id:
        raise ValidationDomainError("ابتدا آژانس فعال را انتخاب کنید.")
    if not (is_super_admin(user) or has_agency_permission(user, agency_id, "agency.manage_policy")):
        raise PermissionDeniedDomainError("عدم مجوز ایجاد قالب قرارداد.")
    return ContractTemplate.objects.create(
        agency_id=agency_id,
        country_id=data.get("country_id", "IR"),
        contract_type=data["contract_type"],
        title=data["title"].strip(),
        body_template=data["body_template"],
        legal_disclaimer=data.get("legal_disclaimer") or "متن حقوقی پیش‌نویس بوده و نیازمند تأیید مدیر آژانس است.",
        is_manager_verified=bool(data.get("is_manager_verified", False)),
        created_by=user,
    )


def list_contracts(*, user: User, agency_id: Optional[UUID], status_filter: Optional[str] = None, q: Optional[str] = None):
    qs = (
        Contract.objects.all_tenants()
        .select_related("property", "deal_type", "template", "currency", "agency")
        .prefetch_related("parties", "amendments__approved_by")
    )
    if agency_id:
        qs = qs.filter(agency_id=agency_id)
    elif not is_super_admin(user):
        raise PermissionDeniedDomainError("ابتدا آژانس را انتخاب کنید.")

    if not is_super_admin(user) and agency_id and not has_agency_permission(user, agency_id, "deal.view_all_agency"):
        membership = get_active_membership(user, agency_id)
        if not membership:
            return Contract.objects.none()
        policy = get_agency_policy(agency_id)
        if policy.contract_visibility == AgencyAccessPolicy.StandardVisibility.MANAGERS_AND_FINANCE:
            if membership.role.code not in ("AGENCY_MANAGER", "BRANCH_MANAGER", "AGENCY_ACCOUNTANT"):
                qs = qs.filter(
                    models.Q(created_by=user) | models.Q(property__agent_assignments__membership=membership)
                ).distinct()
        else:
            qs = qs.filter(
                models.Q(created_by=user) | models.Q(property__agent_assignments__membership=membership)
            ).distinct()

    if status_filter:
        qs = qs.filter(status=status_filter)
    if q:
        clean = q.strip()
        qs = qs.filter(
            models.Q(contract_number__icontains=clean)
            | models.Q(property__title__icontains=clean)
            | models.Q(property__property_code__icontains=clean)
        )
    return qs.order_by("-created_at")


@transaction.atomic
def create_contract(*, user: User, agency_id: Optional[UUID], data: dict) -> Contract:
    if not agency_id:
        raise ValidationDomainError("ابتدا آژانس فعال را انتخاب کنید.")
    membership = get_active_membership(user, agency_id)
    if not membership and not is_super_admin(user):
        raise PermissionDeniedDomainError("عضو فعال آژانس نیستید.")
    if Contract.objects.all_tenants().filter(agency_id=agency_id, contract_number=data["contract_number"]).exists():
        raise ConflictDomainError("شماره قرارداد در این آژانس تکراری است.")

    init_status = data.get("status", Contract.Status.DRAFT)
    if init_status not in {c[0] for c in Contract.Status.choices}:
        raise ValidationDomainError("وضعیت اولیه قرارداد نامعتبر است.")

    contract = Contract.objects.all_tenants().create(
        agency_id=agency_id,
        contract_number=data["contract_number"].strip(),
        internal_tracking_code=data.get("internal_tracking_code") or f"TRK-{data['contract_number']}",
        contract_type=data.get("contract_type", Contract.ContractType.SALE),
        property_id=data["property_id"],
        deal_type_id=data["deal_type_id"],
        template_id=data.get("template_id"),
        currency_id=data.get("currency_id", "IRT"),
        amount=Decimal(data.get("amount", "0")),
        deposit_amount=Decimal(data.get("deposit_amount", "0")),
        rent_amount=Decimal(data.get("rent_amount", "0")),
        advance_payment=Decimal(data.get("advance_payment", "0")),
        remaining_amount=Decimal(data.get("remaining_amount", "0")),
        payment_method=data.get("payment_method", ""),
        start_date=data.get("start_date") or timezone.now(),
        end_date=data.get("end_date"),
        terms_snapshot=data.get("terms_snapshot", ""),
        obligations_json=data.get("obligations_json") or {},
        status=init_status,
        created_by=user,
    )
    for party in data.get("parties", []):
        ContractParty.objects.create(
            contract=contract,
            customer_id=party.get("customer_id"),
            full_name=party["full_name"],
            party_role=party["party_role"],
            created_by=user,
        )
    ContractStatusHistory.objects.create(
        contract=contract,
        from_status="NEW",
        to_status=init_status,
        reason="ایجاد قرارداد در سیستم",
        changed_by=user,
    )
    record_audit_event(
        action="CONTRACT_CREATED",
        resource_type="Contract",
        resource_id=str(contract.id),
        actor=user,
        agency_id=agency_id,
    )
    return contract


@transaction.atomic
def update_contract(*, user: User, agency_id: Optional[UUID], contract_id: UUID, data: dict) -> Contract:
    contract = get_contract(user=user, agency_id=agency_id, contract_id=contract_id)
    if contract.status not in EDITABLE_CONTRACT_STATUSES:
        raise ConflictDomainError(
            "قرارداد امضا، فعال یا تکمیل‌شده قابل ویرایش مستقیم نیست؛ فقط از طریق الحاقیه مجاز ثبت تغییر ممکن است."
        )
    editable_fields = [
        "contract_type",
        "property_id",
        "deal_type_id",
        "template_id",
        "currency_id",
        "amount",
        "deposit_amount",
        "rent_amount",
        "advance_payment",
        "remaining_amount",
        "payment_method",
        "start_date",
        "end_date",
        "terms_snapshot",
        "obligations_json",
    ]
    for field in editable_fields:
        if field in data and data[field] is not None:
            val = data[field]
            if field in ("amount", "deposit_amount", "rent_amount", "advance_payment", "remaining_amount"):
                val = Decimal(val)
            setattr(contract, field, val)
    contract.updated_by = user
    contract.save()

    if "parties" in data and data["parties"] is not None:
        contract.parties.all().delete()
        for party in data["parties"]:
            ContractParty.objects.create(
                contract=contract,
                customer_id=party.get("customer_id"),
                full_name=party["full_name"],
                party_role=party["party_role"],
                created_by=user,
            )

    record_audit_event(
        action="CONTRACT_UPDATED",
        resource_type="Contract",
        resource_id=str(contract.id),
        actor=user,
        agency_id=contract.agency_id,
    )
    return get_contract(user=user, agency_id=agency_id, contract_id=contract.id)


@transaction.atomic
def transition_contract_status(
    *, user: User, agency_id: Optional[UUID], contract_id: UUID, to_status: str, reason: str = ""
) -> Contract:
    valid_statuses = {c[0] for c in Contract.Status.choices}
    if to_status not in valid_statuses:
        raise ValidationDomainError(f"وضعیت «{to_status}» برای قرارداد معتبر نیست.")

    contract = list_contracts(user=user, agency_id=agency_id).filter(id=contract_id).first()
    if not contract:
        raise NotFoundDomainError("قرارداد یافت نشد.")

    prev = contract.status
    if to_status == prev:
        return contract

    allowed = VALID_CONTRACT_TRANSITIONS.get(prev, set())
    if to_status not in allowed:
        raise ValidationDomainError(f"انتقال وضعیت قرارداد از «{prev}» به «{to_status}» مجاز نیست.")

    if to_status == Contract.Status.TERMINATED and not reason.strip():
        raise ValidationDomainError("برای فسخ یا ابطال قرارداد درج دلیل الزامی است.")

    contract.status = to_status
    contract.updated_by = user
    contract.save(update_fields=["status", "updated_by", "updated_at"])
    ContractStatusHistory.objects.create(
        contract=contract,
        from_status=prev,
        to_status=to_status,
        reason=reason,
        changed_by=user,
    )
    record_audit_event(
        action=f"CONTRACT_STATUS_{to_status}",
        resource_type="Contract",
        resource_id=str(contract.id),
        actor=user,
        agency_id=contract.agency_id,
        before_state={"status": prev},
        after_state={"status": to_status, "reason": reason},
    )
    return contract


@transaction.atomic
def archive_contract(*, user: User, agency_id: Optional[UUID], contract_id: UUID) -> Contract:
    contract = list_contracts(user=user, agency_id=agency_id).filter(id=contract_id).first()
    if not contract:
        raise NotFoundDomainError("قرارداد یافت نشد.")
    if contract.status in LOCKED_CONTRACT_STATUSES:
        raise ConflictDomainError("قرارداد امضا، فعال یا تکمیل‌شده قابل حذف یا بایگانی مستقیم نیست.")
    return transition_contract_status(
        user=user,
        agency_id=agency_id,
        contract_id=contract_id,
        to_status=Contract.Status.ARCHIVED,
        reason="بایگانی قرارداد از پنل مدیریت",
    )


@transaction.atomic
def create_contract_amendment(
    *, user: User, agency_id: Optional[UUID], contract_id: UUID, data: dict
) -> ContractAmendment:
    contract = get_contract(user=user, agency_id=agency_id, contract_id=contract_id)
    eff_agency_id = contract.agency_id
    if not (
        is_super_admin(user)
        or has_agency_permission(user, eff_agency_id, "agency.manage_policy")
        or has_agency_permission(user, eff_agency_id, "deal.view_all_agency")
    ):
        raise PermissionDeniedDomainError("عدم مجوز ثبت الحاقیه قرارداد.")

    title = (data.get("title") or "").strip()
    reason = (data.get("reason") or "").strip()
    if not title or not reason:
        raise ValidationDomainError("عنوان و دلیل ثبت الحاقیه الزامی است.")

    last_num = contract.amendments.order_by("-amendment_number").values_list("amendment_number", flat=True).first() or 0
    auto_approve = bool(data.get("approve_immediately", True))
    amendment = ContractAmendment.objects.create(
        contract=contract,
        amendment_number=last_num + 1,
        title=title,
        reason=reason,
        changes_json=data.get("changes_json") or {},
        status=ContractAmendment.Status.APPROVED if auto_approve else ContractAmendment.Status.DRAFT,
        approved_by=user if auto_approve else None,
        approved_at=timezone.now() if auto_approve else None,
        created_by=user,
    )
    record_audit_event(
        action="CONTRACT_AMENDMENT_CREATED",
        resource_type="Contract",
        resource_id=str(contract.id),
        actor=user,
        agency_id=eff_agency_id,
        after_state={"amendment_number": amendment.amendment_number, "title": title},
    )
    return amendment


def list_deals(*, user: User, agency_id: Optional[UUID]):
    qs = (
        Deal.objects.all_tenants()
        .select_related("contract", "property", "primary_agent__user", "co_agent__user", "currency", "agency")
    )
    if agency_id:
        qs = qs.filter(agency_id=agency_id)
    elif not is_super_admin(user):
        raise PermissionDeniedDomainError("ابتدا آژانس را انتخاب کنید.")

    if is_super_admin(user) or (agency_id and has_agency_permission(user, agency_id, "deal.view_all_agency")):
        return qs.order_by("-created_at")
    membership = get_active_membership(user, agency_id)
    if not membership:
        return Deal.objects.none()
    policy = get_agency_policy(agency_id)
    if policy and policy.financial_visibility == AgencyAccessPolicy.StandardVisibility.MANAGERS_AND_FINANCE:
        if membership.role.code in ("AGENCY_MANAGER", "BRANCH_MANAGER", "AGENCY_ACCOUNTANT"):
            return qs.order_by("-created_at")
    return qs.filter(models.Q(primary_agent=membership) | models.Q(co_agent=membership)).order_by("-created_at")


@transaction.atomic
def create_deal(*, user: User, agency_id: Optional[UUID], data: dict) -> Deal:
    from apps.settings.services import get_setting_value
    from common.localization.currency import CurrencyConversionService

    contract_qs = Contract.objects.all_tenants().filter(id=data["contract_id"])
    if agency_id:
        contract_qs = contract_qs.filter(agency_id=agency_id)
    contract = contract_qs.first()
    if not contract:
        raise NotFoundDomainError("قرارداد مرتبط یافت نشد.")
    eff_agency_id = contract.agency_id
    membership = get_active_membership(user, eff_agency_id)
    if Deal.objects.all_tenants().filter(contract=contract).exists():
        raise ConflictDomainError("برای این قرارداد قبلاً معامله ثبت شده است.")
    if Deal.objects.all_tenants().filter(agency_id=eff_agency_id, deal_code=data["deal_code"]).exists():
        raise ConflictDomainError("کد معامله تکراری است.")

    primary_agent_id = data.get("primary_agent_id") or (membership.id if membership else None)
    if not primary_agent_id:
        raise PermissionDeniedDomainError("مشاور اصلی معامله مشخص نیست.")

    deal_currency_id = data.get("currency_id") or contract.currency_id
    base_currency = str(get_setting_value("finance.base_currency", "IRT") or "IRT").upper()
    fx_snapshot = CurrencyConversionService.get_snapshot_rate_to_base(deal_currency_id, base_currency)

    deal = Deal.objects.all_tenants().create(
        agency_id=eff_agency_id,
        deal_code=data["deal_code"],
        contract=contract,
        property=contract.property,
        negotiation_id=data.get("negotiation_id"),
        primary_agent_id=primary_agent_id,
        co_agent_id=data.get("co_agent_id"),
        currency_id=deal_currency_id,
        base_currency_code=base_currency,
        exchange_rate_snapshot=fx_snapshot,
        deal_value=Decimal(data.get("deal_value") or contract.amount),
        status=data.get("status", Deal.Status.CONTRACT_ACTIVE),
        created_by=user,
    )
    DealFinancialLedger.objects.all_tenants().get_or_create(
        agency_id=eff_agency_id,
        deal=deal,
        defaults={
            "currency_id": deal.currency_id,
            "deal_amount": deal.deal_value,
            "total_received": contract.advance_payment,
        },
    )
    record_audit_event(
        action="DEAL_CREATED",
        resource_type="Deal",
        resource_id=str(deal.id),
        actor=user,
        agency_id=eff_agency_id,
    )
    return deal


@transaction.atomic
def close_deal_won(*, user: User, agency_id: Optional[UUID], deal_id: UUID, auto_calculate_commission: bool = True) -> Deal:
    deal = list_deals(user=user, agency_id=agency_id).filter(id=deal_id).first()
    if not deal:
        raise NotFoundDomainError("معامله یافت نشد.")
    eff_agency_id = deal.agency_id
    deal.status = Deal.Status.CLOSED_WON
    deal.closed_at = timezone.now()
    deal.updated_by = user
    deal.save(update_fields=["status", "closed_at", "updated_by", "updated_at"])

    if auto_calculate_commission and not hasattr(deal, "commission"):
        policy = (
            CommissionPolicy.objects.all_tenants()
            .filter(agency_id=eff_agency_id, deal_type=deal.property.deal_type, is_active=True)
            .first()
            or CommissionPolicy.objects.all_tenants().filter(agency_id=eff_agency_id, is_active=True).first()
        )
        if policy:
            ver = policy.versions.filter(is_published=True).order_by("-version_number").first()
            if ver:
                calculate_deal_commission(deal=deal, policy_version=ver, actor=user)
    return deal


def get_contract(*, user: User, agency_id: Optional[UUID], contract_id: UUID) -> Contract:
    contract = (
        list_contracts(user=user, agency_id=agency_id)
        .prefetch_related("status_history__changed_by", "amendments__approved_by")
        .filter(id=contract_id)
        .first()
    )
    if not contract:
        raise NotFoundDomainError("قرارداد یافت نشد.")
    return contract


def get_contract_documents(contract: Contract) -> list[Document]:
    return list(
        Document.objects.all_tenants()
        .filter(contract=contract, is_deleted=False)
        .prefetch_related("versions")
        .order_by("-created_at")
    )


def get_deal(*, user: User, agency_id: Optional[UUID], deal_id: UUID) -> Deal:
    deal = (
        list_deals(user=user, agency_id=agency_id)
        .select_related("negotiation", "contract__deal_type")
        .filter(id=deal_id)
        .first()
    )
    if not deal:
        raise NotFoundDomainError("معامله یافت نشد.")
    return deal

# Path: backend/django_core/apps/contracts/services.py

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
from apps.transactions.models import Deal
from common.exceptions import ConflictDomainError, NotFoundDomainError, PermissionDeniedDomainError
from common.permissions import get_active_membership, get_agency_policy, has_agency_permission, is_super_admin
from .models import Contract, ContractParty, ContractStatusHistory, ContractTemplate


def list_contract_templates(agency_id: Optional[UUID]) -> list[ContractTemplate]:
    qs = ContractTemplate.objects.filter(is_active=True)
    if agency_id:
        qs = qs.filter(models.Q(agency_id=agency_id) | models.Q(agency__isnull=True))
    else:
        qs = qs.filter(agency__isnull=True)
    return list(qs.order_by("-created_at"))


@transaction.atomic
def create_contract_template(*, user: User, agency_id: UUID, data: dict) -> ContractTemplate:
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


def list_contracts(*, user: User, agency_id: UUID):
    qs = (
        Contract.objects.all_tenants()
        .filter(agency_id=agency_id)
        .select_related("property", "deal_type", "template", "currency")
        .prefetch_related("parties")
    )
    if is_super_admin(user) or has_agency_permission(user, agency_id, "deal.view_all_agency"):
        return qs.order_by("-created_at")
    membership = get_active_membership(user, agency_id)
    if not membership:
        return Contract.objects.none()
    policy = get_agency_policy(agency_id)
    if policy.contract_visibility == AgencyAccessPolicy.StandardVisibility.MANAGERS_AND_FINANCE:
        if membership.role.code in ("AGENCY_MANAGER", "BRANCH_MANAGER", "AGENCY_ACCOUNTANT"):
            return qs.order_by("-created_at")
    return qs.filter(
        models.Q(created_by=user) | models.Q(property__agent_assignments__membership=membership)
    ).distinct().order_by("-created_at")


@transaction.atomic
def create_contract(*, user: User, agency_id: UUID, data: dict) -> Contract:
    membership = get_active_membership(user, agency_id)
    if not membership and not is_super_admin(user):
        raise PermissionDeniedDomainError("عضو فعال آژانس نیستید.")
    if Contract.objects.all_tenants().filter(agency_id=agency_id, contract_number=data["contract_number"]).exists():
        raise ConflictDomainError("شماره قرارداد در این آژانس تکراری است.")

    contract = Contract.objects.all_tenants().create(
        agency_id=agency_id,
        contract_number=data["contract_number"],
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
        status=data.get("status", Contract.Status.DRAFT),
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
    record_audit_event(
        action="CONTRACT_CREATED",
        resource_type="Contract",
        resource_id=str(contract.id),
        actor=user,
        agency_id=agency_id,
    )
    return contract


@transaction.atomic
def transition_contract_status(*, user: User, agency_id: UUID, contract_id: UUID, to_status: str, reason: str = "") -> Contract:
    contract = list_contracts(user=user, agency_id=agency_id).filter(id=contract_id).first()
    if not contract:
        raise NotFoundDomainError("قرارداد یافت نشد.")
    prev = contract.status
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
        agency_id=agency_id,
        before_state={"status": prev},
        after_state={"status": to_status},
    )
    return contract


def list_deals(*, user: User, agency_id: UUID):
    qs = (
        Deal.objects.all_tenants()
        .filter(agency_id=agency_id)
        .select_related("contract", "property", "primary_agent__user", "co_agent__user", "currency")
    )
    if is_super_admin(user) or has_agency_permission(user, agency_id, "deal.view_all_agency"):
        return qs.order_by("-created_at")
    membership = get_active_membership(user, agency_id)
    if not membership:
        return Deal.objects.none()
    return qs.filter(models.Q(primary_agent=membership) | models.Q(co_agent=membership)).order_by("-created_at")


@transaction.atomic
def create_deal(*, user: User, agency_id: UUID, data: dict) -> Deal:
    membership = get_active_membership(user, agency_id)
    contract = Contract.objects.all_tenants().filter(id=data["contract_id"], agency_id=agency_id).first()
    if not contract:
        raise NotFoundDomainError("قرارداد مرتبط یافت نشد.")
    if Deal.objects.all_tenants().filter(contract=contract).exists():
        raise ConflictDomainError("برای این قرارداد قبلاً معامله ثبت شده است.")
    if Deal.objects.all_tenants().filter(agency_id=agency_id, deal_code=data["deal_code"]).exists():
        raise ConflictDomainError("کد معامله تکراری است.")

    primary_agent_id = data.get("primary_agent_id") or (membership.id if membership else None)
    if not primary_agent_id:
        raise PermissionDeniedDomainError("مشاور اصلی معامله مشخص نیست.")

    deal = Deal.objects.all_tenants().create(
        agency_id=agency_id,
        deal_code=data["deal_code"],
        contract=contract,
        property=contract.property,
        negotiation_id=data.get("negotiation_id"),
        primary_agent_id=primary_agent_id,
        co_agent_id=data.get("co_agent_id"),
        currency_id=data.get("currency_id") or contract.currency_id,
        deal_value=Decimal(data.get("deal_value") or contract.amount),
        status=data.get("status", Deal.Status.CONTRACT_ACTIVE),
        created_by=user,
    )
    DealFinancialLedger.objects.all_tenants().get_or_create(
        agency_id=agency_id,
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
        agency_id=agency_id,
    )
    return deal


@transaction.atomic
def close_deal_won(*, user: User, agency_id: UUID, deal_id: UUID, auto_calculate_commission: bool = True) -> Deal:
    deal = list_deals(user=user, agency_id=agency_id).filter(id=deal_id).first()
    if not deal:
        raise NotFoundDomainError("معامله یافت نشد.")
    deal.status = Deal.Status.CLOSED_WON
    deal.closed_at = timezone.now()
    deal.updated_by = user
    deal.save(update_fields=["status", "closed_at", "updated_by", "updated_at"])

    if auto_calculate_commission and not hasattr(deal, "commission"):
        policy = (
            CommissionPolicy.objects.all_tenants()
            .filter(agency_id=agency_id, deal_type=deal.property.deal_type, is_active=True)
            .first()
            or CommissionPolicy.objects.all_tenants().filter(agency_id=agency_id, is_active=True).first()
        )
        if policy:
            ver = policy.versions.filter(is_published=True).order_by("-version_number").first()
            if ver:
                calculate_deal_commission(deal=deal, policy_version=ver, actor=user)
    return deal


def get_contract(*, user: User, agency_id: UUID, contract_id: UUID) -> Contract:
    contract = (
        list_contracts(user=user, agency_id=agency_id)
        .prefetch_related("status_history__changed_by")
        .filter(id=contract_id)
        .first()
    )
    if not contract:
        raise NotFoundDomainError("قرارداد یافت نشد.")
    return contract


def get_deal(*, user: User, agency_id: UUID, deal_id: UUID) -> Deal:
    deal = (
        list_deals(user=user, agency_id=agency_id)
        .select_related("negotiation", "contract__deal_type")
        .filter(id=deal_id)
        .first()
    )
    if not deal:
        raise NotFoundDomainError("معامله یافت نشد.")
    return deal


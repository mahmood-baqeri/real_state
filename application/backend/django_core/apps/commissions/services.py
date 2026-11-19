# Path: backend/django_core/apps/commissions/services.py

from decimal import Decimal
from typing import Optional
from uuid import UUID
from django.core.exceptions import ValidationError
from django.db import transaction
from apps.accounts.models import User
from apps.agencies.models import AgencyAccessPolicy
from apps.audit.services import record_audit_event
from apps.transactions.models import Deal
from common.exceptions import ConflictDomainError, NotFoundDomainError, PermissionDeniedDomainError, ValidationDomainError
from common.localization.currency import quantize_amount
from common.permissions import get_active_membership, get_agency_policy, has_agency_permission, is_super_admin
from .models import CommissionPolicy, CommissionPolicyVersion, CommissionShare, DealCommission


@transaction.atomic
def calculate_deal_commission(
    *,
    deal,
    policy_version: CommissionPolicyVersion,
    discount_amount: Decimal = Decimal("0.00"),
    actor=None,
) -> DealCommission:
    """
    Deterministic, Decimal-only commission calculation with 1:1 Deal lock
    preventing duplicate commission creation for the same deal.
    """
    if DealCommission.objects.all_tenants().filter(deal=deal).exists():
        raise ValidationError("Commission has already been calculated for this deal.")

    currency_code = deal.currency_id
    base = Decimal(deal.deal_value)

    if policy_version.formula_type == CommissionPolicyVersion.FormulaType.FIXED:
        gross = quantize_amount(policy_version.fixed_amount, currency_code)
    else:
        gross = quantize_amount(
            (base * policy_version.gross_rate_percent) / Decimal("100"),
            currency_code,
        )

    discount = quantize_amount(discount_amount, currency_code)
    after_discount = max(Decimal("0.00"), gross - discount)
    tax = quantize_amount(
        (after_discount * policy_version.tax_rate_percent) / Decimal("100"),
        currency_code,
    )
    net = quantize_amount(after_discount, currency_code)

    platform_amt = quantize_amount(
        (net * policy_version.platform_share_percent) / Decimal("100"), currency_code
    )
    remaining_for_agency_and_agents = net - platform_amt

    agent_pool = quantize_amount(
        (remaining_for_agency_and_agents * policy_version.primary_agent_percent) / Decimal("100"),
        currency_code,
    )

    shares_to_create = []
    if platform_amt > 0:
        shares_to_create.append(
            {
                "beneficiary_type": CommissionShare.BeneficiaryType.PLATFORM,
                "beneficiary_membership": None,
                "share_percent_of_net": policy_version.platform_share_percent,
                "calculated_amount": platform_amt,
            }
        )

    if deal.co_agent is not None:
        co_amt = quantize_amount(
            (agent_pool * policy_version.co_agent_split_ratio) / Decimal("100"),
            currency_code,
        )
        primary_amt = agent_pool - co_amt
        shares_to_create.append(
            {
                "beneficiary_type": CommissionShare.BeneficiaryType.AGENT,
                "beneficiary_membership": deal.primary_agent,
                "share_percent_of_net": (
                    (primary_amt / net * Decimal("100")).quantize(Decimal("0.0001"))
                    if net > 0
                    else Decimal("0")
                ),
                "calculated_amount": primary_amt,
            }
        )
        shares_to_create.append(
            {
                "beneficiary_type": CommissionShare.BeneficiaryType.AGENT,
                "beneficiary_membership": deal.co_agent,
                "share_percent_of_net": (
                    (co_amt / net * Decimal("100")).quantize(Decimal("0.0001"))
                    if net > 0
                    else Decimal("0")
                ),
                "calculated_amount": co_amt,
            }
        )
    else:
        shares_to_create.append(
            {
                "beneficiary_type": CommissionShare.BeneficiaryType.AGENT,
                "beneficiary_membership": deal.primary_agent,
                "share_percent_of_net": (
                    (agent_pool / net * Decimal("100")).quantize(Decimal("0.0001"))
                    if net > 0
                    else Decimal("0")
                ),
                "calculated_amount": agent_pool,
            }
        )

    allocated_without_house = sum((s["calculated_amount"] for s in shares_to_create), Decimal("0.00"))
    house_amt = net - allocated_without_house
    shares_to_create.append(
        {
            "beneficiary_type": CommissionShare.BeneficiaryType.AGENCY,
            "beneficiary_membership": None,
            "share_percent_of_net": (
                (house_amt / net * Decimal("100")).quantize(Decimal("0.0001"))
                if net > 0
                else Decimal("0")
            ),
            "calculated_amount": house_amt,
        }
    )

    deal_commission = DealCommission.objects.create(
        agency=deal.agency,
        deal=deal,
        policy_version=policy_version,
        currency=deal.currency,
        base_amount=base,
        gross_commission=gross,
        discount_amount=discount,
        tax_amount=tax,
        net_distributable=net,
        calculation_snapshot={
            "formula_type": policy_version.formula_type,
            "gross_rate_percent": str(policy_version.gross_rate_percent),
            "tax_rate_percent": str(policy_version.tax_rate_percent),
            "version_number": policy_version.version_number,
        },
        created_by=actor,
    )

    for s in shares_to_create:
        CommissionShare.objects.create(
            agency=deal.agency,
            deal_commission=deal_commission,
            created_by=actor,
            **s,
        )

    return deal_commission


def list_commissions(*, user: User, agency_id: UUID):
    qs = (
        DealCommission.objects.all_tenants()
        .filter(agency_id=agency_id)
        .select_related("deal__property", "currency", "policy_version__policy")
        .prefetch_related("shares__beneficiary_membership__user")
    )
    if is_super_admin(user) or has_agency_permission(user, agency_id, "commission.view_all_agency"):
        return qs.order_by("-created_at")
    membership = get_active_membership(user, agency_id)
    if not membership:
        return DealCommission.objects.none()
    policy = get_agency_policy(agency_id)
    if policy.commission_visibility == AgencyAccessPolicy.CommissionVisibility.OWN_ONLY:
        return qs.filter(shares__beneficiary_membership=membership).distinct().order_by("-created_at")
    return qs.filter(shares__beneficiary_membership=membership).distinct().order_by("-created_at")


def list_commission_policies(agency_id: UUID) -> list[CommissionPolicy]:
    return list(
        CommissionPolicy.objects.all_tenants()
        .filter(agency_id=agency_id, is_active=True)
        .select_related("deal_type")
        .prefetch_related("versions")
    )


@transaction.atomic
def create_commission_policy(*, user: User, agency_id: UUID, data: dict) -> CommissionPolicy:
    if not (is_super_admin(user) or has_agency_permission(user, agency_id, "agency.manage_policy")):
        raise PermissionDeniedDomainError("عدم مجوز تعریف تعرفه کمیسیون.")
    if CommissionPolicy.objects.all_tenants().filter(
        agency_id=agency_id, deal_type_id=data["deal_type_id"], name=data["name"]
    ).exists():
        raise ConflictDomainError("تعرفه کمیسیون با این نام وجود دارد.")
    policy = CommissionPolicy.objects.all_tenants().create(
        agency_id=agency_id,
        name=data["name"].strip(),
        deal_type_id=data["deal_type_id"],
        created_by=user,
    )
    CommissionPolicyVersion.objects.create(
        policy=policy,
        version_number=1,
        formula_type=data.get("formula_type", CommissionPolicyVersion.FormulaType.PERCENT),
        gross_rate_percent=Decimal(data.get("gross_rate_percent", "1.0000")),
        fixed_amount=Decimal(data.get("fixed_amount", "0.00")),
        tax_rate_percent=Decimal(data.get("tax_rate_percent", "10.0000")),
        platform_share_percent=Decimal(data.get("platform_share_percent", "0.0000")),
        agency_house_percent=Decimal(data.get("agency_house_percent", "50.0000")),
        primary_agent_percent=Decimal(data.get("primary_agent_percent", "50.0000")),
        co_agent_split_ratio=Decimal(data.get("co_agent_split_ratio", "50.0000")),
        created_by=user,
    )
    return policy


@transaction.atomic
def calculate_commission_for_deal_service(
    *, user: User, agency_id: UUID, deal_id: UUID, policy_version_id: Optional[UUID] = None, discount_amount: Decimal = Decimal("0.00")
) -> DealCommission:
    if not (
        is_super_admin(user)
        or has_agency_permission(user, agency_id, "accounting.post")
        or has_agency_permission(user, agency_id, "agency.manage_policy")
    ):
        raise PermissionDeniedDomainError("عدم مجوز محاسبه یا تغییر کمیسیون.")
    deal = Deal.objects.all_tenants().filter(id=deal_id, agency_id=agency_id).first()
    if not deal:
        raise NotFoundDomainError("معامله یافت نشد.")
    if policy_version_id:
        ver = CommissionPolicyVersion.objects.filter(id=policy_version_id, policy__agency_id=agency_id).first()
    else:
        pol = CommissionPolicy.objects.all_tenants().filter(agency_id=agency_id, is_active=True).first()
        ver = pol.versions.order_by("-version_number").first() if pol else None
    if not ver:
        raise NotFoundDomainError("نسخه فعال تعرفه کمیسیون یافت نشد.")
    try:
        return calculate_deal_commission(deal=deal, policy_version=ver, discount_amount=discount_amount, actor=user)
    except ValidationError as exc:
        raise ValidationDomainError(str(exc.message if hasattr(exc, "message") else exc))


@transaction.atomic
def update_commission_status(*, user: User, agency_id: UUID, commission_id: UUID, status_value: str) -> DealCommission:
    if not (
        is_super_admin(user)
        or has_agency_permission(user, agency_id, "accounting.post")
        or has_agency_permission(user, agency_id, "agency.manage_policy")
    ):
        raise PermissionDeniedDomainError("فقط مدیر آژانس یا حسابدار مجاز به تأیید یا تسویه کمیسیون است.")
    dc = DealCommission.objects.all_tenants().filter(id=commission_id, agency_id=agency_id).first()
    if not dc:
        raise NotFoundDomainError("کمیسیون یافت نشد.")
    prev = dc.status
    dc.status = status_value
    dc.updated_by = user
    dc.save(update_fields=["status", "updated_by", "updated_at"])
    record_audit_event(
        action=f"COMMISSION_STATUS_{status_value}",
        resource_type="DealCommission",
        resource_id=str(dc.id),
        actor=user,
        agency_id=agency_id,
        before_state={"status": prev},
        after_state={"status": status_value},
    )
    return dc

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
    locked_deal = Deal.objects.all_tenants().select_for_update().get(pk=deal.pk)
    if DealCommission.objects.all_tenants().filter(deal=locked_deal).exists():
        raise ValidationError("Commission has already been calculated for this deal.")
    if policy_version.policy.agency_id != locked_deal.agency_id:
        raise ValidationError("Commission policy version belongs to another agency.")

    currency_code = locked_deal.currency_id
    base = Decimal(locked_deal.deal_value)
    policy_percentages = [
        Decimal(policy_version.platform_share_percent),
        Decimal(policy_version.agency_house_percent),
        Decimal(policy_version.primary_agent_percent),
        Decimal(policy_version.co_agent_split_ratio),
        Decimal(policy_version.tax_rate_percent),
        Decimal(policy_version.gross_rate_percent),
    ]
    if any(value < 0 or value > 100 for value in policy_percentages):
        raise ValidationError("Commission percentages must be between 0 and 100.")
    if Decimal(policy_version.agency_house_percent) + Decimal(policy_version.primary_agent_percent) != Decimal("100"):
        raise ValidationError("Agency house and agent pool percentages must total exactly 100%.")
    if discount_amount < 0:
        raise ValidationError("Commission discount cannot be negative.")

    if policy_version.formula_type == CommissionPolicyVersion.FormulaType.FIXED:
        gross = quantize_amount(policy_version.fixed_amount, currency_code)
    elif policy_version.formula_type == CommissionPolicyVersion.FormulaType.TIERED:
        tiers = (policy_version.rules_json or {}).get("tiers", [])
        if not isinstance(tiers, list) or not tiers:
            raise ValidationError("Tiered commission requires rules_json.tiers.")
        parsed = []
        for tier in tiers:
            try:
                upper = Decimal(str(tier.get("up_to"))) if tier.get("up_to") is not None else None
                rate = Decimal(str(tier.get("rate_percent")))
            except Exception as exc:
                raise ValidationError("Invalid tiered commission rule.") from exc
            if rate < 0 or rate > 100 or (upper is not None and upper <= 0):
                raise ValidationError("Invalid tier amount or rate.")
            parsed.append((upper, rate))
        parsed.sort(key=lambda item: item[0] if item[0] is not None else Decimal("Infinity"))
        finite_limits = [upper for upper, _ in parsed if upper is not None]
        if len(finite_limits) != len(set(finite_limits)) or any(
            current <= previous for previous, current in zip([Decimal("0")] + finite_limits[:-1], finite_limits)
        ) or parsed[-1][0] is not None:
            raise ValidationError("Tiered commission thresholds must increase strictly and end with an open tier.")
        gross_raw = Decimal("0")
        lower = Decimal("0")
        remaining = base
        for upper, rate in parsed:
            width = remaining if upper is None else min(remaining, max(Decimal("0"), upper - lower))
            if width > 0:
                gross_raw += width * rate / Decimal("100")
                remaining -= width
            if remaining <= 0:
                break
            if upper is not None:
                lower = upper
        if remaining > 0:
            raise ValidationError("Tiered commission rules must include an open-ended final tier.")
        gross = quantize_amount(gross_raw, currency_code)
    else:
        gross = quantize_amount((base * policy_version.gross_rate_percent) / Decimal("100"), currency_code)

    discount = quantize_amount(discount_amount, currency_code)
    if discount > gross:
        raise ValidationError("Commission discount cannot exceed gross commission.")
    if policy_version.fixed_amount < 0:
        raise ValidationError("Fixed commission amount cannot be negative.")
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

    # The agency share is explicitly calculated from the configured house percentage.
    house_amt = remaining_for_agency_and_agents - agent_pool
    if shares_to_create and shares_to_create[-1]["beneficiary_type"] == CommissionShare.BeneficiaryType.AGENCY:
        shares_to_create[-1]["calculated_amount"] = house_amt
        shares_to_create[-1]["share_percent_of_net"] = (house_amt / net * Decimal("100")).quantize(Decimal("0.0001")) if net > 0 else Decimal("0")
    allocated = sum((s["calculated_amount"] for s in shares_to_create), Decimal("0.00"))
    if allocated != net:
        raise ValidationError(f"Commission shares do not balance: {allocated} != {net}.")

    deal_commission = DealCommission.objects.create(
        agency=locked_deal.agency,
        deal=locked_deal,
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
            "agency_house_percent": str(policy_version.agency_house_percent),
            "primary_agent_percent": str(policy_version.primary_agent_percent),
            "platform_share_percent": str(policy_version.platform_share_percent),
            "tiers": (policy_version.rules_json or {}).get("tiers", []),
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
    if is_super_admin(user) or has_agency_permission(user, agency_id, "accounting.view"):
        membership = get_active_membership(user, agency_id)
        if membership and membership.role.code == "BRANCH_MANAGER":
            return qs.filter(
                shares__beneficiary_membership__branch_id=membership.branch_id
            ).distinct().order_by("-created_at") if membership.branch_id else qs.none()
        return qs.order_by("-created_at")
    membership = get_active_membership(user, agency_id)
    if not membership:
        return DealCommission.objects.none()
    # Agents may see only their own commission record; team-lead roles without
    # accounting.view do not receive agency-wide financial data.
    if membership.role.code in ("BRANCH_MANAGER", "SALES_MANAGER", "AGENCY_ACCOUNTANT"):
        return DealCommission.objects.none()
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
    formula_type = data.get("formula_type", CommissionPolicyVersion.FormulaType.PERCENT)
    platform_pct = Decimal(data.get("platform_share_percent", "0"))
    house_pct = Decimal(data.get("agency_house_percent", "50"))
    agent_pct = Decimal(data.get("primary_agent_percent", "50"))
    co_pct = Decimal(data.get("co_agent_split_ratio", "50"))
    if any(v < 0 or v > 100 for v in (platform_pct, house_pct, agent_pct, co_pct)):
        raise ValidationDomainError("درصدهای تعرفه باید بین صفر تا صد باشند.")
    if house_pct + agent_pct != Decimal("100"):
        raise ValidationDomainError("سهم آژانس و مشاور باید دقیقاً ۱۰۰ درصد از مانده قابل تقسیم باشد.")
    if formula_type == CommissionPolicyVersion.FormulaType.TIERED:
        tiers = (data.get("rules_json") or {}).get("tiers", [])
        if not isinstance(tiers, list) or not tiers or tiers[-1].get("up_to") is not None:
            raise ValidationDomainError("تعرفه پلکانی باید tiers معتبر و یک پله نهایی بدون up_to داشته باشد.")
        previous_limit = Decimal("0")
        for tier in tiers[:-1]:
            try:
                upper = Decimal(str(tier["up_to"]))
                rate = Decimal(str(tier["rate_percent"]))
            except Exception as exc:
                raise ValidationDomainError("پله‌های تعرفه پلکانی نامعتبر هستند.") from exc
            if upper <= previous_limit or rate < 0 or rate > 100:
                raise ValidationDomainError("حد هر پله باید افزایشی و نرخ بین صفر تا صد باشد.")
            previous_limit = upper
        try:
            final_rate = Decimal(str(tiers[-1]["rate_percent"]))
        except Exception as exc:
            raise ValidationDomainError("نرخ پله نهایی نامعتبر است.") from exc
        if final_rate < 0 or final_rate > 100:
            raise ValidationDomainError("نرخ پله نهایی باید بین صفر تا صد باشد.")
    policy = CommissionPolicy.objects.all_tenants().create(
        agency_id=agency_id,
        name=data["name"].strip(),
        deal_type_id=data["deal_type_id"],
        created_by=user,
    )
    CommissionPolicyVersion.objects.create(
        policy=policy,
        version_number=1,
        formula_type=formula_type,
        gross_rate_percent=Decimal(data.get("gross_rate_percent", "1.0000")),
        fixed_amount=Decimal(data.get("fixed_amount", "0.00")),
        tax_rate_percent=Decimal(data.get("tax_rate_percent", "10.0000")),
        platform_share_percent=Decimal(data.get("platform_share_percent", "0.0000")),
        agency_house_percent=Decimal(data.get("agency_house_percent", "50.0000")),
        primary_agent_percent=Decimal(data.get("primary_agent_percent", "50.0000")),
        co_agent_split_ratio=co_pct,
        rules_json=data.get("rules_json") or {},
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
    allowed_transitions = {
        DealCommission.Status.CALCULATED: {DealCommission.Status.MANAGER_APPROVED, DealCommission.Status.REVERSED},
        DealCommission.Status.MANAGER_APPROVED: {DealCommission.Status.FINANCE_APPROVED, DealCommission.Status.REVERSED},
        DealCommission.Status.FINANCE_APPROVED: {DealCommission.Status.SETTLED, DealCommission.Status.REVERSED},
        DealCommission.Status.SETTLED: {DealCommission.Status.REVERSED},
        DealCommission.Status.REVERSED: set(),
    }
    if status_value not in DealCommission.Status.values or status_value not in allowed_transitions.get(dc.status, set()):
        raise ValidationDomainError(f"انتقال وضعیت کمیسیون از {dc.status} به {status_value} مجاز نیست.")
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

from decimal import Decimal
from typing import Optional
from uuid import UUID
from django.db import models, transaction
from django.utils import timezone
from apps.accounts.models import User
from apps.agencies.models import AgencyAccessPolicy
from apps.audit.services import record_audit_event
from apps.contracts.models import Contract, ContractParty
from apps.notifications.models import NotificationMessage
from apps.notifications.services import send_notification
from apps.properties.models import Property
from common.exceptions import ConflictDomainError, NotFoundDomainError, PermissionDeniedDomainError, ValidationDomainError
from common.permissions import get_active_membership, get_agency_policy, has_agency_permission, is_super_admin
from .models import Negotiation, NegotiationActivity, NegotiationOfferVersion

VALID_STATUS_VALUES = {choice[0] for choice in Negotiation.Status.choices}
TERMINAL_STATUSES = {
    Negotiation.Status.ACCEPTED,
    Negotiation.Status.REJECTED,
    Negotiation.Status.CANCELLED,
    Negotiation.Status.WITHDRAWN,
    Negotiation.Status.EXPIRED,
}


def list_negotiations(
    *,
    user: User,
    agency_id: UUID,
    status_filter: Optional[str] = None,
    q: Optional[str] = None,
    overdue_only: bool = False,
):
    qs = (
        Negotiation.objects.all_tenants()
        .filter(agency_id=agency_id)
        .select_related(
            "property",
            "property__location",
            "customer",
            "owner_customer",
            "agent_membership__user",
            "deal_type",
            "converted_contract",
        )
        .prefetch_related("offer_versions__currency", "activities__assigned_membership__user", "activities__created_by")
    )
    if not (is_super_admin(user) or has_agency_permission(user, agency_id, "deal.view_all_agency")):
        membership = get_active_membership(user, agency_id)
        if not membership:
            return Negotiation.objects.none()
        policy = get_agency_policy(agency_id)
        allow_mgr = (
            policy.negotiation_visibility == AgencyAccessPolicy.StandardVisibility.MANAGERS_AND_FINANCE
            and membership.role.code in ("AGENCY_MANAGER", "BRANCH_MANAGER", "AGENCY_ACCOUNTANT")
        )
        if not allow_mgr:
            qs = qs.filter(agent_membership=membership)

    if status_filter:
        qs = qs.filter(status=status_filter)
    if overdue_only:
        qs = qs.filter(next_followup_at__isnull=False, next_followup_at__lte=timezone.now()).exclude(
            status__in=list(TERMINAL_STATUSES)
        )
    if q:
        clean = q.strip()
        qs = qs.filter(
            models.Q(property__title__icontains=clean)
            | models.Q(property__property_code__icontains=clean)
            | models.Q(customer__full_name__icontains=clean)
            | models.Q(notes__icontains=clean)
        )
    return qs.order_by("-last_activity_at", "-created_at")


def get_negotiation_detail(*, user: User, agency_id: UUID, negotiation_id: UUID) -> Negotiation:
    neg = list_negotiations(user=user, agency_id=agency_id).filter(id=negotiation_id).first()
    if not neg:
        raise NotFoundDomainError("مذاکره یافت نشد.")
    return neg


@transaction.atomic
def create_negotiation(*, user: User, agency_id: UUID, data: dict) -> Negotiation:
    membership = get_active_membership(user, agency_id)
    if not membership and not is_super_admin(user):
        raise PermissionDeniedDomainError("عضو فعال آژانس نیستید.")

    prop = (
        Property.objects.all_tenants()
        .prefetch_related("owners__owner_customer")
        .filter(id=data["property_id"], agency_id=agency_id, is_deleted=False)
        .first()
    )
    if not prop:
        raise NotFoundDomainError("ملک مرتبط در این آژانس یافت نشد.")

    owner_cust_id = data.get("owner_customer_id")
    if not owner_cust_id:
        primary_owner = prop.owners.filter(is_primary_contact=True).first() or prop.owners.first()
        if primary_owner:
            owner_cust_id = primary_owner.owner_customer_id

    asking_price = Decimal(data.get("asking_price") or prop.total_price or "0")
    init_price = Decimal(data.get("initial_price") or "0") if data.get("initial_price") is not None else Decimal("0")
    init_status = (
        Negotiation.Status.BUYER_OFFERED
        if init_price > 0 and data.get("offered_by", "BUYER") == "BUYER"
        else Negotiation.Status.CREATED
    )

    now = timezone.now()
    neg = Negotiation.objects.all_tenants().create(
        agency_id=agency_id,
        property=prop,
        customer_id=data["customer_id"],
        owner_customer_id=owner_cust_id,
        agent_membership_id=data.get("agent_membership_id") or (membership.id if membership else None),
        deal_type_id=data.get("deal_type_id") or prop.deal_type_id,
        status=init_status,
        asking_price=asking_price,
        initial_proposed_price=init_price,
        latest_proposed_price=init_price,
        next_followup_at=data.get("next_followup_at"),
        next_action=data.get("next_action", "تماس اولیه و انتقال پیشنهاد به مالک"),
        last_activity_at=now,
        notes=data.get("notes", ""),
        created_by=user,
    )

    NegotiationActivity.objects.create(
        negotiation=neg,
        activity_type=NegotiationActivity.ActivityType.STATUS_CHANGE,
        title="ایجاد پرونده مذاکره جدید",
        description=f"پرونده مذاکره برای ملک {prop.property_code} ثبت شد.",
        next_action=neg.next_action,
        next_action_due_at=neg.next_followup_at,
        assigned_membership=neg.agent_membership,
        created_by=user,
    )

    if data.get("initial_price") is not None or data.get("initial_deposit") is not None:
        NegotiationOfferVersion.objects.create(
            negotiation=neg,
            version_number=1,
            offered_by=data.get("offered_by", NegotiationOfferVersion.OfferedBy.BUYER),
            recipient_role="SELLER" if data.get("offered_by", "BUYER") == "BUYER" else "BUYER",
            currency_id=data.get("currency_id", "IRT"),
            proposed_price=init_price,
            proposed_deposit=Decimal(data.get("initial_deposit") or "0"),
            proposed_rent=Decimal(data.get("initial_rent") or "0"),
            payment_terms=data.get("payment_terms", {}),
            notes=data.get("notes", ""),
            created_by=user,
        )
        NegotiationActivity.objects.create(
            negotiation=neg,
            activity_type=NegotiationActivity.ActivityType.OFFER,
            title="ثبت پیشنهاد اولیه قیمت",
            description=f"پیشنهاد نسخه ۱ به مبلغ {init_price:,.0f} ثبت شد.",
            assigned_membership=neg.agent_membership,
            created_by=user,
        )

    record_audit_event(
        action="NEGOTIATION_CREATED",
        resource_type="Negotiation",
        resource_id=str(neg.id),
        actor=user,
        agency_id=agency_id,
    )
    return neg


@transaction.atomic
def add_offer_version(*, user: User, agency_id: UUID, negotiation_id: UUID, data: dict) -> NegotiationOfferVersion:
    neg = get_negotiation_detail(user=user, agency_id=agency_id, negotiation_id=negotiation_id)
    if neg.status in TERMINAL_STATUSES:
        raise ValidationDomainError("امکان ثبت پیشنهاد جدید در مذاکره مختومه‌شده وجود ندارد.")

    neg.offer_versions.filter(status=NegotiationOfferVersion.Status.PENDING).update(
        status=NegotiationOfferVersion.Status.SUPERSEDED
    )
    last_ver = neg.offer_versions.order_by("-version_number").first()
    next_num = (last_ver.version_number + 1) if last_ver else 1

    proposed_price = Decimal(data.get("proposed_price", "0"))
    offered_by = data["offered_by"]
    offer = NegotiationOfferVersion.objects.create(
        negotiation=neg,
        version_number=next_num,
        offered_by=offered_by,
        recipient_role=data.get("recipient_role") or ("SELLER" if offered_by == "BUYER" else "BUYER"),
        currency_id=data.get("currency_id", "IRT"),
        proposed_price=proposed_price,
        proposed_deposit=Decimal(data.get("proposed_deposit", "0")),
        proposed_rent=Decimal(data.get("proposed_rent", "0")),
        discount_amount=Decimal(data.get("discount_amount", "0")),
        payment_terms=data.get("payment_terms", {}),
        notes=data.get("notes", ""),
        valid_until=data.get("valid_until"),
        created_by=user,
    )

    if neg.initial_proposed_price == Decimal("0"):
        neg.initial_proposed_price = proposed_price
    neg.latest_proposed_price = proposed_price
    neg.last_activity_at = timezone.now()
    if offered_by == NegotiationOfferVersion.OfferedBy.BUYER:
        neg.status = (
            Negotiation.Status.BUYER_OFFERED
            if next_num == 1
            else Negotiation.Status.BARGAINING
        )
    elif offered_by == NegotiationOfferVersion.OfferedBy.SELLER:
        neg.status = Negotiation.Status.OWNER_COUNTERED
    else:
        neg.status = Negotiation.Status.BARGAINING
    neg.updated_by = user
    neg.save(
        update_fields=[
            "initial_proposed_price",
            "latest_proposed_price",
            "last_activity_at",
            "status",
            "updated_by",
            "updated_at",
        ]
    )

    NegotiationActivity.objects.create(
        negotiation=neg,
        activity_type=NegotiationActivity.ActivityType.OFFER,
        title=f"پیشنهاد قیمت نسخه {next_num}",
        description=f"از طرف {offered_by} به مبلغ {proposed_price:,.0f}. {data.get('notes', '')}".strip(),
        assigned_membership=neg.agent_membership,
        created_by=user,
    )
    record_audit_event(
        action="NEGOTIATION_OFFER_ADDED",
        resource_type="Negotiation",
        resource_id=str(neg.id),
        actor=user,
        agency_id=agency_id,
        after_state={"version": next_num, "proposed_price": str(proposed_price)},
    )
    return offer


@transaction.atomic
def respond_to_negotiation(
    *,
    user: User,
    agency_id: UUID,
    negotiation_id: UUID,
    status_value: str,
    reason: str = "",
    agreed_price: Optional[Decimal] = None,
    next_followup_at=None,
    next_action: Optional[str] = None,
) -> Negotiation:
    if status_value not in VALID_STATUS_VALUES:
        raise ValidationDomainError("وضعیت انتخاب‌شده برای مذاکره معتبر نیست.")

    neg = get_negotiation_detail(user=user, agency_id=agency_id, negotiation_id=negotiation_id)
    prev_status = neg.status
    now = timezone.now()
    neg.status = status_value
    neg.last_activity_at = now
    if reason:
        neg.outcome_reason = reason[:255]
    if agreed_price is not None:
        neg.agreed_price = agreed_price
    elif status_value == Negotiation.Status.ACCEPTED and neg.agreed_price is None:
        neg.agreed_price = neg.latest_proposed_price or neg.asking_price
    if next_followup_at is not None:
        neg.next_followup_at = next_followup_at
    if next_action is not None:
        neg.next_action = next_action[:200]
    neg.updated_by = user
    neg.save()

    latest = neg.offer_versions.order_by("-version_number").first()
    if latest and status_value in (Negotiation.Status.ACCEPTED, Negotiation.Status.REJECTED):
        latest.status = (
            NegotiationOfferVersion.Status.ACCEPTED
            if status_value == Negotiation.Status.ACCEPTED
            else NegotiationOfferVersion.Status.REJECTED
        )
        latest.response_note = reason
        latest.responded_at = now
        latest.save(update_fields=["status", "response_note", "responded_at", "updated_at"])

    NegotiationActivity.objects.create(
        negotiation=neg,
        activity_type=NegotiationActivity.ActivityType.STATUS_CHANGE,
        title=f"تغییر مرحله مذاکره به {status_value}",
        description=reason or f"تغییر وضعیت از {prev_status} به {status_value}",
        next_action=neg.next_action,
        next_action_due_at=neg.next_followup_at,
        assigned_membership=neg.agent_membership,
        created_by=user,
    )

    if neg.agent_membership_id and neg.agent_membership.user_id != user.id:
        try:
            send_notification(
                recipient_user_id=neg.agent_membership.user_id,
                title=f"به‌روزرسانی وضعیت مذاکره {neg.property.property_code}",
                body=f"وضعیت مذاکره با {neg.customer.full_name} به «{status_value}» تغییر یافت.",
                channel=NotificationMessage.Channel.IN_APP,
                agency_id=agency_id,
                actor=user,
            )
        except Exception:
            pass

    record_audit_event(
        action=f"NEGOTIATION_STATUS_{status_value}",
        resource_type="Negotiation",
        resource_id=str(neg.id),
        actor=user,
        agency_id=agency_id,
        before_state={"status": prev_status},
        after_state={"status": status_value, "agreed_price": str(neg.agreed_price or "")},
    )
    return neg


@transaction.atomic
def add_negotiation_activity(
    *, user: User, agency_id: UUID, negotiation_id: UUID, data: dict
) -> NegotiationActivity:
    neg = get_negotiation_detail(user=user, agency_id=agency_id, negotiation_id=negotiation_id)
    now = timezone.now()
    act = NegotiationActivity.objects.create(
        negotiation=neg,
        activity_type=data.get("activity_type", NegotiationActivity.ActivityType.CALL),
        title=data["title"].strip(),
        description=data.get("description", ""),
        outcome=data.get("outcome", ""),
        next_action=data.get("next_action", ""),
        next_action_due_at=data.get("next_action_due_at"),
        is_completed=bool(data.get("is_completed", True)),
        assigned_membership=neg.agent_membership,
        created_by=user,
    )
    neg.last_activity_at = now
    if data.get("next_action"):
        neg.next_action = str(data["next_action"])[:200]
    if data.get("next_action_due_at"):
        neg.next_followup_at = data["next_action_due_at"]
    neg.updated_by = user
    neg.save(update_fields=["last_activity_at", "next_action", "next_followup_at", "updated_by", "updated_at"])
    return act


@transaction.atomic
def convert_negotiation_to_contract(
    *, user: User, agency_id: UUID, negotiation_id: UUID, contract_number: Optional[str] = None
) -> Contract:
    neg = get_negotiation_detail(user=user, agency_id=agency_id, negotiation_id=negotiation_id)
    if neg.converted_contract_id:
        raise ConflictDomainError("این مذاکره قبلاً به قرارداد تبدیل شده است.")
    if neg.status not in (
        Negotiation.Status.PRE_AGREEMENT,
        Negotiation.Status.AWAITING_FINAL_APPROVAL,
        Negotiation.Status.ACCEPTED,
    ):
        raise ValidationDomainError(
            "تبدیل به قرارداد فقط در مراحل «توافق اولیه»، «در انتظار تأیید نهایی» یا «موفق» مجاز است."
        )

    now = timezone.now()
    resolved_number = contract_number or f"CNT-NEG-{now.strftime('%y%m%d')}-{str(neg.id)[:6].upper()}"
    if Contract.objects.all_tenants().filter(agency_id=agency_id, contract_number=resolved_number).exists():
        resolved_number = f"{resolved_number}-{now.strftime('%H%M')}"

    final_amount = neg.agreed_price or neg.latest_proposed_price or neg.asking_price or neg.property.total_price
    latest_offer = neg.offer_versions.order_by("-version_number").first()

    contract = Contract.objects.all_tenants().create(
        agency_id=agency_id,
        contract_number=resolved_number,
        internal_tracking_code=f"TRK-{resolved_number}",
        contract_type=Contract.ContractType.MORTGAGE_RENT if neg.deal_type.is_rental else Contract.ContractType.SALE,
        property=neg.property,
        deal_type=neg.deal_type,
        currency=neg.property.currency,
        amount=final_amount,
        deposit_amount=latest_offer.proposed_deposit if latest_offer else neg.property.deposit_amount,
        rent_amount=latest_offer.proposed_rent if latest_offer else neg.property.rent_amount,
        start_date=now,
        terms_snapshot=f"قرارداد ایجادشده از مذاکره {neg.id}. یادداشت: {neg.notes}",
        status=Contract.Status.DRAFT,
        created_by=user,
    )
    if neg.owner_customer:
        ContractParty.objects.create(
            contract=contract,
            customer=neg.owner_customer,
            full_name=neg.owner_customer.full_name,
            party_role=ContractParty.Role.OWNER,
            created_by=user,
        )
    ContractParty.objects.create(
        contract=contract,
        customer=neg.customer,
        full_name=neg.customer.full_name,
        party_role=ContractParty.Role.COUNTERPARTY,
        created_by=user,
    )

    neg.status = Negotiation.Status.ACCEPTED
    neg.agreed_price = final_amount
    neg.converted_contract = contract
    neg.last_activity_at = now
    neg.updated_by = user
    neg.save(update_fields=["status", "agreed_price", "converted_contract", "last_activity_at", "updated_by", "updated_at"])

    NegotiationActivity.objects.create(
        negotiation=neg,
        activity_type=NegotiationActivity.ActivityType.CONTRACT_CONVERTED,
        title=f"تبدیل به پیش‌نویس قرارداد {contract.contract_number}",
        description=f"قرارداد به مبلغ {final_amount:,.0f} ایجاد و به مذاکره متصل شد.",
        assigned_membership=neg.agent_membership,
        created_by=user,
    )
    record_audit_event(
        action="NEGOTIATION_CONVERTED_TO_CONTRACT",
        resource_type="Contract",
        resource_id=str(contract.id),
        actor=user,
        agency_id=agency_id,
        after_state={"negotiation_id": str(neg.id), "contract_number": contract.contract_number},
    )
    return contract


def get_negotiation_analytics(*, user: User, agency_id: UUID) -> dict:
    qs = list(list_negotiations(user=user, agency_id=agency_id))
    now = timezone.now()
    total = len(qs)
    won = [n for n in qs if n.status == Negotiation.Status.ACCEPTED]
    lost = [n for n in qs if n.status in (Negotiation.Status.REJECTED, Negotiation.Status.CANCELLED, Negotiation.Status.WITHDRAWN)]
    active = [n for n in qs if n.status not in TERMINAL_STATUSES]
    overdue = [n for n in active if n.next_followup_at and n.next_followup_at <= now]

    stage_counts: dict[str, int] = {}
    discounts: list[float] = []
    durations_days: list[float] = []
    offer_counts: list[int] = []
    failure_reasons: dict[str, int] = {}

    for n in qs:
        stage_counts[n.status] = stage_counts.get(n.status, 0) + 1
        offers = list(n.offer_versions.all())
        offer_counts.append(len(offers))
        if n.asking_price and n.asking_price > 0:
            ref_price = n.agreed_price if n.agreed_price else n.latest_proposed_price
            if ref_price and ref_price > 0:
                delta_pct = float(((n.asking_price - ref_price) / n.asking_price) * Decimal("100"))
                discounts.append(round(delta_pct, 2))
        end_dt = n.last_activity_at or n.updated_at or now
        durations_days.append(max(0.1, (end_dt - n.created_at).total_seconds() / 86400.0))
        if n.status in (Negotiation.Status.REJECTED, Negotiation.Status.CANCELLED) and n.outcome_reason:
            failure_reasons[n.outcome_reason] = failure_reasons.get(n.outcome_reason, 0) + 1

    win_rate = round((len(won) / max(1, len(won) + len(lost))) * 100, 1) if (won or lost) else 0.0
    return {
        "total_count": total,
        "active_count": len(active),
        "won_count": len(won),
        "lost_count": len(lost),
        "overdue_followups_count": len(overdue),
        "win_rate_percent": win_rate,
        "avg_discount_percent": round(sum(discounts) / len(discounts), 2) if discounts else 0.0,
        "avg_duration_days": round(sum(durations_days) / len(durations_days), 1) if durations_days else 0.0,
        "avg_offers_per_negotiation": round(sum(offer_counts) / len(offer_counts), 1) if offer_counts else 0.0,
        "stage_breakdown": [{"status": k, "count": v} for k, v in stage_counts.items()],
        "failure_reasons": [{"reason": k, "count": v} for k, v in failure_reasons.items()],
    }

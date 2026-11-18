from decimal import Decimal
from typing import Optional
from uuid import UUID
from django.db import transaction
from apps.accounts.models import User
from apps.agencies.models import AgencyAccessPolicy
from apps.audit.services import record_audit_event
from common.exceptions import NotFoundDomainError, PermissionDeniedDomainError
from common.permissions import get_active_membership, get_agency_policy, has_agency_permission, is_super_admin
from .models import Negotiation, NegotiationOfferVersion


def list_negotiations(*, user: User, agency_id: UUID):
    qs = (
        Negotiation.objects.all_tenants()
        .filter(agency_id=agency_id)
        .select_related("property", "customer", "agent_membership__user", "deal_type")
        .prefetch_related("offer_versions__currency")
    )
    if is_super_admin(user) or has_agency_permission(user, agency_id, "deal.view_all_agency"):
        return qs.order_by("-created_at")
    membership = get_active_membership(user, agency_id)
    if not membership:
        return Negotiation.objects.none()
    policy = get_agency_policy(agency_id)
    if policy.negotiation_visibility == AgencyAccessPolicy.StandardVisibility.MANAGERS_AND_FINANCE:
        if membership.role.code in ("AGENCY_MANAGER", "BRANCH_MANAGER", "AGENCY_ACCOUNTANT"):
            return qs.order_by("-created_at")
    return qs.filter(agent_membership=membership).order_by("-created_at")


@transaction.atomic
def create_negotiation(*, user: User, agency_id: UUID, data: dict) -> Negotiation:
    membership = get_active_membership(user, agency_id)
    if not membership and not is_super_admin(user):
        raise PermissionDeniedDomainError("عضو فعال آژانس نیستید.")
    neg = Negotiation.objects.all_tenants().create(
        agency_id=agency_id,
        property_id=data["property_id"],
        customer_id=data["customer_id"],
        agent_membership_id=data.get("agent_membership_id") or membership.id,
        deal_type_id=data["deal_type_id"],
        notes=data.get("notes", ""),
        created_by=user,
    )
    if data.get("initial_price") is not None or data.get("initial_deposit") is not None:
        NegotiationOfferVersion.objects.create(
            negotiation=neg,
            version_number=1,
            offered_by=data.get("offered_by", NegotiationOfferVersion.OfferedBy.BUYER),
            currency_id=data.get("currency_id", "IRT"),
            proposed_price=Decimal(data.get("initial_price") or "0"),
            proposed_deposit=Decimal(data.get("initial_deposit") or "0"),
            proposed_rent=Decimal(data.get("initial_rent") or "0"),
            payment_terms=data.get("payment_terms", {}),
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
    neg = list_negotiations(user=user, agency_id=agency_id).filter(id=negotiation_id).first()
    if not neg:
        raise NotFoundDomainError("مذاکره یافت نشد.")
    neg.offer_versions.filter(status=NegotiationOfferVersion.Status.PENDING).update(
        status=NegotiationOfferVersion.Status.SUPERSEDED
    )
    last_ver = neg.offer_versions.order_by("-version_number").first()
    next_num = (last_ver.version_number + 1) if last_ver else 1
    offer = NegotiationOfferVersion.objects.create(
        negotiation=neg,
        version_number=next_num,
        offered_by=data["offered_by"],
        currency_id=data.get("currency_id", "IRT"),
        proposed_price=Decimal(data.get("proposed_price", "0")),
        proposed_deposit=Decimal(data.get("proposed_deposit", "0")),
        proposed_rent=Decimal(data.get("proposed_rent", "0")),
        discount_amount=Decimal(data.get("discount_amount", "0")),
        payment_terms=data.get("payment_terms", {}),
        created_by=user,
    )
    neg.status = Negotiation.Status.COUNTER_OFFERED if next_num > 1 else Negotiation.Status.OPEN
    neg.updated_by = user
    neg.save(update_fields=["status", "updated_by", "updated_at"])
    return offer


@transaction.atomic
def respond_to_negotiation(*, user: User, agency_id: UUID, negotiation_id: UUID, status_value: str) -> Negotiation:
    neg = list_negotiations(user=user, agency_id=agency_id).filter(id=negotiation_id).first()
    if not neg:
        raise NotFoundDomainError("مذاکره یافت نشد.")
    neg.status = status_value
    neg.updated_by = user
    neg.save(update_fields=["status", "updated_by", "updated_at"])
    latest = neg.offer_versions.order_by("-version_number").first()
    if latest and status_value in (Negotiation.Status.ACCEPTED, Negotiation.Status.REJECTED):
        latest.status = (
            NegotiationOfferVersion.Status.ACCEPTED
            if status_value == Negotiation.Status.ACCEPTED
            else NegotiationOfferVersion.Status.REJECTED
        )
        latest.save(update_fields=["status", "updated_at"])
    return neg

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from app.core.django_bridge import run_django
from app.dependencies.auth import RequestContext, require_agency_context
from app.schemas.common import ok

router = APIRouter(prefix="/negotiations", tags=["Negotiations & Offers"])


class NegotiationCreateBody(BaseModel):
    property_id: UUID
    customer_id: UUID
    owner_customer_id: Optional[UUID] = None
    deal_type_id: Optional[str] = None
    agent_membership_id: Optional[UUID] = None
    asking_price: Optional[Decimal] = None
    next_followup_at: Optional[datetime] = None
    next_action: str = "تماس اولیه و انتقال پیشنهاد"
    notes: str = ""
    offered_by: str = "BUYER"
    currency_id: str = "IRT"
    initial_price: Optional[Decimal] = None
    initial_deposit: Optional[Decimal] = None
    initial_rent: Optional[Decimal] = None
    payment_terms: dict[str, Any] = {}


class NegotiationPatchBody(BaseModel):
    owner_customer_id: Optional[UUID] = None
    agent_membership_id: Optional[UUID] = None
    deal_type_id: Optional[str] = None
    asking_price: Optional[Decimal] = None
    next_followup_at: Optional[datetime] = None
    next_action: Optional[str] = None
    notes: Optional[str] = None


class OfferVersionCreateBody(BaseModel):
    offered_by: str
    recipient_role: Optional[str] = None
    currency_id: str = "IRT"
    proposed_price: Decimal = Decimal("0")
    proposed_deposit: Decimal = Decimal("0")
    proposed_rent: Decimal = Decimal("0")
    discount_amount: Decimal = Decimal("0")
    payment_terms: dict[str, Any] = {}
    notes: str = ""
    valid_until: Optional[datetime] = None


class NegotiationRespondBody(BaseModel):
    status: str
    reason: str = ""
    agreed_price: Optional[Decimal] = None
    next_followup_at: Optional[datetime] = None
    next_action: Optional[str] = None


class NegotiationActivityBody(BaseModel):
    activity_type: str = "CALL"
    title: str = Field(min_length=2, max_length=160)
    description: str = ""
    outcome: str = ""
    next_action: str = ""
    next_action_due_at: Optional[datetime] = None
    is_completed: bool = True


class ConvertContractBody(BaseModel):
    contract_number: Optional[str] = None


def _ser_neg(n, include_activities: bool = False) -> dict:
    from django.utils import timezone

    loc = getattr(n.property, "location", None)
    asking = n.asking_price or n.property.total_price or Decimal("0")
    latest_p = n.agreed_price if n.agreed_price is not None else n.latest_proposed_price
    delta = (latest_p - asking) if (asking > 0 and latest_p > 0) else Decimal("0")
    delta_pct = round(float((delta / asking) * Decimal("100")), 2) if (asking > 0 and latest_p > 0) else 0.0
    is_overdue = bool(
        n.next_followup_at
        and n.next_followup_at <= timezone.now()
        and n.status not in ("ACCEPTED", "REJECTED", "CANCELLED", "WITHDRAWN", "EXPIRED")
    )

    payload = {
        "id": str(n.id),
        "agency_id": str(n.agency_id),
        "property_id": str(n.property_id),
        "property_code": n.property.property_code,
        "property_title": n.property.title,
        "property_location": f"{loc.city}، {loc.district}" if loc else "",
        "customer_id": str(n.customer_id),
        "customer_name": n.customer.full_name,
        "owner_customer_id": str(n.owner_customer_id) if n.owner_customer_id else None,
        "owner_name": n.owner_customer.full_name if n.owner_customer else "",
        "agent_membership_id": str(n.agent_membership_id) if n.agent_membership_id else None,
        "agent_name": n.agent_membership.user.full_name if n.agent_membership else "",
        "deal_type": n.deal_type_id,
        "deal_type_name": n.deal_type.name_fa,
        "status": n.status,
        "asking_price": str(asking),
        "initial_proposed_price": str(n.initial_proposed_price),
        "latest_proposed_price": str(n.latest_proposed_price),
        "agreed_price": str(n.agreed_price) if n.agreed_price is not None else None,
        "price_delta": str(delta),
        "price_delta_percent": delta_pct,
        "next_followup_at": n.next_followup_at.isoformat() if n.next_followup_at else None,
        "next_action": n.next_action,
        "is_followup_overdue": is_overdue,
        "last_activity_at": n.last_activity_at.isoformat() if n.last_activity_at else None,
        "outcome_reason": n.outcome_reason,
        "converted_contract_id": str(n.converted_contract_id) if n.converted_contract_id else None,
        "converted_contract_number": n.converted_contract.contract_number if n.converted_contract else None,
        "notes": n.notes,
        "offers": [
            {
                "id": str(o.id),
                "version_number": o.version_number,
                "offered_by": o.offered_by,
                "recipient_role": o.recipient_role,
                "currency": o.currency_id,
                "proposed_price": str(o.proposed_price),
                "proposed_deposit": str(o.proposed_deposit),
                "proposed_rent": str(o.proposed_rent),
                "discount_amount": str(o.discount_amount),
                "payment_terms": o.payment_terms,
                "notes": o.notes,
                "response_note": o.response_note,
                "status": o.status,
                "valid_until": o.valid_until.isoformat() if o.valid_until else None,
                "created_at": o.created_at.isoformat(),
            }
            for o in n.offer_versions.order_by("version_number")
        ],
        "created_at": n.created_at.isoformat(),
    }
    if include_activities:
        payload["activities"] = [
            {
                "id": str(a.id),
                "activity_type": a.activity_type,
                "title": a.title,
                "description": a.description,
                "outcome": a.outcome,
                "next_action": a.next_action,
                "next_action_due_at": a.next_action_due_at.isoformat() if a.next_action_due_at else None,
                "is_completed": a.is_completed,
                "actor_name": a.created_by.full_name if a.created_by else (
                    a.assigned_membership.user.full_name if a.assigned_membership else ""
                ),
                "created_at": a.created_at.isoformat(),
            }
            for a in n.activities.order_by("-created_at")
        ]
    return payload


@router.get("/analytics")
async def negotiation_analytics_endpoint(ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.negotiations.services import get_negotiation_analytics

        return get_negotiation_analytics(user=ctx.user, agency_id=ctx.agency_id)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.get("")
async def list_negotiations_endpoint(
    status: Optional[str] = None,
    q: Optional[str] = None,
    overdue_only: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.negotiations.services import list_negotiations
        from common.pagination import paginate_queryset

        qs = list_negotiations(
            user=ctx.user,
            agency_id=ctx.agency_id,
            status_filter=status,
            q=q,
            overdue_only=overdue_only,
        )
        return paginate_queryset(qs, page=page, page_size=page_size, serializer_fn=lambda n: _ser_neg(n, False))

    items, meta = await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None)
    return ok(items, meta=meta)


@router.get("/{negotiation_id}")
async def get_negotiation_endpoint(
    negotiation_id: UUID, ctx: RequestContext = Depends(require_agency_context)
):
    def _op():
        from apps.negotiations.services import get_negotiation_detail

        n = get_negotiation_detail(user=ctx.user, agency_id=ctx.agency_id, negotiation_id=negotiation_id)
        return _ser_neg(n, include_activities=True)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("", status_code=201)
async def create_negotiation_endpoint(
    body: NegotiationCreateBody, ctx: RequestContext = Depends(require_agency_context)
):
    def _op():
        from apps.negotiations.services import create_negotiation

        n = create_negotiation(user=ctx.user, agency_id=ctx.agency_id, data=body.model_dump())
        return _ser_neg(n, include_activities=True)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.patch("/{negotiation_id}")
async def update_negotiation_endpoint(
    negotiation_id: UUID,
    body: NegotiationPatchBody,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.negotiations.services import update_negotiation

        n = update_negotiation(
            user=ctx.user,
            agency_id=ctx.agency_id,
            negotiation_id=negotiation_id,
            data=body.model_dump(exclude_unset=True),
        )
        return _ser_neg(n, include_activities=True)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/{negotiation_id}/offers", status_code=201)
async def add_offer_endpoint(
    negotiation_id: UUID,
    body: OfferVersionCreateBody,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.negotiations.services import add_offer_version

        o = add_offer_version(
            user=ctx.user,
            agency_id=ctx.agency_id,
            negotiation_id=negotiation_id,
            data=body.model_dump(),
        )
        return {
            "id": str(o.id),
            "version_number": o.version_number,
            "proposed_price": str(o.proposed_price),
            "status": o.status,
        }

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/{negotiation_id}/respond")
async def respond_negotiation_endpoint(
    negotiation_id: UUID,
    body: NegotiationRespondBody,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.negotiations.services import respond_to_negotiation

        n = respond_to_negotiation(
            user=ctx.user,
            agency_id=ctx.agency_id,
            negotiation_id=negotiation_id,
            status_value=body.status,
            reason=body.reason,
            agreed_price=body.agreed_price,
            next_followup_at=body.next_followup_at,
            next_action=body.next_action,
        )
        return {"id": str(n.id), "status": n.status, "agreed_price": str(n.agreed_price or "")}

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/{negotiation_id}/activities", status_code=201)
async def add_activity_endpoint(
    negotiation_id: UUID,
    body: NegotiationActivityBody,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.negotiations.services import add_negotiation_activity

        a = add_negotiation_activity(
            user=ctx.user,
            agency_id=ctx.agency_id,
            negotiation_id=negotiation_id,
            data=body.model_dump(),
        )
        return {
            "id": str(a.id),
            "activity_type": a.activity_type,
            "title": a.title,
            "created_at": a.created_at.isoformat(),
        }

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/{negotiation_id}/convert-to-contract", status_code=201)
async def convert_to_contract_endpoint(
    negotiation_id: UUID,
    body: ConvertContractBody = ConvertContractBody(),
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.negotiations.services import convert_negotiation_to_contract

        c = convert_negotiation_to_contract(
            user=ctx.user,
            agency_id=ctx.agency_id,
            negotiation_id=negotiation_id,
            contract_number=body.contract_number,
        )
        return {
            "contract_id": str(c.id),
            "contract_number": c.contract_number,
            "status": c.status,
            "amount": str(c.amount),
        }

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))

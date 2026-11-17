from decimal import Decimal
from typing import Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from app.core.django_bridge import run_django
from app.dependencies.auth import RequestContext, require_agency_context
from app.schemas.common import ok

router = APIRouter(prefix="/negotiations", tags=["Negotiations & Offers"])


class NegotiationCreateBody(BaseModel):
    property_id: UUID
    customer_id: UUID
    deal_type_id: str
    agent_membership_id: Optional[UUID] = None
    notes: str = ""
    offered_by: str = "BUYER"
    currency_id: str = "IRT"
    initial_price: Optional[Decimal] = None
    initial_deposit: Optional[Decimal] = None
    initial_rent: Optional[Decimal] = None
    payment_terms: dict[str, Any] = {}


class OfferVersionCreateBody(BaseModel):
    offered_by: str
    currency_id: str = "IRT"
    proposed_price: Decimal = Decimal("0")
    proposed_deposit: Decimal = Decimal("0")
    proposed_rent: Decimal = Decimal("0")
    discount_amount: Decimal = Decimal("0")
    payment_terms: dict[str, Any] = {}


class NegotiationRespondBody(BaseModel):
    status: str


def _ser_neg(n) -> dict:
    return {
        "id": str(n.id),
        "property_id": str(n.property_id),
        "property_code": n.property.property_code,
        "property_title": n.property.title,
        "customer_id": str(n.customer_id),
        "customer_name": n.customer.full_name,
        "agent_name": n.agent_membership.user.full_name,
        "deal_type": n.deal_type_id,
        "deal_type_name": n.deal_type.name_fa,
        "status": n.status,
        "notes": n.notes,
        "offers": [
            {
                "id": str(o.id),
                "version_number": o.version_number,
                "offered_by": o.offered_by,
                "currency": o.currency_id,
                "proposed_price": str(o.proposed_price),
                "proposed_deposit": str(o.proposed_deposit),
                "proposed_rent": str(o.proposed_rent),
                "discount_amount": str(o.discount_amount),
                "status": o.status,
                "created_at": o.created_at.isoformat(),
            }
            for o in n.offer_versions.order_by("version_number")
        ],
        "created_at": n.created_at.isoformat(),
    }


@router.get("")
async def list_negotiations_endpoint(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.negotiations.services import list_negotiations
        from common.pagination import paginate_queryset

        qs = list_negotiations(user=ctx.user, agency_id=ctx.agency_id)
        return paginate_queryset(qs, page=page, page_size=page_size, serializer_fn=_ser_neg)

    items, meta = await run_django(_op, agency_id=ctx.agency_id)
    return ok(items, meta=meta)


@router.post("", status_code=201)
async def create_negotiation_endpoint(
    body: NegotiationCreateBody, ctx: RequestContext = Depends(require_agency_context)
):
    def _op():
        from apps.negotiations.services import create_negotiation

        n = create_negotiation(user=ctx.user, agency_id=ctx.agency_id, data=body.model_dump())
        return _ser_neg(n)

    return ok(await run_django(_op, agency_id=ctx.agency_id))


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
        return {"id": str(o.id), "version_number": o.version_number, "status": o.status}

    return ok(await run_django(_op, agency_id=ctx.agency_id))


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
        )
        return {"id": str(n.id), "status": n.status}

    return ok(await run_django(_op, agency_id=ctx.agency_id))

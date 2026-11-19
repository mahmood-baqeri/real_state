from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from app.core.django_bridge import run_django
from app.dependencies.auth import RequestContext, get_current_context, require_agency_context
from app.schemas.common import ok

router = APIRouter(tags=["Contracts & Deals"])


class ContractTemplateCreateBody(BaseModel):
    country_id: str = "IR"
    contract_type: str
    title: str
    body_template: str
    legal_disclaimer: str = ""
    is_manager_verified: bool = False


class ContractPartyBody(BaseModel):
    customer_id: Optional[UUID] = None
    full_name: str
    party_role: str


class ContractCreateBody(BaseModel):
    contract_number: str
    internal_tracking_code: Optional[str] = None
    contract_type: str = "SALE"
    property_id: UUID
    deal_type_id: str
    template_id: Optional[UUID] = None
    currency_id: str = "IRT"
    amount: Decimal = Decimal("0")
    deposit_amount: Decimal = Decimal("0")
    rent_amount: Decimal = Decimal("0")
    advance_payment: Decimal = Decimal("0")
    remaining_amount: Decimal = Decimal("0")
    payment_method: str = ""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    terms_snapshot: str = ""
    status: str = "DRAFT"
    parties: list[ContractPartyBody] = []


class ContractStatusBody(BaseModel):
    status: str
    reason: str = ""


class DealCreateBody(BaseModel):
    deal_code: str
    contract_id: UUID
    negotiation_id: Optional[UUID] = None
    primary_agent_id: Optional[UUID] = None
    co_agent_id: Optional[UUID] = None
    currency_id: Optional[str] = None
    deal_value: Optional[Decimal] = None
    status: str = "CONTRACT_ACTIVE"


class DealCloseBody(BaseModel):
    auto_calculate_commission: bool = True


def _ser_contract(c) -> dict:
    return {
        "id": str(c.id),
        "contract_number": c.contract_number,
        "internal_tracking_code": c.internal_tracking_code,
        "contract_type": c.contract_type,
        "property_id": str(c.property_id),
        "property_code": c.property.property_code,
        "property_title": c.property.title,
        "deal_type": c.deal_type_id,
        "deal_type_name": c.deal_type.name_fa,
        "currency": c.currency_id,
        "amount": str(c.amount),
        "deposit_amount": str(c.deposit_amount),
        "rent_amount": str(c.rent_amount),
        "advance_payment": str(c.advance_payment),
        "remaining_amount": str(c.remaining_amount),
        "payment_method": c.payment_method,
        "status": c.status,
        "start_date": c.start_date.isoformat() if c.start_date else None,
        "end_date": c.end_date.isoformat() if c.end_date else None,
        "parties": [
            {
                "id": str(p.id),
                "full_name": p.full_name,
                "party_role": p.party_role,
                "customer_id": str(p.customer_id) if p.customer_id else None,
            }
            for p in c.parties.all()
        ],
        "created_at": c.created_at.isoformat(),
    }


def _ser_deal(d) -> dict:
    return {
        "id": str(d.id),
        "deal_code": d.deal_code,
        "contract_id": str(d.contract_id),
        "contract_number": d.contract.contract_number,
        "property_id": str(d.property_id),
        "property_code": d.property.property_code,
        "property_title": d.property.title,
        "primary_agent_name": d.primary_agent.user.full_name,
        "co_agent_name": d.co_agent.user.full_name if d.co_agent else None,
        "currency": d.currency_id,
        "deal_value": str(d.deal_value),
        "status": d.status,
        "closed_at": d.closed_at.isoformat() if d.closed_at else None,
        "created_at": d.created_at.isoformat(),
    }


@router.get("/contracts/templates")
async def list_templates_endpoint(ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.contracts.services import list_contract_templates

        return [
            {
                "id": str(t.id),
                "contract_type": t.contract_type,
                "title": t.title,
                "body_template": t.body_template,
                "legal_disclaimer": t.legal_disclaimer,
                "is_manager_verified": t.is_manager_verified,
            }
            for t in list_contract_templates(ctx.agency_id)
        ]

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/contracts/templates", status_code=201)
async def create_template_endpoint(
    body: ContractTemplateCreateBody, ctx: RequestContext = Depends(require_agency_context)
):
    def _op():
        from apps.contracts.services import create_contract_template

        t = create_contract_template(user=ctx.user, agency_id=ctx.agency_id, data=body.model_dump())
        return {"id": str(t.id), "title": t.title}

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.get("/contracts")
async def list_contracts_endpoint(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.contracts.services import list_contracts
        from common.pagination import paginate_queryset

        qs = list_contracts(user=ctx.user, agency_id=ctx.agency_id)
        return paginate_queryset(qs, page=page, page_size=page_size, serializer_fn=_ser_contract)

    items, meta = await run_django(_op, agency_id=ctx.agency_id)
    return ok(items, meta=meta)


@router.post("/contracts", status_code=201)
async def create_contract_endpoint(
    body: ContractCreateBody, ctx: RequestContext = Depends(require_agency_context)
):
    def _op():
        from apps.contracts.services import create_contract

        c = create_contract(user=ctx.user, agency_id=ctx.agency_id, data=body.model_dump())
        return _ser_contract(c)

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/contracts/{contract_id}/status")
async def contract_status_endpoint(
    contract_id: UUID,
    body: ContractStatusBody,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.contracts.services import transition_contract_status

        c = transition_contract_status(
            user=ctx.user,
            agency_id=ctx.agency_id,
            contract_id=contract_id,
            to_status=body.status,
            reason=body.reason,
        )
        return {"id": str(c.id), "status": c.status}

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.get("/deals")
async def list_deals_endpoint(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.contracts.services import list_deals
        from common.pagination import paginate_queryset

        qs = list_deals(user=ctx.user, agency_id=ctx.agency_id)
        return paginate_queryset(qs, page=page, page_size=page_size, serializer_fn=_ser_deal)

    items, meta = await run_django(_op, agency_id=ctx.agency_id)
    return ok(items, meta=meta)


@router.post("/deals", status_code=201)
async def create_deal_endpoint(body: DealCreateBody, ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.contracts.services import create_deal

        d = create_deal(user=ctx.user, agency_id=ctx.agency_id, data=body.model_dump())
        return _ser_deal(d)

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.get("/contracts/{contract_id}")
async def get_contract_endpoint(contract_id: UUID, ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.contracts.services import get_contract

        c = get_contract(user=ctx.user, agency_id=ctx.agency_id, contract_id=contract_id)
        data = _ser_contract(c)
        data["payment_method"] = c.payment_method
        data["terms_snapshot"] = c.terms_snapshot
        data["template_title"] = c.template.title if c.template else None
        data["history"] = [
            {
                "id": str(h.id),
                "from_status": h.from_status,
                "to_status": h.to_status,
                "reason": h.reason,
                "changed_by_name": h.changed_by.full_name if h.changed_by else "سیستم",
                "created_at": h.created_at.isoformat(),
            }
            for h in c.status_history.order_by("-created_at")
        ]
        return data

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.get("/deals/{deal_id}")
async def get_deal_endpoint(deal_id: UUID, ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.contracts.services import get_deal

        d = get_deal(user=ctx.user, agency_id=ctx.agency_id, deal_id=deal_id)
        data = _ser_deal(d)
        ledger = getattr(d, "financial_ledger", None)
        comm = getattr(d, "commission", None)
        data["ledger"] = (
            {
                "deal_amount": str(ledger.deal_amount),
                "total_received": str(ledger.total_received),
                "total_paid": str(ledger.total_paid),
                "receivable_balance": str(ledger.receivable_balance),
            }
            if ledger
            else None
        )
        data["commission"] = (
            {
                "id": str(comm.id),
                "gross_commission": str(comm.gross_commission),
                "net_distributable": str(comm.net_distributable),
                "status": comm.status,
            }
            if comm
            else None
        )
        return data

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/deals/{deal_id}/close")
async def close_deal_endpoint(
    deal_id: UUID,
    body: DealCloseBody = DealCloseBody(),
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.contracts.services import close_deal_won

        d = close_deal_won(
            user=ctx.user,
            agency_id=ctx.agency_id,
            deal_id=deal_id,
            auto_calculate_commission=body.auto_calculate_commission,
        )
        return _ser_deal(d)

    return ok(await run_django(_op, agency_id=ctx.agency_id))


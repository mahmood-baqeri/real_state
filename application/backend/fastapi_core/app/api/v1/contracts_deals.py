from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from app.core.django_bridge import run_django
from app.dependencies.auth import RequestContext, get_current_context, require_agency_context
from app.schemas.common import ok

router = APIRouter(tags=["Contracts & Deals"])


class DealPaymentScheduleBody(BaseModel):
    items: list[dict[str, Any]] = []


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
    obligations_json: dict[str, Any] = {}
    status: str = "DRAFT"
    parties: list[ContractPartyBody] = []


class ContractPatchBody(BaseModel):
    contract_type: Optional[str] = None
    property_id: Optional[UUID] = None
    deal_type_id: Optional[str] = None
    template_id: Optional[UUID] = None
    currency_id: Optional[str] = None
    amount: Optional[Decimal] = None
    deposit_amount: Optional[Decimal] = None
    rent_amount: Optional[Decimal] = None
    advance_payment: Optional[Decimal] = None
    remaining_amount: Optional[Decimal] = None
    payment_method: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    terms_snapshot: Optional[str] = None
    obligations_json: Optional[dict[str, Any]] = None
    parties: Optional[list[ContractPartyBody]] = None


class ContractStatusBody(BaseModel):
    status: str
    reason: str = ""


class ContractAmendmentCreateBody(BaseModel):
    title: str
    reason: str
    changes_json: dict[str, Any] = {}
    approve_immediately: bool = True


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


class DealRoomBody(BaseModel):
    checklist: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []


def _ser_contract(c) -> dict:
    return {
        "id": str(c.id),
        "agency_id": str(c.agency_id),
        "agency_name": c.agency.name if c.agency else None,
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
        "is_editable": c.status in ("DRAFT", "PENDING_REVIEW", "PENDING_PARTIES_APPROVAL"),
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
        "amendments": [
            {
                "id": str(a.id),
                "amendment_number": a.amendment_number,
                "title": a.title,
                "reason": a.reason,
                "changes_json": a.changes_json,
                "status": a.status,
                "approved_by_name": a.approved_by.full_name if a.approved_by else None,
                "approved_at": a.approved_at.isoformat() if a.approved_at else None,
                "created_at": a.created_at.isoformat(),
            }
            for a in c.amendments.order_by("amendment_number")
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
        "deal_room": (d.contract.obligations_json or {}).get("deal_room", {"checklist": [], "events": []}),
        "payment_schedule": (d.contract.obligations_json or {}).get("deal_payment_schedule", {"items": []}),
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

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/contracts/templates", status_code=201)
async def create_template_endpoint(
    body: ContractTemplateCreateBody, ctx: RequestContext = Depends(require_agency_context)
):
    def _op():
        from apps.contracts.services import create_contract_template

        t = create_contract_template(user=ctx.user, agency_id=ctx.agency_id, data=body.model_dump())
        return {"id": str(t.id), "title": t.title}

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.get("/contracts")
async def list_contracts_endpoint(
    status: Optional[str] = None,
    q: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.contracts.services import list_contracts
        from common.pagination import paginate_queryset

        qs = list_contracts(user=ctx.user, agency_id=ctx.agency_id, status_filter=status, q=q)
        return paginate_queryset(qs, page=page, page_size=page_size, serializer_fn=_ser_contract)

    items, meta = await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None)
    return ok(items, meta=meta)


@router.post("/contracts", status_code=201)
async def create_contract_endpoint(
    body: ContractCreateBody, ctx: RequestContext = Depends(require_agency_context)
):
    def _op():
        from apps.contracts.services import create_contract

        c = create_contract(user=ctx.user, agency_id=ctx.agency_id, data=body.model_dump())
        return _ser_contract(c)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.patch("/contracts/{contract_id}")
async def patch_contract_endpoint(
    contract_id: UUID,
    body: ContractPatchBody,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.contracts.services import update_contract

        c = update_contract(
            user=ctx.user,
            agency_id=ctx.agency_id,
            contract_id=contract_id,
            data=body.model_dump(exclude_none=True),
        )
        return _ser_contract(c)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.delete("/contracts/{contract_id}")
async def delete_contract_endpoint(
    contract_id: UUID,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.contracts.services import archive_contract

        c = archive_contract(user=ctx.user, agency_id=ctx.agency_id, contract_id=contract_id)
        return {"id": str(c.id), "status": c.status, "archived": True}

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


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

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/contracts/{contract_id}/amendments", status_code=201)
async def create_contract_amendment_endpoint(
    contract_id: UUID,
    body: ContractAmendmentCreateBody,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.contracts.services import create_contract_amendment

        a = create_contract_amendment(
            user=ctx.user,
            agency_id=ctx.agency_id,
            contract_id=contract_id,
            data=body.model_dump(),
        )
        return {
            "id": str(a.id),
            "amendment_number": a.amendment_number,
            "title": a.title,
            "reason": a.reason,
            "changes_json": a.changes_json,
            "status": a.status,
            "approved_at": a.approved_at.isoformat() if a.approved_at else None,
            "created_at": a.created_at.isoformat(),
        }

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.get("/contracts/{contract_id}")
async def get_contract_endpoint(contract_id: UUID, ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.contracts.services import get_contract, get_contract_documents

        c = get_contract(user=ctx.user, agency_id=ctx.agency_id, contract_id=contract_id)
        data = _ser_contract(c)
        data["payment_method"] = c.payment_method
        data["terms_snapshot"] = c.terms_snapshot
        data["obligations_json"] = c.obligations_json
        data["template_title"] = c.template.title if c.template else None
        data["documents"] = [
            {
                "id": str(d.id),
                "title": d.title,
                "category": d.category,
                "access_level": d.access_level,
                "created_at": d.created_at.isoformat(),
            }
            for d in get_contract_documents(c)
        ]
        data["history"] = [
            {
                "id": str(h.id),
                "from_status": h.from_status,
                "to_status": h.to_status,
                "reason": h.reason,
                "changed_by_name": h.changed_by.full_name if h.changed_by else "سیستم",
                "created_at": h.changed_at.isoformat(),
                "changed_at": h.changed_at.isoformat(),
            }
            for h in c.status_history.order_by("-changed_at")
        ]
        return data

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


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

    items, meta = await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None)
    return ok(items, meta=meta)


@router.post("/deals", status_code=201)
async def create_deal_endpoint(body: DealCreateBody, ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.contracts.services import create_deal

        d = create_deal(user=ctx.user, agency_id=ctx.agency_id, data=body.model_dump())
        return _ser_deal(d)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.get("/deals/financial-summary")
async def deals_financial_summary_endpoint(ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.contracts.services import list_deals
        from apps.accounting.models import DealFinancialLedger

        scoped_deals = list_deals(user=ctx.user, agency_id=ctx.agency_id)
        deal_ids = list(scoped_deals.values_list("id", flat=True))
        ledgers = DealFinancialLedger.objects.all_tenants().filter(deal_id__in=deal_ids)
        grouped = {}
        for row in ledgers.values(
            "currency_id", "deal_amount", "total_received", "total_paid", "net_profit", "settlement_status"
        ):
            currency = row["currency_id"] or "—"
            bucket = grouped.setdefault(currency, {
                "currency": currency, "deal_amount": Decimal("0"), "received": Decimal("0"),
                "paid": Decimal("0"), "receivable": Decimal("0"), "net_profit": Decimal("0"),
                "ledger_count": 0, "open_count": 0, "partial_count": 0, "settled_count": 0,
            })
            amount = row["deal_amount"] or Decimal("0")
            received = row["total_received"] or Decimal("0")
            bucket["deal_amount"] += amount
            bucket["received"] += received
            bucket["paid"] += row["total_paid"] or Decimal("0")
            bucket["receivable"] += max(Decimal("0"), amount - received)
            bucket["net_profit"] += row["net_profit"] or Decimal("0")
            bucket["ledger_count"] += 1
            status = row["settlement_status"]
            if status == DealFinancialLedger.SettlementStatus.SETTLED:
                bucket["settled_count"] += 1
            elif status == DealFinancialLedger.SettlementStatus.PARTIAL:
                bucket["partial_count"] += 1
            else:
                bucket["open_count"] += 1
        return {
            "deal_count": scoped_deals.count(),
        "currencies": [{k: (str(v) if isinstance(v, Decimal) else v) for k, v in bucket.items()}
                       for bucket in grouped.values()],
        }

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


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
                "receivable_balance": str(max(Decimal("0.00"), ledger.deal_amount - ledger.total_received)),
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

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


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

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.put("/deals/{deal_id}/room")
async def update_deal_room_endpoint(
    deal_id: UUID,
    body: DealRoomBody,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.contracts.services import get_deal
        from common.permissions import can_edit_property
        from apps.audit.services import record_audit_event

        deal = get_deal(user=ctx.user, agency_id=ctx.agency_id, deal_id=deal_id)
        if not can_edit_property(ctx.user, deal.property):
            from common.exceptions import PermissionDeniedDomainError, ValidationDomainError
            raise PermissionDeniedDomainError("مجوز ویرایش اتاق معامله را ندارید.")
        if len(body.checklist) > 100 or len(body.events) > 100:
            from common.exceptions import ValidationDomainError
            raise ValidationDomainError("حداکثر ۱۰۰ مورد برای چک‌لیست و تقویم مجاز است.")
        checklist = []
        for item in body.checklist:
            title = str(item.get("title", "")).strip()[:160]
            if not title:
                continue
            checklist.append({"id": str(item.get("id", ""))[:64], "title": title, "done": bool(item.get("done", False))})
        events = []
        for event in body.events:
            title = str(event.get("title", "")).strip()[:160]
            date = str(event.get("date", ""))[:10]
            if not title or len(date) != 10:
                continue
            events.append({"id": str(event.get("id", ""))[:64], "title": title, "date": date, "note": str(event.get("note", ""))[:500]})
        obligations = dict(deal.contract.obligations_json or {})
        room = {"checklist": checklist, "events": events}
        obligations["deal_room"] = room
        deal.contract.obligations_json = obligations
        deal.contract.updated_by = ctx.user
        deal.contract.save(update_fields=["obligations_json", "updated_by", "updated_at"])
        record_audit_event(action="DEAL_ROOM_UPDATED", resource_type="Deal", resource_id=str(deal.id), actor=ctx.user, agency_id=deal.agency_id, after_state=room)
        return room
    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.put("/deals/{deal_id}/payment-schedule")
async def update_deal_payment_schedule_endpoint(
    deal_id: UUID,
    body: DealPaymentScheduleBody,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.contracts.services import get_deal
        from common.permissions import can_edit_property
        from apps.audit.services import record_audit_event
        from common.exceptions import PermissionDeniedDomainError, ValidationDomainError


        deal = get_deal(user=ctx.user, agency_id=ctx.agency_id, deal_id=deal_id)
        if not can_edit_property(ctx.user, deal.property):
            raise PermissionDeniedDomainError("مجوز ویرایش برنامه پرداخت معامله را ندارید.")
        if len(body.items) > 100:
            raise ValidationDomainError("حداکثر ۱۰۰ قسط/مرحله پرداخت مجاز است.")
        cleaned = []
        allowed = {"planned", "paid"}
        for item in body.items:
            title = str(item.get("title", "")).strip()[:160]
            due_date = str(item.get("due_date", ""))[:10]
            if not title or len(due_date) != 10:
                continue
            try:
                amount = Decimal(str(item.get("amount", "0")))
            except Exception:
                raise ValidationDomainError("مبلغ مرحله پرداخت معتبر نیست.")
            if amount < 0:
                raise ValidationDomainError("مبلغ مرحله پرداخت نمی‌تواند منفی باشد.")
            status = str(item.get("status", "planned"))
            if status not in allowed:
                status = "planned"
            cleaned.append({"id": str(item.get("id", ""))[:64], "title": title, "due_date": due_date,
                         "amount": str(amount), "status": status, "note": str(item.get("note", ""))[:500]})
        obligations = dict(deal.contract.obligations_json or {})
        obligations["deal_payment_schedule"] = {"items": cleaned}
        deal.contract.obligations_json = obligations
        deal.contract.updated_by = ctx.user
        deal.contract.save(update_fields=["obligations_json", "updated_by", "updated_at"])
        record_audit_event(action="DEAL_PAYMENT_SCHEDULE_UPDATED", resource_type="Deal", resource_id=str(deal.id), actor=ctx.user, agency_id=deal.agency_id, after_state={"items": cleaned})
        return {"items": cleaned}
    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))

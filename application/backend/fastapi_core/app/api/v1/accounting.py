from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from app.core.django_bridge import run_django
from app.dependencies.auth import RequestContext, require_agency_context
from app.schemas.common import ok

router = APIRouter(prefix="/accounting", tags=["Double-Entry Accounting & Treasury"])


class CoaCreateBody(BaseModel):
    code: str
    name: str
    account_type: str
    level: str = "SUBSIDIARY"
    parent_id: Optional[UUID] = None


class JournalLineBody(BaseModel):
    account_id: UUID
    description: str = ""
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")


class JournalEntryCreateBody(BaseModel):
    entry_number: str
    description: str
    currency_id: str = "IRT"
    source_type: str = "MANUAL"
    lines: list[JournalLineBody]


class ChequeCreateBody(BaseModel):
    direction: str
    cheque_number: str
    bank_name: str
    due_date: date
    amount: Decimal
    currency_id: str = "IRT"
    deal_id: Optional[UUID] = None


class ChequeStatusBody(BaseModel):
    status: str


def _ser_journal_entry(je) -> dict:
    return {
        "id": str(je.id),
        "entry_number": je.entry_number,
        "entry_date": je.entry_date.isoformat(),
        "description": je.description,
        "currency": je.currency_id,
        "status": je.status,
        "source_type": je.source_type,
        "lines": [
            {
                "id": str(l.id),
                "account_id": str(l.account_id),
                "account_code": l.account.code,
                "account_name": l.account.name,
                "description": l.description,
                "debit": str(l.debit),
                "credit": str(l.credit),
            }
            for l in je.lines.all()
        ],
    }


@router.get("/coa")
async def list_coa_endpoint(ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.accounting.services import list_coa

        return [
            {
                "id": str(a.id),
                "code": a.code,
                "name": a.name,
                "account_type": a.account_type,
                "level": a.level,
                "parent_id": str(a.parent_id) if a.parent_id else None,
            }
            for a in list_coa(user=ctx.user, agency_id=ctx.agency_id)
        ]

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/coa", status_code=201)
async def create_coa_endpoint(body: CoaCreateBody, ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.accounting.services import create_coa_account

        a = create_coa_account(user=ctx.user, agency_id=ctx.agency_id, data=body.model_dump())
        return {"id": str(a.id), "code": a.code, "name": a.name}

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.get("/journal-entries")
async def list_journal_entries_endpoint(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.accounting.services import list_journal_entries
        from common.pagination import paginate_queryset

        qs = list_journal_entries(user=ctx.user, agency_id=ctx.agency_id)
        return paginate_queryset(qs, page=page, page_size=page_size, serializer_fn=_ser_journal_entry)

    items, meta = await run_django(_op, agency_id=ctx.agency_id)
    return ok(items, meta=meta)


@router.post("/journal-entries", status_code=201)
async def post_journal_entry_endpoint(
    body: JournalEntryCreateBody, ctx: RequestContext = Depends(require_agency_context)
):
    def _op():
        from apps.accounting.services import post_journal_entry_service

        je = post_journal_entry_service(user=ctx.user, agency_id=ctx.agency_id, data=body.model_dump())
        return _ser_journal_entry(je)

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/journal-entries/{entry_id}/reverse")
async def reverse_journal_entry_endpoint(
    entry_id: UUID, ctx: RequestContext = Depends(require_agency_context)
):
    def _op():
        from apps.accounting.services import reverse_journal_entry_service

        rev = reverse_journal_entry_service(user=ctx.user, agency_id=ctx.agency_id, entry_id=entry_id)
        return _ser_journal_entry(rev)

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.get("/treasury")
async def list_treasury_endpoint(ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.accounting.services import list_treasury_and_cheques

        t = list_treasury_and_cheques(user=ctx.user, agency_id=ctx.agency_id)
        return {
            "bank_accounts": [
                {
                    "id": str(b.id),
                    "bank_name": b.bank_name,
                    "account_number": b.account_number,
                    "iban": b.iban,
                    "currency": b.currency_id,
                    "current_balance": str(b.current_balance),
                }
                for b in t["bank_accounts"]
            ],
            "cash_boxes": [
                {
                    "id": str(c.id),
                    "name": c.name,
                    "currency": c.currency_id,
                    "current_balance": str(c.current_balance),
                }
                for c in t["cash_boxes"]
            ],
            "cheques": [
                {
                    "id": str(ch.id),
                    "direction": ch.direction,
                    "cheque_number": ch.cheque_number,
                    "bank_name": ch.bank_name,
                    "due_date": ch.due_date.isoformat(),
                    "amount": str(ch.amount),
                    "currency": ch.currency_id,
                    "status": ch.status,
                    "deal_code": ch.deal.deal_code if ch.deal else None,
                }
                for ch in t["cheques"]
            ],
            "deal_ledgers": [
                {
                    "id": str(dl.id),
                    "deal_id": str(dl.deal_id),
                    "deal_code": dl.deal.deal_code,
                    "currency": dl.currency_id,
                    "deal_amount": str(dl.deal_amount),
                    "total_received": str(dl.total_received),
                    "total_paid": str(dl.total_paid),
                    "gross_commission": str(dl.gross_commission),
                    "agency_share": str(dl.agency_share),
                    "agents_share": str(dl.agents_share),
                    "net_profit": str(dl.net_profit),
                    "settlement_status": dl.settlement_status,
                }
                for dl in t["deal_ledgers"]
            ],
        }

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/cheques", status_code=201)
async def create_cheque_endpoint(body: ChequeCreateBody, ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.accounting.services import create_cheque

        ch = create_cheque(user=ctx.user, agency_id=ctx.agency_id, data=body.model_dump())
        return {"id": str(ch.id), "cheque_number": ch.cheque_number, "status": ch.status}

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.patch("/cheques/{cheque_id}")
async def patch_cheque_endpoint(
    cheque_id: UUID, body: ChequeStatusBody, ctx: RequestContext = Depends(require_agency_context)
):
    def _op():
        from apps.accounting.services import update_cheque_status

        ch = update_cheque_status(
            user=ctx.user, agency_id=ctx.agency_id, cheque_id=cheque_id, status_value=body.status
        )
        return {"id": str(ch.id), "status": ch.status}

    return ok(await run_django(_op, agency_id=ctx.agency_id))

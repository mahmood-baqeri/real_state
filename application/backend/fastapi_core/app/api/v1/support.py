from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from app.core.django_bridge import run_django
from app.dependencies.auth import RequestContext, get_current_context
from app.schemas.common import ok

router = APIRouter(prefix="/tickets", tags=["Support & Ticketing"])


class TicketAttachmentBody(BaseModel):
    file_name: str
    file_url: str
    mime_type: str = "application/octet-stream"
    file_size_bytes: int = 0


class TicketCreateBody(BaseModel):
    scope: str = "AGENCY"
    category: str = "GENERAL"
    priority: str = "NORMAL"
    subject: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=3)
    attachments: list[TicketAttachmentBody] = []


class TicketMessageBody(BaseModel):
    body: str = Field(min_length=1)
    is_internal_note: bool = False
    attachments: list[TicketAttachmentBody] = []


class TicketStatusBody(BaseModel):
    status: str
    note: str = ""


class TicketAssignBody(BaseModel):
    assignee_user_id: UUID


class TicketRatingBody(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = ""


class CannedReplyBody(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    category: str = "GENERAL"
    body: str = Field(min_length=2)


def _ser_ticket(t, include_internal: bool = False) -> dict:
    msgs = [
        {
            "id": str(m.id),
            "sender_id": str(m.sender_id),
            "sender_name": m.sender.full_name,
            "body": m.body,
            "is_internal_note": m.is_internal_note,
            "attachments": [
                {
                    "id": str(a.id),
                    "file_name": a.file_name,
                    "file_url": a.file_url,
                    "mime_type": a.mime_type,
                    "file_size_bytes": a.file_size_bytes,
                }
                for a in m.attachments.all()
            ],
            "created_at": m.created_at.isoformat(),
        }
        for m in t.messages.all()
        if include_internal or not m.is_internal_note
    ]
    return {
        "id": str(t.id),
        "ticket_number": t.ticket_number,
        "scope": t.scope,
        "agency_id": str(t.agency_id) if t.agency_id else None,
        "agency_name": t.agency.name if t.agency else "پشتیبانی پلتفرم",
        "created_by_name": t.created_by_user.full_name,
        "assigned_to_name": t.assigned_to_user.full_name if t.assigned_to_user else None,
        "category": t.category,
        "priority": t.priority,
        "status": t.status,
        "subject": t.subject,
        "sla_due_at": t.sla_due_at.isoformat() if t.sla_due_at else None,
        "resolved_at": t.resolved_at.isoformat() if t.resolved_at else None,
        "satisfaction_rating": t.satisfaction_rating,
        "satisfaction_comment": t.satisfaction_comment,
        "messages": msgs,
        "status_history": [
            {
                "id": str(h.id),
                "from_status": h.from_status,
                "to_status": h.to_status,
                "changed_by_name": h.changed_by.full_name if h.changed_by else "سیستم",
                "note": h.note,
                "created_at": h.created_at.isoformat(),
            }
            for h in t.status_history.all()
        ],
        "created_at": t.created_at.isoformat(),
    }


@router.get("")
async def list_tickets_endpoint(
    scope: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    ctx: RequestContext = Depends(get_current_context),
):
    def _op():
        from apps.support.services import _is_support_staff, list_tickets
        from common.pagination import paginate_queryset

        qs = list_tickets(user=ctx.user, agency_id=ctx.agency_id, scope=scope, status_filter=status)
        return paginate_queryset(
            qs,
            page=page,
            page_size=page_size,
            serializer_fn=lambda t: _ser_ticket(t, include_internal=_is_support_staff(ctx.user, t)),
        )

    items, meta = await run_django(_op, agency_id=ctx.agency_id)
    return ok(items, meta=meta)


@router.post("", status_code=201)
async def create_ticket_endpoint(body: TicketCreateBody, ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.support.services import create_ticket

        t = create_ticket(user=ctx.user, agency_id=ctx.agency_id, data=body.model_dump())
        return _ser_ticket(t, include_internal=False)

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.get("/canned-replies")
async def list_canned_replies_endpoint(ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.support.services import list_canned_replies

        return [
            {"id": str(r.id), "title": r.title, "category": r.category, "body": r.body}
            for r in list_canned_replies(user=ctx.user, agency_id=ctx.agency_id)
        ]

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/canned-replies", status_code=201)
async def create_canned_reply_endpoint(body: CannedReplyBody, ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.support.services import create_canned_reply

        r = create_canned_reply(user=ctx.user, agency_id=ctx.agency_id, data=body.model_dump())
        return {"id": str(r.id), "title": r.title, "category": r.category, "body": r.body}

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.get("/reports/summary")
async def ticket_report_endpoint(ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.support.services import get_ticket_report

        return get_ticket_report(user=ctx.user, agency_id=ctx.agency_id)

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.get("/{ticket_id}")
async def get_ticket_endpoint(ticket_id: UUID, ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.support.services import get_ticket

        t, can_internal = get_ticket(user=ctx.user, agency_id=ctx.agency_id, ticket_id=ticket_id)
        data = _ser_ticket(t, include_internal=can_internal)
        data["can_manage"] = can_internal
        return data

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/{ticket_id}/messages", status_code=201)
async def add_ticket_message_endpoint(
    ticket_id: UUID, body: TicketMessageBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.support.services import add_ticket_message

        m = add_ticket_message(user=ctx.user, agency_id=ctx.agency_id, ticket_id=ticket_id, data=body.model_dump())
        return {
            "id": str(m.id),
            "sender_name": m.sender.full_name,
            "body": m.body,
            "is_internal_note": m.is_internal_note,
            "created_at": m.created_at.isoformat(),
        }

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/{ticket_id}/status")
async def update_ticket_status_endpoint(
    ticket_id: UUID, body: TicketStatusBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.support.services import update_ticket_status

        t = update_ticket_status(
            user=ctx.user,
            agency_id=ctx.agency_id,
            ticket_id=ticket_id,
            to_status=body.status,
            note=body.note,
        )
        return {"id": str(t.id), "status": t.status}

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/{ticket_id}/assign")
async def assign_ticket_endpoint(
    ticket_id: UUID, body: TicketAssignBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.support.services import assign_ticket

        t = assign_ticket(
            user=ctx.user,
            agency_id=ctx.agency_id,
            ticket_id=ticket_id,
            assignee_user_id=body.assignee_user_id,
        )
        return {"id": str(t.id), "status": t.status, "assigned_to_name": t.assigned_to_user.full_name}

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/{ticket_id}/rating")
async def rate_ticket_endpoint(
    ticket_id: UUID, body: TicketRatingBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.support.services import submit_ticket_rating

        t = submit_ticket_rating(
            user=ctx.user,
            agency_id=ctx.agency_id,
            ticket_id=ticket_id,
            rating=body.rating,
            comment=body.comment,
        )
        return {"id": str(t.id), "satisfaction_rating": t.satisfaction_rating}

    return ok(await run_django(_op, agency_id=ctx.agency_id))

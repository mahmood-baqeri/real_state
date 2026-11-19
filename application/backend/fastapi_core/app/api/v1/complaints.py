# Path: backend/fastapi_core/app/api/v1/complaints.py

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from app.core.django_bridge import run_django
from app.dependencies.auth import RequestContext, get_current_context, get_optional_context
from app.schemas.common import ok

router = APIRouter(prefix="/complaints", tags=["Complaints & Confidential Tracking"])


class ComplaintCreateBody(BaseModel):
    complainant_name: str = ""
    complainant_phone: str = ""
    agency_id: Optional[UUID] = None
    target_type: str = "AGENCY"
    target_title: str = ""
    subject: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=5)
    is_confidential: bool = True


class ComplaintNoteBody(BaseModel):
    note: str = Field(min_length=2)
    is_confidential: bool = True


class ComplaintStatusBody(BaseModel):
    status: str
    resolution_summary: Optional[str] = None
    assigned_to_user_id: Optional[UUID] = None


def _ser_complaint(c, include_notes: bool = False) -> dict:
    return {
        "id": str(c.id),
        "tracking_code": c.tracking_code,
        "complainant_name": c.complainant_name,
        "complainant_phone": c.complainant_phone,
        "agency_id": str(c.agency_id) if c.agency_id else None,
        "agency_name": c.agency.name if c.agency else "پلتفرم",
        "target_type": c.target_type,
        "target_title": c.target_title,
        "subject": c.subject,
        "description": c.description,
        "is_confidential": c.is_confidential,
        "status": c.status,
        "assigned_to_name": c.assigned_to_user.full_name if c.assigned_to_user else None,
        "resolution_summary": c.resolution_summary,
        "resolved_at": c.resolved_at.isoformat() if c.resolved_at else None,
        "notes": (
            [
                {
                    "id": str(n.id),
                    "author_name": n.author.full_name,
                    "note": n.note,
                    "is_confidential": n.is_confidential,
                    "created_at": n.created_at.isoformat(),
                }
                for n in c.notes.all()
            ]
            if include_notes
            else []
        ),
        "created_at": c.created_at.isoformat(),
    }


@router.post("/public", status_code=201)
async def create_public_complaint_endpoint(
    body: ComplaintCreateBody, ctx: RequestContext = Depends(get_optional_context)
):
    def _op():
        from apps.complaints.services import create_complaint

        c = create_complaint(user=ctx.user, agency_id=ctx.agency_id, data=body.model_dump())
        return {
            "id": str(c.id),
            "tracking_code": c.tracking_code,
            "status": c.status,
            "created_at": c.created_at.isoformat(),
        }

    return ok(await run_django(_op))


@router.get("/public/track")
async def track_public_complaint_endpoint(tracking_code: str, phone_number: str):
    def _op():
        from apps.complaints.services import track_public_complaint

        return track_public_complaint(tracking_code=tracking_code, phone_number=phone_number)

    return ok(await run_django(_op))


@router.get("")
async def list_complaints_endpoint(
    status: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    ctx: RequestContext = Depends(get_current_context),
):
    def _op():
        from apps.complaints.services import _can_manage_complaint, list_complaints
        from common.pagination import paginate_queryset

        qs = list_complaints(user=ctx.user, agency_id=ctx.agency_id, status_filter=status)
        return paginate_queryset(
            qs,
            page=page,
            page_size=page_size,
            serializer_fn=lambda c: _ser_complaint(c, include_notes=_can_manage_complaint(ctx.user, c)),
        )

    items, meta = await run_django(_op, agency_id=ctx.agency_id)
    return ok(items, meta=meta)


@router.post("", status_code=201)
async def create_complaint_endpoint(
    body: ComplaintCreateBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.complaints.services import create_complaint

        c = create_complaint(user=ctx.user, agency_id=ctx.agency_id, data=body.model_dump())
        return _ser_complaint(c, include_notes=False)

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/{complaint_id}/notes", status_code=201)
async def add_complaint_note_endpoint(
    complaint_id: UUID, body: ComplaintNoteBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.complaints.services import add_complaint_note

        n = add_complaint_note(
            user=ctx.user,
            complaint_id=complaint_id,
            note=body.note,
            is_confidential=body.is_confidential,
        )
        return {
            "id": str(n.id),
            "author_name": n.author.full_name,
            "note": n.note,
            "is_confidential": n.is_confidential,
            "created_at": n.created_at.isoformat(),
        }

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/{complaint_id}/status")
async def update_complaint_status_endpoint(
    complaint_id: UUID, body: ComplaintStatusBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.complaints.services import update_complaint_status

        c = update_complaint_status(
            user=ctx.user,
            complaint_id=complaint_id,
            to_status=body.status,
            resolution_summary=body.resolution_summary,
            assigned_to_user_id=body.assigned_to_user_id,
        )
        return _ser_complaint(c, include_notes=True)

    return ok(await run_django(_op, agency_id=ctx.agency_id))

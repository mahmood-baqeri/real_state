# Path: backend/fastapi_core/app/api/v1/appointments.py

from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from app.core.django_bridge import run_django
from app.dependencies.auth import RequestContext, get_current_context, require_agency_context
from app.schemas.common import ok
from fastapi import Request
from app.core.rate_limit import rate_limit

router = APIRouter(prefix="/appointments", tags=["Viewing Appointments"])


class PublicAppointmentBody(BaseModel):
    property_id: UUID
    scheduled_start: datetime
    scheduled_end: datetime
    notes: str = ""


class AgencyAppointmentBody(BaseModel):
    property_id: UUID
    customer_id: UUID
    scheduled_start: datetime
    scheduled_end: datetime
    agent_membership_id: Optional[UUID] = None
    status: str = "CONFIRMED"


class AppointmentStatusBody(BaseModel):
    status: str
    agent_report: Optional[str] = None


def _ser_appt(a) -> dict:
    return {
        "id": str(a.id),
        "agency": str(a.agency_id),
        "property": str(a.property_id),
        "property_title": a.property.title,
        "customer": str(a.customer_id),
        "customer_name": a.customer.full_name,
        "agent_membership": str(a.agent_membership_id),
        "agent_name": a.agent_membership.user.full_name,
        "scheduled_start": a.scheduled_start.isoformat(),
        "scheduled_end": a.scheduled_end.isoformat(),
        "status": a.status,
        "customer_feedback": a.customer_feedback,
        "agent_report": a.agent_report,
        "created_at": a.created_at.isoformat(),
    }


@router.get("")
async def get_appointments(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    ctx: RequestContext = Depends(get_current_context),
):
    def _op():
        from apps.appointments.services import list_appointments
        from common.pagination import paginate_queryset

        qs = list_appointments(user=ctx.user, agency_id=ctx.agency_id)
        return paginate_queryset(qs, page=page, page_size=page_size, serializer_fn=_ser_appt)

    items, meta = await run_django(_op, agency_id=ctx.agency_id)
    return ok(items, meta=meta)


@router.post("/request-public", status_code=201)
@rate_limit(scope="public_viewing_request", limit=5, window_seconds=3600)
async def request_public(body: PublicAppointmentBody, ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.appointments.services import request_public_viewing

        appt = request_public_viewing(user=ctx.user, **body.model_dump())
        return _ser_appt(appt)

    return ok(await run_django(_op))


@router.post("", status_code=201)
@rate_limit(scope="agency_appointment_create", limit=60, window_seconds=60)
async def create_appointment(
    body: AgencyAppointmentBody, ctx: RequestContext = Depends(require_agency_context)
):
    def _op():
        from apps.appointments.services import create_agency_appointment

        data = body.model_dump()
        st = data.pop("status")
        appt = create_agency_appointment(user=ctx.user, agency_id=ctx.agency_id, status_value=st, **data)
        return _ser_appt(appt)

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/{appt_id}/confirm")
async def confirm_appointment(appt_id: UUID, ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.appointments.models import ViewingAppointment
        from apps.appointments.services import transition_appointment_status

        appt = transition_appointment_status(
            user=ctx.user,
            agency_id=ctx.agency_id,
            appt_id=appt_id,
            new_status=ViewingAppointment.Status.CONFIRMED,
        )
        return _ser_appt(appt)

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.patch("/{appt_id}/status")
async def update_appointment_status(
    appt_id: UUID, body: AppointmentStatusBody, ctx: RequestContext = Depends(require_agency_context)
):
    def _op():
        from apps.appointments.services import transition_appointment_status

        appt = transition_appointment_status(
            user=ctx.user,
            agency_id=ctx.agency_id,
            appt_id=appt_id,
            new_status=body.status,
            agent_report=body.agent_report,
        )
        return _ser_appt(appt)

    return ok(await run_django(_op, agency_id=ctx.agency_id))

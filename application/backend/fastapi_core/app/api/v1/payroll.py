from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.core.django_bridge import run_django
from app.dependencies.auth import RequestContext, require_agency_context
from app.schemas.common import ok

router = APIRouter(prefix="/payroll", tags=["Payroll & Payslips"])


class PayrollCycleCreateBody(BaseModel):
    title: str
    period_start: datetime
    period_end: datetime


class PayrollCycleStatusBody(BaseModel):
    status: str


def _ser_cycle(c) -> dict:
    return {
        "id": str(c.id),
        "title": c.title,
        "period_start": c.period_start.isoformat(),
        "period_end": c.period_end.isoformat(),
        "status": c.status,
        "payslips": [
            {
                "id": str(ps.id),
                "employee_code": ps.employee.employee_code,
                "employee_name": ps.employee.membership.user.full_name,
                "base_salary_amount": str(ps.base_salary_amount),
                "commission_amount": str(ps.commission_amount),
                "tax_amount": str(ps.tax_amount),
                "net_payable": str(ps.net_payable),
                "status": ps.status,
                "items": [
                    {
                        "id": str(it.id),
                        "item_type": it.item_type,
                        "description": it.description,
                        "amount": str(it.amount),
                    }
                    for it in ps.items.all()
                ],
            }
            for ps in c.payslips.all()
        ],
    }


@router.get("/cycles")
async def list_payroll_cycles_endpoint(ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.payroll.services import list_payroll_cycles

        return [_ser_cycle(c) for c in list_payroll_cycles(user=ctx.user, agency_id=ctx.agency_id)]

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/cycles", status_code=201)
async def create_payroll_cycle_endpoint(
    body: PayrollCycleCreateBody, ctx: RequestContext = Depends(require_agency_context)
):
    def _op():
        from apps.payroll.services import create_and_calculate_payroll_cycle

        c = create_and_calculate_payroll_cycle(
            user=ctx.user,
            agency_id=ctx.agency_id,
            title=body.title,
            period_start=body.period_start,
            period_end=body.period_end,
        )
        return _ser_cycle(c)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/cycles/{cycle_id}/status")
async def payroll_cycle_status_endpoint(
    cycle_id: UUID,
    body: PayrollCycleStatusBody,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.payroll.services import update_payroll_cycle_status

        c = update_payroll_cycle_status(
            user=ctx.user,
            agency_id=ctx.agency_id,
            cycle_id=cycle_id,
            status_value=body.status,
        )
        return {"id": str(c.id), "status": c.status}

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))

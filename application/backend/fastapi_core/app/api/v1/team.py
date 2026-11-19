# Path: backend/fastapi_core/app/api/v1/team.py

from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.core.django_bridge import run_django
from app.dependencies.auth import RequestContext, require_agency_context
from app.schemas.common import ok

router = APIRouter(tags=["Team, Roles & Employees"])


class MemberCreateBody(BaseModel):
    phone_number: str
    first_name: str
    last_name: str
    role_code: str = "REAL_ESTATE_AGENT"
    branch_id: Optional[UUID] = None
    email: Optional[str] = None
    password: Optional[str] = None


class MemberPatchBody(BaseModel):
    role_code: Optional[str] = None
    status: Optional[str] = None
    branch_id: Optional[UUID] = None


class OverrideItem(BaseModel):
    permission_code: str
    effect: str


class OverridesPutBody(BaseModel):
    overrides: list[OverrideItem]


class RoleCreateBody(BaseModel):
    code: str
    name: str
    permission_codes: list[str]


class EmployeeCreateBody(BaseModel):
    membership_id: UUID
    employee_code: str
    job_title: str = "مشاور املاک"
    employment_type: str = "COMMISSION_AGENT"
    hire_date: Optional[date] = None
    monthly_sales_target: Decimal = Decimal("0")
    model_type: str = "FIXED_PLUS_COMMISSION"
    base_salary: Optional[Decimal] = None
    commission_multiplier: Decimal = Decimal("1.0000")


class CompensationPlanBody(BaseModel):
    model_type: str
    currency_id: str = "IRT"
    base_salary: Decimal = Decimal("0")
    commission_multiplier: Decimal = Decimal("1.0000")
    effective_from: Optional[date] = None


@router.get("/team/members")
async def list_team_members(ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.agencies.services import list_agency_members

        return [
            {
                "id": str(m.id),
                "user_id": str(m.user_id),
                "full_name": m.user.full_name,
                "phone_number": m.user.phone_number,
                "email": m.user.email,
                "role_code": m.role.code,
                "role_name": m.role.name,
                "branch_id": str(m.branch_id) if m.branch_id else None,
                "branch_name": m.branch.name if m.branch else None,
                "status": m.status,
                "joined_at": m.joined_at.isoformat(),
                "overrides": [
                    {"permission_code": ov.permission_id, "effect": ov.effect}
                    for ov in m.permission_overrides.all()
                ],
            }
            for m in list_agency_members(actor=ctx.user, agency_id=ctx.agency_id)
        ]

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/team/members", status_code=201)
async def create_team_member(body: MemberCreateBody, ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.accounts.services import add_agency_member

        m = add_agency_member(actor=ctx.user, agency_id=ctx.agency_id, **body.model_dump())
        return {"id": str(m.id), "full_name": m.user.full_name, "role_code": m.role.code}

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.patch("/team/members/{membership_id}")
async def patch_team_member(
    membership_id: UUID, body: MemberPatchBody, ctx: RequestContext = Depends(require_agency_context)
):
    def _op():
        from apps.accounts.services import update_member_role_or_status

        m = update_member_role_or_status(
            actor=ctx.user,
            agency_id=ctx.agency_id,
            membership_id=membership_id,
            role_code=body.role_code,
            status_value=body.status,
            branch_id=body.branch_id,
        )
        return {"id": str(m.id), "role_code": m.role.code, "status": m.status}

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.put("/team/members/{membership_id}/overrides")
async def put_member_overrides(
    membership_id: UUID, body: OverridesPutBody, ctx: RequestContext = Depends(require_agency_context)
):
    def _op():
        from apps.accounts.services import set_membership_overrides

        m = set_membership_overrides(
            actor=ctx.user,
            agency_id=ctx.agency_id,
            membership_id=membership_id,
            overrides=[o.model_dump() for o in body.overrides],
        )
        return {"id": str(m.id), "updated": True}

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.get("/team/roles")
async def get_roles_permissions(ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.accounts.services import list_roles_and_permissions

        roles, perms = list_roles_and_permissions(ctx.agency_id)
        return {
            "roles": [
                {
                    "id": str(r.id),
                    "code": r.code,
                    "name": r.name,
                    "scope": r.scope,
                    "is_system_role": r.is_system_role,
                    "permissions": [p.code for p in r.permissions.all()],
                }
                for r in roles
            ],
            "permissions": [
                {"code": p.code, "module": p.module, "description": p.description} for p in perms
            ],
        }

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/team/roles", status_code=201)
async def create_role_endpoint(body: RoleCreateBody, ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.accounts.services import create_custom_role

        r = create_custom_role(actor=ctx.user, agency_id=ctx.agency_id, **body.model_dump())
        return {"id": str(r.id), "code": r.code, "name": r.name}

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.get("/employees")
async def list_employees_endpoint(ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.payroll.services import list_employees

        return [
            {
                "id": str(e.id),
                "membership_id": str(e.membership_id),
                "full_name": e.membership.user.full_name,
                "phone_number": e.membership.user.phone_number,
                "role_name": e.membership.role.name,
                "branch_name": e.membership.branch.name if e.membership.branch else None,
                "employee_code": e.employee_code,
                "job_title": e.job_title,
                "employment_type": e.employment_type,
                "hire_date": e.hire_date.isoformat(),
                "monthly_sales_target": str(e.monthly_sales_target),
                "is_active": e.is_active,
                "compensation_plans": [
                    {
                        "id": str(p.id),
                        "model_type": p.model_type,
                        "base_salary": str(p.base_salary),
                        "commission_multiplier": str(p.commission_multiplier),
                        "effective_from": p.effective_from.isoformat(),
                        "is_active": p.is_active,
                    }
                    for p in e.compensation_plans.all()
                ],
            }
            for e in list_employees(user=ctx.user, agency_id=ctx.agency_id)
        ]

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/employees", status_code=201)
async def create_employee_endpoint(body: EmployeeCreateBody, ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.payroll.services import create_employee_profile

        e = create_employee_profile(user=ctx.user, agency_id=ctx.agency_id, data=body.model_dump())
        return {"id": str(e.id), "employee_code": e.employee_code}

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/employees/{employee_id}/compensation-plans", status_code=201)
async def create_compensation_plan_endpoint(
    employee_id: UUID, body: CompensationPlanBody, ctx: RequestContext = Depends(require_agency_context)
):
    def _op():
        from apps.payroll.services import create_compensation_plan

        p = create_compensation_plan(
            user=ctx.user, agency_id=ctx.agency_id, employee_id=employee_id, data=body.model_dump()
        )
        return {"id": str(p.id), "model_type": p.model_type, "base_salary": str(p.base_salary)}

    return ok(await run_django(_op, agency_id=ctx.agency_id))

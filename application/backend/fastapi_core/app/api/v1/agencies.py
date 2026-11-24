from decimal import Decimal
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from app.core.django_bridge import run_django
from app.dependencies.auth import RequestContext, get_current_context, get_optional_context
from app.schemas.common import ok

router = APIRouter(prefix="/agencies", tags=["Agencies, Branches & Policies"])


class AgencyCreateBody(BaseModel):
    name: str
    slug: str
    registration_number: str = ""
    tax_id: str = ""
    phone: str = ""
    email: str = ""
    description: str = ""
    country_id: str = "IR"
    default_currency_id: str = "IRT"
    default_calendar: str = "jalali"
    timezone: str = "Asia/Tehran"
    area_unit: str = "SQM"


class AgencyStatusBody(BaseModel):
    status: str


class AgencyPatchBody(BaseModel):
    name: Optional[str] = None
    registration_number: Optional[str] = None
    tax_id: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    description: Optional[str] = None
    country_id: Optional[str] = None
    default_currency_id: Optional[str] = None
    default_calendar: Optional[str] = None
    timezone: Optional[str] = None
    area_unit: Optional[str] = None
    status: Optional[str] = None


class AccessPolicyPatchBody(BaseModel):
    property_view_scope: Optional[str] = None
    property_edit_scope: Optional[str] = None
    customer_view_scope: Optional[str] = None
    customer_edit_scope: Optional[str] = None
    owner_pii_visibility: Optional[str] = None
    negotiation_visibility: Optional[str] = None
    contract_visibility: Optional[str] = None
    financial_visibility: Optional[str] = None
    commission_visibility: Optional[str] = None
    agent_performance_visibility: Optional[str] = None


class BranchCreateBody(BaseModel):
    name: str
    code: str
    country_id: str = "IR"
    province: str = ""
    city: str = ""
    address: str = ""
    phone: str = ""
    is_main: bool = False


class BranchPatchBody(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    country_id: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    is_main: Optional[bool] = None
    is_active: Optional[bool] = None


class CooperationCreateBody(BaseModel):
    provider_agency_id: UUID
    default_split_percent: Decimal = Decimal("50.00")


class CooperationRespondBody(BaseModel):
    status: str


def _ser_agency(a) -> dict:
    return {
        "id": str(a.id),
        "name": a.name,
        "slug": a.slug,
        "registration_number": a.registration_number,
        "tax_id": a.tax_id,
        "phone": a.phone,
        "email": a.email,
        "description": a.description,
        "country": a.country_id,
        "default_currency": a.default_currency_id,
        "default_calendar": a.default_calendar,
        "timezone": a.timezone,
        "area_unit": a.area_unit,
        "status": a.status,
        "owner_name": a.owner_user.full_name,
        "created_at": a.created_at.isoformat(),
    }


def _ser_policy(p) -> dict:
    return {
        "id": str(p.id),
        "agency_id": str(p.agency_id),
        "property_view_scope": p.property_view_scope,
        "property_edit_scope": p.property_edit_scope,
        "customer_view_scope": p.customer_view_scope,
        "customer_edit_scope": p.customer_edit_scope,
        "owner_pii_visibility": p.owner_pii_visibility,
        "negotiation_visibility": p.negotiation_visibility,
        "contract_visibility": p.contract_visibility,
        "financial_visibility": p.financial_visibility,
        "commission_visibility": p.commission_visibility,
        "agent_performance_visibility": p.agent_performance_visibility,
    }


@router.get("")
async def list_agencies(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    ctx: RequestContext = Depends(get_optional_context),
):
    def _op():
        from apps.agencies.services import list_agencies_for_user
        from common.pagination import paginate_queryset

        qs = list_agencies_for_user(ctx.user)
        return paginate_queryset(qs, page=page, page_size=page_size, serializer_fn=_ser_agency)

    items, meta = await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None)
    return ok(items, meta=meta)


@router.post("", status_code=201)
async def create_agency_endpoint(body: AgencyCreateBody, ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.agencies.services import create_agency

        data = body.model_dump()
        tz = data.pop("timezone")
        a = create_agency(owner=ctx.user, timezone_str=tz, **data)
        return _ser_agency(a)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.get("/{agency_id}")
async def get_agency(agency_id: UUID, ctx: RequestContext = Depends(get_optional_context)):
    def _op():
        from apps.agencies.services import get_agency_for_user

        return _ser_agency(get_agency_for_user(ctx.user, agency_id))

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.patch("/{agency_id}")
async def patch_agency_endpoint(
    agency_id: UUID, body: AgencyPatchBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.agencies.services import update_agency

        return _ser_agency(update_agency(actor=ctx.user, agency_id=agency_id, data=body.model_dump(exclude_none=True)))

    return ok(await run_django(_op, agency_id=agency_id))


@router.delete("/{agency_id}")
async def delete_agency_endpoint(agency_id: UUID, ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.agencies.services import soft_delete_agency

        a = soft_delete_agency(actor=ctx.user, agency_id=agency_id)
        return {"id": str(a.id), "archived": True}

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/{agency_id}/status")
async def update_agency_status_endpoint(
    agency_id: UUID, body: AgencyStatusBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.agencies.services import update_agency_status

        return _ser_agency(update_agency_status(actor=ctx.user, agency_id=agency_id, new_status=body.status))

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.get("/{agency_id}/access-policy")
async def get_policy(agency_id: UUID, ctx: RequestContext = Depends(get_current_context)):
    from common.permissions import is_super_admin
    from fastapi import HTTPException
    if not is_super_admin(ctx.user):
        raise HTTPException(status_code=403, detail="این بخش فقط در اختیار مدیر کل است.")
    def _op():
        from apps.agencies.services import get_access_policy

        return _ser_policy(get_access_policy(actor=ctx.user, agency_id=agency_id))

    return ok(await run_django(_op, agency_id=agency_id))


@router.patch("/{agency_id}/access-policy")
async def patch_policy(
    agency_id: UUID, body: AccessPolicyPatchBody, ctx: RequestContext = Depends(get_current_context)
):
    from common.permissions import is_super_admin
    from fastapi import HTTPException
    if not is_super_admin(ctx.user):
        raise HTTPException(status_code=403, detail="این بخش فقط در اختیار مدیر کل است.")
    def _op():
        from apps.agencies.services import update_access_policy

        return _ser_policy(
            update_access_policy(actor=ctx.user, agency_id=agency_id, updates=body.model_dump(exclude_none=True))
        )

    return ok(await run_django(_op, agency_id=agency_id))


@router.get("/{agency_id}/branches")
async def list_branches_endpoint(
    agency_id: UUID,
    include_inactive: bool = Query(default=False),
    ctx: RequestContext = Depends(get_optional_context),
):
    def _op():
        from apps.agencies.services import list_branches

        return [
            {
                "id": str(b.id),
                "name": b.name,
                "code": b.code,
                "country": b.country_id,
                "province": b.province,
                "city": b.city,
                "address": b.address,
                "phone": b.phone,
                "is_main": b.is_main,
                "is_active": b.is_active,
            }
            for b in list_branches(actor=ctx.user, agency_id=agency_id, include_inactive=include_inactive)
        ]

    return ok(await run_django(_op, agency_id=agency_id))


@router.post("/{agency_id}/branches", status_code=201)
async def create_branch_endpoint(
    agency_id: UUID, body: BranchCreateBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.agencies.services import create_branch

        b = create_branch(actor=ctx.user, agency_id=agency_id, data=body.model_dump())
        return {
            "id": str(b.id),
            "name": b.name,
            "code": b.code,
            "city": b.city,
            "address": b.address,
            "phone": b.phone,
            "is_main": b.is_main,
            "is_active": b.is_active,
        }

    return ok(await run_django(_op, agency_id=agency_id))


@router.patch("/{agency_id}/branches/{branch_id}")
async def patch_branch_endpoint(
    agency_id: UUID, branch_id: UUID, body: BranchPatchBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.agencies.services import update_branch

        b = update_branch(actor=ctx.user, agency_id=agency_id, branch_id=branch_id, data=body.model_dump(exclude_none=True))
        return {
            "id": str(b.id),
            "name": b.name,
            "code": b.code,
            "province": b.province,
            "city": b.city,
            "address": b.address,
            "phone": b.phone,
            "is_main": b.is_main,
            "is_active": b.is_active,
        }

    return ok(await run_django(_op, agency_id=agency_id))


@router.delete("/{agency_id}/branches/{branch_id}")
async def delete_branch_endpoint(
    agency_id: UUID, branch_id: UUID, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.agencies.services import soft_delete_branch

        b = soft_delete_branch(actor=ctx.user, agency_id=agency_id, branch_id=branch_id)
        return {"id": str(b.id), "is_active": b.is_active}

    return ok(await run_django(_op, agency_id=agency_id))


@router.get("/{agency_id}/members")
async def list_members_endpoint(agency_id: UUID, ctx: RequestContext = Depends(get_current_context)):
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
            }
            for m in list_agency_members(actor=ctx.user, agency_id=agency_id)
        ]

    return ok(await run_django(_op, agency_id=agency_id))


@router.get("/{agency_id}/cooperations")
async def list_cooperations_endpoint(agency_id: UUID, ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.agencies.services import list_cooperations

        return [
            {
                "id": str(c.id),
                "requester_agency_id": str(c.requester_agency_id),
                "requester_agency_name": c.requester_agency.name,
                "provider_agency_id": str(c.provider_agency_id),
                "provider_agency_name": c.provider_agency.name,
                "default_split_percent": str(c.default_split_percent),
                "status": c.status,
            }
            for c in list_cooperations(actor=ctx.user, agency_id=agency_id)
        ]

    return ok(await run_django(_op, agency_id=agency_id))


@router.post("/{agency_id}/cooperations", status_code=201)
async def create_cooperation_endpoint(
    agency_id: UUID, body: CooperationCreateBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.agencies.services import request_cooperation

        c = request_cooperation(
            actor=ctx.user,
            requester_agency_id=agency_id,
            provider_agency_id=body.provider_agency_id,
            split_percent=body.default_split_percent,
        )
        return {"id": str(c.id), "status": c.status}

    return ok(await run_django(_op, agency_id=agency_id))


@router.post("/{agency_id}/cooperations/{coop_id}/respond")
async def respond_cooperation_endpoint(
    agency_id: UUID,
    coop_id: UUID,
    body: CooperationRespondBody,
    ctx: RequestContext = Depends(get_current_context),
):
    def _op():
        from apps.agencies.services import respond_cooperation

        c = respond_cooperation(actor=ctx.user, agency_id=agency_id, coop_id=coop_id, status_value=body.status)
        return {"id": str(c.id), "status": c.status}

    return ok(await run_django(_op, agency_id=agency_id))

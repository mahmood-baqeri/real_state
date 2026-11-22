from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from app.core.django_bridge import run_django
from app.dependencies.auth import RequestContext, get_current_context
from app.schemas.common import ok

router = APIRouter(prefix="/admin", tags=["System Super Admin"])


class UserStatusBody(BaseModel):
    status: str


class AdminUserCreateBody(BaseModel):
    phone_number: str
    first_name: str = ""
    last_name: str = ""
    email: Optional[str] = None
    password: Optional[str] = None
    platform_role: str = "AGENCY_USER"
    agency_id: Optional[UUID] = None
    branch_id: Optional[UUID] = None
    role_code: Optional[str] = None


class AdminUserPatchBody(BaseModel):
    phone_number: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    platform_role: Optional[str] = None
    status: Optional[str] = None


class AdminMembershipAssignBody(BaseModel):
    agency_id: UUID
    role_code: str
    branch_id: Optional[UUID] = None
    status: str = "ACTIVE"


class AdminSubscriptionCreateBody(BaseModel):
    agency_id: UUID
    plan_code: str
    billing_cycle: str = "MONTHLY"
    duration_days: int = 30
    status: str = "ACTIVE"


class AdminSubscriptionPatchBody(BaseModel):
    plan_code: Optional[str] = None
    billing_cycle: Optional[str] = None
    status: Optional[str] = None
    extend_days: Optional[int] = None


def _ser_admin_user(u) -> dict:
    return {
        "id": str(u.id),
        "phone_number": u.phone_number,
        "email": u.email,
        "first_name": u.first_name,
        "last_name": u.last_name,
        "full_name": u.full_name,
        "platform_role": u.platform_role,
        "status": u.status,
        "is_active": u.is_active,
        "date_joined": u.date_joined.isoformat(),
        "agencies": [m.agency.name for m in u.memberships.all()],
        "memberships": [
            {
                "id": str(m.id),
                "agency_id": str(m.agency_id),
                "agency_name": m.agency.name,
                "role_code": m.role.code,
                "role_name": m.role.name,
                "branch_id": str(m.branch_id) if m.branch_id else None,
                "branch_name": m.branch.name if m.branch else None,
                "status": m.status,
            }
            for m in u.memberships.all()
        ],
    }


@router.get("/users")
async def admin_list_users(
    q: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    ctx: RequestContext = Depends(get_current_context),
):
    def _op():
        from apps.accounts.services import list_all_users_for_admin
        from common.pagination import paginate_queryset

        qs = list_all_users_for_admin(ctx.user, q=q, status=status)
        items, meta = paginate_queryset(qs, page=page, page_size=page_size, serializer_fn=_ser_admin_user)
        return items, meta

    items, meta = await run_django(_op)
    return ok(items, meta=meta)


@router.post("/users", status_code=201)
async def admin_create_user(body: AdminUserCreateBody, ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.accounts.services import create_user_by_admin

        u = create_user_by_admin(actor=ctx.user, data=body.model_dump())
        return _ser_admin_user(u)

    return ok(await run_django(_op))


@router.patch("/users/{user_id}")
async def admin_patch_user(
    user_id: UUID, body: AdminUserPatchBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.accounts.services import update_user_by_admin

        u = update_user_by_admin(actor=ctx.user, target_user_id=user_id, data=body.model_dump(exclude_none=True))
        return _ser_admin_user(u)

    return ok(await run_django(_op))


@router.delete("/users/{user_id}")
async def admin_delete_user(user_id: UUID, ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.accounts.services import soft_delete_user_by_admin

        u = soft_delete_user_by_admin(actor=ctx.user, target_user_id=user_id)
        return {"id": str(u.id), "status": u.status, "deleted": True}

    return ok(await run_django(_op))


@router.post("/users/{user_id}/memberships", status_code=201)
async def admin_assign_membership(
    user_id: UUID, body: AdminMembershipAssignBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.accounts.services import assign_user_membership_by_admin

        m = assign_user_membership_by_admin(
            actor=ctx.user,
            target_user_id=user_id,
            agency_id=body.agency_id,
            role_code=body.role_code,
            branch_id=body.branch_id,
            status_value=body.status,
        )
        return {
            "id": str(m.id),
            "agency_id": str(m.agency_id),
            "role_code": m.role.code,
            "branch_id": str(m.branch_id) if m.branch_id else None,
            "status": m.status,
        }

    return ok(await run_django(_op))


@router.patch("/users/{user_id}/status")
async def admin_update_user_status(
    user_id: UUID,
    body: UserStatusBody,
    ctx: RequestContext = Depends(get_current_context),
):
    def _op():
        from apps.accounts.services import update_user_status_by_admin

        u = update_user_status_by_admin(ctx.user, user_id, body.status)
        return {"id": str(u.id), "status": u.status}

    return ok(await run_django(_op))


@router.get("/subscriptions")
async def admin_list_subscriptions(ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.subscriptions.services import list_agency_subscriptions

        subs = list_agency_subscriptions(user=ctx.user, agency_id=None)
        return [
            {
                "id": str(s.id),
                "agency_id": str(s.agency_id),
                "agency_name": s.agency.name,
                "plan_code": s.plan.code,
                "plan_name": s.plan.name_fa,
                "billing_cycle": s.billing_cycle,
                "status": s.status,
                "starts_at": s.starts_at.isoformat(),
                "expires_at": s.expires_at.isoformat(),
            }
            for s in subs
        ]

    return ok(await run_django(_op))


@router.post("/subscriptions", status_code=201)
async def admin_create_subscription(
    body: AdminSubscriptionCreateBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.subscriptions.services import assign_or_create_agency_subscription

        s = assign_or_create_agency_subscription(actor=ctx.user, data=body.model_dump())
        return {
            "id": str(s.id),
            "agency_id": str(s.agency_id),
            "agency_name": s.agency.name,
            "plan_code": s.plan.code,
            "plan_name": s.plan.name_fa,
            "billing_cycle": s.billing_cycle,
            "status": s.status,
            "starts_at": s.starts_at.isoformat(),
            "expires_at": s.expires_at.isoformat(),
        }

    return ok(await run_django(_op))


@router.patch("/subscriptions/{sub_id}")
async def admin_patch_subscription(
    sub_id: UUID, body: AdminSubscriptionPatchBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.subscriptions.services import update_agency_subscription

        s = update_agency_subscription(actor=ctx.user, sub_id=sub_id, data=body.model_dump(exclude_none=True))
        return {
            "id": str(s.id),
            "agency_id": str(s.agency_id),
            "agency_name": s.agency.name,
            "plan_code": s.plan.code,
            "plan_name": s.plan.name_fa,
            "billing_cycle": s.billing_cycle,
            "status": s.status,
            "starts_at": s.starts_at.isoformat(),
            "expires_at": s.expires_at.isoformat(),
        }

    return ok(await run_django(_op))

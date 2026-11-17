from uuid import UUID
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from app.core.django_bridge import run_django
from app.dependencies.auth import RequestContext, get_current_context
from app.schemas.common import ok

router = APIRouter(prefix="/admin", tags=["System Super Admin"])


class UserStatusBody(BaseModel):
    status: str


@router.get("/users")
async def admin_list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    ctx: RequestContext = Depends(get_current_context),
):
    def _op():
        from apps.accounts.services import list_all_users_for_admin
        from common.pagination import paginate_queryset

        qs = list_all_users_for_admin(ctx.user)

        def _ser(u):
            return {
                "id": str(u.id),
                "phone_number": u.phone_number,
                "email": u.email,
                "full_name": u.full_name,
                "platform_role": u.platform_role,
                "status": u.status,
                "date_joined": u.date_joined.isoformat(),
                "agencies": [m.agency.name for m in u.memberships.all()],
            }

        items, meta = paginate_queryset(qs, page=page, page_size=page_size, serializer_fn=_ser)
        return items, meta

    items, meta = await run_django(_op)
    return ok(items, meta=meta)


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

from typing import Optional
from fastapi import APIRouter, Depends, Query
from app.core.django_bridge import run_django
from app.dependencies.auth import RequestContext, get_current_context
from app.schemas.common import ok

router = APIRouter(tags=["Reports & Audit Logs"])


@router.get("/reports/dashboard")
async def dashboard_summary_endpoint(ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.reports.services import get_dashboard_summary

        return get_dashboard_summary(user=ctx.user, agency_id=ctx.agency_id)

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.get("/reports/analytics")
async def analytics_endpoint(ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.reports.services import get_agency_analytics

        return get_agency_analytics(user=ctx.user, agency_id=ctx.agency_id)

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.get("/audit/logs")
async def audit_logs_endpoint(
    resource_type: Optional[str] = None,
    action: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
    ctx: RequestContext = Depends(get_current_context),
):
    def _op():
        from apps.audit.services import list_audit_logs
        from common.pagination import paginate_queryset

        qs = list_audit_logs(
            user=ctx.user,
            agency_id=ctx.agency_id,
            resource_type=resource_type,
            action=action,
        )
        return paginate_queryset(
            qs,
            page=page,
            page_size=page_size,
            serializer_fn=lambda l: {
                "id": str(l.id),
                "action": l.action,
                "resource_type": l.resource_type,
                "resource_id": l.resource_id,
                "actor_name": l.actor.full_name if l.actor else "سیستم",
                "actor_phone": l.actor.phone_number if l.actor else None,
                "ip_address": l.ip_address,
                "before_state": l.before_state,
                "after_state": l.after_state,
                "metadata": l.metadata,
                "created_at": l.created_at.isoformat(),
            },
        )

    items, meta = await run_django(_op, agency_id=ctx.agency_id)
    return ok(items, meta=meta)

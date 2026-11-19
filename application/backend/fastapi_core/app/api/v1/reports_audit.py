import json
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile
from pydantic import BaseModel
from app.core.django_bridge import run_django
from app.dependencies.auth import RequestContext, get_current_context, require_agency_context
from app.schemas.common import ok

router = APIRouter(tags=["Reports & Audit Logs"])


class DashboardLayoutBody(BaseModel):
    widgets: Optional[list[dict]] = None
    default_period_days: Optional[int] = None


class OnboardingBody(BaseModel):
    toggle_step_key: Optional[str] = None
    dismissed: Optional[bool] = None


@router.get("/reports/dashboard")
async def dashboard_summary_endpoint(
    period_days: int = Query(default=30, ge=1, le=365),
    ctx: RequestContext = Depends(get_current_context),
):
    def _op():
        from apps.reports.services import get_dashboard_summary

        return get_dashboard_summary(
            user=ctx.user, agency_id=ctx.agency_id, period_days=period_days
        )

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.get("/reports/analytics")
async def analytics_endpoint(
    period_days: int = Query(default=30, ge=1, le=365),
    branch_id: Optional[UUID] = None,
    agent_membership_id: Optional[UUID] = None,
    ctx: RequestContext = Depends(get_current_context),
):
    def _op():
        from apps.reports.services import get_agency_analytics

        return get_agency_analytics(
            user=ctx.user,
            agency_id=ctx.agency_id,
            period_days=period_days,
            branch_id=branch_id,
            agent_membership_id=agent_membership_id,
        )

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.get("/reports/operations-center")
async def operations_center_endpoint(ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.reports.services import get_operations_center

        return get_operations_center(user=ctx.user, agency_id=ctx.agency_id)

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.get("/reports/dashboard-layout")
async def get_dashboard_layout_endpoint(ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.reports.services import get_or_save_dashboard_layout

        return get_or_save_dashboard_layout(user=ctx.user, agency_id=ctx.agency_id)

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.put("/reports/dashboard-layout")
async def put_dashboard_layout_endpoint(
    body: DashboardLayoutBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.reports.services import get_or_save_dashboard_layout

        return get_or_save_dashboard_layout(
            user=ctx.user,
            agency_id=ctx.agency_id,
            widgets=body.widgets,
            default_period_days=body.default_period_days,
        )

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.get("/reports/onboarding")
async def get_onboarding_endpoint(ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.reports.services import get_or_update_onboarding

        return get_or_update_onboarding(user=ctx.user, agency_id=ctx.agency_id)

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/reports/onboarding")
async def update_onboarding_endpoint(
    body: OnboardingBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.reports.services import get_or_update_onboarding

        return get_or_update_onboarding(
            user=ctx.user,
            agency_id=ctx.agency_id,
            toggle_step_key=body.toggle_step_key,
            dismissed=body.dismissed,
        )

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/reports/import")
async def import_spreadsheet_endpoint(
    file: UploadFile = File(...),
    module: str = Form(...),
    column_mapping_json: str = Form("{}"),
    commit: bool = Form(False),
    ctx: RequestContext = Depends(require_agency_context),
):
    content = await file.read()
    try:
        mapping = json.loads(column_mapping_json or "{}")
    except Exception:
        mapping = {}

    def _op():
        from apps.reports.services import preview_or_execute_import

        return preview_or_execute_import(
            user=ctx.user,
            agency_id=ctx.agency_id,
            module=module,
            filename=file.filename or "import.xlsx",
            content=content,
            column_mapping=mapping if isinstance(mapping, dict) else {},
            commit=commit,
        )

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.get("/reports/export")
async def export_workbook_endpoint(
    module: str = Query(..., description="properties | customers | accounting"),
    fmt: str = Query(default="xlsx", pattern="^(xlsx|csv)$"),
    ctx: RequestContext = Depends(get_current_context),
):
    def _op():
        from apps.reports.services import export_module_workbook

        return export_module_workbook(
            user=ctx.user, agency_id=ctx.agency_id, module=module, fmt=fmt
        )

    raw, media_type, fname = await run_django(_op, agency_id=ctx.agency_id)
    return Response(
        content=raw,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


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

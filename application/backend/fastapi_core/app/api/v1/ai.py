# Path: backend/fastapi_core/app/api/v1/ai.py

from uuid import UUID
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from app.core.django_bridge import run_django
from app.dependencies.auth import RequestContext, get_current_context, require_agency_context
from app.schemas.common import ok

router = APIRouter(prefix="/ai", tags=["Tenant-Isolated AI Assistant"])


class PropertyCopyBody(BaseModel):
    property_id: UUID
    tone: str = "FORMAL"


class CrmSummaryBody(BaseModel):
    customer_id: UUID


class SeoDraftBody(BaseModel):
    title: str = Field(min_length=2)
    body_excerpt: str = ""
    target_city: str = ""


@router.post("/property-copy")
async def property_copy_endpoint(body: PropertyCopyBody, ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.ai_assistant.services import draft_property_listing

        return draft_property_listing(
            user=ctx.user, agency_id=ctx.agency_id, property_id=body.property_id, tone=body.tone
        )

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/crm-summary")
async def crm_summary_endpoint(body: CrmSummaryBody, ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.ai_assistant.services import summarize_customer_crm

        return summarize_customer_crm(user=ctx.user, agency_id=ctx.agency_id, customer_id=body.customer_id)

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/seo-draft")
async def seo_draft_endpoint(body: SeoDraftBody, ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.ai_assistant.services import draft_seo_metadata

        return draft_seo_metadata(
            user=ctx.user,
            agency_id=ctx.agency_id,
            title=body.title,
            body_excerpt=body.body_excerpt,
            target_city=body.target_city,
        )

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.get("/portfolio-insights")
async def portfolio_insights_endpoint(ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.ai_assistant.services import get_portfolio_insights

        return get_portfolio_insights(user=ctx.user, agency_id=ctx.agency_id)

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.get("/logs")
async def ai_logs_endpoint(ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.ai_assistant.services import list_ai_logs

        return [
            {
                "id": str(log.id),
                "tool_type": log.tool_type,
                "prompt_summary": log.prompt_summary,
                "provider": log.provider,
                "user_name": log.user.full_name,
                "draft_output": log.draft_output,
                "created_at": log.created_at.isoformat(),
            }
            for log in list_ai_logs(user=ctx.user, agency_id=ctx.agency_id)
        ]

    return ok(await run_django(_op, agency_id=ctx.agency_id))

from typing import Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from app.core.django_bridge import run_django
from app.dependencies.auth import RequestContext, get_current_context, require_agency_context
from app.schemas.common import ok

router = APIRouter(prefix="/ai", tags=["Tenant-Isolated AI Assistant (GapGPT)"])


class AssistantChatBody(BaseModel):
    message: str = Field(min_length=1, max_length=3000)
    task_mode: str = "GENERAL"
    model: Optional[str] = None
    history: list[dict[str, Any]] = []


class NegotiationSummaryBody(BaseModel):
    negotiation_id: UUID
    model: Optional[str] = None


class PropertyCopyBody(BaseModel):
    property_id: UUID
    tone: str = "FORMAL"


class CrmSummaryBody(BaseModel):
    customer_id: UUID


class SeoDraftBody(BaseModel):
    title: str = Field(min_length=2)
    body_excerpt: str = ""
    target_city: str = ""


class RssTopicsBody(BaseModel):
    feed_url: Optional[str] = None


@router.get("/status")
async def ai_status_endpoint(ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.ai_assistant.services import get_ai_status

        return get_ai_status(user=ctx.user, agency_id=ctx.agency_id)

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/assistant/chat")
async def assistant_chat_endpoint(
    body: AssistantChatBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.ai_assistant.services import chat_with_assistant

        return chat_with_assistant(
            user=ctx.user,
            agency_id=ctx.agency_id,
            message=body.message,
            task_mode=body.task_mode,
            model=body.model,
            history=body.history,
        )

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/negotiation-summary")
async def negotiation_summary_endpoint(
    body: NegotiationSummaryBody, ctx: RequestContext = Depends(require_agency_context)
):
    def _op():
        from apps.ai_assistant.services import summarize_negotiation_with_ai

        return summarize_negotiation_with_ai(
            user=ctx.user,
            agency_id=ctx.agency_id,
            negotiation_id=body.negotiation_id,
            model=body.model,
        )

    return ok(await run_django(_op, agency_id=ctx.agency_id))


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


@router.post("/rss-topics")
async def rss_topics_endpoint(body: RssTopicsBody, ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.ai_assistant.services import fetch_rss_topic_ideas

        return fetch_rss_topic_ideas(
            user=ctx.user,
            agency_id=ctx.agency_id,
            feed_url=body.feed_url,
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
                "model_name": log.model_name,
                "tokens_used": log.tokens_used,
                "latency_ms": log.latency_ms,
                "user_name": log.user.full_name,
                "draft_output": log.draft_output,
                "created_at": log.created_at.isoformat(),
            }
            for log in list_ai_logs(user=ctx.user, agency_id=ctx.agency_id)
        ]

    return ok(await run_django(_op, agency_id=ctx.agency_id))


class ContentTopicsBody(BaseModel):
    content_type: str = "ARTICLE"
    focus_city: str = ""
    audience: str = ""


class ContentGenerateBody(BaseModel):
    topic: str = Field(min_length=3, max_length=240)
    content_type: str = "ARTICLE"
    language: str = "fa"
    tone: str = "PROFESSIONAL"
    target_audience: str = "خریداران و سرمایه‌گذاران املاک"
    keywords: list[str] = []
    custom_instructions: str = ""
    model: Optional[str] = None


class ContentRewriteBody(BaseModel):
    title: str = ""
    content_body: str = Field(min_length=5)
    instruction: str = "بهبود خوانایی و ساختار سئو"
    tone: str = "PROFESSIONAL"
    language: str = "fa"
    keywords: list[str] = []
    model: Optional[str] = None


class SaveAiDraftBody(BaseModel):
    title: str = Field(min_length=3, max_length=240)
    slug: str = Field(min_length=2, max_length=240)
    article_type: str = "ARTICLE"
    summary: str = ""
    content_body: str = Field(min_length=10)
    language: str = "fa"
    tone: str = "PROFESSIONAL"
    target_audience: str = ""
    keywords: list[str] = []
    ai_model: str = ""
    ai_tokens_used: int = 0
    meta_title: str = ""
    meta_description: str = ""
    tags: list[str] = []


@router.get("/content/topics")
async def get_ai_content_topics_endpoint(
    content_type: str = "ARTICLE",
    focus_city: str = "",
    audience: str = "",
    ctx: RequestContext = Depends(get_current_context),
):
    def _op():
        from apps.ai_assistant.services import suggest_content_topics

        return suggest_content_topics(
            user=ctx.user,
            agency_id=ctx.agency_id,
            content_type=content_type,
            focus_city=focus_city,
            audience=audience,
        )

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/content/topics")
async def post_ai_content_topics_endpoint(
    body: ContentTopicsBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.ai_assistant.services import suggest_content_topics

        return suggest_content_topics(
            user=ctx.user,
            agency_id=ctx.agency_id,
            content_type=body.content_type,
            focus_city=body.focus_city,
            audience=body.audience,
        )

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/content/generate")
async def generate_ai_content_endpoint(
    body: ContentGenerateBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.ai_assistant.services import generate_ai_content

        return generate_ai_content(
            user=ctx.user, agency_id=ctx.agency_id, data=body.model_dump()
        )

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/content/rewrite")
async def rewrite_ai_content_endpoint(
    body: ContentRewriteBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.ai_assistant.services import rewrite_ai_content

        return rewrite_ai_content(
            user=ctx.user, agency_id=ctx.agency_id, data=body.model_dump()
        )

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/content/save-draft", status_code=201)
async def save_ai_content_draft_endpoint(
    body: SaveAiDraftBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.ai_assistant.services import save_ai_content_to_cms

        art = save_ai_content_to_cms(
            user=ctx.user, agency_id=ctx.agency_id, data=body.model_dump()
        )
        return {
            "id": str(art.id),
            "title": art.title,
            "slug": art.slug,
            "article_type": art.article_type,
            "status": art.status,
            "ai_generated": art.ai_generated,
        }

    return ok(await run_django(_op, agency_id=ctx.agency_id))


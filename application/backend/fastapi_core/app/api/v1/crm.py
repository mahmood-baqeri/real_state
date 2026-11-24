from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.core.django_bridge import run_django
from app.dependencies.auth import RequestContext, require_agency_context
from app.schemas.common import ok

router = APIRouter(prefix="/crm", tags=["CRM Pipeline & Follow-ups"])


class PipelineUpsertBody(BaseModel):
    customer_id: UUID
    stage_id: UUID
    property_id: Optional[UUID] = None
    notes: str = ""


class PipelineStageMoveBody(BaseModel):
    stage_id: UUID
    notes: Optional[str] = None


class TaskCreateBody(BaseModel):
    customer_id: UUID
    title: str
    due_at: datetime
    assigned_membership_id: Optional[UUID] = None


class TaskPatchBody(BaseModel):
    status: str


class InteractionCreateBody(BaseModel):
    customer_id: UUID
    channel: str = "NOTE"
    summary: str
    is_private: bool = True


def _ser_pipeline_item(it) -> dict:
    return {
        "id": str(it.id),
        "customer": str(it.customer_id),
        "customer_name": it.customer.full_name,
        "stage": str(it.stage_id),
        "stage_code": it.stage.code,
        "stage_name": it.stage.name,
        "property": str(it.property_id) if it.property_id else None,
        "property_title": it.property.title if it.property else None,
        "assigned_agent_name": it.assigned_membership.user.full_name if it.assigned_membership else None,
        "notes": it.notes,
        "updated_at": it.updated_at.isoformat(),
    }


@router.get("/stages")
async def get_stages(ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.crm.services import list_pipeline_stages

        return [
            {
                "id": str(s.id),
                "code": s.code,
                "name": s.name,
                "sort_order": s.sort_order,
                "is_terminal_won": s.is_terminal_won,
                "is_terminal_lost": s.is_terminal_lost,
            }
            for s in list_pipeline_stages(ctx.agency_id)
        ]

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.get("/pipeline")
async def get_pipeline(ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.crm.services import list_pipeline_items

        return [_ser_pipeline_item(it) for it in list_pipeline_items(user=ctx.user, agency_id=ctx.agency_id)]

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/pipeline", status_code=201)
async def upsert_pipeline(body: PipelineUpsertBody, ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.crm.services import upsert_pipeline_item

        it = upsert_pipeline_item(user=ctx.user, agency_id=ctx.agency_id, **body.model_dump())
        return _ser_pipeline_item(it)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.patch("/pipeline/{item_id}")
async def move_pipeline_stage(
    item_id: UUID, body: PipelineStageMoveBody, ctx: RequestContext = Depends(require_agency_context)
):
    def _op():
        from apps.crm.services import move_pipeline_item_stage

        it = move_pipeline_item_stage(
            user=ctx.user, agency_id=ctx.agency_id, item_id=item_id, stage_id=body.stage_id, notes=body.notes
        )
        return _ser_pipeline_item(it)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.get("/tasks")
async def get_tasks(ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.crm.services import list_follow_up_tasks

        return [
            {
                "id": str(t.id),
                "customer": str(t.customer_id),
                "customer_name": t.customer.full_name,
                "agent_name": t.assigned_membership.user.full_name,
                "title": t.title,
                "due_at": t.due_at.isoformat(),
                "status": t.status,
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            }
            for t in list_follow_up_tasks(user=ctx.user, agency_id=ctx.agency_id)
        ]

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/tasks", status_code=201)
async def post_task(body: TaskCreateBody, ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.crm.services import create_follow_up_task

        t = create_follow_up_task(user=ctx.user, agency_id=ctx.agency_id, **body.model_dump())
        return {"id": str(t.id), "title": t.title, "status": t.status}

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.patch("/tasks/{task_id}")
async def patch_task(task_id: UUID, body: TaskPatchBody, ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.crm.services import update_follow_up_task_status

        t = update_follow_up_task_status(
            user=ctx.user, agency_id=ctx.agency_id, task_id=task_id, status_value=body.status
        )
        return {"id": str(t.id), "status": t.status}

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.get("/interactions")
async def get_interactions(
    customer_id: Optional[UUID] = None, ctx: RequestContext = Depends(require_agency_context)
):
    def _op():
        from apps.crm.services import list_interactions

        return [
            {
                "id": str(i.id),
                "customer_id": str(i.customer_id),
                "customer_name": i.customer.full_name,
                "agent_name": i.membership.user.full_name if i.membership else None,
                "channel": i.channel,
                "summary": i.summary,
                "is_private": i.is_private,
                "created_at": i.created_at.isoformat(),
            }
            for i in list_interactions(user=ctx.user, agency_id=ctx.agency_id, customer_id=customer_id)
        ]

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/interactions", status_code=201)
async def post_interaction(body: InteractionCreateBody, ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.crm.services import add_interaction_log

        i = add_interaction_log(user=ctx.user, agency_id=ctx.agency_id, **body.model_dump())
        return {"id": str(i.id), "channel": i.channel}

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))

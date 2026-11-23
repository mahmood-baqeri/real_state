from typing import Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from app.core.django_bridge import run_django
from app.dependencies.auth import RequestContext, get_current_context, get_optional_context
from app.schemas.common import ok

router = APIRouter(prefix="/surveys", tags=["Surveys & Feedback"])


class SurveyQuestionBody(BaseModel):
    sort_order: int = 1
    question_text: str = Field(min_length=2, max_length=320)
    question_type: str
    options: list[str] = []
    is_required: bool = True


class SurveyCreateBody(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    slug: str = Field(min_length=2, max_length=120)
    description: str = ""
    target_audience: str = "CUSTOMERS"
    crm_trigger_event: str = "NONE"
    is_active: bool = True
    allow_anonymous: bool = True
    questions: list[SurveyQuestionBody]


class SurveyPatchBody(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=180)
    description: Optional[str] = None
    target_audience: Optional[str] = None
    crm_trigger_event: Optional[str] = None
    is_active: Optional[bool] = None
    allow_anonymous: Optional[bool] = None


class SurveyQuestionPatchBody(BaseModel):
    sort_order: Optional[int] = None
    question_text: Optional[str] = Field(default=None, min_length=2, max_length=320)
    question_type: Optional[str] = None
    options: Optional[list[str]] = None
    is_required: Optional[bool] = None


class SurveyQuestionsReorderBody(BaseModel):
    question_ids: list[UUID]


class SurveyAnswerSubmitBody(BaseModel):
    question_id: UUID
    answer_text: str = ""
    answer_number: Optional[float] = None
    selected_options: list[Any] = []


class SurveySubmitBody(BaseModel):
    respondent_identifier: str = ""
    respondent_name: str = ""
    answers: list[SurveyAnswerSubmitBody]


def _ser_survey(s) -> dict:
    return {
        "id": str(s.id),
        "agency_id": str(s.agency_id) if s.agency_id else None,
        "agency_name": s.agency.name if s.agency else "پلتفرم",
        "title": s.title,
        "slug": s.slug,
        "description": s.description,
        "target_audience": s.target_audience,
        "crm_trigger_event": s.crm_trigger_event,
        "is_active": s.is_active,
        "allow_anonymous": s.allow_anonymous,
        "responses_count": s.responses.count(),
        "questions": [
            {
                "id": str(q.id),
                "sort_order": q.sort_order,
                "question_text": q.question_text,
                "question_type": q.question_type,
                "options": q.options,
                "is_required": q.is_required,
            }
            for q in s.questions.all()
        ],
        "created_at": s.created_at.isoformat(),
    }


@router.get("/public/{slug}")
async def get_public_survey_endpoint(slug: str):
    def _op():
        from apps.surveys.services import get_survey_by_slug

        return _ser_survey(get_survey_by_slug(slug=slug))

    return ok(await run_django(_op))


@router.post("/public/{slug}/submit", status_code=201)
async def submit_public_survey_endpoint(
    slug: str, body: SurveySubmitBody, ctx: RequestContext = Depends(get_optional_context)
):
    def _op():
        from apps.surveys.services import submit_survey_response

        resp = submit_survey_response(
            slug=slug,
            user=ctx.user,
            respondent_identifier=body.respondent_identifier or "guest-session",
            respondent_name=body.respondent_name,
            answers=[a.model_dump() for a in body.answers],
        )
        return {"id": str(resp.id), "submitted_at": resp.submitted_at.isoformat()}

    return ok(await run_django(_op))


@router.get("")
async def list_surveys_endpoint(
    public_only: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    ctx: RequestContext = Depends(get_optional_context),
):
    def _op():
        from apps.surveys.services import list_surveys
        from common.pagination import paginate_queryset

        qs = list_surveys(user=ctx.user, agency_id=ctx.agency_id, public_only=public_only)
        return paginate_queryset(qs, page=page, page_size=page_size, serializer_fn=_ser_survey)

    items, meta = await run_django(_op, agency_id=ctx.agency_id)
    return ok(items, meta=meta)


@router.post("", status_code=201)
async def create_survey_endpoint(body: SurveyCreateBody, ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.surveys.services import create_survey

        s = create_survey(user=ctx.user, agency_id=ctx.agency_id, data=body.model_dump())
        return _ser_survey(s)

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.get("/analytics/compare")
async def compare_surveys_endpoint(ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.surveys.services import compare_surveys

        return compare_surveys(user=ctx.user, agency_id=ctx.agency_id)

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.get("/{survey_id}")
async def get_survey_detail_endpoint(survey_id: UUID, ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.surveys.services import get_survey_by_id

        return _ser_survey(get_survey_by_id(user=ctx.user, agency_id=ctx.agency_id, survey_id=survey_id))

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.patch("/{survey_id}")
async def update_survey_endpoint(
    survey_id: UUID, body: SurveyPatchBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.surveys.services import update_survey

        s = update_survey(user=ctx.user, agency_id=ctx.agency_id, survey_id=survey_id, data=body.model_dump(exclude_none=True))
        return _ser_survey(s)

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/{survey_id}/questions", status_code=201)
async def add_survey_question_endpoint(
    survey_id: UUID, body: SurveyQuestionBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.surveys.services import add_survey_question

        q = add_survey_question(user=ctx.user, agency_id=ctx.agency_id, survey_id=survey_id, data=body.model_dump())
        return {
            "id": str(q.id),
            "sort_order": q.sort_order,
            "question_text": q.question_text,
            "question_type": q.question_type,
            "options": q.options,
            "is_required": q.is_required,
        }

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.patch("/{survey_id}/questions/{question_id}")
async def update_survey_question_endpoint(
    survey_id: UUID,
    question_id: UUID,
    body: SurveyQuestionPatchBody,
    ctx: RequestContext = Depends(get_current_context),
):
    def _op():
        from apps.surveys.services import update_survey_question

        q = update_survey_question(
            user=ctx.user,
            agency_id=ctx.agency_id,
            survey_id=survey_id,
            question_id=question_id,
            data=body.model_dump(exclude_none=True),
        )
        return {
            "id": str(q.id),
            "sort_order": q.sort_order,
            "question_text": q.question_text,
            "question_type": q.question_type,
            "options": q.options,
            "is_required": q.is_required,
        }

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.delete("/{survey_id}/questions/{question_id}")
async def delete_survey_question_endpoint(
    survey_id: UUID, question_id: UUID, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.surveys.services import delete_survey_question

        delete_survey_question(user=ctx.user, agency_id=ctx.agency_id, survey_id=survey_id, question_id=question_id)
        return {"deleted": True}

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/{survey_id}/questions/reorder")
async def reorder_survey_questions_endpoint(
    survey_id: UUID, body: SurveyQuestionsReorderBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.surveys.services import reorder_survey_questions

        qs = reorder_survey_questions(
            user=ctx.user, agency_id=ctx.agency_id, survey_id=survey_id, ordered_question_ids=body.question_ids
        )
        return [
            {
                "id": str(q.id),
                "sort_order": q.sort_order,
                "question_text": q.question_text,
                "question_type": q.question_type,
                "options": q.options,
                "is_required": q.is_required,
            }
            for q in qs
        ]

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.get("/{survey_id}/responses")
async def list_survey_responses_endpoint(survey_id: UUID, ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.surveys.services import list_survey_responses

        return list_survey_responses(user=ctx.user, agency_id=ctx.agency_id, survey_id=survey_id)

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.get("/{survey_id}/analytics")
async def survey_analytics_endpoint(survey_id: UUID, ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.surveys.services import get_survey_analytics

        return get_survey_analytics(user=ctx.user, agency_id=ctx.agency_id, survey_id=survey_id)

    return ok(await run_django(_op, agency_id=ctx.agency_id))

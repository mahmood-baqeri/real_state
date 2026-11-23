from decimal import Decimal
from typing import Optional
from uuid import UUID
from django.db import models, transaction
from django.utils import timezone
from apps.accounts.models import User
from apps.audit.services import record_audit_event
from common.exceptions import (
    ConflictDomainError,
    NotFoundDomainError,
    PermissionDeniedDomainError,
    ValidationDomainError,
)
from common.permissions import get_active_membership, is_super_admin
from .models import Survey, SurveyAnswer, SurveyQuestion, SurveyResponse


def _assert_survey_admin(user: User, agency_id: Optional[UUID]) -> None:
    if is_super_admin(user):
        return
    if agency_id:
        mem = get_active_membership(user, agency_id)
        if mem and mem.role.code in ("AGENCY_MANAGER", "BRANCH_MANAGER"):
            return
    raise PermissionDeniedDomainError("مدیریت نظرسنجی فقط برای مدیر آژانس/شعبه یا ادمین کل مجاز است.")


def list_surveys(*, user: Optional[User], agency_id: Optional[UUID], public_only: bool = False):
    qs = Survey.objects.prefetch_related("questions").select_related("agency")
    if public_only:
        qs = qs.filter(is_active=True, target_audience__in=[Survey.TargetAudience.PUBLIC, Survey.TargetAudience.ALL])
    elif user and is_super_admin(user):
        if agency_id:
            qs = qs.filter(models.Q(agency_id=agency_id) | models.Q(agency__isnull=True))
    elif agency_id:
        qs = qs.filter(models.Q(agency_id=agency_id) | models.Q(agency__isnull=True))
    else:
        qs = qs.filter(is_active=True)
    return qs.order_by("-created_at")


def get_survey_by_slug(*, slug: str) -> Survey:
    survey = Survey.objects.prefetch_related("questions").select_related("agency").filter(slug=slug).first()
    if not survey:
        raise NotFoundDomainError("نظرسنجی مورد نظر یافت نشد.")
    return survey


def get_survey_by_id(*, user: User, agency_id: Optional[UUID], survey_id: UUID) -> Survey:
    survey = Survey.objects.prefetch_related("questions").select_related("agency").filter(id=survey_id).first()
    if not survey:
        raise NotFoundDomainError("نظرسنجی یافت نشد.")
    if not is_super_admin(user) and survey.agency_id and agency_id != survey.agency_id:
        if not get_active_membership(user, survey.agency_id):
            raise PermissionDeniedDomainError("اجازه دسترسی به این نظرسنجی را ندارید.")
    return survey


@transaction.atomic
def create_survey(*, user: User, agency_id: Optional[UUID], data: dict) -> Survey:
    _assert_survey_admin(user, agency_id)
    slug = data["slug"].strip().lower()
    if Survey.objects.filter(slug=slug).exists():
        raise ConflictDomainError("شناسه یکتا (slug) نظرسنجی تکراری است.")

    questions_data = data.get("questions") or []
    if not questions_data:
        raise ValidationDomainError("نظرسنجی باید حداقل یک سؤال داشته باشد.")

    survey = Survey.objects.create(
        agency_id=agency_id,
        title=data["title"].strip(),
        slug=slug,
        description=data.get("description", "").strip(),
        target_audience=data.get("target_audience", Survey.TargetAudience.CUSTOMERS),
        crm_trigger_event=data.get("crm_trigger_event", Survey.CrmTriggerEvent.NONE),
        is_active=bool(data.get("is_active", True)),
        allow_anonymous=bool(data.get("allow_anonymous", True)),
        created_by=user,
    )
    for idx, q in enumerate(questions_data, start=1):
        SurveyQuestion.objects.create(
            survey=survey,
            sort_order=int(q.get("sort_order", idx)),
            question_text=q["question_text"].strip(),
            question_type=q["question_type"],
            options=q.get("options") or [],
            is_required=bool(q.get("is_required", True)),
            created_by=user,
        )
    record_audit_event(
        action="SURVEY_CREATED",
        resource_type="Survey",
        resource_id=str(survey.id),
        actor=user,
        agency_id=agency_id,
    )
    return survey


@transaction.atomic
def submit_survey_response(
    *,
    slug: str,
    user: Optional[User],
    respondent_identifier: str,
    respondent_name: str,
    answers: list[dict],
) -> SurveyResponse:
    survey = get_survey_by_slug(slug=slug)
    if not survey.is_active:
        raise ValidationDomainError("این نظرسنجی در حال حاضر غیرفعال است.")
    now = timezone.now()
    if survey.starts_at and now < survey.starts_at:
        raise ValidationDomainError("زمان شروع این نظرسنجی هنوز فرا نرسیده است.")
    if survey.ends_at and now > survey.ends_at:
        raise ValidationDomainError("مهلت پاسخ‌دهی به این نظرسنجی به پایان رسیده است.")

    ident = f"user:{user.id}" if user else f"anon:{respondent_identifier.strip()}"
    if not ident or ident == "anon:":
        raise ValidationDomainError("شناسه پاسخ‌دهنده نامعتبر است.")
    if SurveyResponse.objects.filter(survey=survey, respondent_identifier=ident).exists():
        raise ConflictDomainError("شما قبلاً در این نظرسنجی شرکت کرده‌اید.")

    q_map = {str(q.id): q for q in survey.questions.all()}
    ans_map = {str(a["question_id"]): a for a in answers}

    for qid, q in q_map.items():
        if q.is_required:
            a = ans_map.get(qid)
            if not a:
                raise ValidationDomainError(f"پاسخ به سؤال «{q.question_text}» الزامی است.")
            if q.question_type in (
                SurveyQuestion.QuestionType.SHORT_TEXT,
                SurveyQuestion.QuestionType.LONG_TEXT,
                SurveyQuestion.QuestionType.TEXT,
                SurveyQuestion.QuestionType.YES_NO,
            ) and not str(a.get("answer_text") or "").strip():
                raise ValidationDomainError(f"پاسخ متنی به سؤال «{q.question_text}» الزامی است.")
            if q.question_type in (
                SurveyQuestion.QuestionType.SINGLE_SELECT,
                SurveyQuestion.QuestionType.MULTI_SELECT,
            ) and not list(a.get("selected_options") or []):
                raise ValidationDomainError(f"انتخاب گزینه برای سؤال «{q.question_text}» الزامی است.")
            if q.question_type in (
                SurveyQuestion.QuestionType.RATING,
                SurveyQuestion.QuestionType.STARS,
                SurveyQuestion.QuestionType.SCALE,
                SurveyQuestion.QuestionType.NPS,
            ) and a.get("answer_number") is None:
                raise ValidationDomainError(f"امتیاز عددی برای سؤال «{q.question_text}» الزامی است.")

    response = SurveyResponse.objects.create(
        survey=survey,
        respondent_user=user,
        respondent_identifier=ident,
        respondent_name=(respondent_name or (user.full_name if user else "کاربر مهمان")).strip(),
    )

    for a in answers:
        qid = str(a["question_id"])
        q = q_map.get(qid)
        if not q:
            continue
        ans_num = a.get("answer_number")
        ans_text = str(a.get("answer_text") or "").strip()
        sel_opts = list(a.get("selected_options") or [])

        if q.question_type in (SurveyQuestion.QuestionType.RATING, SurveyQuestion.QuestionType.STARS):
            if ans_num is not None and not (1 <= float(ans_num) <= 5):
                raise ValidationDomainError("امتیاز باید بین ۱ تا ۵ باشد.")
            if q.is_required and ans_num is None:
                raise ValidationDomainError("امتیاز باید بین ۱ تا ۵ باشد.")
        elif q.question_type == SurveyQuestion.QuestionType.SCALE:
            if ans_num is not None and not (1 <= float(ans_num) <= 10):
                raise ValidationDomainError("مقیاس باید بین ۱ تا ۱۰ باشد.")
            if q.is_required and ans_num is None:
                raise ValidationDomainError("مقیاس باید بین ۱ تا ۱۰ باشد.")
        elif q.question_type == SurveyQuestion.QuestionType.NPS:
            if ans_num is not None and not (0 <= float(ans_num) <= 10):
                raise ValidationDomainError("امتیاز NPS باید بین ۰ تا ۱۰ باشد.")
            if q.is_required and ans_num is None:
                raise ValidationDomainError("امتیاز NPS باید بین ۰ تا ۱۰ باشد.")
        elif q.question_type == SurveyQuestion.QuestionType.YES_NO:
            if ans_text and ans_text.upper() not in ("YES", "NO", "بله", "خیر"):
                raise ValidationDomainError("پاسخ بله/خیر معتبر نیست.")
        elif q.question_type == SurveyQuestion.QuestionType.SINGLE_SELECT:
            if sel_opts and len(sel_opts) != 1:
                raise ValidationDomainError("برای سؤال تک‌انتخابی دقیقاً یک گزینه انتخاب کنید.")

        SurveyAnswer.objects.create(
            response=response,
            question=q,
            answer_text=ans_text,
            answer_number=Decimal(str(ans_num)) if ans_num is not None else None,
            selected_options=sel_opts,
        )
    return response


@transaction.atomic
def update_survey(*, user: User, agency_id: Optional[UUID], survey_id: UUID, data: dict) -> Survey:
    survey = get_survey_by_id(user=user, agency_id=agency_id, survey_id=survey_id)
    _assert_survey_admin(user, survey.agency_id or agency_id)

    if "title" in data and data["title"] is not None:
        title = str(data["title"]).strip()
        if len(title) < 3:
            raise ValidationDomainError("عنوان نظرسنجی باید حداقل ۳ کاراکتر باشد.")
        survey.title = title
    if "description" in data and data["description"] is not None:
        survey.description = str(data["description"]).strip()
    if "target_audience" in data and data["target_audience"] is not None:
        if data["target_audience"] not in Survey.TargetAudience.values:
            raise ValidationDomainError("مخاطب هدف نظرسنجی نامعتبر است.")
        survey.target_audience = data["target_audience"]
    if "crm_trigger_event" in data and data["crm_trigger_event"] is not None:
        if data["crm_trigger_event"] not in Survey.CrmTriggerEvent.values:
            raise ValidationDomainError("رویداد ماشه CRM نامعتبر است.")
        survey.crm_trigger_event = data["crm_trigger_event"]
    if "is_active" in data and data["is_active"] is not None:
        survey.is_active = bool(data["is_active"])
    if "allow_anonymous" in data and data["allow_anonymous"] is not None:
        survey.allow_anonymous = bool(data["allow_anonymous"])

    survey.updated_by = user
    survey.save()
    record_audit_event(
        action="SURVEY_UPDATED",
        resource_type="Survey",
        resource_id=str(survey.id),
        actor=user,
        agency_id=survey.agency_id or agency_id,
    )
    return survey


@transaction.atomic
def add_survey_question(*, user: User, agency_id: Optional[UUID], survey_id: UUID, data: dict) -> SurveyQuestion:
    survey = get_survey_by_id(user=user, agency_id=agency_id, survey_id=survey_id)
    _assert_survey_admin(user, survey.agency_id or agency_id)

    q_type = data.get("question_type")
    if q_type not in SurveyQuestion.QuestionType.values:
        raise ValidationDomainError("نوع سؤال نظرسنجی نامعتبر است.")

    max_order = survey.questions.aggregate(models.Max("sort_order")).get("sort_order__max") or 0
    sort_order = int(data.get("sort_order") or (max_order + 1))

    q = SurveyQuestion.objects.create(
        survey=survey,
        sort_order=sort_order,
        question_text=str(data["question_text"]).strip(),
        question_type=q_type,
        options=list(data.get("options") or []),
        is_required=bool(data.get("is_required", True)),
        created_by=user,
    )
    return q


@transaction.atomic
def update_survey_question(
    *, user: User, agency_id: Optional[UUID], survey_id: UUID, question_id: UUID, data: dict
) -> SurveyQuestion:
    survey = get_survey_by_id(user=user, agency_id=agency_id, survey_id=survey_id)
    _assert_survey_admin(user, survey.agency_id or agency_id)

    q = SurveyQuestion.objects.filter(id=question_id, survey=survey).first()
    if not q:
        raise NotFoundDomainError("سؤال مورد نظر یافت نشد.")

    if "question_text" in data and data["question_text"] is not None:
        q.question_text = str(data["question_text"]).strip()
    if "question_type" in data and data["question_type"] is not None:
        if data["question_type"] not in SurveyQuestion.QuestionType.values:
            raise ValidationDomainError("نوع سؤال نظرسنجی نامعتبر است.")
        q.question_type = data["question_type"]
    if "options" in data and data["options"] is not None:
        q.options = [str(opt).strip() for opt in data["options"] if str(opt).strip()]
    if "is_required" in data and data["is_required"] is not None:
        q.is_required = bool(data["is_required"])
    if "sort_order" in data and data["sort_order"] is not None:
        q.sort_order = int(data["sort_order"])
    q.updated_by = user
    q.save()
    return q


@transaction.atomic
def delete_survey_question(*, user: User, agency_id: Optional[UUID], survey_id: UUID, question_id: UUID) -> None:
    survey = get_survey_by_id(user=user, agency_id=agency_id, survey_id=survey_id)
    _assert_survey_admin(user, survey.agency_id or agency_id)

    q = SurveyQuestion.objects.filter(id=question_id, survey=survey).first()
    if not q:
        raise NotFoundDomainError("سؤال مورد نظر یافت نشد.")
    if survey.questions.count() <= 1:
        raise ValidationDomainError("نظرسنجی باید حداقل یک سؤال فعال داشته باشد.")
    q.delete()


@transaction.atomic
def reorder_survey_questions(
    *, user: User, agency_id: Optional[UUID], survey_id: UUID, ordered_question_ids: list[UUID]
) -> list[SurveyQuestion]:
    survey = get_survey_by_id(user=user, agency_id=agency_id, survey_id=survey_id)
    _assert_survey_admin(user, survey.agency_id or agency_id)

    q_by_id = {q.id: q for q in survey.questions.all()}
    order_idx = 1
    for qid in ordered_question_ids:
        q = q_by_id.pop(qid, None)
        if q:
            q.sort_order = order_idx
            q.save(update_fields=["sort_order", "updated_at"])
            order_idx += 1
    for remaining in q_by_id.values():
        remaining.sort_order = order_idx
        remaining.save(update_fields=["sort_order", "updated_at"])
        order_idx += 1
    return list(survey.questions.order_by("sort_order", "created_at"))


def list_survey_responses(*, user: User, agency_id: Optional[UUID], survey_id: UUID) -> list[dict]:
    survey = get_survey_by_id(user=user, agency_id=agency_id, survey_id=survey_id)
    responses = (
        survey.responses.select_related("respondent_user")
        .prefetch_related("answers__question")
        .order_by("-submitted_at")[:200]
    )
    return [
        {
            "id": str(r.id),
            "respondent_name": r.respondent_name or (r.respondent_user.full_name if r.respondent_user else "مهمان"),
            "respondent_identifier": r.respondent_identifier,
            "submitted_at": r.submitted_at.isoformat(),
            "answers": [
                {
                    "question_id": str(a.question_id),
                    "question_text": a.question.question_text,
                    "question_type": a.question.question_type,
                    "answer_text": a.answer_text,
                    "answer_number": float(a.answer_number) if a.answer_number is not None else None,
                    "selected_options": a.selected_options or [],
                }
                for a in r.answers.all()
            ],
        }
        for r in responses
    ]


def get_survey_analytics(*, user: User, agency_id: Optional[UUID], survey_id: UUID) -> dict:
    survey = get_survey_by_id(user=user, agency_id=agency_id, survey_id=survey_id)
    responses = list(survey.responses.prefetch_related("answers").all())
    total_responses = len(responses)

    question_stats = []
    nps_score = None

    for q in survey.questions.all():
        q_answers = [ans for r in responses for ans in r.answers.all() if ans.question_id == q.id]
        numeric_vals = [float(a.answer_number) for a in q_answers if a.answer_number is not None]
        avg_val = round(sum(numeric_vals) / len(numeric_vals), 2) if numeric_vals else None

        distribution: dict[str, int] = {}
        if q.question_type in (SurveyQuestion.QuestionType.SINGLE_SELECT, SurveyQuestion.QuestionType.MULTI_SELECT):
            for opt in q.options:
                distribution[str(opt)] = 0
            for a in q_answers:
                for opt in a.selected_options or []:
                    key = str(opt)
                    distribution[key] = distribution.get(key, 0) + 1
        elif q.question_type == SurveyQuestion.QuestionType.YES_NO:
            for a in q_answers:
                k = a.answer_text or "نامشخص"
                distribution[k] = distribution.get(k, 0) + 1
        elif numeric_vals:
            for v in numeric_vals:
                k = str(int(v)) if v.is_integer() else str(v)
                distribution[k] = distribution.get(k, 0) + 1

        q_nps = None
        if q.question_type == SurveyQuestion.QuestionType.NPS and numeric_vals:
            promoters = sum(1 for v in numeric_vals if v >= 9)
            detractors = sum(1 for v in numeric_vals if v <= 6)
            q_nps = round(((promoters - detractors) / len(numeric_vals)) * 100, 1)
            nps_score = q_nps

        question_stats.append(
            {
                "question_id": str(q.id),
                "question_text": q.question_text,
                "question_type": q.question_type,
                "response_count": len(q_answers),
                "average": avg_val,
                "nps": q_nps,
                "distribution": distribution,
                "sample_texts": [a.answer_text for a in q_answers if a.answer_text][:10],
            }
        )

    return {
        "survey_id": str(survey.id),
        "title": survey.title,
        "slug": survey.slug,
        "total_responses": total_responses,
        "nps_score": nps_score,
        "questions": question_stats,
    }


def compare_surveys(*, user: User, agency_id: Optional[UUID]) -> list[dict]:
    surveys = list_surveys(user=user, agency_id=agency_id)[:10]
    comparison = []
    for s in surveys:
        responses = list(s.responses.prefetch_related("answers").all())
        all_nums = [
            float(a.answer_number)
            for r in responses
            for a in r.answers.all()
            if a.answer_number is not None
        ]
        comparison.append(
            {
                "survey_id": str(s.id),
                "title": s.title,
                "slug": s.slug,
                "responses_count": len(responses),
                "overall_avg": round(sum(all_nums) / len(all_nums), 2) if all_nums else None,
            }
        )
    return comparison

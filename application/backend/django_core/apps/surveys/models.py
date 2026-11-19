from django.conf import settings
from django.db import models
from common.models import BaseModel


class Survey(BaseModel):
    class TargetAudience(models.TextChoices):
        PUBLIC = "PUBLIC", "Public Portal"
        CUSTOMERS = "CUSTOMERS", "Agency Customers"
        AGENTS = "AGENTS", "Real Estate Agents"
        ALL = "ALL", "All Users"

    class CrmTriggerEvent(models.TextChoices):
        NONE = "NONE", "Manual / Standalone"
        VIEWING_COMPLETED = "VIEWING_COMPLETED", "After Viewing Appointment"
        CONTRACT_SIGNED = "CONTRACT_SIGNED", "After Contract Signed"
        TICKET_RESOLVED = "TICKET_RESOLVED", "After Ticket Resolved"

    agency = models.ForeignKey(
        "agencies.Agency", null=True, blank=True, on_delete=models.CASCADE, related_name="surveys"
    )
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True, default="")
    target_audience = models.CharField(
        max_length=20, choices=TargetAudience.choices, default=TargetAudience.CUSTOMERS
    )
    crm_trigger_event = models.CharField(
        max_length=32, choices=CrmTriggerEvent.choices, default=CrmTriggerEvent.NONE
    )
    is_active = models.BooleanField(default=True)
    allow_anonymous = models.BooleanField(default=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "surveys_survey"
        ordering = ["-created_at"]


class SurveyQuestion(BaseModel):
    class QuestionType(models.TextChoices):
        RATING = "RATING", "Numeric Rating (1-5)"
        STARS = "STARS", "Star Rating (1-5)"
        SINGLE_SELECT = "SINGLE_SELECT", "Single Choice"
        MULTI_SELECT = "MULTI_SELECT", "Multiple Choice"
        TEXT = "TEXT", "Free Text"
        YES_NO = "YES_NO", "Yes / No"
        SCALE = "SCALE", "Linear Scale (1-10)"
        NPS = "NPS", "Net Promoter Score (0-10)"

    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name="questions")
    sort_order = models.PositiveIntegerField(default=1)
    question_text = models.CharField(max_length=320)
    question_type = models.CharField(max_length=20, choices=QuestionType.choices)
    options = models.JSONField(default=list, blank=True)
    is_required = models.BooleanField(default=True)

    class Meta:
        db_table = "surveys_question"
        ordering = ["sort_order", "created_at"]


class SurveyResponse(BaseModel):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name="responses")
    respondent_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    respondent_identifier = models.CharField(max_length=128)
    respondent_name = models.CharField(max_length=120, blank=True, default="")
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "surveys_response"
        unique_together = ("survey", "respondent_identifier")
        ordering = ["-submitted_at"]


class SurveyAnswer(BaseModel):
    response = models.ForeignKey(SurveyResponse, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(SurveyQuestion, on_delete=models.CASCADE, related_name="answers")
    answer_text = models.TextField(blank=True, default="")
    answer_number = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    selected_options = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "surveys_answer"
        unique_together = ("response", "question")

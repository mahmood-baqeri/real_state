from django.conf import settings
from django.db import models
from common.models import BaseModel


class AiInteractionLog(BaseModel):
    class ToolType(models.TextChoices):
        PROPERTY_COPY = "PROPERTY_COPY", "Property Listing Copy Draft"
        CRM_SUMMARY = "CRM_SUMMARY", "Customer CRM Summary"
        SEO_DRAFT = "SEO_DRAFT", "SEO Metadata Draft"
        PORTFOLIO_INSIGHT = "PORTFOLIO_INSIGHT", "Portfolio Performance Insight"

    agency = models.ForeignKey(
        "agencies.Agency", null=True, blank=True, on_delete=models.CASCADE, related_name="ai_logs"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ai_logs"
    )
    tool_type = models.CharField(max_length=32, choices=ToolType.choices)
    resource_type = models.CharField(max_length=64, blank=True, default="")
    resource_id = models.CharField(max_length=64, blank=True, default="")
    prompt_summary = models.CharField(max_length=300)
    draft_output = models.JSONField(default=dict)
    provider = models.CharField(max_length=32, default="DOMAIN_ENGINE")

    class Meta:
        db_table = "ai_interaction_log"
        ordering = ["-created_at"]

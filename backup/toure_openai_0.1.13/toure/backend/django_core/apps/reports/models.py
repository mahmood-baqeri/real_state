from django.conf import settings
from django.db import models
from common.models import BaseModel


class DashboardLayout(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dashboard_layouts"
    )
    agency = models.ForeignKey(
        "agencies.Agency", null=True, blank=True, on_delete=models.CASCADE
    )
    role_code = models.CharField(max_length=64, default="DEFAULT", db_index=True)
    widgets_json = models.JSONField(default=list)
    default_period_days = models.PositiveSmallIntegerField(default=30)

    class Meta:
        db_table = "reports_dashboard_layout"
        unique_together = ("user", "agency", "role_code")


class OnboardingProgress(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="onboarding_progress"
    )
    agency = models.ForeignKey(
        "agencies.Agency", null=True, blank=True, on_delete=models.CASCADE
    )
    role_code = models.CharField(max_length=64, default="DEFAULT")
    completed_steps_json = models.JSONField(default=list)
    dismissed = models.BooleanField(default=False)

    class Meta:
        db_table = "reports_onboarding_progress"
        unique_together = ("user", "agency", "role_code")


class ImportJob(BaseModel):
    class Status(models.TextChoices):
        PREVIEWED = "PREVIEWED", "Previewed"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="import_jobs"
    )
    module = models.CharField(max_length=48, default="properties")
    file_name = models.CharField(max_length=255)
    total_rows = models.PositiveIntegerField(default=0)
    imported_rows = models.PositiveIntegerField(default=0)
    duplicate_rows = models.PositiveIntegerField(default=0)
    error_rows = models.PositiveIntegerField(default=0)
    column_mapping_json = models.JSONField(default=dict)
    errors_json = models.JSONField(default=list)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.PREVIEWED)

    class Meta:
        db_table = "reports_import_job"
        ordering = ["-created_at"]

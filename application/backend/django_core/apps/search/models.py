from django.conf import settings
from django.db import models
from common.models import BaseModel


class SavedSearch(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_searches"
    )
    title = models.CharField(max_length=120)
    filters_json = models.JSONField(default=dict)
    notify_on_match = models.BooleanField(default=True)

    class Meta:
        db_table = "search_saved_search"


class SavedView(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_views"
    )
    agency = models.ForeignKey(
        "agencies.Agency", null=True, blank=True, on_delete=models.CASCADE, related_name="saved_views"
    )
    module = models.CharField(max_length=48, db_index=True)
    title = models.CharField(max_length=120)
    filters_json = models.JSONField(default=dict)
    sort_by = models.CharField(max_length=64, blank=True, default="")
    columns_json = models.JSONField(default=list)
    layout_mode = models.CharField(max_length=24, default="table")
    is_default = models.BooleanField(default=False)

    class Meta:
        db_table = "search_saved_view"
        ordering = ["-is_default", "-updated_at"]

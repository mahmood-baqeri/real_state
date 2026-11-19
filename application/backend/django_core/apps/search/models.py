# Path: backend/django_core/apps/search/models.py

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

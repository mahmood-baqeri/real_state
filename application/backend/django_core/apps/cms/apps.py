# Path: backend/django_core/apps/cms/apps.py

from django.apps import AppConfig


class CmsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.cms"
    verbose_name = "CMS & Public Portal"

# Path: backend/django_core/apps/properties/apps.py

from django.apps import AppConfig


class PropertiesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.properties"
    verbose_name = "Property Management"

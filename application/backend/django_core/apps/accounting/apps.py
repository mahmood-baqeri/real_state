# Path: backend/django_core/apps/accounting/apps.py

from django.apps import AppConfig


class AccountingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounting"
    verbose_name = "Double-Entry Accounting & Treasury"

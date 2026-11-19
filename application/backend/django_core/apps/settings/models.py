# Path: backend/django_core/apps/settings/models.py

from decimal import Decimal
from django.db import models
from common.encryption import decrypt_sensitive_value, encrypt_sensitive_value
from common.models import BaseModel


class Country(models.Model):
    code = models.CharField(max_length=2, primary_key=True)  # ISO 3166-1 alpha-2
    name_fa = models.CharField(max_length=100)
    name_en = models.CharField(max_length=100)
    default_currency_code = models.CharField(max_length=10, default="IRT")
    default_calendar = models.CharField(
        max_length=16,
        choices=[("jalali", "Jalali"), ("gregorian", "Gregorian")],
        default="jalali",
    )
    default_timezone = models.CharField(max_length=64, default="Asia/Tehran")
    phone_prefix = models.CharField(max_length=8, default="+98")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "settings_country"

    def __str__(self) -> str:
        return f"{self.code} ({self.name_en})"


class Currency(models.Model):
    code = models.CharField(max_length=10, primary_key=True)  # IRT, IRR, USD, EUR, AED
    name_fa = models.CharField(max_length=64)
    name_en = models.CharField(max_length=64)
    symbol = models.CharField(max_length=16)
    decimal_places = models.PositiveSmallIntegerField(default=0)
    base_unit_factor = models.DecimalField(
        max_digits=18, decimal_places=6, default=Decimal("1.000000")
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "settings_currency"

    def __str__(self) -> str:
        return self.code


class ProviderConfiguration(BaseModel):
    class Category(models.TextChoices):
        PAYMENT = "PAYMENT", "Payment"
        SMS = "SMS", "SMS"
        MAP = "MAP", "Map"

    agency = models.ForeignKey(
        "agencies.Agency",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="provider_configs",
    )
    category = models.CharField(max_length=16, choices=Category.choices, db_index=True)
    provider_key = models.CharField(max_length=64)
    display_name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=False)
    is_sandbox = models.BooleanField(default=True)
    encrypted_credentials = models.TextField(blank=True, default="")
    config_json = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "settings_provider_configuration"
        indexes = [models.Index(fields=["agency", "category", "is_active"])]

    def set_credentials(self, raw_json: str) -> None:
        self.encrypted_credentials = encrypt_sensitive_value(raw_json)

    def get_credentials(self) -> str:
        return decrypt_sensitive_value(self.encrypted_credentials)


class PlatformSetting(models.Model):
    key = models.CharField(max_length=128, primary_key=True)
    value_json = models.JSONField(default=dict)
    description = models.TextField(blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "settings_platform_setting"

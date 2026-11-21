from decimal import Decimal
from django.conf import settings as dj_settings
from django.db import models
from django.utils import timezone as dj_timezone
from common.encryption import decrypt_sensitive_value, encrypt_sensitive_value
from common.models import BaseModel


class CalendarSystem(models.Model):
    code = models.CharField(max_length=16, primary_key=True)  # jalali, gregorian
    name_fa = models.CharField(max_length=64)
    name_en = models.CharField(max_length=64)
    date_format = models.CharField(max_length=40, default="YYYY/MM/DD")
    datetime_format = models.CharField(max_length=48, default="YYYY/MM/DD HH:mm")
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, db_index=True)
    sort_order = models.PositiveSmallIntegerField(default=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "settings_calendar_system"
        ordering = ["sort_order", "code"]

    def __str__(self) -> str:
        return self.code


class Country(models.Model):
    code = models.CharField(max_length=2, primary_key=True)  # ISO 3166-1 alpha-2
    alpha3_code = models.CharField(max_length=3, blank=True, default="")
    name_fa = models.CharField(max_length=100)
    name_en = models.CharField(max_length=100)
    default_currency_code = models.CharField(max_length=10, default="IRT")
    default_calendar = models.CharField(max_length=16, default="jalali")
    supported_calendars = models.JSONField(default=list, blank=True)
    default_language = models.CharField(max_length=8, default="fa")
    supported_languages = models.JSONField(default=list, blank=True)
    default_timezone = models.CharField(max_length=64, default="Asia/Tehran")
    phone_prefix = models.CharField(max_length=8, default="+98")
    flag_url = models.CharField(max_length=300, blank=True, default="")
    sort_order = models.PositiveSmallIntegerField(default=100)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "settings_country"
        ordering = ["sort_order", "code"]

    def __str__(self) -> str:
        return f"{self.code} ({self.name_en})"


class Currency(models.Model):
    code = models.CharField(max_length=10, primary_key=True)  # IRT, IRR, USD, EUR, AED
    name_fa = models.CharField(max_length=64)
    name_en = models.CharField(max_length=64)
    symbol = models.CharField(max_length=16)
    decimal_places = models.PositiveSmallIntegerField(default=0)
    minor_unit = models.CharField(max_length=32, blank=True, default="")
    description = models.CharField(max_length=255, blank=True, default="")
    base_unit_factor = models.DecimalField(
        max_digits=18, decimal_places=6, default=Decimal("1.000000")
    )
    sort_order = models.PositiveSmallIntegerField(default=100)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "settings_currency"
        ordering = ["sort_order", "code"]

    def __str__(self) -> str:
        return self.code


class ExchangeRate(BaseModel):
    base_currency = models.ForeignKey(
        Currency, on_delete=models.CASCADE, related_name="fx_base_rates"
    )
    quote_currency = models.ForeignKey(
        Currency, on_delete=models.CASCADE, related_name="fx_quote_rates"
    )
    rate = models.DecimalField(max_digits=18, decimal_places=6)
    effective_at = models.DateTimeField(default=dj_timezone.now)
    source = models.CharField(max_length=48, default="MANUAL")
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "settings_exchange_rate"
        unique_together = ("base_currency", "quote_currency")
        ordering = ["base_currency_id", "quote_currency_id"]


class ExchangeRateHistory(BaseModel):
    base_currency_code = models.CharField(max_length=10, db_index=True)
    quote_currency_code = models.CharField(max_length=10, db_index=True)
    previous_rate = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    new_rate = models.DecimalField(max_digits=18, decimal_places=6)
    source = models.CharField(max_length=48, default="MANUAL")
    change_reason = models.CharField(max_length=255, blank=True, default="")
    changed_by = models.ForeignKey(
        dj_settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        db_table = "settings_exchange_rate_history"
        ordering = ["-created_at"]


class ProviderConfiguration(BaseModel):
    class Category(models.TextChoices):
        PAYMENT = "PAYMENT", "Payment"
        SMS = "SMS", "SMS"
        MAP = "MAP", "Map"
        AI = "AI", "AI Assistant"
        EMAIL = "EMAIL", "Email"
        STORAGE = "STORAGE", "Storage"

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
    description = models.CharField(max_length=255, blank=True, default="")
    priority = models.PositiveSmallIntegerField(default=10)
    is_active = models.BooleanField(default=False)
    is_sandbox = models.BooleanField(default=True)
    encrypted_credentials = models.TextField(blank=True, default="")
    config_json = models.JSONField(default=dict, blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    last_check_status = models.CharField(max_length=24, blank=True, default="")
    last_check_message = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "settings_provider_configuration"
        indexes = [models.Index(fields=["agency", "category", "is_active", "priority"])]

    def set_credentials(self, raw_json: str) -> None:
        self.encrypted_credentials = encrypt_sensitive_value(raw_json)

    def get_credentials(self) -> str:
        return decrypt_sensitive_value(self.encrypted_credentials)


class SystemSetting(BaseModel):
    class ValueType(models.TextChoices):
        STRING = "STRING", "String"
        INTEGER = "INTEGER", "Integer"
        DECIMAL = "DECIMAL", "Decimal"
        BOOLEAN = "BOOLEAN", "Boolean"
        JSON = "JSON", "JSON"
        SECRET = "SECRET", "Secret"
        SELECT = "SELECT", "Select"

    class SensitivityLevel(models.TextChoices):
        PUBLIC = "PUBLIC", "Public"
        INTERNAL = "INTERNAL", "Internal"
        SECRET = "SECRET", "Secret"

    key = models.CharField(max_length=128, db_index=True)
    agency = models.ForeignKey(
        "agencies.Agency",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="system_settings",
    )
    country_code = models.CharField(max_length=2, blank=True, default="", db_index=True)
    title_fa = models.CharField(max_length=160)
    title_en = models.CharField(max_length=160, blank=True, default="")
    description = models.TextField(blank=True, default="")
    category = models.CharField(max_length=48, db_index=True)
    subcategory = models.CharField(max_length=48, blank=True, default="GENERAL")
    value_type = models.CharField(max_length=16, choices=ValueType.choices, default=ValueType.STRING)
    value_json = models.JSONField(default=dict, blank=True)
    default_value_json = models.JSONField(default=dict, blank=True)
    encrypted_value = models.TextField(blank=True, default="")
    validation_schema = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    sensitivity_level = models.CharField(
        max_length=16, choices=SensitivityLevel.choices, default=SensitivityLevel.INTERNAL, db_index=True
    )
    is_editable = models.BooleanField(default=True)
    requires_restart = models.BooleanField(default=False)
    sort_order = models.PositiveSmallIntegerField(default=100)

    class Meta:
        db_table = "settings_system_setting"
        ordering = ["category", "sort_order", "key"]
        constraints = [
            models.UniqueConstraint(
                fields=["key", "agency", "country_code"],
                name="uq_system_setting_scope",
            )
        ]

    def set_secret(self, raw_value: str) -> None:
        self.encrypted_value = encrypt_sensitive_value(raw_value)
        self.value_json = {"value": "****" if raw_value else ""}

    def get_secret(self) -> str:
        return decrypt_sensitive_value(self.encrypted_value)


class SystemSettingHistory(BaseModel):
    setting_key = models.CharField(max_length=128, db_index=True)
    agency_id_snapshot = models.UUIDField(null=True, blank=True)
    previous_value_json = models.JSONField(default=dict, null=True, blank=True)
    new_value_json = models.JSONField(default=dict, null=True, blank=True)
    is_secret = models.BooleanField(default=False)
    change_reason = models.CharField(max_length=255, blank=True, default="")
    changed_by = models.ForeignKey(
        dj_settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        db_table = "settings_system_setting_history"
        ordering = ["-created_at"]


class BrandMediaSlot(models.Model):
    slot_key = models.CharField(max_length=64, primary_key=True)
    category = models.CharField(max_length=32, default="BRANDING", db_index=True)
    title_fa = models.CharField(max_length=140)
    description = models.CharField(max_length=255, blank=True, default="")
    image_url = models.CharField(max_length=500, blank=True, default="")
    dark_image_url = models.CharField(max_length=500, blank=True, default="")
    file_key = models.CharField(max_length=300, blank=True, default="")
    alt_text = models.CharField(max_length=200, blank=True, default="")
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=100)
    updated_by = models.ForeignKey(
        dj_settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "settings_brand_media_slot"
        ordering = ["sort_order", "slot_key"]


class SiteContentBlock(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PUBLISHED = "PUBLISHED", "Published"

    slug_key = models.CharField(max_length=80, primary_key=True)
    page_key = models.CharField(max_length=48, default="HOME", db_index=True)
    section_key = models.CharField(max_length=64, default="GENERAL")
    title_fa = models.CharField(max_length=200, blank=True, default="")
    subtitle_fa = models.CharField(max_length=400, blank=True, default="")
    body_html = models.TextField(blank=True, default="")
    cta_label = models.CharField(max_length=80, blank=True, default="")
    cta_href = models.CharField(max_length=200, blank=True, default="")
    items_json = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PUBLISHED, db_index=True)
    sort_order = models.PositiveSmallIntegerField(default=100)
    is_active = models.BooleanField(default=True)
    updated_by = models.ForeignKey(
        dj_settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "settings_site_content_block"
        ordering = ["page_key", "sort_order", "slug_key"]


class Province(BaseModel):
    country = models.ForeignKey(
        Country, on_delete=models.PROTECT, default="IR", related_name="provinces"
    )
    code = models.CharField(max_length=24, blank=True, default="")
    name_fa = models.CharField(max_length=100, db_index=True)
    name_en = models.CharField(max_length=100, blank=True, default="")
    slug = models.SlugField(max_length=120, unique=True, allow_unicode=True)
    center_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    center_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=100)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "settings_geo_province"
        ordering = ["sort_order", "name_fa"]
        unique_together = ("country", "name_fa")

    def __str__(self) -> str:
        return self.name_fa


class City(BaseModel):
    province = models.ForeignKey(Province, on_delete=models.PROTECT, related_name="cities")
    name_fa = models.CharField(max_length=100, db_index=True)
    name_en = models.CharField(max_length=100, blank=True, default="")
    slug = models.SlugField(max_length=120, allow_unicode=True)
    center_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    center_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=100)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "settings_geo_city"
        ordering = ["sort_order", "name_fa"]
        unique_together = ("province", "name_fa")
        indexes = [models.Index(fields=["province", "is_active", "name_fa"])]

    def __str__(self) -> str:
        return f"{self.province.name_fa} - {self.name_fa}"


class District(BaseModel):
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name="districts")
    name_fa = models.CharField(max_length=100, db_index=True)
    name_en = models.CharField(max_length=100, blank=True, default="")
    slug = models.SlugField(max_length=120, allow_unicode=True)
    center_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    center_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=100)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "settings_geo_district"
        ordering = ["sort_order", "name_fa"]
        unique_together = ("city", "name_fa")
        indexes = [models.Index(fields=["city", "is_active", "name_fa"])]

    def __str__(self) -> str:
        return f"{self.city.name_fa} - {self.name_fa}"


class Neighborhood(BaseModel):
    district = models.ForeignKey(District, on_delete=models.PROTECT, related_name="neighborhoods")
    name_fa = models.CharField(max_length=100, db_index=True)
    name_en = models.CharField(max_length=100, blank=True, default="")
    slug = models.SlugField(max_length=120, allow_unicode=True)
    center_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    center_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=100)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "settings_geo_neighborhood"
        ordering = ["sort_order", "name_fa"]
        unique_together = ("district", "name_fa")
        indexes = [models.Index(fields=["district", "is_active", "name_fa"])]

    def __str__(self) -> str:
        return f"{self.district.name_fa} - {self.name_fa}"


class PlatformSetting(models.Model):
    key = models.CharField(max_length=128, primary_key=True)
    value_json = models.JSONField(default=dict)
    description = models.TextField(blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "settings_platform_setting"

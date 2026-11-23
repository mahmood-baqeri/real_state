from decimal import Decimal
from typing import Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from pydantic import BaseModel
from app.core.django_bridge import run_django
from app.dependencies.auth import RequestContext, get_current_context, get_optional_context
from app.schemas.common import ok

router = APIRouter(prefix="/settings", tags=["Global Settings, Localization & Providers"])


class ProviderUpsertBody(BaseModel):
    category: str
    provider_key: str
    display_name: str
    description: str = ""
    priority: int = 10
    is_active: bool = True
    is_sandbox: bool = True
    config_json: dict[str, Any] = {}
    credentials: Optional[dict[str, Any]] = None


class SettingUpdateItem(BaseModel):
    key: str
    value: Any = None
    country_code: str = ""
    create_if_missing: bool = False
    title_fa: Optional[str] = None
    title_en: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    value_type: Optional[str] = None
    sensitivity_level: Optional[str] = None


class SettingsBulkUpdateBody(BaseModel):
    updates: list[SettingUpdateItem]
    change_reason: str = ""


class SettingResetBody(BaseModel):
    change_reason: str = ""


class BrandSlotUpdateBody(BaseModel):
    title_fa: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    dark_image_url: Optional[str] = None
    alt_text: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class SiteContentBlockBody(BaseModel):
    page_key: str = "HOME"
    section_key: str = "GENERAL"
    title_fa: str = ""
    subtitle_fa: str = ""
    body_html: str = ""
    cta_label: str = ""
    cta_href: str = ""
    items_json: list[Any] = []
    status: str = "PUBLISHED"
    sort_order: int = 100
    is_active: bool = True


class CalendarUpsertBody(BaseModel):
    code: str
    name_fa: str
    name_en: str = ""
    date_format: str = "YYYY/MM/DD"
    datetime_format: str = "YYYY/MM/DD HH:mm"
    is_default: bool = False
    is_active: bool = True
    sort_order: int = 100


class CalendarToggleBody(BaseModel):
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


class CountryUpsertBody(BaseModel):
    code: str
    alpha3_code: str = ""
    name_fa: str
    name_en: str
    default_currency_code: str = "IRT"
    default_calendar: str = "jalali"
    supported_calendars: list[str] = ["jalali"]
    default_language: str = "fa"
    supported_languages: list[str] = ["fa"]
    default_timezone: str = "Asia/Tehran"
    phone_prefix: str = "+98"
    flag_url: str = ""
    sort_order: int = 100
    is_active: bool = True


class CurrencyUpsertBody(BaseModel):
    code: str
    name_fa: str
    name_en: str = ""
    symbol: str = ""
    decimal_places: int = 0
    minor_unit: str = ""
    description: str = ""
    base_unit_factor: Decimal = Decimal("1.000000")
    sort_order: int = 100
    is_active: bool = True


class ExchangeRateUpsertBody(BaseModel):
    base_currency_code: str
    quote_currency_code: str
    rate: Decimal
    source: str = "MANUAL"
    is_active: bool = True
    change_reason: str = ""


class ActiveToggleBody(BaseModel):
    is_active: bool


def _ser_provider(c) -> dict:
    from apps.settings.services import mask_provider_credentials

    return {
        "id": str(c.id),
        "agency_id": str(c.agency_id) if c.agency_id else None,
        "category": c.category,
        "provider_key": c.provider_key,
        "display_name": c.display_name,
        "description": c.description,
        "priority": c.priority,
        "is_active": c.is_active,
        "is_sandbox": c.is_sandbox,
        "config_json": c.config_json,
        "has_credentials": bool(c.encrypted_credentials),
        "masked_credentials": mask_provider_credentials(c),
        "last_checked_at": c.last_checked_at.isoformat() if c.last_checked_at else None,
        "last_check_status": c.last_check_status,
        "last_check_message": c.last_check_message,
    }


def _ser_country(c, area_unit: str = "sqm") -> dict:
    return {
        "code": c.code,
        "alpha3_code": c.alpha3_code,
        "name_fa": c.name_fa,
        "name_en": c.name_en,
        "default_language": c.default_language,
        "supported_languages": c.supported_languages or [c.default_language],
        "default_calendar": c.default_calendar,
        "supported_calendars": c.supported_calendars or [c.default_calendar],
        "default_currency": c.default_currency_code,
        "default_currency_code": c.default_currency_code,
        "timezone": c.default_timezone,
        "default_timezone": c.default_timezone,
        "phone_prefix": c.phone_prefix,
        "flag_url": c.flag_url,
        "sort_order": c.sort_order,
        "is_active": c.is_active,
        "area_unit": area_unit,
    }


def _ser_calendar(cal) -> dict:
    return {
        "code": cal.code,
        "name_fa": cal.name_fa,
        "name_en": cal.name_en,
        "date_format": cal.date_format,
        "datetime_format": cal.datetime_format,
        "is_default": cal.is_default,
        "is_active": cal.is_active,
        "sort_order": cal.sort_order,
    }


def _ser_currency(cur) -> dict:
    return {
        "code": cur.code,
        "name_fa": cur.name_fa,
        "name_en": cur.name_en,
        "symbol": cur.symbol,
        "decimal_places": cur.decimal_places,
        "minor_unit": cur.minor_unit,
        "description": cur.description,
        "base_unit_factor": str(cur.base_unit_factor),
        "exchange_rate_to_base": str(cur.base_unit_factor),
        "sort_order": cur.sort_order,
        "is_active": cur.is_active,
    }


def _ser_fx(fx) -> dict:
    return {
        "id": str(fx.id),
        "base_currency_code": fx.base_currency_id,
        "quote_currency_code": fx.quote_currency_id,
        "rate": str(fx.rate),
        "source": fx.source,
        "effective_at": fx.effective_at.isoformat(),
        "is_active": fx.is_active,
    }


@router.get("/public-bootstrap")
async def public_bootstrap_endpoint(ctx: RequestContext = Depends(get_optional_context)):
    def _op():
        from apps.settings.services import get_public_bootstrap

        return get_public_bootstrap(agency_id=ctx.agency_id)

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.get("/localization")
async def localization_endpoint(ctx: RequestContext = Depends(get_optional_context)):
    def _op():
        from apps.settings.services import get_localization_metadata

        meta = get_localization_metadata(agency_id=ctx.agency_id)
        area_unit = meta["area_unit"]
        return {
            "countries": [_ser_country(c, area_unit=area_unit) for c in meta["countries"]],
            "calendars": [_ser_calendar(cal) for cal in meta["calendars"]],
            "currencies": [_ser_currency(cur) for cur in meta["currencies"]],
            "exchange_rates": [_ser_fx(fx) for fx in meta["exchange_rates"]],
            "area_unit": area_unit,
            "map_provider": meta["map_provider"],
            "available_adapters": meta["available_adapters"],
        }

    return ok(await run_django(_op, agency_id=ctx.agency_id))


# ==============================================================================
# Global System Settings Registry
# ==============================================================================


@router.get("/registry")
async def list_settings_registry_endpoint(
    category: Optional[str] = Query(default=None),
    country_code: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
    ctx: RequestContext = Depends(get_current_context),
):
    def _op():
        from apps.settings.services import list_system_settings, serialize_system_setting

        items = list_system_settings(
            user=ctx.user,
            agency_id=ctx.agency_id,
            category=category,
            country_code=country_code,
            q=q,
        )
        return [serialize_system_setting(s) for s in items]

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.put("/registry")
async def bulk_update_settings_endpoint(
    body: SettingsBulkUpdateBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.settings.services import bulk_update_system_settings, serialize_system_setting

        items = bulk_update_system_settings(
            user=ctx.user,
            agency_id=ctx.agency_id,
            updates=[u.model_dump(exclude_none=True) for u in body.updates],
            change_reason=body.change_reason,
        )
        return [serialize_system_setting(s) for s in items]

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/registry/{setting_id}/reset")
async def reset_setting_endpoint(
    setting_id: UUID,
    body: SettingResetBody = SettingResetBody(),
    ctx: RequestContext = Depends(get_current_context),
):
    def _op():
        from apps.settings.services import reset_system_setting_to_default, serialize_system_setting

        s = reset_system_setting_to_default(
            user=ctx.user, setting_id=setting_id, change_reason=body.change_reason
        )
        return serialize_system_setting(s)

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.get("/registry/history")
async def list_setting_history_endpoint(
    setting_key: Optional[str] = Query(default=None),
    ctx: RequestContext = Depends(get_current_context),
):
    def _op():
        from apps.settings.services import list_setting_history

        return [
            {
                "id": str(h.id),
                "setting_key": h.setting_key,
                "agency_id_snapshot": str(h.agency_id_snapshot) if h.agency_id_snapshot else None,
                "previous_value": "****" if h.is_secret else (h.previous_value_json or {}).get("value"),
                "new_value": "****" if h.is_secret else (h.new_value_json or {}).get("value"),
                "is_secret": h.is_secret,
                "change_reason": h.change_reason,
                "changed_by_name": h.changed_by.full_name if h.changed_by else "سیستم",
                "created_at": h.created_at.isoformat(),
            }
            for h in list_setting_history(
                user=ctx.user, agency_id=ctx.agency_id, setting_key=setting_key
            )
        ]

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/registry/rollback/{history_id}")
async def rollback_setting_endpoint(
    history_id: UUID, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.settings.services import rollback_system_setting, serialize_system_setting

        return serialize_system_setting(rollback_system_setting(user=ctx.user, history_id=history_id))

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.get("/health")
async def system_health_endpoint(ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.settings.services import get_system_health

        return get_system_health(user=ctx.user)

    return ok(await run_django(_op))


# ==============================================================================
# Branding Media & Site Content Blocks
# ==============================================================================


@router.get("/branding")
async def list_branding_endpoint(include_inactive: bool = False):
    def _op():
        from apps.settings.services import list_brand_media_slots

        return [
            {
                "id": str(s.slot_key),
                "slot_key": s.slot_key,
                "category": s.category,
                "title_fa": s.title_fa,
                "description": s.description,
                "image_url": s.image_url,
                "dark_image_url": s.dark_image_url,
                "alt_text": s.alt_text,
                "is_active": s.is_active,
                "sort_order": s.sort_order,
            }
            for s in list_brand_media_slots(include_inactive=include_inactive)
        ]

    return ok(await run_django(_op))


@router.put("/branding/{slot_key}")
async def update_branding_slot_endpoint(
    slot_key: str, body: BrandSlotUpdateBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.settings.services import update_brand_media_slot

        s = update_brand_media_slot(
            user=ctx.user, slot_key=slot_key, data=body.model_dump(exclude_none=True)
        )
        return {
            "id": str(s.slot_key),
            "slot_key": s.slot_key,
            "image_url": s.image_url,
            "dark_image_url": s.dark_image_url,
            "alt_text": s.alt_text,
            "is_active": s.is_active,
        }

    return ok(await run_django(_op))


@router.post("/branding/{slot_key}/upload")
async def upload_branding_slot_endpoint(
    slot_key: str,
    file: UploadFile = File(...),
    dark_variant: bool = Form(False),
    alt_text: Optional[str] = Form(None),
    ctx: RequestContext = Depends(get_current_context),
):
    content = await file.read()

    def _op():
        from apps.settings.services import upload_brand_media_slot

        s = upload_brand_media_slot(
            user=ctx.user,
            slot_key=slot_key,
            filename=file.filename or "asset.png",
            content_type=file.content_type or "",
            content=content,
            dark_variant=dark_variant,
            alt_text=alt_text,
        )
        return {
            "id": str(s.slot_key),
            "slot_key": s.slot_key,
            "image_url": s.image_url,
            "dark_image_url": s.dark_image_url,
            "alt_text": s.alt_text,
        }

    return ok(await run_django(_op))


@router.delete("/branding/{slot_key}/image")
async def delete_branding_slot_image_endpoint(
    slot_key: str,
    dark_variant: bool = Query(default=False),
    ctx: RequestContext = Depends(get_current_context),
):
    def _op():
        from apps.settings.services import clear_brand_media_slot_image

        s = clear_brand_media_slot_image(user=ctx.user, slot_key=slot_key, dark_variant=dark_variant)
        return {
            "id": str(s.slot_key),
            "slot_key": s.slot_key,
            "image_url": s.image_url,
            "dark_image_url": s.dark_image_url,
        }

    return ok(await run_django(_op))


@router.get("/content-blocks")
async def list_content_blocks_endpoint(
    page_key: Optional[str] = Query(default=None),
    published_only: bool = Query(default=True),
):
    def _op():
        from apps.settings.services import list_site_content_blocks

        return [
            {
                "id": str(b.pk),
                "slug_key": b.slug_key,
                "page_key": b.page_key,
                "section_key": b.section_key,
                "title_fa": b.title_fa,
                "subtitle_fa": b.subtitle_fa,
                "body_html": b.body_html,
                "cta_label": b.cta_label,
                "cta_href": b.cta_href,
                "items_json": b.items_json or [],
                "status": b.status,
                "sort_order": b.sort_order,
                "is_active": b.is_active,
            }
            for b in list_site_content_blocks(page_key=page_key, published_only=published_only)
        ]

    return ok(await run_django(_op))


@router.put("/content-blocks/{slug_key}")
async def upsert_content_block_endpoint(
    slug_key: str, body: SiteContentBlockBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.settings.services import upsert_site_content_block

        b = upsert_site_content_block(user=ctx.user, slug_key=slug_key, data=body.model_dump())
        return {
            "id": str(b.pk),
            "slug_key": b.slug_key,
            "page_key": b.page_key,
            "section_key": b.section_key,
            "title_fa": b.title_fa,
            "subtitle_fa": b.subtitle_fa,
            "body_html": b.body_html,
            "cta_label": b.cta_label,
            "cta_href": b.cta_href,
            "items_json": b.items_json or [],
            "status": b.status,
            "sort_order": b.sort_order,
            "is_active": b.is_active,
        }

    return ok(await run_django(_op))


# ==============================================================================
# Dynamic Calendars, Countries, Currencies & Exchange Rates
# ==============================================================================


@router.get("/calendars")
async def list_calendars_endpoint(include_inactive: bool = True):
    def _op():
        from apps.settings.services import list_calendars

        return [_ser_calendar(c) for c in list_calendars(include_inactive=include_inactive)]

    return ok(await run_django(_op))


@router.post("/calendars", status_code=201)
async def upsert_calendar_endpoint(
    body: CalendarUpsertBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.settings.services import upsert_calendar

        return _ser_calendar(upsert_calendar(user=ctx.user, data=body.model_dump()))

    return ok(await run_django(_op))


@router.patch("/calendars/{code}/toggle")
async def toggle_calendar_endpoint(
    code: str, body: CalendarToggleBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.settings.services import toggle_calendar

        return _ser_calendar(
            toggle_calendar(user=ctx.user, code=code, is_active=body.is_active, is_default=body.is_default)
        )

    return ok(await run_django(_op))


@router.get("/countries")
async def list_countries_endpoint(include_inactive: bool = True):
    def _op():
        from apps.settings.services import list_countries

        return [_ser_country(c) for c in list_countries(include_inactive=include_inactive)]

    return ok(await run_django(_op))


@router.post("/countries", status_code=201)
async def upsert_country_endpoint(
    body: CountryUpsertBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.settings.services import upsert_country

        return _ser_country(upsert_country(user=ctx.user, data=body.model_dump()))

    return ok(await run_django(_op))


@router.patch("/countries/{code}/toggle")
async def toggle_country_endpoint(
    code: str, body: ActiveToggleBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.settings.services import toggle_country

        return _ser_country(toggle_country(user=ctx.user, code=code, is_active=body.is_active))

    return ok(await run_django(_op))


@router.get("/currencies")
async def list_currencies_endpoint(include_inactive: bool = True):
    def _op():
        from apps.settings.services import list_currencies

        return [_ser_currency(c) for c in list_currencies(include_inactive=include_inactive)]

    return ok(await run_django(_op))


@router.post("/currencies", status_code=201)
async def upsert_currency_endpoint(
    body: CurrencyUpsertBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.settings.services import upsert_currency

        return _ser_currency(upsert_currency(user=ctx.user, data=body.model_dump()))

    return ok(await run_django(_op))


@router.patch("/currencies/{code}/toggle")
async def toggle_currency_endpoint(
    code: str, body: ActiveToggleBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.settings.services import toggle_currency

        return _ser_currency(toggle_currency(user=ctx.user, code=code, is_active=body.is_active))

    return ok(await run_django(_op))


@router.get("/exchange-rates")
async def list_exchange_rates_endpoint(include_inactive: bool = True):
    def _op():
        from apps.settings.services import list_exchange_rates

        return [_ser_fx(fx) for fx in list_exchange_rates(include_inactive=include_inactive)]

    return ok(await run_django(_op))


@router.post("/exchange-rates", status_code=201)
async def upsert_exchange_rate_endpoint(
    body: ExchangeRateUpsertBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.settings.services import upsert_exchange_rate

        return _ser_fx(upsert_exchange_rate(user=ctx.user, data=body.model_dump()))

    return ok(await run_django(_op))


@router.get("/exchange-rates/history")
async def list_exchange_rate_history_endpoint(ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.settings.services import list_exchange_rate_history

        return [
            {
                "id": str(h.id),
                "base_currency_code": h.base_currency_code,
                "quote_currency_code": h.quote_currency_code,
                "previous_rate": str(h.previous_rate) if h.previous_rate is not None else None,
                "new_rate": str(h.new_rate),
                "source": h.source,
                "change_reason": h.change_reason,
                "changed_by_name": h.changed_by.full_name if h.changed_by else "سیستم",
                "created_at": h.created_at.isoformat(),
            }
            for h in list_exchange_rate_history(user=ctx.user)
        ]

    return ok(await run_django(_op))


# ==============================================================================
# Provider Configurations (SMS, Payment, Map, AI)
# ==============================================================================


@router.get("/providers")
async def list_providers_endpoint(
    category: Optional[str] = Query(default=None),
    ctx: RequestContext = Depends(get_current_context),
):
    def _op():
        from apps.settings.services import list_provider_configs

        return [
            _ser_provider(c)
            for c in list_provider_configs(user=ctx.user, agency_id=ctx.agency_id, category=category)
        ]

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/providers")
async def upsert_provider_endpoint(
    body: ProviderUpsertBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.settings.services import upsert_provider_config

        c = upsert_provider_config(
            user=ctx.user,
            agency_id=ctx.agency_id,
            data=body.model_dump(exclude_none=True),
        )
        return _ser_provider(c)

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/providers/{config_id}/test")
async def test_provider_endpoint(
    config_id: UUID, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.settings.services import test_provider_config

        return test_provider_config(user=ctx.user, agency_id=ctx.agency_id, config_id=config_id)

    return ok(await run_django(_op, agency_id=ctx.agency_id))

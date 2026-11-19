# Path: backend/fastapi_core/app/api/v1/settings.py

from typing import Any, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.core.django_bridge import run_django
from app.dependencies.auth import RequestContext, get_current_context
from app.schemas.common import ok

router = APIRouter(prefix="/settings", tags=["Localization & Providers"])


class ProviderUpsertBody(BaseModel):
    category: str
    provider_key: str
    display_name: str
    is_active: bool = True
    is_sandbox: bool = True
    config_json: dict[str, Any] = {}
    credentials: Optional[dict[str, Any]] = None


@router.get("/localization")
async def localization_endpoint():
    def _op():
        from apps.settings.services import get_localization_metadata

        meta = get_localization_metadata()
        return {
            "countries": [
                {
                    "code": c.code,
                    "name_fa": c.name_fa,
                    "name_en": c.name_en,
                    "default_language": c.default_language,
                    "default_calendar": c.default_calendar,
                    "default_currency": c.default_currency_id,
                    "timezone": c.default_timezone,
                    "area_unit": c.default_area_unit,
                }
                for c in meta["countries"]
            ],
            "currencies": [
                {
                    "code": cur.code,
                    "name_fa": cur.name_fa,
                    "name_en": cur.name_en,
                    "symbol": cur.symbol,
                    "decimal_places": cur.decimal_places,
                    "exchange_rate_to_base": str(cur.exchange_rate_to_base),
                }
                for cur in meta["currencies"]
            ],
            "map_provider": meta["map_provider"],
            "available_adapters": {
                "payment": [
                    {"key": "sandbox", "name": "درگاه پرداخت آزمایشی (Sandbox)"},
                    {"key": "zarinpal_ready", "name": "آداپتر آماده زرین‌پال"},
                ],
                "sms": [
                    {"key": "console", "name": "آداپتر پیامک آزمایشی (Console)"},
                    {"key": "kavenegar_ready", "name": "آداپتر آماده کاوه‌نگار"},
                ],
                "map": [
                    {"key": "osm_tile", "name": "نقشه OpenStreetMap"},
                    {"key": "neshan_ready", "name": "آداپتر آماده نشان"},
                ],
            },
        }

    return ok(await run_django(_op))


@router.get("/providers")
async def list_providers_endpoint(ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.settings.services import list_provider_configs

        return [
            {
                "id": str(c.id),
                "agency_id": str(c.agency_id) if c.agency_id else None,
                "category": c.category,
                "provider_key": c.provider_key,
                "display_name": c.display_name,
                "is_active": c.is_active,
                "is_sandbox": c.is_sandbox,
                "config_json": c.config_json,
                "has_credentials": bool(c.encrypted_credentials),
            }
            for c in list_provider_configs(user=ctx.user, agency_id=ctx.agency_id)
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
        return {
            "id": str(c.id),
            "category": c.category,
            "provider_key": c.provider_key,
            "display_name": c.display_name,
            "is_active": c.is_active,
            "is_sandbox": c.is_sandbox,
        }

    return ok(await run_django(_op, agency_id=ctx.agency_id))

from typing import Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from app.core.django_bridge import run_django
from app.dependencies.auth import RequestContext, get_current_context, get_optional_context
from app.schemas.common import ok

router = APIRouter(prefix="/settings", tags=["Localization & Providers"])


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


@router.get("/localization")
async def localization_endpoint(ctx: RequestContext = Depends(get_optional_context)):
    def _op():
        from apps.settings.services import get_localization_metadata

        meta = get_localization_metadata(agency_id=ctx.agency_id)
        return {
            "countries": [
                {
                    "code": c.code,
                    "name_fa": c.name_fa,
                    "name_en": c.name_en,
                    "default_language": "fa" if c.code == "IR" else "en",
                    "default_calendar": c.default_calendar,
                    "default_currency": c.default_currency_code,
                    "timezone": c.default_timezone,
                    "phone_prefix": c.phone_prefix,
                    "area_unit": "sqm",
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
                    "exchange_rate_to_base": str(cur.base_unit_factor),
                }
                for cur in meta["currencies"]
            ],
            "map_provider": meta["map_provider"],
            "available_adapters": meta["available_adapters"],
        }

    return ok(await run_django(_op, agency_id=ctx.agency_id))


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

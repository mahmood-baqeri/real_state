# Path: backend/django_core/apps/settings/services.py

import json
from typing import Optional
from uuid import UUID
from django.db import transaction
from apps.accounts.models import User
from apps.audit.services import record_audit_event
from common.exceptions import PermissionDeniedDomainError
from common.permissions import has_agency_permission, is_super_admin
from integrations.registry import get_map_provider
from .models import Country, Currency, ProviderConfiguration


def get_localization_metadata() -> dict:
    map_cfg = get_map_provider().get_client_tile_config()
    return {
        "countries": list(Country.objects.filter(is_active=True).order_by("code")),
        "currencies": list(Currency.objects.filter(is_active=True).order_by("code")),
        "map_provider": {
            "provider_key": map_cfg.provider_key,
            "tile_url": map_cfg.tile_url,
            "attribution": map_cfg.attribution,
        },
    }


def list_provider_configs(*, user: User, agency_id: Optional[UUID]) -> list[ProviderConfiguration]:
    if agency_id:
        if not (is_super_admin(user) or has_agency_permission(user, agency_id, "agency.manage_policy")):
            raise PermissionDeniedDomainError("عدم دسترسی به تنظیمات ارائه‌دهندگان آژانس.")
        return list(ProviderConfiguration.objects.filter(agency_id__in=[None, agency_id]).order_by("category", "-is_active"))
    if not is_super_admin(user):
        raise PermissionDeniedDomainError("عدم دسترسی به تنظیمات سراسری ارائه‌دهندگان.")
    return list(ProviderConfiguration.objects.filter(agency__isnull=True).order_by("category", "-is_active"))


@transaction.atomic
def upsert_provider_config(*, user: User, agency_id: Optional[UUID], data: dict) -> ProviderConfiguration:
    if agency_id:
        if not (is_super_admin(user) or has_agency_permission(user, agency_id, "agency.manage_policy")):
            raise PermissionDeniedDomainError("عدم مجوز تنظیم ارائه‌دهندگان.")
    elif not is_super_admin(user):
        raise PermissionDeniedDomainError("فقط مدیر کل مجاز به تنظیم ارائه‌دهندگان پلتفرم است.")

    category = data["category"]
    provider_key = data["provider_key"]
    is_active = bool(data.get("is_active", True))

    if is_active:
        ProviderConfiguration.objects.filter(agency_id=agency_id, category=category).update(is_active=False)

    cfg, _ = ProviderConfiguration.objects.update_or_create(
        agency_id=agency_id,
        category=category,
        provider_key=provider_key,
        defaults={
            "display_name": data["display_name"],
            "is_active": is_active,
            "is_sandbox": bool(data.get("is_sandbox", True)),
            "config_json": data.get("config_json", {}),
            "created_by": user,
        },
    )
    if data.get("credentials"):
        cfg.set_credentials(json.dumps(data["credentials"]))
        cfg.save(update_fields=["encrypted_credentials", "updated_at"])

    record_audit_event(
        action="PROVIDER_CONFIG_UPDATED",
        resource_type="ProviderConfiguration",
        resource_id=str(cfg.id),
        actor=user,
        agency_id=agency_id,
    )
    return cfg

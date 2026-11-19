import json
import re
from typing import Optional
from uuid import UUID
from django.db import models, transaction
from django.utils import timezone
from django.utils.text import slugify
from apps.accounts.models import User
from apps.audit.services import record_audit_event
from common.exceptions import ConflictDomainError, NotFoundDomainError, PermissionDeniedDomainError, ValidationDomainError
from common.permissions import has_agency_permission, is_super_admin
from integrations.registry import (
    AI_PROVIDERS,
    MAP_PROVIDERS,
    PAYMENT_PROVIDERS,
    SMS_PROVIDERS,
    get_ai_provider,
    get_map_provider,
    get_payment_provider,
)
from .models import City, Country, Currency, District, Neighborhood, ProviderConfiguration, Province


def _safe_slug(name_en: str, name_fa: str, prefix: str = "") -> str:
    base = slugify(name_en or "", allow_unicode=False)
    if not base:
        clean = re.sub(r"[^\w\s-]", "", name_fa or "").strip().replace(" ", "-")
        base = clean or "loc"
    return f"{prefix}-{base}".strip("-")[:110]


def resolve_active_provider_config(
    *, category: str, agency_id: Optional[UUID] = None, provider_key: Optional[str] = None
) -> Optional[ProviderConfiguration]:
    qs = ProviderConfiguration.objects.filter(category=category)
    if provider_key:
        qs = qs.filter(provider_key=provider_key)
    else:
        qs = qs.filter(is_active=True)

    if agency_id:
        cfg = qs.filter(agency_id=agency_id).order_by("priority", "-updated_at").first()
        if cfg:
            return cfg
    return qs.filter(agency__isnull=True).order_by("priority", "-updated_at").first()


def parse_provider_credentials(cfg: Optional[ProviderConfiguration]) -> dict:
    if not cfg or not cfg.encrypted_credentials:
        return {}
    try:
        raw = cfg.get_credentials()
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def mask_provider_credentials(cfg: ProviderConfiguration) -> dict[str, str]:
    creds = parse_provider_credentials(cfg)
    masked: dict[str, str] = {}
    for k, v in creds.items():
        s = str(v or "")
        if len(s) <= 4:
            masked[k] = "****" if s else ""
        else:
            masked[k] = f"{s[:2]}{'*' * min(8, len(s) - 4)}{s[-2:]}"
    return masked


def get_localization_metadata(agency_id: Optional[UUID] = None) -> dict:
    active_map_cfg = resolve_active_provider_config(
        category=ProviderConfiguration.Category.MAP, agency_id=agency_id
    )
    provider_key = active_map_cfg.provider_key if active_map_cfg else None
    try:
        map_adapter = get_map_provider(provider_key)
    except ValueError:
        map_adapter = get_map_provider("osm")

    creds = parse_provider_credentials(active_map_cfg)
    cfg_json = (active_map_cfg.config_json or {}) if active_map_cfg else {}
    map_cfg = map_adapter.get_client_tile_config(
        custom_tile_url=str(cfg_json.get("custom_tile_url") or ""),
        api_key=str(creds.get("api_key") or ""),
    )
    return {
        "countries": list(Country.objects.filter(is_active=True).order_by("code")),
        "currencies": list(Currency.objects.filter(is_active=True).order_by("code")),
        "map_provider": {
            "provider_key": map_cfg.provider_key,
            "display_name": active_map_cfg.display_name if active_map_cfg else map_cfg.display_name,
            "tile_url": map_cfg.tile_url,
            "dark_tile_url": map_cfg.dark_tile_url,
            "attribution": map_cfg.attribution,
            "max_zoom": map_cfg.max_zoom,
            "requires_api_key": map_cfg.requires_api_key,
        },
        "available_adapters": {
            "payment": [
                {
                    "key": k,
                    "name": cls.display_name,
                    "supports_sandbox": cls.supports_sandbox,
                    "required_fields": cls.required_credential_fields,
                }
                for k, cls in PAYMENT_PROVIDERS.items()
            ],
            "map": [
                {"key": k, "name": cls.display_name}
                for k, cls in MAP_PROVIDERS.items()
            ],
            "ai": [
                {"key": k, "name": cls.display_name}
                for k, cls in AI_PROVIDERS.items()
            ],
            "sms": [
                {"key": k, "name": getattr(cls, "display_name", k)}
                for k, cls in SMS_PROVIDERS.items()
            ],
        },
    }


def list_provider_configs(
    *, user: User, agency_id: Optional[UUID], category: Optional[str] = None
) -> list[ProviderConfiguration]:
    if agency_id:
        if not (is_super_admin(user) or has_agency_permission(user, agency_id, "agency.manage_policy")):
            raise PermissionDeniedDomainError("عدم دسترسی به تنظیمات ارائه‌دهندگان آژانس.")
        qs = ProviderConfiguration.objects.filter(agency_id__in=[None, agency_id])
    elif is_super_admin(user):
        qs = ProviderConfiguration.objects.filter(agency__isnull=True)
    else:
        raise PermissionDeniedDomainError("عدم دسترسی به تنظیمات سراسری ارائه‌دهندگان.")
    if category:
        qs = qs.filter(category=category)
    return list(qs.order_by("category", "-is_active", "priority", "provider_key"))


@transaction.atomic
def upsert_provider_config(*, user: User, agency_id: Optional[UUID], data: dict) -> ProviderConfiguration:
    target_agency_id = agency_id
    if target_agency_id:
        if not (is_super_admin(user) or has_agency_permission(user, target_agency_id, "agency.manage_policy")):
            raise PermissionDeniedDomainError("عدم مجوز تنظیم ارائه‌دهندگان.")
    elif not is_super_admin(user):
        raise PermissionDeniedDomainError("فقط مدیر کل مجاز به تنظیم ارائه‌دهندگان پلتفرم است.")

    category = data["category"]
    provider_key = data["provider_key"]
    is_active = bool(data.get("is_active", True))

    if is_active and category in (
        ProviderConfiguration.Category.MAP,
        ProviderConfiguration.Category.SMS,
        ProviderConfiguration.Category.AI,
    ):
        ProviderConfiguration.objects.filter(agency_id=target_agency_id, category=category).update(is_active=False)

    cfg, _ = ProviderConfiguration.objects.update_or_create(
        agency_id=target_agency_id,
        category=category,
        provider_key=provider_key,
        defaults={
            "display_name": data["display_name"],
            "description": data.get("description", ""),
            "priority": int(data.get("priority", 10)),
            "is_active": is_active,
            "is_sandbox": bool(data.get("is_sandbox", True)),
            "config_json": data.get("config_json", {}),
            "created_by": user,
            "updated_by": user,
        },
    )
    if data.get("credentials"):
        existing = parse_provider_credentials(cfg)
        for k, v in data["credentials"].items():
            if v is not None and str(v).strip() and "****" not in str(v):
                existing[k] = str(v).strip()
        cfg.set_credentials(json.dumps(existing))
        cfg.save(update_fields=["encrypted_credentials", "updated_at"])

    record_audit_event(
        action="PROVIDER_CONFIG_UPDATED",
        resource_type="ProviderConfiguration",
        resource_id=str(cfg.id),
        actor=user,
        agency_id=target_agency_id,
        after_state={
            "category": category,
            "provider_key": provider_key,
            "is_active": is_active,
            "is_sandbox": cfg.is_sandbox,
        },
    )
    return cfg


@transaction.atomic
def test_provider_config(*, user: User, agency_id: Optional[UUID], config_id: UUID) -> dict:
    cfg = ProviderConfiguration.objects.filter(id=config_id).first()
    if not cfg:
        raise NotFoundDomainError("پیکربندی درگاه یا سرویس یافت نشد.")
    if cfg.agency_id:
        if not (is_super_admin(user) or has_agency_permission(user, cfg.agency_id, "agency.manage_policy")):
            raise PermissionDeniedDomainError("عدم مجوز تست اتصال این سرویس.")
    elif not is_super_admin(user) and not (agency_id and has_agency_permission(user, agency_id, "agency.manage_policy")):
        raise PermissionDeniedDomainError("عدم مجوز تست اتصال سرویس سراسری.")

    creds = parse_provider_credentials(cfg)
    result = {"ok": True, "status": "READY", "message": "پیکربندی معتبر است."}

    if cfg.category == ProviderConfiguration.Category.PAYMENT:
        adapter = get_payment_provider(cfg.provider_key)
        res = adapter.test_connection(credentials=creds, is_sandbox=cfg.is_sandbox)
        result = {"ok": res.ok, "status": res.status, "message": res.message}
    elif cfg.category == ProviderConfiguration.Category.AI:
        adapter = get_ai_provider(cfg.provider_key)
        res = adapter.check_health(
            api_key=str(creds.get("api_key") or ""),
            base_url=str((cfg.config_json or {}).get("base_url") or ""),
        )
        result = {
            "ok": bool(res.get("configured")),
            "status": "CONNECTED" if res.get("configured") else "FALLBACK_ENGINE",
            "message": str(res.get("message") or ""),
        }
    elif cfg.category == ProviderConfiguration.Category.MAP:
        adapter = get_map_provider(cfg.provider_key)
        tile_cfg = adapter.get_client_tile_config(
            custom_tile_url=str((cfg.config_json or {}).get("custom_tile_url") or ""),
            api_key=str(creds.get("api_key") or ""),
        )
        ok_status = bool(tile_cfg.tile_url) and (not tile_cfg.requires_api_key or bool(creds.get("api_key")))
        result = {
            "ok": ok_status,
            "status": "READY" if ok_status else "FALLBACK_OSM",
            "message": f"سرویس نقشه {tile_cfg.display_name} آماده است.",
        }

    cfg.last_checked_at = timezone.now()
    cfg.last_check_status = result["status"]
    cfg.last_check_message = result["message"][:255]
    cfg.save(update_fields=["last_checked_at", "last_check_status", "last_check_message", "updated_at"])
    return result


# ==============================================================================
# Hierarchical Geography Services (Province -> City -> District -> Neighborhood)
# ==============================================================================


def _assert_geo_manager(user: User, agency_id: Optional[UUID] = None) -> None:
    if is_super_admin(user):
        return
    if agency_id and has_agency_permission(user, agency_id, "agency.manage_policy"):
        return
    raise PermissionDeniedDomainError("فقط مدیر مجاز امکان ایجاد یا ویرایش اطلاعات جغرافیایی را دارد.")


def list_provinces(*, country_id: str = "IR", q: Optional[str] = None, active_only: bool = True):
    qs = Province.objects.filter(country_id=country_id)
    if active_only:
        qs = qs.filter(is_active=True)
    if q:
        qs = qs.filter(models.Q(name_fa__icontains=q.strip()) | models.Q(name_en__icontains=q.strip()))
    return qs.order_by("sort_order", "name_fa")


def list_cities(*, province_id: Optional[UUID] = None, q: Optional[str] = None, active_only: bool = True):
    qs = City.objects.select_related("province")
    if province_id:
        qs = qs.filter(province_id=province_id)
    if active_only:
        qs = qs.filter(is_active=True, province__is_active=True)
    if q:
        qs = qs.filter(models.Q(name_fa__icontains=q.strip()) | models.Q(name_en__icontains=q.strip()))
    return qs.order_by("sort_order", "name_fa")


def list_districts(*, city_id: Optional[UUID] = None, q: Optional[str] = None, active_only: bool = True):
    qs = District.objects.select_related("city__province")
    if city_id:
        qs = qs.filter(city_id=city_id)
    if active_only:
        qs = qs.filter(is_active=True, city__is_active=True)
    if q:
        qs = qs.filter(models.Q(name_fa__icontains=q.strip()) | models.Q(name_en__icontains=q.strip()))
    return qs.order_by("sort_order", "name_fa")


def list_neighborhoods(*, district_id: Optional[UUID] = None, city_id: Optional[UUID] = None, q: Optional[str] = None, active_only: bool = True):
    qs = Neighborhood.objects.select_related("district__city__province")
    if district_id:
        qs = qs.filter(district_id=district_id)
    if city_id:
        qs = qs.filter(district__city_id=city_id)
    if active_only:
        qs = qs.filter(is_active=True, district__is_active=True)
    if q:
        qs = qs.filter(models.Q(name_fa__icontains=q.strip()) | models.Q(name_en__icontains=q.strip()))
    return qs.order_by("sort_order", "name_fa")


def resolve_location_hierarchy(
    *,
    province_id: Optional[UUID] = None,
    city_id: Optional[UUID] = None,
    district_id: Optional[UUID] = None,
    neighborhood_id: Optional[UUID] = None,
) -> tuple[Optional[Province], Optional[City], Optional[District], Optional[Neighborhood]]:
    prov = Province.objects.filter(id=province_id, is_active=True).first() if province_id else None
    if province_id and not prov:
        raise ValidationDomainError("استان انتخاب‌شده معتبر یا فعال نیست.")

    city = City.objects.select_related("province").filter(id=city_id, is_active=True).first() if city_id else None
    if city_id and not city:
        raise ValidationDomainError("شهر انتخاب‌شده معتبر یا فعال نیست.")
    if city:
        if prov and city.province_id != prov.id:
            raise ValidationDomainError("شهر انتخاب‌شده متعلق به استان انتخابی نیست.")
        prov = prov or city.province

    district = (
        District.objects.select_related("city__province").filter(id=district_id, is_active=True).first()
        if district_id
        else None
    )
    if district_id and not district:
        raise ValidationDomainError("منطقه انتخاب‌شده معتبر یا فعال نیست.")
    if district:
        if city and district.city_id != city.id:
            raise ValidationDomainError("منطقه انتخاب‌شده متعلق به شهر انتخابی نیست.")
        city = city or district.city
        if prov and city.province_id != prov.id:
            raise ValidationDomainError("منطقه انتخاب‌شده با استان هم‌خوانی ندارد.")
        prov = prov or city.province

    neighborhood = (
        Neighborhood.objects.select_related("district__city__province")
        .filter(id=neighborhood_id, is_active=True)
        .first()
        if neighborhood_id
        else None
    )
    if neighborhood_id and not neighborhood:
        raise ValidationDomainError("محله انتخاب‌شده معتبر یا فعال نیست.")
    if neighborhood:
        if district and neighborhood.district_id != district.id:
            raise ValidationDomainError("محله انتخاب‌شده متعلق به منطقه انتخابی نیست.")
        district = district or neighborhood.district
        if city and district.city_id != city.id:
            raise ValidationDomainError("محله انتخاب‌شده با شهر هم‌خوانی ندارد.")
        city = city or district.city
        prov = prov or city.province

    return prov, city, district, neighborhood


@transaction.atomic
def create_province(*, user: User, agency_id: Optional[UUID], data: dict) -> Province:
    _assert_geo_manager(user, agency_id)
    name_fa = data["name_fa"].strip()
    country_id = data.get("country_id", "IR")
    if Province.objects.filter(country_id=country_id, name_fa=name_fa).exists():
        raise ConflictDomainError("این استان قبلاً ثبت شده است.")
    return Province.objects.create(
        country_id=country_id,
        code=data.get("code", ""),
        name_fa=name_fa,
        name_en=data.get("name_en", ""),
        slug=data.get("slug") or _safe_slug(data.get("name_en", ""), name_fa, "prov"),
        center_lat=data.get("center_lat"),
        center_lng=data.get("center_lng"),
        sort_order=int(data.get("sort_order", 100)),
        is_active=bool(data.get("is_active", True)),
        created_by=user,
    )


@transaction.atomic
def create_city(*, user: User, agency_id: Optional[UUID], data: dict) -> City:
    _assert_geo_manager(user, agency_id)
    prov = Province.objects.filter(id=data["province_id"]).first()
    if not prov:
        raise NotFoundDomainError("استان والد یافت نشد.")
    name_fa = data["name_fa"].strip()
    if City.objects.filter(province=prov, name_fa=name_fa).exists():
        raise ConflictDomainError("این شهر در استان انتخاب‌شده قبلاً ثبت شده است.")
    return City.objects.create(
        province=prov,
        name_fa=name_fa,
        name_en=data.get("name_en", ""),
        slug=data.get("slug") or _safe_slug(data.get("name_en", ""), name_fa, f"city-{prov.code or 'ir'}"),
        center_lat=data.get("center_lat"),
        center_lng=data.get("center_lng"),
        sort_order=int(data.get("sort_order", 100)),
        is_active=bool(data.get("is_active", True)),
        created_by=user,
    )


@transaction.atomic
def create_district(*, user: User, agency_id: Optional[UUID], data: dict) -> District:
    _assert_geo_manager(user, agency_id)
    city = City.objects.filter(id=data["city_id"]).first()
    if not city:
        raise NotFoundDomainError("شهر والد یافت نشد.")
    name_fa = data["name_fa"].strip()
    if District.objects.filter(city=city, name_fa=name_fa).exists():
        raise ConflictDomainError("این منطقه در شهر انتخاب‌شده قبلاً ثبت شده است.")
    return District.objects.create(
        city=city,
        name_fa=name_fa,
        name_en=data.get("name_en", ""),
        slug=data.get("slug") or _safe_slug(data.get("name_en", ""), name_fa, "dist"),
        center_lat=data.get("center_lat"),
        center_lng=data.get("center_lng"),
        sort_order=int(data.get("sort_order", 100)),
        is_active=bool(data.get("is_active", True)),
        created_by=user,
    )


@transaction.atomic
def create_neighborhood(*, user: User, agency_id: Optional[UUID], data: dict) -> Neighborhood:
    _assert_geo_manager(user, agency_id)
    district = District.objects.filter(id=data["district_id"]).first()
    if not district:
        raise NotFoundDomainError("منطقه والد یافت نشد.")
    name_fa = data["name_fa"].strip()
    if Neighborhood.objects.filter(district=district, name_fa=name_fa).exists():
        raise ConflictDomainError("این محله در منطقه انتخاب‌شده قبلاً ثبت شده است.")
    return Neighborhood.objects.create(
        district=district,
        name_fa=name_fa,
        name_en=data.get("name_en", ""),
        slug=data.get("slug") or _safe_slug(data.get("name_en", ""), name_fa, "nbr"),
        center_lat=data.get("center_lat"),
        center_lng=data.get("center_lng"),
        sort_order=int(data.get("sort_order", 100)),
        is_active=bool(data.get("is_active", True)),
        created_by=user,
    )


@transaction.atomic
def toggle_geo_node(*, user: User, agency_id: Optional[UUID], level: str, node_id: UUID, is_active: Optional[bool] = None, name_fa: Optional[str] = None):
    _assert_geo_manager(user, agency_id)
    model_map = {
        "province": Province,
        "city": City,
        "district": District,
        "neighborhood": Neighborhood,
    }
    cls = model_map.get(level)
    if not cls:
        raise ValidationDomainError("سطح جغرافیایی نامعتبر است.")
    node = cls.objects.filter(id=node_id).first()
    if not node:
        raise NotFoundDomainError("آیتم جغرافیایی یافت نشد.")
    if is_active is not None:
        node.is_active = bool(is_active)
    if name_fa is not None and name_fa.strip():
        node.name_fa = name_fa.strip()
    node.updated_by = user
    node.save()
    return node

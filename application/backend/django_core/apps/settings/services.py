from decimal import Decimal
import json
import os
import re
from typing import Any, Optional
from uuid import UUID
from django.core.cache import cache
from django.db import connection, models, transaction
from django.utils import timezone
from django.utils.text import slugify
import redis as redis_lib
from apps.accounts.models import User, UserSession
from apps.audit.services import record_audit_event
from common.exceptions import (
    ConflictDomainError,
    NotFoundDomainError,
    PermissionDeniedDomainError,
    ValidationDomainError,
)
from common.localization.currency import invalidate_currency_cache
from common.tenant.context import tenant_bypass
from common.permissions import has_agency_permission, is_super_admin
from common.sanitizer import sanitize_html
from integrations.registry import (
    AI_PROVIDERS,
    MAP_PROVIDERS,
    PAYMENT_PROVIDERS,
    SMS_PROVIDERS,
    get_ai_provider,
    get_map_provider,
    get_payment_provider,
    get_sms_provider,
    get_storage_provider,
)
from integrations.storage import validate_uploaded_file
from .models import (
    BrandMediaSlot,
    CalendarSystem,
    City,
    Country,
    Currency,
    District,
    ExchangeRate,
    ExchangeRateHistory,
    Neighborhood,
    ProviderConfiguration,
    Province,
    SiteContentBlock,
    SystemSetting,
    SystemSettingHistory,
)

SETTINGS_CACHE_PREFIX = "bonyan:settings:"
PUBLIC_BOOTSTRAP_CACHE_PREFIX = "bonyan:public_bootstrap:"
RATE_LIMITS_REDIS_KEY = "bonyan:security:rate_limits"


def _safe_slug(name_en: str, name_fa: str, prefix: str = "") -> str:
    base = slugify(name_en or "", allow_unicode=False)
    if not base:
        clean = re.sub(r"[^\w\s-]", "", name_fa or "").strip().replace(" ", "-")
        base = clean or "loc"
    return f"{prefix}-{base}".strip("-")[:110]


SETTINGS_CACHE_VERSION_KEY = f"{SETTINGS_CACHE_PREFIX}version"


def _get_settings_cache_version() -> int:
    try:
        ver = cache.get(SETTINGS_CACHE_VERSION_KEY)
        if ver is None:
            cache.set(SETTINGS_CACHE_VERSION_KEY, 1, timeout=None)
            return 1
        return int(ver)
    except Exception:
        return 1


def invalidate_settings_cache(key: Optional[str] = None) -> None:
    try:
        try:
            cache.incr(SETTINGS_CACHE_VERSION_KEY)
        except Exception:
            cur = cache.get(SETTINGS_CACHE_VERSION_KEY) or 1
            cache.set(SETTINGS_CACHE_VERSION_KEY, int(cur) + 1, timeout=None)
        if key:
            cache.delete(f"{SETTINGS_CACHE_PREFIX}val:{key}")
        cache.delete(f"{PUBLIC_BOOTSTRAP_CACHE_PREFIX}global")
    except Exception:
        pass


def invalidate_public_bootstrap_cache(agency_id: Optional[UUID] = None) -> None:
    try:
        cache.delete(f"{PUBLIC_BOOTSTRAP_CACHE_PREFIX}global")
        if agency_id:
            cache.delete(f"{PUBLIC_BOOTSTRAP_CACHE_PREFIX}{agency_id}")
    except Exception:
        pass


def _sync_rate_limits_to_redis() -> None:
    try:
        redis_url = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")
        default_rpm = int(get_setting_value("security.rate_limit_default_rpm", 180) or 180)
        auth_rpm = int(get_setting_value("security.rate_limit_auth_rpm", 30) or 30)
        window_sec = int(get_setting_value("security.rate_limit_window_seconds", 60) or 60)
        client = redis_lib.Redis.from_url(redis_url, socket_connect_timeout=1)
        client.set(
            RATE_LIMITS_REDIS_KEY,
            json.dumps(
                {
                    "default_limit": max(10, default_rpm),
                    "auth_limit": max(5, auth_rpm),
                    "window_seconds": max(10, window_sec),
                }
            ),
            ex=3600,
        )
    except Exception:
        pass


def _extract_setting_typed_value(setting: SystemSetting) -> Any:
    if setting.value_type == SystemSetting.ValueType.SECRET:
        return setting.get_secret()
    raw = (setting.value_json or {}).get("value")
    if raw is None and setting.default_value_json:
        raw = setting.default_value_json.get("value")
    if setting.value_type == SystemSetting.ValueType.INTEGER and raw is not None:
        try:
            return int(raw)
        except Exception:
            return raw
    if setting.value_type == SystemSetting.ValueType.DECIMAL and raw is not None:
        try:
            return Decimal(str(raw))
        except Exception:
            return raw
    if setting.value_type == SystemSetting.ValueType.BOOLEAN:
        if isinstance(raw, bool):
            return raw
        return str(raw).lower() in ("true", "1", "yes", "on")
    return raw


def get_setting_value(
    key: str,
    default: Any = None,
    *,
    agency_id: Optional[UUID] = None,
    country_code: Optional[str] = None,
) -> Any:
    """مقدار فعال آژانس را با پیش‌فرض سراسری همان کلید تطبیق می‌دهد."""
    ver = _get_settings_cache_version()
    cache_key = f"{SETTINGS_CACHE_PREFIX}v{ver}:val:{key}:{agency_id or 'g'}:{country_code or 'all'}"
    try:
        cached = cache.get(cache_key)
        if cached is not None and isinstance(cached, dict) and "v" in cached:
            return cached["v"]
    except Exception:
        pass

    try:
        settings_query = SystemSetting.objects.filter(key=key, is_active=True)
        candidates = list(settings_query.filter(agency_id=agency_id)) if agency_id else []
        with tenant_bypass(reason="system_configuration"):
            candidates.extend(settings_query.filter(agency__isnull=True))
    except Exception:
        return default

    if not candidates:
        return default

    cc = (country_code or "").upper()
    best: Optional[SystemSetting] = None
    best_rank = -1
    for item in candidates:
        rank = 0
        if item.agency_id and agency_id and item.agency_id == agency_id:
            rank += 4
        elif item.agency_id is not None:
            continue
        if item.country_code and cc and item.country_code.upper() == cc:
            rank += 2
        elif item.country_code:
            continue
        if rank > best_rank:
            best_rank = rank
            best = item

    if not best:
        return default

    val = _extract_setting_typed_value(best)
    result = default if val is None else val
    if best.value_type != SystemSetting.ValueType.SECRET:
        try:
            cache.set(cache_key, {"v": str(result) if isinstance(result, Decimal) else result}, timeout=120)
        except Exception:
            pass
    return result


def serialize_system_setting(s: SystemSetting) -> dict:
    is_secret = (
        s.value_type == SystemSetting.ValueType.SECRET
        or s.sensitivity_level == SystemSetting.SensitivityLevel.SECRET
    )
    if is_secret:
        has_secret = bool(s.encrypted_value)
        val_display = "****" if has_secret else ""
        def_display = ""
    else:
        val_display = (s.value_json or {}).get("value")
        def_display = (s.default_value_json or {}).get("value")

    return {
        "id": str(s.id),
        "key": s.key,
        "agency_id": str(s.agency_id) if s.agency_id else None,
        "country_code": s.country_code,
        "title_fa": s.title_fa,
        "title_en": s.title_en,
        "description": s.description,
        "category": s.category,
        "subcategory": s.subcategory,
        "value_type": s.value_type,
        "value": val_display,
        "default_value": def_display,
        "has_secret_value": bool(s.encrypted_value) if is_secret else False,
        "validation_schema": s.validation_schema or {},
        "is_active": s.is_active,
        "sensitivity_level": s.sensitivity_level,
        "is_editable": s.is_editable,
        "requires_restart": s.requires_restart,
        "sort_order": s.sort_order,
        "updated_at": s.updated_at.isoformat(),
    }


def list_system_settings(
    *,
    user: User,
    agency_id: Optional[UUID] = None,
    category: Optional[str] = None,
    country_code: Optional[str] = None,
    q: Optional[str] = None,
) -> list[SystemSetting]:
    if not is_super_admin(user):
        raise PermissionDeniedDomainError("مرکز تنظیمات سیستم فقط برای مدیر کل مجاز است.")

    qs = SystemSetting.objects.all()
    if is_super_admin(user):
        if agency_id:
            qs = qs.filter(models.Q(agency_id=agency_id) | models.Q(agency__isnull=True))
        else:
            qs = qs.filter(agency__isnull=True)
    else:
        qs = qs.filter(models.Q(agency_id=agency_id) | models.Q(agency__isnull=True)).exclude(
            sensitivity_level=SystemSetting.SensitivityLevel.SECRET
        )

    if category:
        qs = qs.filter(category=category)
    if country_code:
        qs = qs.filter(country_code=country_code.upper())
    if q:
        clean = q.strip()
        qs = qs.filter(
            models.Q(key__icontains=clean)
            | models.Q(title_fa__icontains=clean)
            | models.Q(title_en__icontains=clean)
            | models.Q(description__icontains=clean)
        )
    rows = list(qs.order_by("category", "sort_order", "key"))
    if agency_id:
        merged: dict[tuple[str, str], SystemSetting] = {}
        for item in rows:
            map_key = (item.key, item.country_code)
            existing = merged.get(map_key)
            if existing is None or (item.agency_id is not None and existing.agency_id is None):
                merged[map_key] = item
        return sorted(merged.values(), key=lambda x: (x.category, x.sort_order, x.key))
    return rows


def _validate_and_coerce_setting_value(setting: SystemSetting, raw_value: Any) -> Any:
    vtype = setting.value_type
    schema = setting.validation_schema or {}

    if vtype == SystemSetting.ValueType.BOOLEAN:
        if isinstance(raw_value, bool):
            return raw_value
        s = str(raw_value).strip().lower()
        if s in ("true", "1", "yes", "on"):
            return True
        if s in ("false", "0", "no", "off"):
            return False
        raise ValidationDomainError(f"مقدار نامعتبر برای تنظیم بولی «{setting.title_fa}».")

    if vtype == SystemSetting.ValueType.INTEGER:
        try:
            num = int(raw_value)
        except Exception as exc:
            raise ValidationDomainError(f"مقدار «{setting.title_fa}» باید عدد صحیح باشد.") from exc
        if "min" in schema and num < int(schema["min"]):
            raise ValidationDomainError(f"مقدار «{setting.title_fa}» نباید کمتر از {schema['min']} باشد.")
        if "max" in schema and num > int(schema["max"]):
            raise ValidationDomainError(f"مقدار «{setting.title_fa}» نباید بیشتر از {schema['max']} باشد.")
        return num

    if vtype == SystemSetting.ValueType.DECIMAL:
        try:
            dec = Decimal(str(raw_value))
        except Exception as exc:
            raise ValidationDomainError(f"مقدار «{setting.title_fa}» باید عدد اعشاری معتبر باشد.") from exc
        if "min" in schema and dec < Decimal(str(schema["min"])):
            raise ValidationDomainError(f"مقدار «{setting.title_fa}» نباید کمتر از {schema['min']} باشد.")
        if "max" in schema and dec > Decimal(str(schema["max"])):
            raise ValidationDomainError(f"مقدار «{setting.title_fa}» نباید بیشتر از {schema['max']} باشد.")
        return str(dec)

    if vtype == SystemSetting.ValueType.SELECT:
        val_str = str(raw_value).strip()
        # Keep the visual-style registry forward-compatible on existing databases:
        # deployments must not require a seed run just to accept the new presets.
        if setting.key == "branding.default_theme_preset":
            valid_vals = ["glass", "neo", "organic", "custom"]
        else:
            choices = schema.get("choices") or []
            valid_vals = [c.get("value") if isinstance(c, dict) else c for c in choices]
        if valid_vals and val_str not in valid_vals:
            raise ValidationDomainError(f"مقدار انتخاب‌شده برای «{setting.title_fa}» در گزینه‌های مجاز نیست.")
        return val_str

    if vtype == SystemSetting.ValueType.JSON:
        if isinstance(raw_value, (dict, list)):
            return raw_value
        try:
            return json.loads(str(raw_value))
        except Exception as exc:
            raise ValidationDomainError(f"ساختار JSON برای «{setting.title_fa}» نامعتبر است.") from exc

    return str(raw_value) if raw_value is not None else ""


@transaction.atomic
def bulk_update_system_settings(
    *,
    user: User,
    agency_id: Optional[UUID],
    updates: list[dict],
    change_reason: str = "",
) -> list[SystemSetting]:
    if not updates:
        raise ValidationDomainError("لیست تغییرات تنظیمات خالی است.")
    target_agency_id = agency_id if (agency_id and not is_super_admin(user)) else agency_id
    if target_agency_id:
        if not is_super_admin(user):
            raise PermissionDeniedDomainError("ویرایش تنظیمات فقط برای مدیر کل مجاز است.")
    elif not is_super_admin(user):
        raise PermissionDeniedDomainError("فقط مدیر کل مجاز به ویرایش تنظیمات سراسری پلتفرم است.")

    updated_items: list[SystemSetting] = []
    rate_limit_touched = False

    for item in updates:
        key = str(item.get("key") or "").strip()
        if not key:
            continue
        base_setting = SystemSetting.objects.filter(
            key=key, agency__isnull=True, country_code=""
        ).first()
        if not base_setting:
            base_setting = SystemSetting.objects.filter(key=key).first()
        if not base_setting:
            if not is_super_admin(user) or not item.get("create_if_missing"):
                raise NotFoundDomainError(f"کلید تنظیمات «{key}» یافت نشد.")
            base_setting = SystemSetting.objects.create(
                key=key,
                agency_id=target_agency_id,
                country_code=str(item.get("country_code") or "").upper(),
                title_fa=str(item.get("title_fa") or key),
                title_en=str(item.get("title_en") or key),
                description=str(item.get("description") or ""),
                category=str(item.get("category") or "GENERAL").upper(),
                subcategory=str(item.get("subcategory") or "GENERAL").upper(),
                value_type=str(item.get("value_type") or SystemSetting.ValueType.STRING),
                value_json={"value": item.get("value", "")},
                default_value_json={"value": item.get("value", "")},
                sensitivity_level=str(item.get("sensitivity_level") or SystemSetting.SensitivityLevel.INTERNAL),
                is_editable=True,
                created_by=user,
            )

        if not base_setting.is_editable:
            raise PermissionDeniedDomainError(f"تنظیم «{base_setting.title_fa}» قفل‌شده و غیرقابل ویرایش است.")
        if not is_super_admin(user) and base_setting.sensitivity_level == SystemSetting.SensitivityLevel.SECRET:
            raise PermissionDeniedDomainError("دسترسی به تنظیمات محرمانه فقط برای مدیر کل مجاز است.")

        cc = str(item.get("country_code") or "").upper()
        if target_agency_id or cc:
            setting, _ = SystemSetting.objects.get_or_create(
                key=key,
                agency_id=target_agency_id,
                country_code=cc,
                defaults={
                    "title_fa": base_setting.title_fa,
                    "title_en": base_setting.title_en,
                    "description": base_setting.description,
                    "category": base_setting.category,
                    "subcategory": base_setting.subcategory,
                    "value_type": base_setting.value_type,
                    "value_json": dict(base_setting.value_json or {}),
                    "default_value_json": dict(base_setting.default_value_json or {}),
                    "validation_schema": dict(base_setting.validation_schema or {}),
                    "sensitivity_level": base_setting.sensitivity_level,
                    "is_editable": base_setting.is_editable,
                    "requires_restart": base_setting.requires_restart,
                    "sort_order": base_setting.sort_order,
                    "created_by": user,
                },
            )
        else:
            setting = base_setting

        is_secret = (
            setting.value_type == SystemSetting.ValueType.SECRET
            or setting.sensitivity_level == SystemSetting.SensitivityLevel.SECRET
        )
        raw_val = item.get("value")

        if is_secret:
            s_val = str(raw_val or "").strip()
            if not s_val or "****" in s_val:
                continue
            prev_masked = {"value": "****" if setting.encrypted_value else ""}
            setting.set_secret(s_val)
            setting.updated_by = user
            setting.save(update_fields=["encrypted_value", "value_json", "updated_by", "updated_at"])
            new_masked = {"value": "****"}
        else:
            coerced = _validate_and_coerce_setting_value(setting, raw_val)
            prev_masked = dict(setting.value_json or {})
            new_masked = {"value": coerced}
            setting.value_json = new_masked
            setting.updated_by = user
            setting.save(update_fields=["value_json", "updated_by", "updated_at"])

        SystemSettingHistory.objects.create(
            setting_key=setting.key,
            agency_id_snapshot=setting.agency_id,
            previous_value_json=prev_masked,
            new_value_json=new_masked,
            is_secret=is_secret,
            change_reason=change_reason[:255] or "به‌روزرسانی از پنل تنظیمات",
            changed_by=user,
            created_by=user,
        )
        record_audit_event(
            action="SYSTEM_SETTING_UPDATED",
            resource_type="SystemSetting",
            resource_id=setting.key,
            actor=user,
            agency_id=setting.agency_id,
            before_state={"value": "****"} if is_secret else prev_masked,
            after_state={"value": "****"} if is_secret else new_masked,
            metadata={"reason": change_reason[:200]},
        )
        invalidate_settings_cache(setting.key)
        if setting.key.startswith("security.rate_limit"):
            rate_limit_touched = True
        updated_items.append(setting)

    invalidate_public_bootstrap_cache(target_agency_id)
    if rate_limit_touched:
        _sync_rate_limits_to_redis()
    return updated_items


@transaction.atomic
def reset_system_setting_to_default(
    *, user: User, setting_id: UUID, change_reason: str = ""
) -> SystemSetting:
    setting = SystemSetting.objects.filter(id=setting_id).first()
    if not setting:
        raise NotFoundDomainError("تنظیم مورد نظر یافت نشد.")
    if setting.agency_id:
        if not is_super_admin(user):
            raise PermissionDeniedDomainError("عدم مجوز بازنشانی تنظیم آژانس.")
    elif not is_super_admin(user):
        raise PermissionDeniedDomainError("فقط مدیر کل مجاز به بازنشانی تنظیمات پلتفرم است.")

    if setting.value_type == SystemSetting.ValueType.SECRET:
        raise ValidationDomainError("تنظیمات محرمانه قابلیت بازنشانی خودکار به مقدار پیش‌فرض ندارند.")

    prev = dict(setting.value_json or {})
    setting.value_json = dict(setting.default_value_json or {})
    setting.updated_by = user
    setting.save(update_fields=["value_json", "updated_by", "updated_at"])

    SystemSettingHistory.objects.create(
        setting_key=setting.key,
        agency_id_snapshot=setting.agency_id,
        previous_value_json=prev,
        new_value_json=setting.value_json,
        is_secret=False,
        change_reason=change_reason[:255] or "بازنشانی به مقدار پیش‌فرض",
        changed_by=user,
        created_by=user,
    )
    record_audit_event(
        action="SYSTEM_SETTING_RESET",
        resource_type="SystemSetting",
        resource_id=setting.key,
        actor=user,
        agency_id=setting.agency_id,
        before_state=prev,
        after_state=setting.value_json,
    )
    invalidate_settings_cache(setting.key)
    invalidate_public_bootstrap_cache(setting.agency_id)
    if setting.key.startswith("security.rate_limit"):
        _sync_rate_limits_to_redis()
    return setting


@transaction.atomic
def rollback_system_setting(*, user: User, history_id: UUID) -> SystemSetting:
    if not is_super_admin(user):
        raise PermissionDeniedDomainError("فقط مدیر کل مجاز به بازگشت نسخه تنظیمات است.")
    hist = SystemSettingHistory.objects.filter(id=history_id).first()
    if not hist:
        raise NotFoundDomainError("رکورد تاریخچه تنظیمات یافت نشد.")
    if hist.is_secret:
        raise ValidationDomainError("بازگشت مقدار برای تنظیمات محرمانه مجاز نیست.")
    setting = SystemSetting.objects.filter(
        key=hist.setting_key, agency_id=hist.agency_id_snapshot
    ).first()
    if not setting:
        raise NotFoundDomainError("تنظیم متناظر یافت نشد.")

    prev = dict(setting.value_json or {})
    setting.value_json = dict(hist.previous_value_json or {})
    setting.updated_by = user
    setting.save(update_fields=["value_json", "updated_by", "updated_at"])

    SystemSettingHistory.objects.create(
        setting_key=setting.key,
        agency_id_snapshot=setting.agency_id,
        previous_value_json=prev,
        new_value_json=setting.value_json,
        is_secret=False,
        change_reason=f"بازگشت به نسخه قبلی ({str(hist.id)[:8]})",
        changed_by=user,
        created_by=user,
    )
    invalidate_settings_cache(setting.key)
    invalidate_public_bootstrap_cache(setting.agency_id)
    if setting.key.startswith("security.rate_limit"):
        _sync_rate_limits_to_redis()
    return setting


def list_setting_history(
    *, user: User, agency_id: Optional[UUID] = None, setting_key: Optional[str] = None
) -> list[SystemSettingHistory]:
    if not is_super_admin(user):
        raise PermissionDeniedDomainError("عدم دسترسی به تاریخچه تغییرات تنظیمات.")
    qs = SystemSettingHistory.objects.select_related("changed_by")
    if not is_super_admin(user):
        qs = qs.filter(agency_id_snapshot=agency_id, is_secret=False)
    elif agency_id:
        qs = qs.filter(agency_id_snapshot=agency_id)
    if setting_key:
        qs = qs.filter(setting_key=setting_key)
    return list(qs.order_by("-created_at")[:100])


def get_system_health(*, user: User) -> dict:
    if not is_super_admin(user):
        raise PermissionDeniedDomainError("فقط مدیر کل مجاز به مشاهده وضعیت سلامت و زیرساخت است.")

    db_ok = False
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
            db_ok = cur.fetchone() == (1,)
    except Exception:
        db_ok = False

    redis_ok = False
    try:
        r = redis_lib.Redis.from_url(os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0"), socket_connect_timeout=1)
        redis_ok = bool(r.ping())
    except Exception:
        redis_ok = False

    env_checks = [
        {"key": "DATABASE_URL", "label": "اتصال پایگاه‌داده PostgreSQL", "configured": bool(os.environ.get("DATABASE_URL"))},
        {"key": "REDIS_URL", "label": "سرویس حافظه Redis", "configured": bool(os.environ.get("REDIS_URL"))},
        {"key": "JWT_SIGNING_KEY", "label": "کلید امضای توکن JWT", "configured": bool(os.environ.get("JWT_SIGNING_KEY") or os.environ.get("SECRET_KEY"))},
        {"key": "FIELD_ENCRYPTION_KEY", "label": "کلید رمزنگاری فیلدهای محرمانه (Fernet)", "configured": bool(os.environ.get("FIELD_ENCRYPTION_KEY") or os.environ.get("SECRET_KEY"))},
        {"key": "VAPID_PUBLIC_KEY", "label": "کلید اعلان مرورگر (Web Push VAPID)", "configured": bool(os.environ.get("VAPID_PUBLIC_KEY"))},
        {"key": "S3_BUCKET_NAME", "label": "ذخیره‌سازی ابری S3 / MinIO", "configured": bool(os.environ.get("S3_BUCKET_NAME"))},
    ]

    providers = list(ProviderConfiguration.objects.filter(agency__isnull=True).order_by("category", "priority"))
    active_sessions_count = UserSession.objects.filter(revoked_at__isnull=True).count()
    suspicious_sessions_count = UserSession.objects.filter(revoked_at__isnull=True, is_suspicious=True).count()

    return {
        "database_ok": db_ok,
        "redis_ok": redis_ok,
        "environment_mode": os.environ.get("DJANGO_ENV", "development"),
        "settings_count": SystemSetting.objects.filter(agency__isnull=True).count(),
        "active_sessions_count": active_sessions_count,
        "suspicious_sessions_count": suspicious_sessions_count,
        "env_status": env_checks,
        "providers_summary": [
            {
                "category": p.category,
                "provider_key": p.provider_key,
                "display_name": p.display_name,
                "is_active": p.is_active,
                "is_sandbox": p.is_sandbox,
                "last_check_status": p.last_check_status or ("READY" if p.is_active else "INACTIVE"),
            }
            for p in providers
        ],
    }


# ==============================================================================
# Branding Media Slots & Site Content Blocks
# ==============================================================================


def list_brand_media_slots(*, include_inactive: bool = False) -> list[BrandMediaSlot]:
    qs = BrandMediaSlot.objects.all()
    if not include_inactive:
        qs = qs.filter(is_active=True)
    return list(qs.order_by("sort_order", "slot_key"))


@transaction.atomic
def upload_brand_media_slot(
    *,
    user: User,
    slot_key: str,
    filename: str,
    content_type: str,
    content: bytes,
    dark_variant: bool = False,
    alt_text: Optional[str] = None,
) -> BrandMediaSlot:
    if not is_super_admin(user):
        raise PermissionDeniedDomainError("فقط مدیر کل مجاز به بارگذاری رسانه‌های برند است.")
    clean_key = slot_key.strip().lower()
    if not clean_key:
        raise ValidationDomainError("شناسه جایگاه رسانه معتبر نیست.")
    slot, _ = BrandMediaSlot.objects.get_or_create(
        slot_key=clean_key,
        defaults={
            "title_fa": clean_key,
            "category": "BRANDING",
        },
    )

    safe_name, verified_mime = validate_uploaded_file(
        filename=filename, content_type=content_type, content=content
    )
    if not verified_mime.startswith("image/"):
        raise ValidationDomainError("فقط فایل‌های تصویری معتبر (PNG, JPG, WebP, ICO) برای رسانه برند مجاز هستند.")

    storage = get_storage_provider()
    stored = storage.put_bytes(
        key_prefix=f"platform/branding/{clean_key}",
        safe_filename=safe_name,
        content=content,
        mime_type=verified_mime,
    )
    if dark_variant:
        slot.dark_image_url = stored.url
    else:
        slot.image_url = stored.url
        slot.file_key = stored.file_key
    if alt_text is not None:
        slot.alt_text = alt_text[:200]
    slot.updated_by = user
    slot.save()

    record_audit_event(
        action="BRAND_MEDIA_UPLOADED",
        resource_type="BrandMediaSlot",
        resource_id=clean_key,
        actor=user,
        after_state={"url": stored.url, "dark_variant": dark_variant},
    )
    invalidate_public_bootstrap_cache()
    return slot


@transaction.atomic
def clear_brand_media_slot_image(
    *, user: User, slot_key: str, dark_variant: bool = False
) -> BrandMediaSlot:
    if not is_super_admin(user):
        raise PermissionDeniedDomainError("فقط مدیر کل مجاز به حذف تصویر رسانه برند است.")
    slot = BrandMediaSlot.objects.filter(slot_key=slot_key).first()
    if not slot:
        raise NotFoundDomainError("جایگاه رسانه برند یافت نشد.")
    if dark_variant:
        slot.dark_image_url = ""
    else:
        slot.image_url = ""
        slot.file_key = ""
    slot.updated_by = user
    slot.save()
    record_audit_event(
        action="BRAND_MEDIA_CLEARED",
        resource_type="BrandMediaSlot",
        resource_id=slot_key,
        actor=user,
        after_state={"dark_variant": dark_variant},
    )
    invalidate_public_bootstrap_cache()
    return slot


@transaction.atomic
def update_brand_media_slot(*, user: User, slot_key: str, data: dict) -> BrandMediaSlot:
    if not is_super_admin(user):
        raise PermissionDeniedDomainError("فقط مدیر کل مجاز به ویرایش جایگاه رسانه برند است.")
    slot, _ = BrandMediaSlot.objects.get_or_create(
        slot_key=slot_key,
        defaults={
            "title_fa": data.get("title_fa") or slot_key,
            "category": data.get("category") or "BRANDING",
        },
    )
    for field in ("title_fa", "description", "image_url", "dark_image_url", "alt_text", "category", "is_active", "sort_order"):
        if field in data and data[field] is not None:
            setattr(slot, field, data[field])
    slot.updated_by = user
    slot.save()
    invalidate_public_bootstrap_cache()
    return slot


def list_site_content_blocks(*, page_key: Optional[str] = None, published_only: bool = True) -> list[SiteContentBlock]:
    qs = SiteContentBlock.objects.all()
    if published_only:
        qs = qs.filter(status=SiteContentBlock.Status.PUBLISHED, is_active=True)
    if page_key:
        qs = qs.filter(page_key=page_key.upper())
    return list(qs.order_by("page_key", "sort_order", "slug_key"))


@transaction.atomic
def upsert_site_content_block(*, user: User, slug_key: str, data: dict) -> SiteContentBlock:
    if not is_super_admin(user):
        raise PermissionDeniedDomainError("فقط مدیر کل مجاز به ویرایش محتوای صفحات عمومی پلتفرم است.")
    clean_slug = slug_key.strip().lower()
    body_html = sanitize_html(data.get("body_html") or "") if "body_html" in data else None

    defaults: dict[str, Any] = {
        "page_key": str(data.get("page_key") or "HOME").upper(),
        "section_key": str(data.get("section_key") or "GENERAL").upper(),
        "title_fa": str(data.get("title_fa") or ""),
        "subtitle_fa": str(data.get("subtitle_fa") or ""),
        "body_html": body_html or "",
        "cta_label": str(data.get("cta_label") or ""),
        "cta_href": str(data.get("cta_href") or ""),
        "items_json": data.get("items_json") or [],
        "status": str(data.get("status") or SiteContentBlock.Status.PUBLISHED),
        "sort_order": int(data.get("sort_order", 100)),
        "is_active": bool(data.get("is_active", True)),
        "updated_by": user,
    }
    block, created = SiteContentBlock.objects.get_or_create(slug_key=clean_slug, defaults=defaults)
    if not created:
        for f in ("page_key", "section_key", "title_fa", "subtitle_fa", "cta_label", "cta_href", "items_json", "status", "sort_order", "is_active"):
            if f in data and data[f] is not None:
                setattr(block, f, data[f])
        if body_html is not None:
            block.body_html = body_html
        block.updated_by = user
        block.save()

    record_audit_event(
        action="SITE_CONTENT_BLOCK_UPDATED",
        resource_type="SiteContentBlock",
        resource_id=clean_slug,
        actor=user,
        after_state={"status": block.status, "page_key": block.page_key},
    )
    invalidate_public_bootstrap_cache()
    return block


# ==============================================================================
# Dynamic Countries, Calendars, Currencies & Exchange Rates (Decimal)
# ==============================================================================


def _assert_localization_admin(user: User) -> None:
    if not is_super_admin(user):
        raise PermissionDeniedDomainError("مدیریت کشورها، تقویم‌ها، ارزها و نرخ تبدیل فقط توسط مدیر کل مجاز است.")


def list_calendars(*, include_inactive: bool = True) -> list[CalendarSystem]:
    qs = CalendarSystem.objects.all()
    if not include_inactive:
        qs = qs.filter(is_active=True)
    return list(qs.order_by("sort_order", "code"))


@transaction.atomic
def upsert_calendar(*, user: User, data: dict) -> CalendarSystem:
    _assert_localization_admin(user)
    code = str(data["code"]).strip().lower()
    is_default = bool(data.get("is_default", False))
    if is_default:
        CalendarSystem.objects.exclude(code=code).update(is_default=False)
    cal, _ = CalendarSystem.objects.update_or_create(
        code=code,
        defaults={
            "name_fa": str(data["name_fa"]).strip(),
            "name_en": str(data.get("name_en") or code.title()).strip(),
            "date_format": str(data.get("date_format") or "YYYY/MM/DD").strip(),
            "datetime_format": str(data.get("datetime_format") or "YYYY/MM/DD HH:mm").strip(),
            "is_default": is_default,
            "is_active": bool(data.get("is_active", True)),
            "sort_order": int(data.get("sort_order", 100)),
        },
    )
    invalidate_public_bootstrap_cache()
    return cal


@transaction.atomic
def toggle_calendar(*, user: User, code: str, is_active: Optional[bool] = None, is_default: Optional[bool] = None) -> CalendarSystem:
    _assert_localization_admin(user)
    cal = CalendarSystem.objects.filter(code=code.strip().lower()).first()
    if not cal:
        raise NotFoundDomainError("تقویم یافت نشد.")
    if is_active is not None:
        cal.is_active = bool(is_active)
    if is_default:
        CalendarSystem.objects.exclude(code=cal.code).update(is_default=False)
        cal.is_default = True
        cal.is_active = True
    cal.save()
    invalidate_public_bootstrap_cache()
    return cal


def list_countries(*, include_inactive: bool = True) -> list[Country]:
    qs = Country.objects.all()
    if not include_inactive:
        qs = qs.filter(is_active=True)
    return list(qs.order_by("sort_order", "code"))


@transaction.atomic
def upsert_country(*, user: User, data: dict) -> Country:
    _assert_localization_admin(user)
    code = str(data["code"]).strip().upper()
    if len(code) != 2 or not code.isalpha():
        raise ValidationDomainError("کد کشور باید دقیقاً ۲ حرف انگلیسی (ISO 3166-1 Alpha-2) باشد.")
    cals = data.get("supported_calendars") or [data.get("default_calendar", "jalali")]
    langs = data.get("supported_languages") or [data.get("default_language", "fa")]
    country, _ = Country.objects.update_or_create(
        code=code,
        defaults={
            "alpha3_code": str(data.get("alpha3_code") or "").strip().upper()[:3],
            "name_fa": str(data["name_fa"]).strip(),
            "name_en": str(data["name_en"]).strip(),
            "default_currency_code": str(data.get("default_currency_code") or "IRT").strip().upper(),
            "default_calendar": str(data.get("default_calendar") or "jalali").strip().lower(),
            "supported_calendars": list(cals),
            "default_language": str(data.get("default_language") or "fa").strip().lower(),
            "supported_languages": list(langs),
            "default_timezone": str(data.get("default_timezone") or "Asia/Tehran").strip(),
            "phone_prefix": str(data.get("phone_prefix") or "+98").strip(),
            "flag_url": str(data.get("flag_url") or "").strip(),
            "sort_order": int(data.get("sort_order", 100)),
            "is_active": bool(data.get("is_active", True)),
        },
    )
    record_audit_event(
        action="COUNTRY_UPSERTED",
        resource_type="Country",
        resource_id=country.code,
        actor=user,
        after_state={"name_fa": country.name_fa, "is_active": country.is_active},
    )
    invalidate_public_bootstrap_cache()
    return country


@transaction.atomic
def toggle_country(*, user: User, code: str, is_active: bool) -> Country:
    _assert_localization_admin(user)
    country = Country.objects.filter(code=code.strip().upper()).first()
    if not country:
        raise NotFoundDomainError("کشور یافت نشد.")
    country.is_active = bool(is_active)
    country.save(update_fields=["is_active"])
    invalidate_public_bootstrap_cache()
    return country


def list_currencies(*, include_inactive: bool = True) -> list[Currency]:
    qs = Currency.objects.all()
    if not include_inactive:
        qs = qs.filter(is_active=True)
    return list(qs.order_by("sort_order", "code"))


@transaction.atomic
def upsert_currency(*, user: User, data: dict) -> Currency:
    _assert_localization_admin(user)
    code = str(data["code"]).strip().upper()
    if len(code) < 2 or len(code) > 10:
        raise ValidationDomainError("کد ارز نامعتبر است.")
    cur, _ = Currency.objects.update_or_create(
        code=code,
        defaults={
            "name_fa": str(data["name_fa"]).strip(),
            "name_en": str(data.get("name_en") or code).strip(),
            "symbol": str(data.get("symbol") or code).strip(),
            "decimal_places": max(0, min(6, int(data.get("decimal_places", 0)))),
            "minor_unit": str(data.get("minor_unit") or "").strip(),
            "description": str(data.get("description") or "").strip(),
            "base_unit_factor": Decimal(str(data.get("base_unit_factor") or "1")),
            "sort_order": int(data.get("sort_order", 100)),
            "is_active": bool(data.get("is_active", True)),
        },
    )
    record_audit_event(
        action="CURRENCY_UPSERTED",
        resource_type="Currency",
        resource_id=cur.code,
        actor=user,
        after_state={"name_fa": cur.name_fa, "decimal_places": cur.decimal_places, "is_active": cur.is_active},
    )
    invalidate_currency_cache()
    invalidate_public_bootstrap_cache()
    return cur


@transaction.atomic
def toggle_currency(*, user: User, code: str, is_active: bool) -> Currency:
    _assert_localization_admin(user)
    cur = Currency.objects.filter(code=code.strip().upper()).first()
    if not cur:
        raise NotFoundDomainError("ارز یافت نشد.")
    cur.is_active = bool(is_active)
    cur.save(update_fields=["is_active"])
    invalidate_currency_cache()
    invalidate_public_bootstrap_cache()
    return cur


def list_exchange_rates(*, include_inactive: bool = True) -> list[ExchangeRate]:
    qs = ExchangeRate.objects.select_related("base_currency", "quote_currency")
    if not include_inactive:
        qs = qs.filter(is_active=True, base_currency__is_active=True, quote_currency__is_active=True)
    return list(qs.order_by("base_currency__sort_order", "quote_currency__sort_order"))


@transaction.atomic
def upsert_exchange_rate(*, user: User, data: dict) -> ExchangeRate:
    _assert_localization_admin(user)
    base_code = str(data["base_currency_code"]).strip().upper()
    quote_code = str(data["quote_currency_code"]).strip().upper()
    if base_code == quote_code:
        raise ValidationDomainError("ارز مبدأ و ارز مقصد نمی‌توانند یکسان باشند.")
    rate_val = Decimal(str(data["rate"]))
    if rate_val <= Decimal("0"):
        raise ValidationDomainError("نرخ تبدیل باید عددی بزرگ‌تر از صفر باشد.")

    base_cur = Currency.objects.filter(code=base_code).first()
    quote_cur = Currency.objects.filter(code=quote_code).first()
    if not base_cur or not quote_cur:
        raise NotFoundDomainError("ارز مبدأ یا مقصد یافت نشد.")

    existing = ExchangeRate.objects.filter(base_currency=base_cur, quote_currency=quote_cur).first()
    prev_rate = existing.rate if existing else None

    fx, _ = ExchangeRate.objects.update_or_create(
        base_currency=base_cur,
        quote_currency=quote_cur,
        defaults={
            "rate": rate_val,
            "effective_at": data.get("effective_at") or timezone.now(),
            "source": str(data.get("source") or "MANUAL").strip().upper(),
            "is_active": bool(data.get("is_active", True)),
            "updated_by": user,
            **({"created_by": user} if not existing else {}),
        },
    )
    ExchangeRateHistory.objects.create(
        base_currency_code=base_code,
        quote_currency_code=quote_code,
        previous_rate=prev_rate,
        new_rate=rate_val,
        source=fx.source,
        change_reason=str(data.get("change_reason") or "به‌روزرسانی نرخ تبدیل ارز")[:255],
        changed_by=user,
        created_by=user,
    )
    record_audit_event(
        action="EXCHANGE_RATE_UPDATED",
        resource_type="ExchangeRate",
        resource_id=f"{base_code}->{quote_code}",
        actor=user,
        before_state={"rate": str(prev_rate)} if prev_rate is not None else None,
        after_state={"rate": str(rate_val), "source": fx.source},
    )
    invalidate_currency_cache()
    invalidate_public_bootstrap_cache()
    return fx


def list_exchange_rate_history(*, user: User) -> list[ExchangeRateHistory]:
    _assert_localization_admin(user)
    return list(ExchangeRateHistory.objects.select_related("changed_by").order_by("-created_at")[:100])


# ==============================================================================
# Provider Configurations & Public Bootstrap
# ==============================================================================


def resolve_active_provider_config(
    *, category: str, agency_id: Optional[UUID] = None, provider_key: Optional[str] = None
) -> Optional[ProviderConfiguration]:
    """ارائه‌دهندهٔ مجاز آژانس یا پیش‌فرض سراسری همان دسته را پیدا می‌کند."""
    qs = ProviderConfiguration.objects.filter(category=category)
    if provider_key:
        qs = qs.filter(provider_key=provider_key)
    else:
        qs = qs.filter(is_active=True)

    if agency_id:
        cfg = qs.filter(agency_id=agency_id).order_by("priority", "-updated_at").first()
        if cfg:
            return cfg
    with tenant_bypass(reason="system_configuration"):
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
    area_unit = str(get_setting_value("localization.default_area_unit", "sqm", agency_id=agency_id) or "sqm")

    return {
        "countries": list(Country.objects.filter(is_active=True).order_by("sort_order", "code")),
        "calendars": list(CalendarSystem.objects.filter(is_active=True).order_by("sort_order", "code")),
        "currencies": list(Currency.objects.filter(is_active=True).order_by("sort_order", "code")),
        "exchange_rates": list(
            ExchangeRate.objects.select_related("base_currency", "quote_currency")
            .filter(is_active=True, base_currency__is_active=True, quote_currency__is_active=True)
            .order_by("base_currency__sort_order", "quote_currency__sort_order")
        ),
        "area_unit": area_unit,
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
                {
                    "key": k,
                    "name": getattr(cls, "display_name", k),
                    "supports_sandbox": getattr(cls, "supports_sandbox", False),
                    "required_fields": getattr(cls, "required_credential_fields", []),
                }
                for k, cls in SMS_PROVIDERS.items()
            ],
        },
    }


def get_public_bootstrap(agency_id: Optional[UUID] = None) -> dict:
    cache_key = f"{PUBLIC_BOOTSTRAP_CACHE_PREFIX}{agency_id or 'global'}"
    try:
        cached = cache.get(cache_key)
        if isinstance(cached, dict) and cached:
            return cached
    except Exception:
        pass

    from apps.cms.models import LegalDocument

    loc_meta = get_localization_metadata(agency_id=agency_id)
    public_settings_qs = SystemSetting.objects.filter(
        agency__isnull=True,
        country_code="",
        is_active=True,
        sensitivity_level=SystemSetting.SensitivityLevel.PUBLIC,
    )
    public_settings = {
        s.key: _extract_setting_typed_value(s) for s in public_settings_qs
    }
    if agency_id:
        for s in SystemSetting.objects.filter(
            agency_id=agency_id,
            is_active=True,
            sensitivity_level=SystemSetting.SensitivityLevel.PUBLIC,
        ):
            public_settings[s.key] = _extract_setting_typed_value(s)

    # Ensure JSON serializable (convert Decimal -> str)
    clean_settings = {
        k: (str(v) if isinstance(v, Decimal) else v) for k, v in public_settings.items()
    }

    branding_slots = {
        slot.slot_key: {
            "slot_key": slot.slot_key,
            "category": slot.category,
            "title_fa": slot.title_fa,
            "image_url": slot.image_url,
            "dark_image_url": slot.dark_image_url,
            "alt_text": slot.alt_text,
        }
        for slot in BrandMediaSlot.objects.filter(is_active=True).order_by("sort_order", "slot_key")
    }

    content_blocks = {
        blk.slug_key: {
            "slug_key": blk.slug_key,
            "page_key": blk.page_key,
            "section_key": blk.section_key,
            "title_fa": blk.title_fa,
            "subtitle_fa": blk.subtitle_fa,
            "body_html": sanitize_html(blk.body_html),
            "cta_label": blk.cta_label,
            "cta_href": blk.cta_href,
            "items_json": blk.items_json or [],
        }
        for blk in SiteContentBlock.objects.filter(
            status=SiteContentBlock.Status.PUBLISHED, is_active=True
        ).order_by("page_key", "sort_order", "slug_key")
    }

    legal_docs = [
        {
            "slug": doc.slug,
            "doc_type": doc.doc_type,
            "title_fa": doc.title_fa,
            "version_number": doc.version_number,
            "requires_acceptance": doc.requires_acceptance,
            "effective_at": doc.effective_at.isoformat() if doc.effective_at else None,
        }
        for doc in LegalDocument.objects.filter(status=LegalDocument.Status.PUBLISHED).order_by("sort_order", "slug")
    ]

    payload = {
        "public_settings": clean_settings,
        "branding": branding_slots,
        "content_blocks": content_blocks,
        "legal_documents": legal_docs,
        "countries": [
            {
                "code": c.code,
                "alpha3_code": c.alpha3_code,
                "name_fa": c.name_fa,
                "name_en": c.name_en,
                "default_language": c.default_language,
                "supported_languages": c.supported_languages or [c.default_language],
                "default_calendar": c.default_calendar,
                "supported_calendars": c.supported_calendars or [c.default_calendar],
                "default_currency": c.default_currency_code,
                "timezone": c.default_timezone,
                "phone_prefix": c.phone_prefix,
                "flag_url": c.flag_url,
                "area_unit": loc_meta["area_unit"],
            }
            for c in loc_meta["countries"]
        ],
        "calendars": [
            {
                "code": cal.code,
                "name_fa": cal.name_fa,
                "name_en": cal.name_en,
                "date_format": cal.date_format,
                "datetime_format": cal.datetime_format,
                "is_default": cal.is_default,
            }
            for cal in loc_meta["calendars"]
        ],
        "currencies": [
            {
                "code": cur.code,
                "name_fa": cur.name_fa,
                "name_en": cur.name_en,
                "symbol": cur.symbol,
                "decimal_places": cur.decimal_places,
                "minor_unit": cur.minor_unit,
                "description": cur.description,
                "exchange_rate_to_base": str(cur.base_unit_factor),
            }
            for cur in loc_meta["currencies"]
        ],
        "exchange_rates": [
            {
                "id": str(fx.id),
                "base_currency_code": fx.base_currency_id,
                "quote_currency_code": fx.quote_currency_id,
                "rate": str(fx.rate),
                "source": fx.source,
                "effective_at": fx.effective_at.isoformat(),
            }
            for fx in loc_meta["exchange_rates"]
        ],
        "map_provider": loc_meta["map_provider"],
    }
    try:
        cache.set(cache_key, payload, timeout=60)
    except Exception:
        pass
    return payload


def list_provider_configs(
    *, user: User, agency_id: Optional[UUID], category: Optional[str] = None
) -> list[ProviderConfiguration]:
    if agency_id:
        if not is_super_admin(user):
            raise PermissionDeniedDomainError("تنظیمات ارائه‌دهندگان فقط برای مدیر کل مجاز است.")
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
        if not is_super_admin(user):
            raise PermissionDeniedDomainError("تنظیم ارائه‌دهندگان فقط برای مدیر کل مجاز است.")
    elif not is_super_admin(user):
        raise PermissionDeniedDomainError("فقط مدیر کل مجاز به تنظیم ارائه‌دهندگان پلتفرم است.")

    category = data["category"]
    provider_key = data["provider_key"]
    is_active = bool(data.get("is_active", True))

    # For MAP & AI single primary active; for PAYMENT & SMS allow multiple active for priority fallback
    if is_active and category in (
        ProviderConfiguration.Category.MAP,
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
    invalidate_public_bootstrap_cache(target_agency_id)
    return cfg


@transaction.atomic
def test_provider_config(*, user: User, agency_id: Optional[UUID], config_id: UUID) -> dict:
    cfg = ProviderConfiguration.objects.filter(id=config_id).first()
    if not cfg:
        raise NotFoundDomainError("پیکربندی درگاه یا سرویس یافت نشد.")
    if not is_super_admin(user):
        raise PermissionDeniedDomainError("تست اتصال سرویس‌ها فقط برای مدیر کل مجاز است.")

    creds = parse_provider_credentials(cfg)
    result = {"ok": True, "status": "READY", "message": "پیکربندی معتبر است."}

    if cfg.category == ProviderConfiguration.Category.PAYMENT:
        adapter = get_payment_provider(cfg.provider_key)
        res = adapter.test_connection(credentials=creds, is_sandbox=cfg.is_sandbox)
        result = {"ok": res.ok, "status": res.status, "message": res.message}
    elif cfg.category == ProviderConfiguration.Category.SMS:
        adapter = get_sms_provider(cfg.provider_key)
        result = adapter.test_connection(credentials=creds, is_sandbox=cfg.is_sandbox)
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
    raise PermissionDeniedDomainError("مدیریت اطلاعات جغرافیایی فقط برای مدیر کل مجاز است.")


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

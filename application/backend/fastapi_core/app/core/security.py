"""صدور و اعتبارسنجی توکن نشست و عادی‌سازی نشانی IP برای ممیزی."""

from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Any, Optional
import ipaddress
import uuid
import jwt
from .config import settings


def extract_client_ip(raw_host: Optional[str]) -> Optional[str]:
    """فقط IP معتبر را برای ذخیره در فیلد نشانی شبکه برمی‌گرداند."""
    if not raw_host:
        return None
    if raw_host == "testclient":
        return "127.0.0.1"
    try:
        return str(ipaddress.ip_address(raw_host.strip()))
    except ValueError:
        return None


def _resolve_dynamic_ttl() -> tuple[int, int]:
    """مدت توکن را از تنظیمات فعال و در صورت خطا از پیش‌فرض اجرا می‌گیرد."""
    access_mins = settings.ACCESS_TOKEN_EXPIRE_MINUTES
    refresh_days = settings.REFRESH_TOKEN_EXPIRE_DAYS
    try:
        from apps.settings.services import get_setting_value

        access_mins = max(5, int(get_setting_value("security.access_token_ttl_minutes", access_mins) or access_mins))
        refresh_days = max(1, int(get_setting_value("security.refresh_token_ttl_days", refresh_days) or refresh_days))
    except Exception:
        pass
    return access_mins, refresh_days


def build_token_pair(*, user, session, membership=None) -> dict[str, Any]:
    """توکن دسترسی و تازه‌سازی را با شناسهٔ مشترک نشست صادر می‌کند."""
    now = datetime.now(dt_timezone.utc)
    access_mins, refresh_days = _resolve_dynamic_ttl()
    access_exp = now + timedelta(minutes=access_mins)
    refresh_exp = now + timedelta(days=refresh_days)

    base_claims = {
        "user_id": str(user.id),
        "jti": str(session.jti),
        "session_id": str(session.id),
        "platform_role": user.platform_role,
        "agency_id": str(membership.agency_id) if membership else None,
        "agency_role": membership.role.code if membership else None,
        "membership_id": str(membership.id) if membership else None,
        "iat": int(now.timestamp()),
    }

    access_payload = {
        **base_claims,
        "token_type": "access",
        "exp": int(access_exp.timestamp()),
    }
    refresh_payload = {
        **base_claims,
        "token_type": "refresh",
        "exp": int(refresh_exp.timestamp()),
    }

    return {
        "access": jwt.encode(access_payload, settings.JWT_SIGNING_KEY, algorithm=settings.JWT_ALGORITHM),
        "refresh": jwt.encode(refresh_payload, settings.JWT_SIGNING_KEY, algorithm=settings.JWT_ALGORITHM),
        "token_type": "Bearer",
        "expires_in": access_mins * 60,
    }


def decode_jwt_token(token: str, *, expected_type: Optional[str] = None) -> dict[str, Any]:
    """امضا، انقضا و شناسه‌های لازم برای توکن مورد انتظار را بررسی می‌کند."""
    required = ["exp"]
    if expected_type in {"access", "refresh"}:
        required.extend(("user_id", "jti"))
    payload = jwt.decode(
        token, settings.JWT_SIGNING_KEY, algorithms=[settings.JWT_ALGORITHM],
        options={"require": required},
    )
    if expected_type and payload.get("token_type") != expected_type:
        raise jwt.InvalidTokenError("Invalid token type.")
    if expected_type in {"access", "refresh"}:
        try:
            uuid.UUID(str(payload["user_id"]))
            uuid.UUID(str(payload["jti"]))
        except ValueError as exc:
            raise jwt.InvalidTokenError("Invalid session identifiers.") from exc
    return payload


def new_jti() -> uuid.UUID:
    """شناسهٔ تازه برای صدور یا چرخش نشست فراهم می‌کند."""
    return uuid.uuid4()

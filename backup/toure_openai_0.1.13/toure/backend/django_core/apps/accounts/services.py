from datetime import timedelta
import hashlib
import secrets
from typing import Optional
from uuid import UUID
import pyotp
from django.core.cache import cache
from django.db import models, transaction
from django.utils import timezone
from apps.audit.services import record_audit_event
from common.encryption import decrypt_sensitive_value, encrypt_sensitive_value
from common.exceptions import (
    AuthenticationDomainError,
    ConflictDomainError,
    NotFoundDomainError,
    PermissionDeniedDomainError,
    RateLimitDomainError,
    ValidationDomainError,
)
from common.permissions import get_active_membership, has_agency_permission, is_super_admin
from .models import (
    AgencyMembership,
    LoginAttemptLog,
    MembershipPermissionOverride,
    Permission,
    Role,
    RolePermission,
    User,
    UserSession,
)


def _get_security_setting(key: str, default):
    try:
        from apps.settings.services import get_setting_value

        return get_setting_value(key, default)
    except Exception:
        return default


def _validate_password_policy(password: str) -> None:
    min_len = int(_get_security_setting("security.password_min_length", 8) or 8)
    req_upper = bool(_get_security_setting("security.password_require_uppercase", False))
    req_digit = bool(_get_security_setting("security.password_require_digit", False))
    req_special = bool(_get_security_setting("security.password_require_special", False))

    if len(password or "") < min_len:
        raise ValidationDomainError(f"رمز عبور باید حداقل {min_len} کاراکتر باشد.")
    if req_upper and not any(ch.isupper() for ch in password):
        raise ValidationDomainError("رمز عبور باید حداقل شامل یک حرف بزرگ انگلیسی باشد.")
    if req_digit and not any(ch.isdigit() for ch in password):
        raise ValidationDomainError("رمز عبور باید حداقل شامل یک رقم باشد.")
    if req_special and not any(not ch.isalnum() for ch in password):
        raise ValidationDomainError("رمز عبور باید حداقل شامل یک کاراکتر ویژه (مانند @ یا #) باشد.")


def _lockout_cache_key(identifier: str, ip_address: Optional[str]) -> str:
    return f"auth_fail:{identifier}:{ip_address or 'unknown'}"


def _check_brute_force_lock(identifier: str, ip_address: Optional[str]) -> None:
    max_fails = int(_get_security_setting("security.brute_force_max_fails", 5) or 5)
    key = _lockout_cache_key(identifier, ip_address)
    try:
        fails = int(cache.get(key) or 0)
    except Exception:
        fails = 0
    if fails >= max_fails:
        raise RateLimitDomainError(
            "تعداد تلاش‌های ناموفق بیش از حد مجاز بوده است. لطفاً پس از پایان زمان قفل مجدداً تلاش کنید."
        )


def _increment_brute_force_fail(identifier: str, ip_address: Optional[str]) -> None:
    window_sec = int(_get_security_setting("security.brute_force_lockout_seconds", 600) or 600)
    key = _lockout_cache_key(identifier, ip_address)
    try:
        current = int(cache.get(key) or 0) + 1
        cache.set(key, current, timeout=window_sec)
    except Exception:
        pass


def _clear_brute_force_fail(identifier: str, ip_address: Optional[str]) -> None:
    try:
        cache.delete(_lockout_cache_key(identifier, ip_address))
    except Exception:
        pass


def _infer_device_type(user_agent: str, device_name: str) -> str:
    combined = f"{user_agent} {device_name}".lower()
    if any(k in combined for k in ("iphone", "android", "mobile", "pwa")):
        return "MOBILE"
    if any(k in combined for k in ("ipad", "tablet")):
        return "TABLET"
    if any(k in combined for k in ("curl", "python", "httpx", "postman", "api")):
        return "API_CLIENT"
    return "WEB"


@transaction.atomic
def register_user(
    *,
    phone_number: str,
    password: str,
    first_name: str = "",
    last_name: str = "",
    email: Optional[str] = None,
    preferred_language: str = "fa",
    preferred_calendar: str = "jalali",
    preferred_currency: str = "IRT",
) -> User:
    if not bool(_get_security_setting("general.allow_public_registration", True)):
        raise PermissionDeniedDomainError("ثبت‌نام عمومی کاربران در حال حاضر از مرکز تنظیمات غیرفعال است.")

    clean_phone = phone_number.strip()
    _validate_password_policy(password)
    if User.objects.filter(phone_number=clean_phone).exists():
        raise ConflictDomainError("این شماره موبایل قبلاً ثبت شده است.")
    clean_email = email.strip().lower() if email else None
    if clean_email and User.objects.filter(email=clean_email).exists():
        raise ConflictDomainError("این ایمیل قبلاً ثبت شده است.")

    user = User.objects.create_user(
        phone_number=clean_phone,
        password=password,
        email=clean_email,
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        preferred_language=preferred_language,
        preferred_calendar=preferred_calendar,
        preferred_currency=preferred_currency,
        platform_role=User.PlatformRole.CUSTOMER,
        status=User.Status.ACTIVE,
    )
    record_audit_event(
        action="USER_REGISTERED",
        resource_type="User",
        resource_id=str(user.id),
        actor=user,
    )
    return user


def authenticate_user_credentials(
    *,
    phone_number: str,
    password: str,
    ip_address: Optional[str] = None,
    user_agent: str = "",
    device_name: str = "Web Browser",
    mfa_code: Optional[str] = None,
) -> tuple[User, UserSession, Optional[AgencyMembership]]:
    identifier = phone_number.strip()
    _check_brute_force_lock(identifier, ip_address)

    user = User.objects.filter(phone_number=identifier).first()
    if user is None or not user.check_password(password):
        _increment_brute_force_fail(identifier, ip_address)
        LoginAttemptLog.objects.create(
            identifier=identifier,
            user=user,
            ip_address=ip_address,
            succeeded=False,
            failure_reason="INVALID_CREDENTIALS",
        )
        record_audit_event(
            action="USER_LOGIN_FAILED",
            resource_type="User",
            resource_id=str(user.id) if user else identifier,
            actor=user,
            ip_address=ip_address,
            metadata={"reason": "INVALID_CREDENTIALS"},
        )
        raise AuthenticationDomainError("شماره موبایل یا رمز عبور نادرست است.")

    if not user.can_authenticate():
        LoginAttemptLog.objects.create(
            identifier=identifier,
            user=user,
            ip_address=ip_address,
            succeeded=False,
            failure_reason=f"ACCOUNT_{user.status}",
        )
        raise PermissionDeniedDomainError("حساب کاربری شما فعال نیست.")

    # Enforce MFA if enabled on user OR enforced globally by security policy when MFA is configured
    mfa_policy = str(_get_security_setting("security.mfa_policy", "OPTIONAL") or "OPTIONAL").upper()
    requires_mfa = bool(user.is_mfa_enabled)
    if (
        (mfa_policy == "ALL_REQUIRED" or (mfa_policy == "ADMINS_REQUIRED" and user.platform_role == User.PlatformRole.SUPER_ADMIN))
        and user.mfa_secret_encrypted
    ):
        requires_mfa = True

    if requires_mfa:
        secret = decrypt_sensitive_value(user.mfa_secret_encrypted)
        totp = pyotp.TOTP(secret) if secret else None
        if not mfa_code or not totp or not totp.verify(mfa_code.strip(), valid_window=1):
            _increment_brute_force_fail(identifier, ip_address)
            LoginAttemptLog.objects.create(
                identifier=identifier,
                user=user,
                ip_address=ip_address,
                succeeded=False,
                failure_reason="INVALID_OR_MISSING_MFA",
            )
            raise AuthenticationDomainError(
                "کد احراز هویت دوعاملی (MFA) الزامی یا نامعتبر است.",
                code="MFA_REQUIRED",
            )

    _clear_brute_force_fail(identifier, ip_address)
    now = timezone.now()
    user.last_login = now
    user.save(update_fields=["last_login"])

    LoginAttemptLog.objects.create(
        identifier=identifier,
        user=user,
        ip_address=ip_address,
        succeeded=True,
    )

    # Suspicious login detection (new IP or recent failed attempts)
    recent_prior_ips = set(
        UserSession.objects.filter(user=user).exclude(ip_address__isnull=True).values_list("ip_address", flat=True)[:10]
    )
    recent_fails = LoginAttemptLog.objects.filter(
        identifier=identifier,
        succeeded=False,
        created_at__gte=now - timedelta(minutes=15),
    ).count()
    is_suspicious = bool((ip_address and recent_prior_ips and ip_address not in recent_prior_ips) or recent_fails >= 3)

    # Enforce max concurrent active sessions
    max_sessions = int(_get_security_setting("security.max_concurrent_sessions", 5) or 5)
    active_sessions = list(
        UserSession.objects.filter(user=user, revoked_at__isnull=True).order_by("last_active_at")
    )
    if max_sessions > 0 and len(active_sessions) >= max_sessions:
        overflow = active_sessions[: len(active_sessions) - max_sessions + 1]
        UserSession.objects.filter(id__in=[s.id for s in overflow]).update(revoked_at=now)

    refresh_ttl_days = int(_get_security_setting("security.refresh_token_ttl_days", 7) or 7)
    session = UserSession.objects.create(
        user=user,
        device_name=device_name[:128],
        device_type=_infer_device_type(user_agent, device_name),
        auth_method="PASSWORD_MFA" if requires_mfa else "PASSWORD",
        ip_address=ip_address,
        user_agent=(user_agent or "")[:255],
        is_suspicious=is_suspicious,
        last_active_at=now,
        expires_at=now + timedelta(days=refresh_ttl_days),
    )
    membership = (
        AgencyMembership.objects.select_related("agency", "role", "branch")
        .filter(user=user, status=AgencyMembership.Status.ACTIVE)
        .first()
    )
    record_audit_event(
        action="USER_LOGIN_SUCCEEDED",
        resource_type="User",
        resource_id=str(user.id),
        actor=user,
        agency_id=membership.agency_id if membership else None,
        ip_address=ip_address,
        metadata={"device_name": device_name[:128], "is_suspicious": is_suspicious},
    )
    return user, session, membership


def setup_mfa_for_user(user: User) -> dict:
    secret = pyotp.random_base32()
    user.mfa_secret_encrypted = encrypt_sensitive_value(secret)
    user.save(update_fields=["mfa_secret_encrypted", "updated_at"])
    uri = pyotp.TOTP(secret).provisioning_uri(
        name=user.phone_number,
        issuer_name="Bonyan Melk",
    )
    return {"secret": secret, "otpauth_uri": uri, "is_mfa_enabled": user.is_mfa_enabled}


def enable_mfa_for_user(user: User, code: str) -> User:
    secret = decrypt_sensitive_value(user.mfa_secret_encrypted)
    if not secret:
        raise ValidationDomainError("ابتدا راه‌اندازی احراز هویت دوعاملی را شروع کنید.")
    if not pyotp.TOTP(secret).verify(code.strip(), valid_window=1):
        raise ValidationDomainError("کد تأیید دوعاملی نامعتبر است.")
    user.is_mfa_enabled = True
    user.save(update_fields=["is_mfa_enabled", "updated_at"])
    record_audit_event(
        action="MFA_ENABLED",
        resource_type="User",
        resource_id=str(user.id),
        actor=user,
    )
    return user


def disable_mfa_for_user(user: User, code: str) -> User:
    if not user.is_mfa_enabled:
        return user
    secret = decrypt_sensitive_value(user.mfa_secret_encrypted)
    if not secret or not pyotp.TOTP(secret).verify(code.strip(), valid_window=1):
        raise ValidationDomainError("کد تأیید دوعاملی برای غیرفعال‌سازی نامعتبر است.")
    user.is_mfa_enabled = False
    user.mfa_secret_encrypted = ""
    user.save(update_fields=["is_mfa_enabled", "mfa_secret_encrypted", "updated_at"])
    record_audit_event(
        action="MFA_DISABLED",
        resource_type="User",
        resource_id=str(user.id),
        actor=user,
    )
    return user


def validate_active_session_for_refresh(*, user_id: str, jti: str) -> tuple[User, UserSession]:
    user = User.objects.filter(id=user_id).first()
    if not user or not user.can_authenticate():
        raise AuthenticationDomainError("کاربر یافت نشد یا غیرفعال است.")
    session = UserSession.objects.filter(user=user, jti=jti, revoked_at__isnull=True).first()
    if not session:
        raise AuthenticationDomainError("نشست کاربری منقضی یا لغو شده است.")

    now = timezone.now()
    if session.expires_at and session.expires_at < now:
        session.revoked_at = now
        session.save(update_fields=["revoked_at"])
        raise AuthenticationDomainError("نشست کاربری منقضی شده است.")

    idle_timeout_mins = int(_get_security_setting("security.session_idle_timeout_minutes", 480) or 0)
    if idle_timeout_mins > 0 and session.last_active_at < now - timedelta(minutes=idle_timeout_mins):
        session.revoked_at = now
        session.save(update_fields=["revoked_at"])
        raise AuthenticationDomainError("نشست به دلیل عدم فعالیت بیش از حد منقضی شد.")
    return user, session


def rotate_user_session(*, old_session: UserSession, new_jti: UUID) -> UserSession:
    old_session.jti = new_jti
    old_session.last_active_at = timezone.now()
    old_session.save(update_fields=["jti", "last_active_at"])
    return old_session


def request_password_reset_otp(*, phone_number: str) -> dict:
    clean_phone = phone_number.strip()
    user = User.objects.filter(phone_number=clean_phone, is_active=True).first()
    if not user:
        raise NotFoundDomainError("کاربری با این شماره موبایل یافت نشد.")

    otp_code = f"{secrets.randbelow(900000) + 100000}"
    otp_hash = hashlib.sha256(otp_code.encode()).hexdigest()
    cache.set(f"pwd_reset:{clean_phone}", otp_hash, timeout=600)

    from apps.notifications.services import dispatch_sms_with_policy

    sms_res = dispatch_sms_with_policy(
        phone_number=clean_phone,
        event_type="PASSWORD_RESET",
        template_key="password_reset_otp",
        tokens={"code": otp_code, "name": user.full_name},
        is_otp=True,
        actor=user,
    )
    record_audit_event(
        action="PASSWORD_RESET_OTP_REQUESTED",
        resource_type="User",
        resource_id=str(user.id),
        actor=user,
    )
    return {
        "sent": bool(sms_res.get("accepted")),
        "provider": sms_res.get("provider_key", "console"),
        "expires_in_seconds": 600,
        "sandbox_otp": otp_code if sms_res.get("provider_key") == "console" else None,
    }


@transaction.atomic
def confirm_password_reset_otp(*, phone_number: str, otp_code: str, new_password: str) -> User:
    clean_phone = phone_number.strip()
    _validate_password_policy(new_password)
    expected_hash = cache.get(f"pwd_reset:{clean_phone}")
    provided_hash = hashlib.sha256(otp_code.strip().encode()).hexdigest()
    if not expected_hash or expected_hash != provided_hash:
        raise ValidationDomainError("کد تأیید نامعتبر یا منقضی شده است.")

    user = User.objects.filter(phone_number=clean_phone).first()
    if not user:
        raise NotFoundDomainError("کاربر یافت نشد.")

    user.set_password(new_password)
    user.save(update_fields=["password", "updated_at"])
    UserSession.objects.filter(user=user, revoked_at__isnull=True).update(revoked_at=timezone.now())
    cache.delete(f"pwd_reset:{clean_phone}")
    record_audit_event(
        action="PASSWORD_RESET_CONFIRMED",
        resource_type="User",
        resource_id=str(user.id),
        actor=user,
    )
    return user


def list_user_sessions(user: User) -> list[UserSession]:
    return list(
        UserSession.objects.filter(user=user, revoked_at__isnull=True).order_by("-last_active_at")
    )


def revoke_user_session(user: User, session_id: UUID) -> bool:
    updated = UserSession.objects.filter(
        id=session_id, user=user, revoked_at__isnull=True
    ).update(revoked_at=timezone.now())
    if updated > 0:
        record_audit_event(
            action="USER_SESSION_REVOKED",
            resource_type="UserSession",
            resource_id=str(session_id),
            actor=user,
        )
    return updated > 0


# ==============================================================================
# SuperAdmin Security & Session Management Console
# ==============================================================================


def list_all_active_sessions(
    *, actor: User, user_id: Optional[UUID] = None, suspicious_only: bool = False, q: Optional[str] = None
) -> list[UserSession]:
    if not is_super_admin(actor):
        raise PermissionDeniedDomainError("فقط مدیر کل مجاز به مشاهده نشست‌های کل سامانه است.")
    qs = UserSession.objects.select_related("user").filter(revoked_at__isnull=True)
    if user_id:
        qs = qs.filter(user_id=user_id)
    if suspicious_only:
        qs = qs.filter(is_suspicious=True)
    if q:
        clean = q.strip()
        qs = qs.filter(
            models.Q(user__phone_number__icontains=clean)
            | models.Q(user__first_name__icontains=clean)
            | models.Q(user__last_name__icontains=clean)
            | models.Q(device_name__icontains=clean)
        )
    return list(qs.order_by("-last_active_at")[:200])


@transaction.atomic
def revoke_session_by_admin(*, actor: User, session_id: UUID) -> bool:
    if not is_super_admin(actor):
        raise PermissionDeniedDomainError("فقط مدیر کل مجاز به لغو نشست کاربران است.")
    session = UserSession.objects.select_related("user").filter(id=session_id, revoked_at__isnull=True).first()
    if not session:
        raise NotFoundDomainError("نشست فعال یافت نشد.")
    session.revoked_at = timezone.now()
    session.save(update_fields=["revoked_at"])
    record_audit_event(
        action="ADMIN_SESSION_REVOKED",
        resource_type="UserSession",
        resource_id=str(session.id),
        actor=actor,
        after_state={"target_user": session.user.phone_number, "device_name": session.device_name},
    )
    return True


@transaction.atomic
def revoke_all_user_sessions(*, actor: User, target_user_id: UUID) -> int:
    if not is_super_admin(actor):
        raise PermissionDeniedDomainError("فقط مدیر کل مجاز به مسدودسازی نشست‌های کاربر است.")
    target = User.objects.filter(id=target_user_id).first()
    if not target:
        raise NotFoundDomainError("کاربر یافت نشد.")
    count = UserSession.objects.filter(user=target, revoked_at__isnull=True).update(revoked_at=timezone.now())
    record_audit_event(
        action="ADMIN_USER_ALL_SESSIONS_REVOKED",
        resource_type="User",
        resource_id=str(target.id),
        actor=actor,
        after_state={"revoked_count": count},
    )
    return count


@transaction.atomic
def emergency_force_logout_all(
    *, actor: User, password_confirm: str, current_jti: Optional[str] = None, exclude_current: bool = True
) -> int:
    if not is_super_admin(actor):
        raise PermissionDeniedDomainError("فقط مدیر کل مجاز به اجرای خروج اضطراری سراسری است.")
    if not password_confirm or not actor.check_password(password_confirm):
        raise AuthenticationDomainError("رمز عبور مدیر کل برای تأیید عملیات اضطراری نادرست است.")

    qs = UserSession.objects.filter(revoked_at__isnull=True)
    if exclude_current and current_jti:
        qs = qs.exclude(jti=current_jti)
    count = qs.update(revoked_at=timezone.now())
    record_audit_event(
        action="EMERGENCY_GLOBAL_FORCE_LOGOUT",
        resource_type="UserSession",
        resource_id="ALL",
        actor=actor,
        after_state={"revoked_count": count, "excluded_current": exclude_current},
    )
    return count


def list_security_events(*, actor: User) -> list[LoginAttemptLog]:
    if not is_super_admin(actor):
        raise PermissionDeniedDomainError("فقط مدیر کل مجاز به مشاهده رویدادهای امنیتی است.")
    return list(LoginAttemptLog.objects.select_related("user").order_by("-created_at")[:150])


# ==============================================================================
# Profile, Admin User Management, Roles & Quotas
# ==============================================================================


def update_user_profile(user: User, **fields) -> User:
    allowed = [
        "first_name",
        "last_name",
        "email",
        "preferred_language",
        "preferred_calendar",
        "preferred_currency",
        "timezone",
    ]
    update_fields = ["updated_at"]
    for k in allowed:
        if k in fields and fields[k] is not None:
            val = fields[k]
            if k == "email" and val:
                val = val.strip().lower()
                if User.objects.filter(email=val).exclude(pk=user.pk).exists():
                    raise ConflictDomainError("این ایمیل قبلاً توسط کاربر دیگری ثبت شده است.")
            setattr(user, k, val)
            update_fields.append(k)
    user.save(update_fields=update_fields)
    return user


def list_all_users_for_admin(actor: User, q: Optional[str] = None, status: Optional[str] = None):
    if not is_super_admin(actor):
        raise PermissionDeniedDomainError("فقط مدیر کل به لیست کل کاربران دسترسی دارد.")
    qs = (
        User.objects.exclude(status=User.Status.DELETED)
        .prefetch_related("memberships__agency", "memberships__role", "memberships__branch")
        .order_by("-date_joined")
    )
    if status:
        qs = qs.filter(status=status)
    if q and q.strip():
        clean = q.strip()
        qs = qs.filter(
            models.Q(phone_number__icontains=clean)
            | models.Q(first_name__icontains=clean)
            | models.Q(last_name__icontains=clean)
            | models.Q(email__icontains=clean)
        )
    return qs


@transaction.atomic
def create_user_by_admin(*, actor: User, data: dict) -> User:
    if not is_super_admin(actor):
        raise PermissionDeniedDomainError("فقط مدیر کل مجاز به ایجاد کاربر است.")
    clean_phone = str(data.get("phone_number") or "").strip()
    if not clean_phone:
        raise ValidationDomainError("شماره موبایل الزامی است.")
    if User.objects.filter(phone_number=clean_phone).exists():
        raise ConflictDomainError("این شماره موبایل قبلاً ثبت شده است.")

    clean_email = str(data.get("email") or "").strip().lower() or None
    if clean_email and User.objects.filter(email=clean_email).exists():
        raise ConflictDomainError("این ایمیل قبلاً ثبت شده است.")

    password = str(data.get("password") or "Bonyan@12345")
    platform_role = data.get("platform_role") or User.PlatformRole.AGENCY_USER
    if platform_role not in User.PlatformRole.values:
        raise ValidationDomainError("نقش پلتفرمی نامعتبر است.")

    user = User.objects.create_user(
        phone_number=clean_phone,
        password=password,
        first_name=str(data.get("first_name") or "").strip(),
        last_name=str(data.get("last_name") or "").strip(),
        email=clean_email,
        platform_role=platform_role,
        status=User.Status.ACTIVE,
        is_active=True,
    )

    if data.get("agency_id") and data.get("role_code"):
        assign_user_membership_by_admin(
            actor=actor,
            target_user_id=user.id,
            agency_id=data["agency_id"],
            role_code=data["role_code"],
            branch_id=data.get("branch_id"),
            status_value=AgencyMembership.Status.ACTIVE,
        )

    record_audit_event(
        action="USER_CREATED_BY_ADMIN",
        resource_type="User",
        resource_id=str(user.id),
        actor=actor,
        after_state={"phone_number": user.phone_number, "platform_role": user.platform_role},
    )
    return user


@transaction.atomic
def update_user_by_admin(*, actor: User, target_user_id: UUID, data: dict) -> User:
    if not is_super_admin(actor):
        raise PermissionDeniedDomainError("فقط مدیر کل مجاز به ویرایش کاربر است.")
    target = User.objects.filter(id=target_user_id).first()
    if not target:
        raise NotFoundDomainError("کاربر یافت نشد.")

    if "phone_number" in data and data["phone_number"] is not None:
        clean_phone = str(data["phone_number"]).strip()
        if User.objects.filter(phone_number=clean_phone).exclude(id=target.id).exists():
            raise ConflictDomainError("شماره موبایل تکراری است.")
        target.phone_number = clean_phone

    if "email" in data and data["email"] is not None:
        clean_email = str(data["email"]).strip().lower() or None
        if clean_email and User.objects.filter(email=clean_email).exclude(id=target.id).exists():
            raise ConflictDomainError("ایمیل تکراری است.")
        target.email = clean_email

    for field in ("first_name", "last_name"):
        if field in data and data[field] is not None:
            setattr(target, field, str(data[field]).strip())

    if "platform_role" in data and data["platform_role"] is not None:
        if data["platform_role"] not in User.PlatformRole.values:
            raise ValidationDomainError("نقش پلتفرمی نامعتبر است.")
        target.platform_role = data["platform_role"]

    if "status" in data and data["status"] is not None:
        if data["status"] not in User.Status.values:
            raise ValidationDomainError("وضعیت کاربری نامعتبر است.")
        target.status = data["status"]
        target.is_active = data["status"] == User.Status.ACTIVE
        if data["status"] != User.Status.ACTIVE:
            UserSession.objects.filter(user=target, revoked_at__isnull=True).update(revoked_at=timezone.now())

    if data.get("password"):
        _validate_password_policy(str(data["password"]))
        target.set_password(str(data["password"]))

    target.save()
    record_audit_event(
        action="USER_UPDATED_BY_ADMIN",
        resource_type="User",
        resource_id=str(target.id),
        actor=actor,
    )
    return target


@transaction.atomic
def soft_delete_user_by_admin(*, actor: User, target_user_id: UUID) -> User:
    if not is_super_admin(actor):
        raise PermissionDeniedDomainError("فقط مدیر کل مجاز به غیرفعال‌سازی یا حذف نرم کاربر است.")
    if actor.id == target_user_id:
        raise ConflictDomainError("امکان حذف حساب کاربری جاری خودتان وجود ندارد.")
    target = User.objects.filter(id=target_user_id).first()
    if not target:
        raise NotFoundDomainError("کاربر یافت نشد.")
    target.status = User.Status.DELETED
    target.is_active = False
    target.save(update_fields=["status", "is_active", "updated_at"])
    AgencyMembership.objects.filter(user=target, status=AgencyMembership.Status.ACTIVE).update(
        status=AgencyMembership.Status.SUSPENDED
    )
    UserSession.objects.filter(user=target, revoked_at__isnull=True).update(revoked_at=timezone.now())
    record_audit_event(
        action="USER_SOFT_DELETED",
        resource_type="User",
        resource_id=str(target.id),
        actor=actor,
    )
    return target


@transaction.atomic
def assign_user_membership_by_admin(
    *,
    actor: User,
    target_user_id: UUID,
    agency_id: UUID,
    role_code: str,
    branch_id: Optional[UUID] = None,
    status_value: str = "ACTIVE",
) -> AgencyMembership:
    if not is_super_admin(actor):
        raise PermissionDeniedDomainError("فقط مدیر کل مجاز به تخصیص آژانس و شعبه کاربر است.")
    target = User.objects.filter(id=target_user_id).first()
    if not target:
        raise NotFoundDomainError("کاربر یافت نشد.")
    role = (
        Role.objects.filter(code=role_code, agency_id=agency_id).first()
        or Role.objects.filter(code=role_code, agency__isnull=True).first()
    )
    if not role:
        raise NotFoundDomainError("نقش انتخاب‌شده یافت نشد.")
    if status_value not in AgencyMembership.Status.values:
        raise ValidationDomainError("وضعیت عضویت نامعتبر است.")

    membership, _ = AgencyMembership.objects.update_or_create(
        user=target,
        agency_id=agency_id,
        defaults={
            "role": role,
            "branch_id": branch_id,
            "status": status_value,
        },
    )
    if target.platform_role == User.PlatformRole.CUSTOMER:
        target.platform_role = User.PlatformRole.AGENCY_USER
        target.save(update_fields=["platform_role", "updated_at"])
    record_audit_event(
        action="USER_MEMBERSHIP_ASSIGNED",
        resource_type="AgencyMembership",
        resource_id=str(membership.id),
        actor=actor,
        agency_id=agency_id,
        after_state={"user_id": str(target.id), "role": role.code, "branch_id": str(branch_id) if branch_id else None},
    )
    return membership


def update_user_status_by_admin(actor: User, target_user_id: UUID, status_value: str) -> User:
    if not is_super_admin(actor):
        raise PermissionDeniedDomainError("فقط مدیر کل مجاز به تغییر وضعیت کاربر است.")
    target = User.objects.filter(id=target_user_id).first()
    if not target:
        raise NotFoundDomainError("کاربر یافت نشد.")
    if status_value not in User.Status.values:
        raise ValidationDomainError("وضعیت کاربری نامعتبر است.")
    prev = target.status
    target.status = status_value
    target.is_active = status_value == User.Status.ACTIVE
    target.save(update_fields=["status", "is_active", "updated_at"])
    if status_value != User.Status.ACTIVE:
        UserSession.objects.filter(user=target, revoked_at__isnull=True).update(revoked_at=timezone.now())
    record_audit_event(
        action="USER_STATUS_UPDATED",
        resource_type="User",
        resource_id=str(target.id),
        actor=actor,
        before_state={"status": prev},
        after_state={"status": status_value},
    )
    return target


def list_roles_and_permissions(agency_id: Optional[UUID]):
    perms = list(Permission.objects.all().order_by("module", "code"))
    roles_qs = Role.objects.prefetch_related("permissions")
    if agency_id:
        roles_qs = roles_qs.filter(agency_id__in=[None, agency_id])
    else:
        roles_qs = roles_qs.filter(agency__isnull=True)
    return list(roles_qs.order_by("is_system_role", "name")), perms


@transaction.atomic
def create_custom_role(
    *,
    actor: User,
    agency_id: UUID,
    code: str,
    name: str,
    permission_codes: list[str],
) -> Role:
    if not (is_super_admin(actor) or has_agency_permission(actor, agency_id, "agency.manage_policy")):
        raise PermissionDeniedDomainError("عدم مجوز تعریف یا ویرایش نقش در آژانس.")
    clean_code = code.strip().upper()
    if Role.objects.filter(code=clean_code, agency_id=agency_id).exists():
        raise ConflictDomainError("نقشی با این کد در آژانس وجود دارد.")
    role = Role.objects.create(
        code=clean_code,
        name=name.strip(),
        scope=Role.Scope.AGENCY,
        agency_id=agency_id,
        is_system_role=False,
    )
    valid_perms = Permission.objects.filter(code__in=permission_codes)
    for p in valid_perms:
        RolePermission.objects.get_or_create(role=role, permission=p)
    record_audit_event(
        action="ROLE_CREATED",
        resource_type="Role",
        resource_id=str(role.id),
        actor=actor,
        agency_id=agency_id,
        after_state={"code": role.code, "permissions": permission_codes},
    )
    return role


@transaction.atomic
def add_agency_member(
    *,
    actor: User,
    agency_id: UUID,
    phone_number: str,
    first_name: str,
    last_name: str,
    role_code: str,
    branch_id: Optional[UUID] = None,
    password: Optional[str] = None,
    email: Optional[str] = None,
) -> AgencyMembership:
    if not (is_super_admin(actor) or has_agency_permission(actor, agency_id, "agency.manage_policy")):
        raise PermissionDeniedDomainError("شما مجوز افزودن عضو به آژانس را ندارید.")

    role = (
        Role.objects.filter(code=role_code, agency_id=agency_id).first()
        or Role.objects.filter(code=role_code, agency__isnull=True).first()
    )
    if not role:
        raise NotFoundDomainError("نقش انتخاب‌شده یافت نشد.")

    clean_phone = phone_number.strip()
    user = User.objects.filter(phone_number=clean_phone).first()
    already_member = bool(user and AgencyMembership.objects.filter(user=user, agency_id=agency_id, status=AgencyMembership.Status.ACTIVE).exists())

    # Enforce active subscription max_agents quota for new members
    if not already_member and not is_super_admin(actor):
        from apps.subscriptions.models import AgencySubscription

        active_sub = (
            AgencySubscription.objects.select_related("plan")
            .filter(
                agency_id=agency_id,
                status__in=[AgencySubscription.Status.ACTIVE, AgencySubscription.Status.TRIAL],
            )
            .order_by("-expires_at")
            .first()
        )
        if active_sub and active_sub.plan:
            current_agents = AgencyMembership.objects.filter(
                agency_id=agency_id, status=AgencyMembership.Status.ACTIVE
            ).count()
            if current_agents >= active_sub.plan.max_agents:
                raise PermissionDeniedDomainError(
                    f"سقف مجاز مشاوران پلن اشتراک شما ({active_sub.plan.max_agents} نفر) تکمیل شده است. لطفاً پلن خود را ارتقا دهید."
                )

    if user is None:
        user = User.objects.create_user(
            phone_number=clean_phone,
            password=password or "Agent@12345",
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            email=email.strip().lower() if email else None,
            platform_role=User.PlatformRole.AGENCY_USER,
            status=User.Status.ACTIVE,
        )
    elif user.platform_role == User.PlatformRole.CUSTOMER:
        user.platform_role = User.PlatformRole.AGENCY_USER
        user.save(update_fields=["platform_role", "updated_at"])

    membership, created = AgencyMembership.objects.update_or_create(
        user=user,
        agency_id=agency_id,
        defaults={
            "role": role,
            "branch_id": branch_id,
            "status": AgencyMembership.Status.ACTIVE,
        },
    )
    record_audit_event(
        action="AGENCY_MEMBER_ADDED" if created else "AGENCY_MEMBER_UPDATED",
        resource_type="AgencyMembership",
        resource_id=str(membership.id),
        actor=actor,
        agency_id=agency_id,
        after_state={"user": str(user.id), "role": role.code},
    )
    return membership


@transaction.atomic
def update_member_role_or_status(
    *,
    actor: User,
    agency_id: UUID,
    membership_id: UUID,
    role_code: Optional[str] = None,
    status_value: Optional[str] = None,
    branch_id: Optional[UUID] = None,
    clear_branch: bool = False,
) -> AgencyMembership:
    if not (is_super_admin(actor) or has_agency_permission(actor, agency_id, "agency.manage_policy")):
        raise PermissionDeniedDomainError("عدم مجوز ویرایش عضویت تیم.")
    membership = AgencyMembership.objects.filter(id=membership_id, agency_id=agency_id).first()
    if not membership:
        raise NotFoundDomainError("عضویت یافت نشد.")
    prev_role = membership.role.code
    if role_code:
        role = (
            Role.objects.filter(code=role_code, agency_id=agency_id).first()
            or Role.objects.filter(code=role_code, agency__isnull=True).first()
        )
        if not role:
            raise NotFoundDomainError("نقش یافت نشد.")
        membership.role = role
    if status_value:
        if status_value not in AgencyMembership.Status.values:
            raise ValidationDomainError("وضعیت عضویت نامعتبر است.")
        membership.status = status_value
    if clear_branch:
        membership.branch = None
    elif branch_id is not None:
        membership.branch_id = branch_id
    membership.save()
    record_audit_event(
        action="AGENCY_MEMBER_ROLE_UPDATED",
        resource_type="AgencyMembership",
        resource_id=str(membership.id),
        actor=actor,
        agency_id=agency_id,
        before_state={"role": prev_role},
        after_state={"role": membership.role.code, "status": membership.status},
    )
    return membership


@transaction.atomic
def soft_delete_agency_member(*, actor: User, agency_id: UUID, membership_id: UUID) -> AgencyMembership:
    if not (is_super_admin(actor) or has_agency_permission(actor, agency_id, "agency.manage_policy")):
        raise PermissionDeniedDomainError("عدم مجوز تعلیق یا حذف عضو تیم.")
    membership = AgencyMembership.objects.filter(id=membership_id, agency_id=agency_id).first()
    if not membership:
        raise NotFoundDomainError("عضویت یافت نشد.")
    if membership.user_id == actor.id and not is_super_admin(actor):
        raise ConflictDomainError("نمی‌توانید عضویت فعال خودتان را لغو کنید.")
    membership.status = AgencyMembership.Status.LEFT
    membership.save(update_fields=["status"])
    record_audit_event(
        action="AGENCY_MEMBER_REMOVED",
        resource_type="AgencyMembership",
        resource_id=str(membership.id),
        actor=actor,
        agency_id=agency_id,
    )
    return membership


@transaction.atomic
def set_membership_overrides(
    *,
    actor: User,
    agency_id: UUID,
    membership_id: UUID,
    overrides: list[dict],
) -> AgencyMembership:
    if not (is_super_admin(actor) or has_agency_permission(actor, agency_id, "agency.manage_policy")):
        raise PermissionDeniedDomainError("عدم مجوز تنظیم دسترسی‌های فردی.")
    membership = AgencyMembership.objects.filter(id=membership_id, agency_id=agency_id).first()
    if not membership:
        raise NotFoundDomainError("عضویت یافت نشد.")
    MembershipPermissionOverride.objects.filter(membership=membership).delete()
    for item in overrides:
        perm = Permission.objects.filter(code=item["permission_code"]).first()
        if perm and item["effect"] in ("ALLOW", "DENY"):
            MembershipPermissionOverride.objects.create(
                membership=membership, permission=perm, effect=item["effect"]
            )
    record_audit_event(
        action="MEMBERSHIP_OVERRIDES_UPDATED",
        resource_type="AgencyMembership",
        resource_id=str(membership.id),
        actor=actor,
        agency_id=agency_id,
        after_state={"overrides": overrides},
    )
    return membership

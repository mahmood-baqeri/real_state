# Path: backend/django_core/apps/accounts/services.py

import hashlib
import secrets
from typing import Optional
from uuid import UUID
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from apps.audit.services import record_audit_event
from common.exceptions import (
    AuthenticationDomainError,
    ConflictDomainError,
    NotFoundDomainError,
    PermissionDeniedDomainError,
    ValidationDomainError,
)
from common.permissions import get_active_membership, has_agency_permission, is_super_admin
from integrations.registry import get_sms_provider
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
    clean_phone = phone_number.strip()
    if len(password) < 8:
        raise ValidationDomainError("رمز عبور باید حداقل ۸ کاراکتر باشد.")
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
) -> tuple[User, UserSession, Optional[AgencyMembership]]:
    identifier = phone_number.strip()
    user = User.objects.filter(phone_number=identifier).first()
    if user is None or not user.check_password(password):
        LoginAttemptLog.objects.create(
            identifier=identifier,
            user=user,
            ip_address=ip_address,
            succeeded=False,
            failure_reason="INVALID_CREDENTIALS",
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

    user.last_login = timezone.now()
    user.save(update_fields=["last_login"])

    LoginAttemptLog.objects.create(
        identifier=identifier,
        user=user,
        ip_address=ip_address,
        succeeded=True,
    )
    session = UserSession.objects.create(
        user=user,
        device_name=device_name[:128],
        ip_address=ip_address,
        user_agent=(user_agent or "")[:255],
        last_active_at=timezone.now(),
    )
    membership = (
        AgencyMembership.objects.select_related("agency", "role", "branch")
        .filter(user=user, status=AgencyMembership.Status.ACTIVE)
        .first()
    )
    return user, session, membership


def validate_active_session_for_refresh(*, user_id: str, jti: str) -> tuple[User, UserSession]:
    user = User.objects.filter(id=user_id).first()
    if not user or not user.can_authenticate():
        raise AuthenticationDomainError("کاربر یافت نشد یا غیرفعال است.")
    session = UserSession.objects.filter(user=user, jti=jti, revoked_at__isnull=True).first()
    if not session:
        raise AuthenticationDomainError("نشست کاربری منقضی یا لغو شده است.")
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

    sms = get_sms_provider()
    sms_res = sms.send_otp(clean_phone, "password_reset", {"code": otp_code})
    record_audit_event(
        action="PASSWORD_RESET_OTP_REQUESTED",
        resource_type="User",
        resource_id=str(user.id),
        actor=user,
    )
    return {
        "sent": True,
        "provider": sms_res.provider_key,
        "expires_in_seconds": 600,
        # Exposed only in sandbox/console mode to support self-contained testing without real SMS gateway
        "sandbox_otp": otp_code if sms_res.provider_key == "console" else None,
    }


@transaction.atomic
def confirm_password_reset_otp(*, phone_number: str, otp_code: str, new_password: str) -> User:
    clean_phone = phone_number.strip()
    if len(new_password) < 8:
        raise ValidationDomainError("رمز عبور جدید باید حداقل ۸ کاراکتر باشد.")
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
    return updated > 0


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


def list_all_users_for_admin(actor: User):
    if not is_super_admin(actor):
        raise PermissionDeniedDomainError("فقط مدیر کل به لیست کل کاربران دسترسی دارد.")
    return User.objects.prefetch_related("memberships__agency", "memberships__role").order_by("-date_joined")


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
) -> AgencyMembership:
    if not (is_super_admin(actor) or has_agency_permission(actor, agency_id, "agency.manage_policy")):
        raise PermissionDeniedDomainError("عدم مجوز ویرایش عضویت تیم.")
    membership = AgencyMembership.objects.filter(id=membership_id, agency_id=agency_id).first()
    if not membership:
        raise NotFoundDomainError("عضویت یافت نشد.")
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
    if branch_id is not None:
        membership.branch_id = branch_id
    membership.save()
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

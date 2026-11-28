from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, status
import jwt
from pydantic import BaseModel, Field
from app.core.django_bridge import run_django
from app.core.security import build_token_pair, decode_jwt_token, extract_client_ip, new_jti
from app.core.config import settings
from app.dependencies.auth import RequestContext, get_current_context
from app.schemas.common import ok

router = APIRouter(prefix="/auth", tags=["Authentication & Profile"])


class RegisterBody(BaseModel):
    phone_number: str = Field(min_length=7, max_length=24)
    password: str = Field(min_length=8, max_length=128)
    first_name: str = ""
    last_name: str = ""
    email: Optional[str] = None
    preferred_language: str = "fa"
    preferred_calendar: str = "jalali"
    preferred_currency: str = "IRT"


class LoginBody(BaseModel):
    phone_number: str
    password: str
    device_name: str = "Web Browser"
    mfa_code: Optional[str] = None


class MfaCodeBody(BaseModel):
    code: str = Field(min_length=6, max_length=8)


class RefreshBody(BaseModel):
    refresh: str


class PasswordResetRequestBody(BaseModel):
    phone_number: str


class PasswordResetConfirmBody(BaseModel):
    phone_number: str
    otp_code: str
    new_password: str = Field(min_length=8)


class ProfilePatchBody(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    preferred_language: Optional[str] = None
    preferred_calendar: Optional[str] = None
    preferred_currency: Optional[str] = None
    timezone: Optional[str] = None


def _serialize_user(user) -> dict:
    from apps.accounts.models import AgencyMembership
    from common.permissions import get_effective_permissions

    memberships = list(
        user.memberships.select_related("agency", "role", "branch").filter(
            status=AgencyMembership.Status.ACTIVE
        )
    )
    active_agency = memberships[0].agency_id if memberships else None
    return {
        "id": str(user.id),
        "phone_number": user.phone_number,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": user.full_name,
        "platform_role": user.platform_role,
        "status": user.status,
        "preferred_language": user.preferred_language,
        "preferred_calendar": user.preferred_calendar,
        "preferred_currency": user.preferred_currency,
        "timezone": user.timezone,
        "is_mfa_enabled": user.is_mfa_enabled,
        "effective_permissions": get_effective_permissions(user, active_agency),
        "memberships": [
            {
                "id": str(m.id),
                "agency_id": str(m.agency_id),
                "agency_name": m.agency.name,
                "role_code": m.role.code,
                "role_name": m.role.name,
                "branch_id": str(m.branch_id) if m.branch_id else None,
                "branch_name": m.branch.name if m.branch else None,
            }
            for m in memberships
        ],
    }


@router.post("/register", status_code=201)
async def register(body: RegisterBody):
    def _op():
        from apps.accounts.services import register_user

        user = register_user(**body.model_dump())
        return _serialize_user(user)

    return ok(await run_django(_op))


@router.post("/login")
async def login(body: LoginBody, request: Request):
    """ورود را انجام می‌دهد و رویداد تلاش ناموفق را پیش از پاسخ خطا ثبت می‌کند."""
    from common.exceptions import AuthenticationDomainError, PermissionDeniedDomainError

    ip = extract_client_ip(request.client.host if request.client else None)
    ua = request.headers.get("user-agent", "")

    def _op():
        from apps.accounts.services import authenticate_user_credentials
        from common.tenant.context import scoped_user

        try:
            user, session, membership = authenticate_user_credentials(
                phone_number=body.phone_number,
                password=body.password,
                ip_address=ip,
                user_agent=ua,
                device_name=body.device_name,
                mfa_code=body.mfa_code,
            )
        except (AuthenticationDomainError, PermissionDeniedDomainError) as exc:
            return exc
        tokens = build_token_pair(user=user, session=session, membership=membership)
        with scoped_user(user.id):
            return {**tokens, "user": _serialize_user(user)}

    result = await run_django(_op)
    if isinstance(result, (AuthenticationDomainError, PermissionDeniedDomainError)):
        raise result
    return ok(result)


@router.post("/refresh")
async def refresh_token(body: RefreshBody):
    try:
        payload = decode_jwt_token(body.refresh, expected_type="refresh")
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="توکن تازه‌سازی نامعتبر یا منقضی شده است.",
        ) from exc

    def _op():
        from apps.accounts.models import AgencyMembership
        from apps.accounts.services import rotate_user_session, validate_active_session_for_refresh

        user, session = validate_active_session_for_refresh(
            user_id=str(payload.get("user_id")),
            jti=str(payload.get("jti")),
        )
        rotated = rotate_user_session(old_session=session, new_jti=new_jti())
        membership = (
            AgencyMembership.objects.select_related("agency", "role", "branch")
            .filter(user=user, status=AgencyMembership.Status.ACTIVE)
            .first()
        )
        return build_token_pair(user=user, session=rotated, membership=membership)

    return ok(await run_django(_op, user_id=UUID(payload["user_id"])))


@router.post("/logout")
async def logout(ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from django.utils import timezone
        from apps.accounts.models import UserSession
        from apps.audit.services import record_audit_event

        if ctx.session_jti:
            UserSession.objects.filter(
                user=ctx.user, jti=ctx.session_jti, revoked_at__isnull=True
            ).update(revoked_at=timezone.now())
        record_audit_event(
            action="USER_LOGOUT",
            resource_type="User",
            resource_id=str(ctx.user.id),
            actor=ctx.user,
            agency_id=ctx.agency_id,
        )
        return {"logged_out": True}

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/mfa/setup")
async def mfa_setup(ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.accounts.services import setup_mfa_for_user

        return setup_mfa_for_user(ctx.user)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/mfa/enable")
async def mfa_enable(body: MfaCodeBody, ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.accounts.services import enable_mfa_for_user

        user = enable_mfa_for_user(ctx.user, body.code)
        return {"is_mfa_enabled": user.is_mfa_enabled}

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/mfa/disable")
async def mfa_disable(body: MfaCodeBody, ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.accounts.services import disable_mfa_for_user

        user = disable_mfa_for_user(ctx.user, body.code)
        return {"is_mfa_enabled": user.is_mfa_enabled}

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/password-reset/request")
async def password_reset_request(body: PasswordResetRequestBody):
    def _op():
        from apps.accounts.services import request_password_reset_otp

        return request_password_reset_otp(phone_number=body.phone_number)

    return ok(await run_django(_op))


@router.post("/password-reset/confirm")
async def password_reset_confirm(body: PasswordResetConfirmBody):
    def _op():
        from apps.accounts.services import confirm_password_reset_otp

        confirm_password_reset_otp(
            phone_number=body.phone_number,
            otp_code=body.otp_code,
            new_password=body.new_password,
        )
        return {"password_updated": True}

    return ok(await run_django(_op))


@router.get("/me")
async def get_me(ctx: RequestContext = Depends(get_current_context)):
    return ok(await run_django(lambda: _serialize_user(ctx.user), agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/ws-ticket")
async def create_websocket_ticket(ctx: RequestContext = Depends(get_current_context)):
    from datetime import timedelta
    import uuid
    import jwt

    def _op():
        from django.utils import timezone
        from apps.accounts.models import UserSession, WebSocketTicket
        now = timezone.now()
        session = UserSession.objects.filter(
            user=ctx.user, jti=ctx.session_jti, revoked_at__isnull=True
        ).first()
        if not session or (session.expires_at and session.expires_at <= now):
            raise HTTPException(status_code=401, detail="نشست کاربری معتبر نیست.")
        WebSocketTicket.objects.filter(user=ctx.user, expires_at__lt=now).delete()
        ticket_id = uuid.uuid4()
        expires_at = now + timedelta(seconds=30)
        WebSocketTicket.objects.create(
            id=ticket_id,
            ticket_jti=ticket_id,
            user=ctx.user,
            session_jti=str(ctx.session_jti),
            agency_id=ctx.agency_id,
            expires_at=expires_at,
        )
        payload = {
            "user_id": str(ctx.user.id),
            "session_jti": str(ctx.session_jti),
            "ticket_id": str(ticket_id),
            "agency_id": str(ctx.agency_id) if ctx.agency_id else None,
            "token_type": "ws_ticket",
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
        }
        return jwt.encode(payload, settings.JWT_SIGNING_KEY, algorithm=settings.JWT_ALGORITHM)

    ticket = await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id)
    return ok({"ticket": ticket, "expires_in": 30})


@router.patch("/me")
async def patch_me(body: ProfilePatchBody, ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.accounts.services import update_user_profile

        updated = update_user_profile(ctx.user, **body.model_dump())
        return _serialize_user(updated)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


class EmergencyForceLogoutBody(BaseModel):
    password_confirm: str
    exclude_current: bool = True


def _ser_session(s, current_jti: Optional[str] = None) -> dict:
    return {
        "id": str(s.id),
        "user_id": str(s.user_id),
        "user_name": s.user.full_name if s.user else "",
        "user_phone": s.user.phone_number if s.user else "",
        "device_name": s.device_name,
        "device_type": s.device_type,
        "auth_method": s.auth_method,
        "ip_address": s.ip_address,
        "user_agent": s.user_agent,
        "is_suspicious": s.is_suspicious,
        "suspicious_reason": getattr(s, "suspicious_reason", ""),
        "last_active_at": s.last_active_at.isoformat(),
        "expires_at": s.expires_at.isoformat() if s.expires_at else None,
        "created_at": s.created_at.isoformat(),
        "is_current": bool(current_jti and str(s.jti) == str(current_jti)),
    }


@router.get("/sessions")
async def list_sessions(ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.accounts.services import list_user_sessions

        return [_ser_session(s, ctx.session_jti) for s in list_user_sessions(ctx.user)]

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: UUID, ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.accounts.services import revoke_user_session

        ok_flag = revoke_user_session(ctx.user, session_id)
        if not ok_flag:
            raise HTTPException(status_code=404, detail="نشست مورد نظر یافت نشد.")
        return {"revoked": True}

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.get("/admin/sessions")
async def admin_list_sessions(
    user_id: Optional[UUID] = None,
    suspicious_only: bool = False,
    q: Optional[str] = None,
    ctx: RequestContext = Depends(get_current_context),
):
    def _op():
        from apps.accounts.services import list_all_active_sessions

        return [
            _ser_session(s, ctx.session_jti)
            for s in list_all_active_sessions(
                actor=ctx.user, user_id=user_id, suspicious_only=suspicious_only, q=q
            )
        ]

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.delete("/admin/sessions/{session_id}")
async def admin_revoke_session(session_id: UUID, ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.accounts.services import revoke_session_by_admin

        return {"revoked": revoke_session_by_admin(actor=ctx.user, session_id=session_id)}

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/admin/users/{user_id}/revoke-sessions")
async def admin_revoke_user_sessions(user_id: UUID, ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.accounts.services import revoke_all_user_sessions

        return {"revoked_count": revoke_all_user_sessions(actor=ctx.user, target_user_id=user_id)}

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/admin/emergency-force-logout")
async def admin_emergency_force_logout(
    body: EmergencyForceLogoutBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.accounts.services import emergency_force_logout_all

        cnt = emergency_force_logout_all(
            actor=ctx.user,
            password_confirm=body.password_confirm,
            current_jti=ctx.session_jti,
            exclude_current=body.exclude_current,
        )
        return {"revoked_count": cnt}

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.get("/admin/security-events")
async def admin_security_events(ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.accounts.services import list_security_events

        return [
            {
                "id": str(ev.id),
                "identifier": ev.identifier,
                "user_name": ev.user.full_name if ev.user else None,
                "ip_address": ev.ip_address,
                "succeeded": ev.succeeded,
                "failure_reason": ev.failure_reason,
                "created_at": ev.created_at.isoformat(),
            }
            for ev in list_security_events(actor=ctx.user)
        ]

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))

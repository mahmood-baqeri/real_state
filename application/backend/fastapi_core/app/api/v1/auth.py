from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, status
import jwt
from pydantic import BaseModel, Field
from app.core.django_bridge import run_django
from app.core.security import build_token_pair, decode_jwt_token, new_jti
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
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent", "")

    def _op():
        from apps.accounts.services import authenticate_user_credentials

        user, session, membership = authenticate_user_credentials(
            phone_number=body.phone_number,
            password=body.password,
            ip_address=ip,
            user_agent=ua,
            device_name=body.device_name,
        )
        tokens = build_token_pair(user=user, session=session, membership=membership)
        return {**tokens, "user": _serialize_user(user)}

    return ok(await run_django(_op))


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

    return ok(await run_django(_op))


@router.post("/logout")
async def logout(ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from django.utils import timezone
        from apps.accounts.models import UserSession

        if ctx.session_jti:
            UserSession.objects.filter(
                user=ctx.user, jti=ctx.session_jti, revoked_at__isnull=True
            ).update(revoked_at=timezone.now())
        return {"logged_out": True}

    return ok(await run_django(_op))


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
    return ok(await run_django(lambda: _serialize_user(ctx.user), agency_id=ctx.agency_id))


@router.patch("/me")
async def patch_me(body: ProfilePatchBody, ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.accounts.services import update_user_profile

        updated = update_user_profile(ctx.user, **body.model_dump())
        return _serialize_user(updated)

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.get("/sessions")
async def list_sessions(ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.accounts.services import list_user_sessions

        return [
            {
                "id": str(s.id),
                "device_name": s.device_name,
                "ip_address": s.ip_address,
                "user_agent": s.user_agent,
                "last_active_at": s.last_active_at.isoformat(),
                "is_current": str(s.jti) == str(ctx.session_jti),
            }
            for s in list_user_sessions(ctx.user)
        ]

    return ok(await run_django(_op))


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: UUID, ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.accounts.services import revoke_user_session

        ok_flag = revoke_user_session(ctx.user, session_id)
        if not ok_flag:
            raise HTTPException(status_code=404, detail="نشست مورد نظر یافت نشد.")
        return {"revoked": True}

    return ok(await run_django(_op))

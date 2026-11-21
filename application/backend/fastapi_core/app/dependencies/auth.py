from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Optional
from uuid import UUID
from fastapi import Depends, Header, HTTPException, status
import jwt
from app.core.django_bridge import run_django
from app.core.security import decode_jwt_token


@dataclass
class RequestContext:
    user: Optional[Any] = None
    agency_id: Optional[UUID] = None
    membership: Optional[Any] = None
    session_jti: Optional[str] = None
    is_authenticated: bool = False


def _resolve_auth_sync(token: str, header_agency_id: Optional[str]) -> RequestContext:
    from django.utils import timezone
    from apps.accounts.models import AgencyMembership, User, UserSession
    from common.permissions import is_super_admin

    try:
        payload = decode_jwt_token(token, expected_type="access")
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="توکن احراز هویت نامعتبر یا منقضی شده است.",
        ) from exc

    user_id = payload.get("user_id")
    jti = payload.get("jti")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="توکن نامعتبر است.")

    user = User.objects.filter(id=user_id).first()
    if not user or not user.can_authenticate():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="حساب کاربری غیرفعال است.")

    if jti:
        session = UserSession.objects.filter(user=user, jti=jti, revoked_at__isnull=True).first()
        if not session:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="نشست کاربری لغو شده است.")
        now = timezone.now()
        if session.expires_at and session.expires_at < now:
            session.revoked_at = now
            session.save(update_fields=["revoked_at"])
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="نشست کاربری منقضی شده است.")
        try:
            from apps.settings.services import get_setting_value

            idle_mins = int(get_setting_value("security.session_idle_timeout_minutes", 480) or 0)
        except Exception:
            idle_mins = 480
        if idle_mins > 0 and session.last_active_at < now - timedelta(minutes=idle_mins):
            session.revoked_at = now
            session.save(update_fields=["revoked_at"])
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="نشست به دلیل عدم فعالیت منقضی شده است.")
        if (now - session.last_active_at).total_seconds() >= 60:
            session.last_active_at = now
            session.save(update_fields=["last_active_at"])

    resolved_agency_id: Optional[UUID] = None
    if header_agency_id:
        try:
            candidate = UUID(header_agency_id.strip())
            if is_super_admin(user) or AgencyMembership.objects.filter(
                user=user, agency_id=candidate, status=AgencyMembership.Status.ACTIVE
            ).exists():
                resolved_agency_id = candidate
        except ValueError:
            pass

    if resolved_agency_id is None and payload.get("agency_id"):
        try:
            candidate = UUID(str(payload["agency_id"]))
            if is_super_admin(user) or AgencyMembership.objects.filter(
                user=user, agency_id=candidate, status=AgencyMembership.Status.ACTIVE
            ).exists():
                resolved_agency_id = candidate
        except ValueError:
            pass

    membership = None
    if resolved_agency_id:
        membership = (
            AgencyMembership.objects.select_related("agency", "role", "branch")
            .filter(user=user, agency_id=resolved_agency_id, status=AgencyMembership.Status.ACTIVE)
            .first()
        )
    elif not is_super_admin(user):
        membership = (
            AgencyMembership.objects.select_related("agency", "role", "branch")
            .filter(user=user, status=AgencyMembership.Status.ACTIVE)
            .first()
        )
        if membership:
            resolved_agency_id = membership.agency_id

    return RequestContext(
        user=user,
        agency_id=resolved_agency_id,
        membership=membership,
        session_jti=jti,
        is_authenticated=True,
    )


async def get_optional_context(
    authorization: Optional[str] = Header(default=None),
    x_agency_id: Optional[str] = Header(default=None, alias="X-Agency-ID"),
) -> RequestContext:
    if not authorization or not authorization.startswith("Bearer "):
        return RequestContext(is_authenticated=False)
    token = authorization.split(" ", 1)[1].strip()
    return await run_django(_resolve_auth_sync, token, x_agency_id)


async def get_current_context(
    ctx: RequestContext = Depends(get_optional_context),
) -> RequestContext:
    if not ctx.is_authenticated or ctx.user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="برای انجام این عملیات باید وارد حساب کاربری شوید.",
        )
    return ctx


async def require_agency_context(
    ctx: RequestContext = Depends(get_current_context),
) -> RequestContext:
    from common.permissions import is_super_admin

    if ctx.agency_id is None and not is_super_admin(ctx.user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="شناسه آژانس فعال برای این کاربر یافت نشد.",
        )
    return ctx

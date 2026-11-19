# Path: backend/fastapi_core/app/core/security.py

from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Any, Optional
import uuid
import jwt
from .config import settings


def build_token_pair(*, user, session, membership=None) -> dict[str, Any]:
    now = datetime.now(dt_timezone.utc)
    access_exp = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_exp = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

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
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


def decode_jwt_token(token: str, *, expected_type: Optional[str] = None) -> dict[str, Any]:
    payload = jwt.decode(token, settings.JWT_SIGNING_KEY, algorithms=[settings.JWT_ALGORITHM])
    if expected_type and payload.get("token_type") != expected_type:
        raise jwt.InvalidTokenError("Invalid token type.")
    return payload


def new_jti() -> uuid.UUID:
    return uuid.uuid4()

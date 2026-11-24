from .base import *  # noqa: F401, F403
import re
from cryptography.fernet import Fernet

DEBUG = False

if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
    raise RuntimeError("Production environment strictly requires PostgreSQL.")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_HTTPONLY = True


# Production must never inherit development defaults or share signing/encryption keys.
def _require_secret(name: str, value: str, *, min_length: int = 32) -> None:
    if not value or value.strip() != value or len(value) < min_length:
        raise RuntimeError(f"{name} must be explicitly configured with at least {min_length} characters.")
    lowered = value.lower()
    if any(marker in lowered for marker in (
        "change-me", "dev-insecure", "secret-key", "example",
        "development", "change-before-production", "placeholder", "test-only",
    )):
        raise RuntimeError(f"{name} contains a known placeholder value.")

_require_secret("DJANGO_SECRET_KEY", SECRET_KEY)
_require_secret("JWT_SIGNING_KEY", JWT_SIGNING_KEY)
if SECRET_KEY == JWT_SIGNING_KEY:
    raise RuntimeError("JWT_SIGNING_KEY must be independent from DJANGO_SECRET_KEY.")

if not FIELD_ENCRYPTION_KEY:
    raise RuntimeError("DJANGO_FIELD_ENCRYPTION_KEY is required in Production.")
try:
    Fernet(FIELD_ENCRYPTION_KEY.encode("ascii"))
except Exception as exc:
    raise RuntimeError("DJANGO_FIELD_ENCRYPTION_KEY must be a valid Fernet key.") from exc
if FIELD_ENCRYPTION_KEY in {SECRET_KEY, JWT_SIGNING_KEY}:
    raise RuntimeError("Field-encryption key must be independent from Django and JWT signing keys.")

if PRIVATE_MEDIA_ROOT == MEDIA_ROOT or MEDIA_ROOT in PRIVATE_MEDIA_ROOT.parents or PRIVATE_MEDIA_ROOT in MEDIA_ROOT.parents:
    raise RuntimeError("PRIVATE_MEDIA_ROOT and PUBLIC_MEDIA_ROOT must be separate and non-overlapping.")
if ACTIVE_STORAGE_PROVIDER == "s3":
    if not S3_PRIVATE_BUCKET_NAME or S3_PRIVATE_BUCKET_NAME == S3_BUCKET_NAME:
        raise RuntimeError("S3_PRIVATE_BUCKET_NAME must be a dedicated bucket, different from S3_BUCKET_NAME.")
    if not S3_PRIVATE_BUCKET_BLOCK_PUBLIC_ACCESS:
        raise RuntimeError("S3_PRIVATE_BUCKET_BLOCK_PUBLIC_ACCESS=true is required in Production.")

if ACTIVE_PAYMENT_PROVIDER == "sandbox":
    raise RuntimeError("Sandbox payment provider is forbidden in Production.")
if ACTIVE_PAYMENT_PROVIDER not in {"zarinpal", "zibal", "idpay"}:
    raise RuntimeError("Production requires a supported live payment provider.")

if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
    raise RuntimeError("Production DJANGO_ALLOWED_HOSTS must be explicitly restricted.")

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = os.environ.get("DJANGO_SECURE_SSL_REDIRECT", "1").lower() in {"1", "true", "yes"}
SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_SECURE_HSTS_SECONDS", "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

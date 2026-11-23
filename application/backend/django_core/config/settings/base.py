from datetime import timedelta
import os
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR.parent.parent / ".env")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-insecure-secret-key-change-in-prod")
DEBUG = os.environ.get("DJANGO_DEBUG", "False").lower() == "true"

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0").split(",")
    if h.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Core Domain Apps (Modular Monolith — Single Source of Truth)
    "apps.settings",
    "apps.audit",
    "apps.accounts",
    "apps.agencies",
    "apps.branches",
    "apps.properties",
    "apps.property_media",
    "apps.customers",
    "apps.crm",
    "apps.leads",
    "apps.appointments",
    "apps.negotiations",
    "apps.contracts",
    "apps.transactions",
    "apps.commissions",
    "apps.accounting",
    "apps.employees",
    "apps.payroll",
    "apps.subscriptions",
    "apps.payments",
    "apps.notifications",
    "apps.documents",
    "apps.reports",
    "apps.search",
    "apps.support",
    "apps.complaints",
    "apps.surveys",
    "apps.ai_assistant",
    "apps.cms",
    "apps.virtual_tours",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "common.tenant.middleware.TenantContextMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


def parse_database_url(url: str) -> dict:
    parsed = urlparse(url)
    if parsed.scheme in ("postgres", "postgresql"):
        query_params = {k: v[-1] for k, v in parse_qs(parsed.query).items() if v}
        db_config = {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_NAME", ""),
            "USER": os.environ.get("POSTGRES_USER", ""),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
            "HOST": os.environ.get("POSTGRES_HOST", ""),
            "PORT": os.environ.get("POSTGRES_PORT", ""),
            "CONN_MAX_AGE": 60,
            "CONN_HEALTH_CHECKS": True,
        }
        if query_params:
            db_config["OPTIONS"] = query_params
        return db_config
    raise ValueError(
        f"Unsupported DATABASE_URL scheme '{parsed.scheme}'. PostgreSQL is strictly required."
    )


DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://realestate_user:realestate_pass@127.0.0.1:5432/realestate_db",
)
DATABASES = {"default": parse_database_url(DATABASE_URL)}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fa"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Localization Defaults (Country-agnostic architecture; configurable per Agency/User)
PLATFORM_DEFAULTS = {
    "COUNTRY": os.environ.get("DEFAULT_COUNTRY", "IR"),
    "LANGUAGE": os.environ.get("DEFAULT_LANGUAGE", "fa"),
    "CALENDAR": os.environ.get("DEFAULT_CALENDAR", "jalali"),
    "CURRENCY": os.environ.get("DEFAULT_CURRENCY", "IRT"),
    "AREA_UNIT": "SQM",
    "TIMEZONE": os.environ.get("DEFAULT_TIMEZONE", "UTC"),
}

# Field-Level Encryption Key (Fernet)
FIELD_ENCRYPTION_KEY = os.environ.get("DJANGO_FIELD_ENCRYPTION_KEY", "")

# Redis & Celery
REDIS_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TIMEZONE = "UTC"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}

# External Provider Adapter Defaults
ACTIVE_PAYMENT_PROVIDER = os.environ.get("ACTIVE_PAYMENT_PROVIDER", "sandbox")
ACTIVE_SMS_PROVIDER = os.environ.get("ACTIVE_SMS_PROVIDER", "console")
ACTIVE_EMAIL_PROVIDER = os.environ.get("ACTIVE_EMAIL_PROVIDER", "console")
ACTIVE_MAP_PROVIDER = os.environ.get("ACTIVE_MAP_PROVIDER", "osm")
ACTIVE_STORAGE_PROVIDER = os.environ.get("ACTIVE_STORAGE_PROVIDER", "local")
ACTIVE_PUSH_PROVIDER = os.environ.get("ACTIVE_PUSH_PROVIDER", "sandbox")
ACTIVE_ANALYTICS_PROVIDER = os.environ.get("ACTIVE_ANALYTICS_PROVIDER", "internal")
ACTIVE_AI_PROVIDER = os.environ.get("ACTIVE_AI_PROVIDER", "gapgpt")

# GapGPT OpenAI-Compatible AI Provider (https://api.gapgpt.app/v1)
GAPGPT_API_KEY = os.environ.get("GAPGPT_API_KEY", "")
GAPGPT_BASE_URL = os.environ.get("GAPGPT_BASE_URL", "https://api.gapgpt.app/v1")
GAPGPT_DEFAULT_MODEL = os.environ.get("GAPGPT_DEFAULT_MODEL", "gpt-4o")
GAPGPT_TIMEOUT_SECONDS = int(os.environ.get("GAPGPT_TIMEOUT_SECONDS", "25"))

# Storage & Upload Limits
MAX_UPLOAD_FILE_BYTES = int(os.environ.get("MAX_UPLOAD_FILE_BYTES", str(10 * 1024 * 1024)))
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "")
S3_ENDPOINT_URL = os.environ.get("S3_ENDPOINT_URL", "")
S3_ACCESS_KEY_ID = os.environ.get("S3_ACCESS_KEY_ID", "")
S3_SECRET_ACCESS_KEY = os.environ.get("S3_SECRET_ACCESS_KEY", "")
S3_REGION = os.environ.get("S3_REGION", "us-east-1")

# Email & VAPID Config
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "no-reply@bonyanmelk.ir")
VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
VAPID_CLAIMS_EMAIL = os.environ.get("VAPID_CLAIMS_EMAIL", "mailto:support@bonyanmelk.ir")

# JWT Configuration (consumed by FastAPI Sole Web API Layer)
JWT_SIGNING_KEY = os.environ.get("JWT_SIGNING_KEY", SECRET_KEY)
JWT_ALGORITHM = "HS256"
JWT_ACCESS_LIFETIME = timedelta(minutes=int(os.environ.get("JWT_ACCESS_LIFETIME_MINUTES", "30")))
JWT_REFRESH_LIFETIME = timedelta(days=int(os.environ.get("JWT_REFRESH_LIFETIME_DAYS", "7")))

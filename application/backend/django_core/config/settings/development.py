# application/backend/config/settings/development.py
"""
تنظیمات محیط لوکال — روی base.py سوار می‌شود.

استفاده:
    set DJANGO_SETTINGS_MODULE=config.settings.local          (Windows CMD)
    $env:DJANGO_SETTINGS_MODULE="config.settings.local"       (PowerShell)

حالت‌های DB:
  1) Postgres عادی      →  DATABASE_URL از .env خوانده می‌شود
  2) SQLite sandbox      →  USE_LOCAL_SANDBOX_DB=1 ست شود
"""

import os
from .base import *  # noqa: F401, F403

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
DEBUG = True

# در لوکال همه هاست‌ها مجاز باشند (توسعه روی موبایل/شبکه داخلی هم راحت بشه)
ALLOWED_HOSTS = ["*"]

# کلید امن موقت لوکال — در prod حتماً override شود
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY", "local-dev-only-secret-key-not-for-production"
)

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
# حالت پیش‌فرض: Postgres از DATABASE_URL (که در base.py پارس شده)
#
# حالت sandbox (بدون Postgres):
#   set USE_LOCAL_SANDBOX_DB=1
#   → روی SQLite فایل‌محور در application/backend/local_dev.sqlite3
if os.environ.get("USE_LOCAL_SANDBOX_DB") == "1":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "local_dev.sqlite3",
        }
    }

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------
# لوکال: in-memory، نیازی به Redis برای cache نیست
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "realestate-dev-cache",
        "TIMEOUT": 300,
    }
}

# ---------------------------------------------------------------------------
# Sessions / CSRF
# ---------------------------------------------------------------------------
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = False          # چون HTTP در لوکال
CSRF_COOKIE_SECURE = False
CSRF_COOKIE_HTTPONLY = False           # فرانت Next.js به آن نیاز دارد
SESSION_ENGINE = "django.contrib.sessions.backends.db"

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://localhost:8010",
    "http://127.0.0.1:8010",
    "http://localhost:8020",
    "http://127.0.0.1:8020",
]

# ---------------------------------------------------------------------------
# CORS — اجازه به فرانت Next.js
# ---------------------------------------------------------------------------
# نکته: corsheaders باید در INSTALLED_APPS و MIDDLEWARE بالای CommonMiddleware باشد
# (در base.py رعایت شده)

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "x-tenant-id",       # هدر چندمستأجری پروژه شما
    "x-agency-id",
]

CORS_ALLOW_METHODS = ["DELETE", "GET", "OPTIONS", "PATCH", "POST", "PUT"]

# ---------------------------------------------------------------------------
# Celery — در لوکال می‌توانید بدون worker اجرا کنید
# ---------------------------------------------------------------------------
# پیش‌فرض: taskها به‌صورت eager اجرا شوند تا نیازی به worker نباشد.
# اگر می‌خواهید worker واقعی اجرا کنید، این دو خط را کامنت کنید.
CELERY_TASK_ALWAYS_EAGER = os.environ.get("CELERY_EAGER", "1") == "1"
CELERY_TASK_EAGER_PROPAGATES = True

# ---------------------------------------------------------------------------
# Email — چاپ روی کنسول به‌جای ارسال واقعی
# ---------------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ---------------------------------------------------------------------------
# Logging — برای دیباگ راحت‌تر
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "[{asctime}] {levelname} {name}: {message}",
            "style": "{",
            "datefmt": "%H:%M:%S",
        },
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {pathname}:{lineno} — {message}",
            "style": "{",
            "datefmt": "%H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["console"],
            "level": "INFO",       # برای دیدن SQL: "DEBUG"
            "propagate": False,
        },
        "backend": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "celery": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# ---------------------------------------------------------------------------
# امنیت — در لوکال خاموش تا با HTTP کار کند
# ---------------------------------------------------------------------------
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_PROXY_SSL_HEADER = None

# ---------------------------------------------------------------------------
# Static — در لوکال فایل‌ها را از staticfiles/ بخوان
# ---------------------------------------------------------------------------
STATICFILES_DIRS = []  # اگر پوشه static در ریشه دارید: [BASE_DIR / "static"]

# ---------------------------------------------------------------------------
# Django Debug Toolbar — اختیاری
# ---------------------------------------------------------------------------
# اگر نصب است می‌توانید فعال کنید:
# INSTALLED_APPS += ["debug_toolbar"]
# MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")
# INTERNAL_IPS = ["127.0.0.1"]
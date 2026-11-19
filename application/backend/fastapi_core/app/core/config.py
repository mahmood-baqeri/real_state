# Path: backend/fastapi_core/app/core/config.py

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# فایل: fastapi_core/app/core/config.py
# BASE_DIR باید به application/backend برسد
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_FASTAPI_ROOT = Path(__file__).resolve().parent.parent.parent  # = fastapi_core


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    APP_NAME: str = "بنیان ملک | Core Enterprise Web API"
    API_PREFIX: str = "/api/v1"

    # مسیر Django Core (پکیج قابل import)
    BACKEND_DIR: str = os.environ.get(
        "BACKEND_DIR", str(_BACKEND_ROOT / "django_core")
    )
    DJANGO_SETTINGS_MODULE: str = os.environ.get(
        "DJANGO_SETTINGS_MODULE", "config.settings.development"
    )

    # JWT
    JWT_SIGNING_KEY: str = os.environ.get(
        "JWT_SIGNING_KEY",
        os.environ.get("DJANGO_SECRET_KEY", "dev-insecure-secret-key-change-in-prod"),
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.environ.get("JWT_ACCESS_LIFETIME_MINUTES", "60")
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(
        os.environ.get("JWT_REFRESH_LIFETIME_DAYS", "7")
    )

    # CORS — لیست صریح، هرگز "*"
    CORS_ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]

    # Rate limiting
    REDIS_URL: str = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")
    RATE_LIMIT_ENABLED: bool = os.environ.get("RATE_LIMIT_ENABLED", "1") == "1"

    # Environment flag (به‌جای استفاده از settings.DEBUG مستقیم)
    ENVIRONMENT: str = os.environ.get("ENVIRONMENT", "development")


settings = Settings()
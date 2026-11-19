import os
from pathlib import Path
from pydantic_settings import BaseSettings

# .../backend/fastapi_core/app/core/config.py -> parent^4 == .../backend
BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _parse_origins() -> list[str]:
    raw = os.environ.get(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    )
    origins = [o.strip() for o in raw.split(",") if o.strip() and o.strip() != "*"]
    app_url = (os.environ.get("APP_URL") or "").strip().rstrip("/")
    if app_url and app_url.startswith(("http://", "https://")) and app_url not in origins:
        origins.append(app_url)
    return origins or ["http://localhost:3000"]


class Settings(BaseSettings):
    APP_NAME: str = "بنیان ملک | Core Enterprise Web API"
    API_PREFIX: str = "/api/v1"
    BACKEND_DIR: str = os.environ.get("BACKEND_DIR", str(BACKEND_ROOT / "django_core"))
    REDIS_URL: str = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")
    JWT_SIGNING_KEY: str = os.environ.get(
        "JWT_SIGNING_KEY",
        os.environ.get("DJANGO_SECRET_KEY", "dev-insecure-secret-key-change-in-prod"),
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.environ.get("JWT_ACCESS_LIFETIME_MINUTES", "60"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.environ.get("JWT_REFRESH_LIFETIME_DAYS", "7"))

    @property
    def CORS_ALLOWED_ORIGINS(self) -> list[str]:
        return _parse_origins()


settings = Settings()

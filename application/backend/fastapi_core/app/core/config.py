import os
from pathlib import Path
from pydantic_settings import BaseSettings

# .../backend/fastapi/app/core/config.py -> parent^4 == .../backend
BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    APP_NAME: str = "بنیان ملک | Core Enterprise Web API"
    API_PREFIX: str = "/api/v1"
    BACKEND_DIR: str = os.environ.get("BACKEND_DIR", str(BACKEND_ROOT / "django_core"))
    JWT_SIGNING_KEY: str = os.environ.get(
        "JWT_SIGNING_KEY",
        os.environ.get("DJANGO_SECRET_KEY", "dev-insecure-secret-key-change-in-prod"),
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.environ.get("JWT_ACCESS_LIFETIME_MINUTES", "60"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.environ.get("JWT_REFRESH_LIFETIME_DAYS", "7"))


settings = Settings()

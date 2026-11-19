# Path: backend/fastapi_core/main.py

from app.main import app, lifespan, v1_router

__all__ = ["app", "lifespan", "v1_router"]

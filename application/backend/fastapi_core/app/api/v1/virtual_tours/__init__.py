from fastapi import APIRouter
from .capture_panorama import router as capture_panorama_router
from .files_public import router as files_public_router
from .geometry_models import router as geometry_models_router
from .scans import router as scans_router
from .tours import router as tours_router

router = APIRouter()
router.include_router(files_public_router)
router.include_router(tours_router)
router.include_router(capture_panorama_router)
router.include_router(geometry_models_router)
router.include_router(scans_router)

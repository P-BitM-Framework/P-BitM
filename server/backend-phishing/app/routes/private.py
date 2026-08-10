"""Private campaign API assembled from responsibility-specific routers."""

from fastapi import APIRouter

from .private_collection import (
    api_router as collection_api_router,
    raw_router as collection_raw_router,
)
from .private_commands import api_router as commands_api_router
from .private_sessions import api_router as sessions_api_router
from .private_webcam import api_router as webcam_api_router

api_router = APIRouter(prefix="/api")
api_router.include_router(sessions_api_router)
api_router.include_router(collection_api_router)
api_router.include_router(commands_api_router)
api_router.include_router(webcam_api_router)

raw_router = APIRouter()
raw_router.include_router(collection_raw_router)

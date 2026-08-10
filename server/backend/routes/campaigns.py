"""Campaign API router assembled from responsibility-specific modules."""

from fastapi import APIRouter

from .campaign_actions import router as actions_router
from .campaign_lifecycle import router as lifecycle_router
from .campaign_victims import router as victims_router

# The application supplies the final ``/api/campaigns`` prefix. Copying the
# already-built routes preserves the collection-level empty path while avoiding
# FastAPI's prohibition on nesting an empty child path below an empty prefix.
router = APIRouter()
router.routes.extend(lifecycle_router.routes)
router.routes.extend(victims_router.routes)
router.routes.extend(actions_router.routes)

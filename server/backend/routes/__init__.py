# admin-backend/routes/__init__.py
from .auth import router as auth_router
from .campaigns import router as campaigns_router
from .users import router as users_router
from .target_lists import router as target_lists_router
from .email_templates import router as email_templates_router
from .sending_profiles import router as sending_profiles_router
from .tracking import router as tracking_router
from .plugins import router as plugins_router
from .landing_pages import router as landing_pages_router
from .modules import router as modules_router

__all__ = [
    "auth_router",
    "campaigns_router",
    "users_router",
    "target_lists_router",
    "email_templates_router",
    "sending_profiles_router",
    "tracking_router",
    "plugins_router",
    "landing_pages_router",
    "modules_router"
]
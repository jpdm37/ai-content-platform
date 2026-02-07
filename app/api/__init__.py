from app.api.auth import router as auth_router
from app.api.brands import router as brands_router
from app.api.categories import router as categories_router
from app.api.trends import router as trends_router
from app.api.generate import router as generate_router
from app.api.lora import router as lora_router
from app.api.billing import router as billing_router
from app.api.social import router as social_router
from app.api.video import router as video_router
from app.api.studio import router as studio_router
from app.api.brandvoice import router as brandvoice_router
from app.api.analytics import router as analytics_router
from app.api.assistant import router as assistant_router
from app.api.admin import router as admin_router
from app.api.costs import router as costs_router
from app.api.onboarding import router as onboarding_router
from app.api.templates import router as templates_router
from app.api.digest import router as digest_router
from app.api.calendar import router as calendar_router
from app.api.abtesting import router as abtesting_router
from app.api.performance import router as performance_router

__all__ = [
    "auth_router",
    "brands_router",
    "categories_router", 
    "trends_router",
    "generate_router",
    "lora_router",
    "billing_router",
    "social_router",
    "video_router",
    "studio_router",
    "brandvoice_router",
    "analytics_router",
    "assistant_router",
    "admin_router",
    "costs_router",
    "onboarding_router",
    "templates_router",
    "digest_router",
    "calendar_router",
    "abtesting_router",
    "performance_router"
]

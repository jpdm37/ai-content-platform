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
    "assistant_router"
]

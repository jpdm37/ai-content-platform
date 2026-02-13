"""
API Routes Initialization

Registers all API routers with the FastAPI application.
"""
from fastapi import APIRouter

# Import all routers
from app.api.auth import router as auth_router
from app.api.brands import router as brands_router
from app.api.categories import router as categories_router
from app.api.trends import router as trends_router
from app.api.generate import router as generate_router
from app.api.avatar import router as avatar_router  # NEW: Avatar generation endpoints

# Try to import optional routers
try:
    from app.api.social import router as social_router
    HAS_SOCIAL = True
except ImportError:
    HAS_SOCIAL = False

try:
    from app.api.onboarding import router as onboarding_router
    HAS_ONBOARDING = True
except ImportError:
    HAS_ONBOARDING = False

try:
    from app.api.billing import router as billing_router
    HAS_BILLING = True
except ImportError:
    HAS_BILLING = False

try:
    from app.lora.api import router as lora_router
    HAS_LORA = True
except ImportError:
    HAS_LORA = False

try:
    from app.api.studio import router as studio_router
    HAS_STUDIO = True
except ImportError:
    HAS_STUDIO = False

try:
    from app.api.calendar import router as calendar_router
    HAS_CALENDAR = True
except ImportError:
    HAS_CALENDAR = False

# Create main API router
api_router = APIRouter()

# Register core routers (always available)
api_router.include_router(auth_router)
api_router.include_router(brands_router)
api_router.include_router(categories_router)
api_router.include_router(trends_router)
api_router.include_router(generate_router)
api_router.include_router(avatar_router)  # Avatar endpoints for onboarding

# Register optional routers if available
if HAS_SOCIAL:
    api_router.include_router(social_router)

if HAS_ONBOARDING:
    api_router.include_router(onboarding_router)

if HAS_BILLING:
    api_router.include_router(billing_router)

if HAS_LORA:
    api_router.include_router(lora_router)

if HAS_STUDIO:
    api_router.include_router(studio_router)

if HAS_CALENDAR:
    api_router.include_router(calendar_router)


def get_available_routes():
    """Return list of available API modules"""
    routes = [
        "auth",
        "brands", 
        "categories",
        "trends",
        "generate",
        "avatar"  # Always available
    ]
    
    if HAS_SOCIAL:
        routes.append("social")
    if HAS_ONBOARDING:
        routes.append("onboarding")
    if HAS_BILLING:
        routes.append("billing")
    if HAS_LORA:
        routes.append("lora")
    if HAS_STUDIO:
        routes.append("studio")
    if HAS_CALENDAR:
        routes.append("calendar")
    
    return routes

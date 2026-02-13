"""
API Routes Initialization

Exports all routers for main.py to import.
Each router is imported with error handling to prevent startup failures.
"""
from fastapi import APIRouter

# ============ Import all routers with error handling ============

# Core routers (required)
try:
    from app.api.auth import router as auth_router
except ImportError as e:
    print(f"Warning: Could not import auth_router: {e}")
    auth_router = APIRouter(prefix="/auth", tags=["auth"])

try:
    from app.api.brands import router as brands_router
except ImportError as e:
    print(f"Warning: Could not import brands_router: {e}")
    brands_router = APIRouter(prefix="/brands", tags=["brands"])

try:
    from app.api.categories import router as categories_router
except ImportError as e:
    print(f"Warning: Could not import categories_router: {e}")
    categories_router = APIRouter(prefix="/categories", tags=["categories"])

try:
    from app.api.trends import router as trends_router
except ImportError as e:
    print(f"Warning: Could not import trends_router: {e}")
    trends_router = APIRouter(prefix="/trends", tags=["trends"])

try:
    from app.api.generate import router as generate_router
except ImportError as e:
    print(f"Warning: Could not import generate_router: {e}")
    generate_router = APIRouter(prefix="/generate", tags=["generate"])

# Avatar router
try:
    from app.api.avatar import router as avatar_router
except ImportError as e:
    print(f"Warning: Could not import avatar_router: {e}")
    avatar_router = APIRouter(prefix="/avatar", tags=["avatar"])

# LoRA router - try app.lora.api first, then app.api.lora
try:
    from app.lora.api import router as lora_router
except ImportError:
    try:
        from app.api.lora import router as lora_router
    except ImportError as e:
        print(f"Warning: Could not import lora_router: {e}")
        lora_router = APIRouter(prefix="/lora", tags=["lora"])

# Billing router
try:
    from app.api.billing import router as billing_router
except ImportError as e:
    print(f"Warning: Could not import billing_router: {e}")
    billing_router = APIRouter(prefix="/billing", tags=["billing"])

# Social router
try:
    from app.api.social import router as social_router
except ImportError as e:
    print(f"Warning: Could not import social_router: {e}")
    social_router = APIRouter(prefix="/social", tags=["social"])

# Video router
try:
    from app.api.video import router as video_router
except ImportError as e:
    print(f"Warning: Could not import video_router: {e}")
    video_router = APIRouter(prefix="/video", tags=["video"])

# Studio router
try:
    from app.api.studio import router as studio_router
except ImportError as e:
    print(f"Warning: Could not import studio_router: {e}")
    studio_router = APIRouter(prefix="/studio", tags=["studio"])

# Brand Voice router
try:
    from app.api.brandvoice import router as brandvoice_router
except ImportError as e:
    print(f"Warning: Could not import brandvoice_router: {e}")
    brandvoice_router = APIRouter(prefix="/brandvoice", tags=["brandvoice"])

# Analytics router
try:
    from app.api.analytics import router as analytics_router
except ImportError as e:
    print(f"Warning: Could not import analytics_router: {e}")
    analytics_router = APIRouter(prefix="/analytics", tags=["analytics"])

# Assistant router
try:
    from app.api.assistant import router as assistant_router
except ImportError as e:
    print(f"Warning: Could not import assistant_router: {e}")
    assistant_router = APIRouter(prefix="/assistant", tags=["assistant"])

# Costs router
try:
    from app.api.costs import router as costs_router
except ImportError as e:
    print(f"Warning: Could not import costs_router: {e}")
    costs_router = APIRouter(prefix="/costs", tags=["costs"])

# Onboarding router
try:
    from app.api.onboarding import router as onboarding_router
except ImportError as e:
    print(f"Warning: Could not import onboarding_router: {e}")
    onboarding_router = APIRouter(prefix="/onboarding", tags=["onboarding"])

# Templates router
try:
    from app.api.templates import router as templates_router
except ImportError as e:
    print(f"Warning: Could not import templates_router: {e}")
    templates_router = APIRouter(prefix="/templates", tags=["templates"])

# Digest router
try:
    from app.api.digest import router as digest_router
except ImportError as e:
    print(f"Warning: Could not import digest_router: {e}")
    digest_router = APIRouter(prefix="/digest", tags=["digest"])

# Calendar router
try:
    from app.api.calendar import router as calendar_router
except ImportError as e:
    print(f"Warning: Could not import calendar_router: {e}")
    calendar_router = APIRouter(prefix="/calendar", tags=["calendar"])

# A/B Testing router
try:
    from app.api.abtesting import router as abtesting_router
except ImportError as e:
    print(f"Warning: Could not import abtesting_router: {e}")
    abtesting_router = APIRouter(prefix="/abtesting", tags=["abtesting"])

# Performance router
try:
    from app.api.performance import router as performance_router
except ImportError as e:
    print(f"Warning: Could not import performance_router: {e}")
    performance_router = APIRouter(prefix="/performance", tags=["performance"])

# Setup router
try:
    from app.api.setup import router as setup_router
except ImportError as e:
    print(f"Warning: Could not import setup_router: {e}")
    setup_router = APIRouter(prefix="/setup", tags=["setup"])


# ============ Export all routers ============
__all__ = [
    'auth_router',
    'brands_router',
    'categories_router',
    'trends_router',
    'generate_router',
    'avatar_router',
    'lora_router',
    'billing_router',
    'social_router',
    'video_router',
    'studio_router',
    'brandvoice_router',
    'analytics_router',
    'assistant_router',
    'costs_router',
    'onboarding_router',
    'templates_router',
    'digest_router',
    'calendar_router',
    'abtesting_router',
    'performance_router',
    'setup_router',
]

"""
Rate Limiting Middleware
========================

Implements tiered rate limiting based on user subscription level.
Uses SlowAPI with Redis backend for distributed rate limiting.
"""

import logging
from typing import Optional, Callable
from fastapi import Request, HTTPException, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.responses import JSONResponse

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ==================== Rate Limit Configuration ====================

# Limits by subscription tier (requests per minute)
TIER_LIMITS = {
    "free": {
        "default": "10/minute",
        "auth": "5/minute",
        "generation": "3/minute",
        "upload": "5/minute",
        "api": "20/minute",
    },
    "creator": {
        "default": "60/minute",
        "auth": "10/minute",
        "generation": "20/minute",
        "upload": "20/minute",
        "api": "100/minute",
    },
    "pro": {
        "default": "120/minute",
        "auth": "20/minute",
        "generation": "60/minute",
        "upload": "60/minute",
        "api": "300/minute",
    },
    "agency": {
        "default": "300/minute",
        "auth": "30/minute",
        "generation": "120/minute",
        "upload": "120/minute",
        "api": "600/minute",
    },
}

# Endpoint categories for rate limiting
ENDPOINT_CATEGORIES = {
    # Auth endpoints - stricter limits
    "/api/v1/auth/login": "auth",
    "/api/v1/auth/register": "auth",
    "/api/v1/auth/forgot-password": "auth",
    "/api/v1/auth/reset-password": "auth",
    "/api/v1/admin/login": "auth",
    
    # Generation endpoints - resource intensive
    "/api/v1/generate": "generation",
    "/api/v1/studio/projects": "generation",
    "/api/v1/video/generate": "generation",
    "/api/v1/lora/train": "generation",
    "/api/v1/brandvoice/generate": "generation",
    "/api/v1/assistant/chat": "generation",
    
    # Upload endpoints
    "/api/v1/lora/images": "upload",
    "/api/v1/video/upload": "upload",
    
    # Default API endpoints
    "default": "api",
}


# ==================== Key Functions ====================

def get_user_identifier(request: Request) -> str:
    """
    Get unique identifier for rate limiting.
    Uses user ID if authenticated, otherwise IP address.
    """
    # Try to get user from request state (set by auth middleware)
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "id"):
        return f"user:{user.id}"
    
    # Try to get from authorization header
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        # Use first 16 chars of token as identifier
        token_prefix = auth_header[7:23]
        return f"token:{token_prefix}"
    
    # Fall back to IP address
    return f"ip:{get_remote_address(request)}"


def get_user_tier(request: Request) -> str:
    """Get user's subscription tier for rate limit selection."""
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "subscription_tier"):
        return user.subscription_tier
    
    # Check if request has tier info from middleware
    tier = getattr(request.state, "subscription_tier", None)
    if tier:
        return tier
    
    return "free"


def get_endpoint_category(path: str) -> str:
    """Determine the rate limit category for an endpoint."""
    # Check exact matches first
    if path in ENDPOINT_CATEGORIES:
        return ENDPOINT_CATEGORIES[path]
    
    # Check prefix matches
    for endpoint, category in ENDPOINT_CATEGORIES.items():
        if endpoint != "default" and path.startswith(endpoint):
            return category
    
    return "api"  # Default category


def get_rate_limit_string(request: Request) -> str:
    """
    Dynamic rate limit based on user tier and endpoint.
    """
    tier = get_user_tier(request)
    category = get_endpoint_category(request.url.path)
    
    tier_limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
    limit = tier_limits.get(category, tier_limits["default"])
    
    return limit


# ==================== Limiter Setup ====================

def create_limiter() -> Limiter:
    """Create and configure the rate limiter."""
    
    # Use Redis if available, otherwise in-memory
    storage_uri = settings.redis_url if settings.redis_url else "memory://"
    
    limiter = Limiter(
        key_func=get_user_identifier,
        default_limits=["100/minute"],
        storage_uri=storage_uri,
        strategy="fixed-window",
        headers_enabled=True,  # Add X-RateLimit headers
    )
    
    return limiter


# Create global limiter instance
limiter = create_limiter()


# ==================== Exception Handler ====================

async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Custom handler for rate limit exceeded errors."""
    
    tier = get_user_tier(request)
    
    # Build helpful error message
    message = f"Rate limit exceeded. "
    
    if tier == "free":
        message += "Upgrade to Creator plan for higher limits."
    elif tier == "creator":
        message += "Upgrade to Pro plan for higher limits."
    elif tier == "pro":
        message += "Upgrade to Agency plan for highest limits."
    else:
        message += "Please wait before making more requests."
    
    response = JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "rate_limit_exceeded",
            "message": message,
            "retry_after": exc.detail,
            "tier": tier,
            "upgrade_url": "/pricing" if tier != "agency" else None
        },
        headers={
            "Retry-After": str(exc.detail),
            "X-RateLimit-Tier": tier
        }
    )
    
    logger.warning(
        f"Rate limit exceeded: {get_user_identifier(request)} "
        f"on {request.url.path} (tier: {tier})"
    )
    
    return response


# ==================== Decorator Helpers ====================

def limit_by_tier(category: str = "default"):
    """
    Decorator factory for tier-based rate limiting.
    
    Usage:
        @router.post("/generate")
        @limit_by_tier("generation")
        async def generate_content(...):
            ...
    """
    def get_limit(request: Request) -> str:
        tier = get_user_tier(request)
        tier_limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
        return tier_limits.get(category, tier_limits["default"])
    
    return limiter.limit(get_limit)


# Pre-configured decorators for common use cases
limit_auth = limit_by_tier("auth")
limit_generation = limit_by_tier("generation")
limit_upload = limit_by_tier("upload")
limit_api = limit_by_tier("api")


# ==================== Middleware Setup ====================

def setup_rate_limiting(app):
    """
    Configure rate limiting for the FastAPI app.
    
    Call this in main.py:
        from app.core.rate_limit import setup_rate_limiting, limiter
        setup_rate_limiting(app)
        app.state.limiter = limiter
    """
    # Add limiter to app state
    app.state.limiter = limiter
    
    # Add exception handler
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    
    # Add middleware
    app.add_middleware(SlowAPIMiddleware)
    
    logger.info("Rate limiting configured successfully")


# ==================== Health Check Bypass ====================

# Endpoints that should bypass rate limiting
BYPASS_ENDPOINTS = [
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
]


def should_bypass_rate_limit(request: Request) -> bool:
    """Check if request should bypass rate limiting."""
    return request.url.path in BYPASS_ENDPOINTS


# ==================== Rate Limit Info Endpoint ====================

async def get_rate_limit_info(request: Request) -> dict:
    """Get current rate limit status for user."""
    tier = get_user_tier(request)
    limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
    
    return {
        "tier": tier,
        "limits": limits,
        "identifier": get_user_identifier(request),
        "upgrade_available": tier != "agency"
    }

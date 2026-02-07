"""
AI Content Platform - Main Application
FastAPI application for AI-powered social media content generation
"""
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.core.config import get_settings
from app.core.database import engine, Base, SessionLocal
from app.core.sentry import init_sentry, setup_sentry_middleware
from app.core.rate_limit import setup_rate_limiting, limiter
from app.api import (
    auth_router,
    brands_router,
    categories_router,
    trends_router,
    generate_router,
    lora_router,
    billing_router,
    social_router,
    video_router,
    studio_router,
    brandvoice_router,
    analytics_router,
    assistant_router,
    costs_router,
    onboarding_router,
    templates_router,
    digest_router,
    calendar_router,
    abtesting_router,
    performance_router
)
from app.api.admin import router as admin_router
from app.api.admin_enhanced import router as admin_enhanced_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()

# Initialize Sentry (before app creation)
if settings.sentry_dsn:
    init_sentry(
        dsn=settings.sentry_dsn,
        environment=settings.environment
    )
    logger.info(f"Sentry initialized for {settings.environment}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="""
    AI Content Platform API
    
    Generate AI-powered social media content including:
    - AI Avatar/Persona creation for brands
    - Trend scraping from multiple sources
    - Image generation using AI
    - Caption and hashtag generation
    - Video generation with lip-sync
    - Brand voice training
    
    Built for production-ready AI content creation.
    """,
    version=settings.app_version,
    lifespan=lifespan
)

# Setup Sentry middleware (before other middleware)
if settings.sentry_dsn:
    setup_sentry_middleware(app)

# Setup rate limiting
if settings.rate_limit_enabled:
    setup_rate_limiting(app)
    logger.info("Rate limiting enabled")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:3000",
        "http://localhost:5173",
    ] if settings.environment == "production" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    # In production, don't expose error details
    if settings.environment == "production":
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "message": "An unexpected error occurred. Please try again later.",
            }
        )
    else:
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "message": str(exc),
                "type": type(exc).__name__
            }
        )

# Include routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(brands_router, prefix="/api/v1")
app.include_router(categories_router, prefix="/api/v1")
app.include_router(trends_router, prefix="/api/v1")
app.include_router(generate_router, prefix="/api/v1")
app.include_router(lora_router, prefix="/api/v1")
app.include_router(billing_router, prefix="/api/v1")
app.include_router(social_router, prefix="/api/v1")
app.include_router(video_router, prefix="/api/v1")
app.include_router(studio_router, prefix="/api/v1")
app.include_router(brandvoice_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(assistant_router, prefix="/api/v1")
app.include_router(costs_router, prefix="/api/v1")
app.include_router(onboarding_router, prefix="/api/v1")
app.include_router(templates_router, prefix="/api/v1")
app.include_router(digest_router, prefix="/api/v1")
app.include_router(calendar_router, prefix="/api/v1")
app.include_router(abtesting_router, prefix="/api/v1")
app.include_router(performance_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(admin_enhanced_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI Content Platform API",
        "version": settings.app_version,
        "environment": settings.environment,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and load balancers"""
    db_status = "unknown"
    redis_status = "not configured (using in-memory)"
    
    # Test database connection
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)[:100]}"
        logger.error(f"Database health check failed: {e}")
    
    # Test Redis connection (if configured)
    if settings.redis_url:
        try:
            import redis
            r = redis.from_url(settings.redis_url, socket_connect_timeout=2)
            r.ping()
            redis_status = "connected"
        except Exception as e:
            redis_status = "error (falling back to in-memory)"
            logger.warning(f"Redis health check failed: {e}")
    
    # Overall status
    is_healthy = db_status == "connected"
    
    return {
        "status": "healthy" if is_healthy else "degraded",
        "version": settings.app_version,
        "environment": settings.environment,
        "checks": {
            "database": db_status,
            "redis": redis_status,
            "sentry": "configured" if settings.sentry_dsn else "not configured",
            "rate_limiting": "enabled" if settings.rate_limit_enabled else "disabled"
        }
    }

@app.get("/api/v1/status")
async def api_status():
    """API status and configuration check"""
    return {
        "api_version": settings.app_version,
        "environment": settings.environment,
        "features": {
            "openai": bool(settings.openai_api_key),
            "replicate": bool(settings.replicate_api_token),
            "stripe": bool(settings.stripe_secret_key),
            "email": bool(settings.smtp_host),
            "sentry": bool(settings.sentry_dsn),
            "rate_limiting": settings.rate_limit_enabled
        },
        "endpoints": {
            "auth": "/api/v1/auth",
            "brands": "/api/v1/brands",
            "studio": "/api/v1/studio",
            "video": "/api/v1/video",
            "social": "/api/v1/social",
            "billing": "/api/v1/billing",
            "analytics": "/api/v1/analytics",
            "costs": "/api/v1/costs"
        }
    }


@app.get("/api/v1/rate-limit-info")
@limiter.limit("10/minute")
async def rate_limit_info(request: Request):
    """Get current rate limit status"""
    from app.core.rate_limit import get_rate_limit_info
    return await get_rate_limit_info(request)

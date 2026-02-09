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
allowed_origins = [
    settings.frontend_url,
    "http://localhost:3000",
    "http://localhost:5173",
    "https://ai-content-platform-1-iogw.onrender.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin for origin in allowed_origins if origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    # Get error message safely
    error_message = str(exc) if exc else "An unexpected error occurred"
    error_type = type(exc).__name__ if exc else "Unknown"
    
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
                "message": error_message,
                "type": error_type
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


@app.get("/fix-db")
async def fix_database():
    """Add missing database columns across core feature tables."""
    from sqlalchemy import text
    from app.core.database import engine

    statements = [
        # lora_models table
        "ALTER TABLE lora_models ADD COLUMN IF NOT EXISTS version VARCHAR(50)",
        "ALTER TABLE lora_models ADD COLUMN IF NOT EXISTS trigger_word VARCHAR(255)",
        "ALTER TABLE lora_models ADD COLUMN IF NOT EXISTS base_model VARCHAR(100)",
        "ALTER TABLE lora_models ADD COLUMN IF NOT EXISTS training_steps INTEGER",
        "ALTER TABLE lora_models ADD COLUMN IF NOT EXISTS learning_rate FLOAT",
        "ALTER TABLE lora_models ADD COLUMN IF NOT EXISTS lora_rank INTEGER",
        "ALTER TABLE lora_models ADD COLUMN IF NOT EXISTS resolution INTEGER",
        "ALTER TABLE lora_models ADD COLUMN IF NOT EXISTS replicate_training_id VARCHAR(255)",
        "ALTER TABLE lora_models ADD COLUMN IF NOT EXISTS replicate_model_owner VARCHAR(255)",
        "ALTER TABLE lora_models ADD COLUMN IF NOT EXISTS replicate_model_name VARCHAR(255)",
        "ALTER TABLE lora_models ADD COLUMN IF NOT EXISTS replicate_version VARCHAR(255)",
        "ALTER TABLE lora_models ADD COLUMN IF NOT EXISTS lora_weights_url TEXT",
        "ALTER TABLE lora_models ADD COLUMN IF NOT EXISTS lora_weights_size_mb FLOAT",
        "ALTER TABLE lora_models ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'pending'",
        "ALTER TABLE lora_models ADD COLUMN IF NOT EXISTS progress_percent INTEGER DEFAULT 0",
        "ALTER TABLE lora_models ADD COLUMN IF NOT EXISTS error_message TEXT",
        "ALTER TABLE lora_models ADD COLUMN IF NOT EXISTS consistency_score FLOAT",
        "ALTER TABLE lora_models ADD COLUMN IF NOT EXISTS test_images_generated INTEGER DEFAULT 0",
        "ALTER TABLE lora_models ADD COLUMN IF NOT EXISTS training_cost_usd FLOAT",
        "ALTER TABLE lora_models ADD COLUMN IF NOT EXISTS training_duration_seconds INTEGER",
        "ALTER TABLE lora_models ADD COLUMN IF NOT EXISTS training_started_at TIMESTAMP",
        "ALTER TABLE lora_models ADD COLUMN IF NOT EXISTS training_completed_at TIMESTAMP",
        "ALTER TABLE lora_models ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE",
        "ALTER TABLE lora_models ADD COLUMN IF NOT EXISTS is_public BOOLEAN DEFAULT FALSE",

        # studio_projects table
        "ALTER TABLE studio_projects ADD COLUMN IF NOT EXISTS brief TEXT",
        "ALTER TABLE studio_projects ADD COLUMN IF NOT EXISTS target_platforms TEXT",
        "ALTER TABLE studio_projects ADD COLUMN IF NOT EXISTS content_types TEXT",
        "ALTER TABLE studio_projects ADD COLUMN IF NOT EXISTS tone VARCHAR(100)",
        "ALTER TABLE studio_projects ADD COLUMN IF NOT EXISTS num_variations INTEGER DEFAULT 1",
        "ALTER TABLE studio_projects ADD COLUMN IF NOT EXISTS lora_model_id INTEGER",
        "ALTER TABLE studio_projects ADD COLUMN IF NOT EXISTS include_video BOOLEAN DEFAULT FALSE",
        "ALTER TABLE studio_projects ADD COLUMN IF NOT EXISTS video_duration VARCHAR(20)",
        "ALTER TABLE studio_projects ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'draft'",
        "ALTER TABLE studio_projects ADD COLUMN IF NOT EXISTS progress_percent INTEGER DEFAULT 0",
        "ALTER TABLE studio_projects ADD COLUMN IF NOT EXISTS current_step VARCHAR(100)",
        "ALTER TABLE studio_projects ADD COLUMN IF NOT EXISTS captions_generated INTEGER DEFAULT 0",
        "ALTER TABLE studio_projects ADD COLUMN IF NOT EXISTS images_generated INTEGER DEFAULT 0",
        "ALTER TABLE studio_projects ADD COLUMN IF NOT EXISTS videos_generated INTEGER DEFAULT 0",
        "ALTER TABLE studio_projects ADD COLUMN IF NOT EXISTS total_cost_usd FLOAT",
        "ALTER TABLE studio_projects ADD COLUMN IF NOT EXISTS error_message TEXT",
        "ALTER TABLE studio_projects ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP",
        "ALTER TABLE studio_projects ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP",

        # scheduled_social_posts table
        "ALTER TABLE scheduled_social_posts ADD COLUMN IF NOT EXISTS scheduled_for TIMESTAMP",
        "ALTER TABLE scheduled_social_posts ADD COLUMN IF NOT EXISTS timezone VARCHAR(50)",
        "ALTER TABLE scheduled_social_posts ADD COLUMN IF NOT EXISTS platform_specific JSON",
        "ALTER TABLE scheduled_social_posts ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'scheduled'",
        "ALTER TABLE scheduled_social_posts ADD COLUMN IF NOT EXISTS published_at TIMESTAMP",
        "ALTER TABLE scheduled_social_posts ADD COLUMN IF NOT EXISTS platform_post_id VARCHAR(255)",
        "ALTER TABLE scheduled_social_posts ADD COLUMN IF NOT EXISTS platform_post_url TEXT",
        "ALTER TABLE scheduled_social_posts ADD COLUMN IF NOT EXISTS error_message TEXT",
        "ALTER TABLE scheduled_social_posts ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0",
        "ALTER TABLE scheduled_social_posts ADD COLUMN IF NOT EXISTS engagement_data JSON",
        "ALTER TABLE scheduled_social_posts ADD COLUMN IF NOT EXISTS last_engagement_sync TIMESTAMP",
        "ALTER TABLE scheduled_social_posts ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP",

        # social_accounts table
        "ALTER TABLE social_accounts ADD COLUMN IF NOT EXISTS platform VARCHAR(50)",
        "ALTER TABLE social_accounts ADD COLUMN IF NOT EXISTS platform_user_id VARCHAR(255)",
        "ALTER TABLE social_accounts ADD COLUMN IF NOT EXISTS platform_username VARCHAR(255)",
        "ALTER TABLE social_accounts ADD COLUMN IF NOT EXISTS platform_display_name VARCHAR(255)",
        "ALTER TABLE social_accounts ADD COLUMN IF NOT EXISTS profile_image_url TEXT",
        "ALTER TABLE social_accounts ADD COLUMN IF NOT EXISTS access_token TEXT",
        "ALTER TABLE social_accounts ADD COLUMN IF NOT EXISTS refresh_token TEXT",
        "ALTER TABLE social_accounts ADD COLUMN IF NOT EXISTS token_expires_at TIMESTAMP",
        "ALTER TABLE social_accounts ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE",
        "ALTER TABLE social_accounts ADD COLUMN IF NOT EXISTS last_synced_at TIMESTAMP",
        "ALTER TABLE social_accounts ADD COLUMN IF NOT EXISTS last_error TEXT",
        "ALTER TABLE social_accounts ADD COLUMN IF NOT EXISTS platform_data JSON",
        "ALTER TABLE social_accounts ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP",

        # generated_videos table
        "ALTER TABLE generated_videos ADD COLUMN IF NOT EXISTS audio_duration_seconds FLOAT",
        "ALTER TABLE generated_videos ADD COLUMN IF NOT EXISTS resolution VARCHAR(20)",
        "ALTER TABLE generated_videos ADD COLUMN IF NOT EXISTS fps INTEGER DEFAULT 30",
        "ALTER TABLE generated_videos ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'pending'",
        "ALTER TABLE generated_videos ADD COLUMN IF NOT EXISTS progress_percent INTEGER DEFAULT 0",
        "ALTER TABLE generated_videos ADD COLUMN IF NOT EXISTS video_url TEXT",
        "ALTER TABLE generated_videos ADD COLUMN IF NOT EXISTS thumbnail_url TEXT",
        "ALTER TABLE generated_videos ADD COLUMN IF NOT EXISTS error_message TEXT",
        "ALTER TABLE generated_videos ADD COLUMN IF NOT EXISTS processing_started_at TIMESTAMP",
        "ALTER TABLE generated_videos ADD COLUMN IF NOT EXISTS processing_completed_at TIMESTAMP",
        "ALTER TABLE generated_videos ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP",

        # ab_tests table
        "ALTER TABLE ab_tests ADD COLUMN IF NOT EXISTS name VARCHAR(255)",
        "ALTER TABLE ab_tests ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'draft'",
        "ALTER TABLE ab_tests ADD COLUMN IF NOT EXISTS start_date TIMESTAMP",
        "ALTER TABLE ab_tests ADD COLUMN IF NOT EXISTS end_date TIMESTAMP",
        "ALTER TABLE ab_tests ADD COLUMN IF NOT EXISTS winner_variant_id INTEGER",

        # billing/admin support tables
        "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS stripe_price_id VARCHAR(255)",
        "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS generations_reset_at TIMESTAMP",
        "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP",
        "ALTER TABLE payments ADD COLUMN IF NOT EXISTS stripe_invoice_id VARCHAR(255)",
        "ALTER TABLE payments ADD COLUMN IF NOT EXISTS stripe_charge_id VARCHAR(255)",
        "ALTER TABLE usage_records ADD COLUMN IF NOT EXISTS usage_metadata JSON",
        "ALTER TABLE coupons ADD COLUMN IF NOT EXISTS applicable_tiers JSON",
        "ALTER TABLE coupons ADD COLUMN IF NOT EXISTS stripe_coupon_id VARCHAR(255)",
        "ALTER TABLE admin_users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP",
        "ALTER TABLE admin_users ADD COLUMN IF NOT EXISTS last_login TIMESTAMP",
        "ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS user_agent TEXT",
        "ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS updated_by INTEGER",

        # Seed categories (idempotent)
        "INSERT INTO categories (name, description) SELECT 'Fashion', 'Fashion content' WHERE NOT EXISTS (SELECT 1 FROM categories WHERE name='Fashion')",
        "INSERT INTO categories (name, description) SELECT 'Technology', 'Tech content' WHERE NOT EXISTS (SELECT 1 FROM categories WHERE name='Technology')",
        "INSERT INTO categories (name, description) SELECT 'Food', 'Food content' WHERE NOT EXISTS (SELECT 1 FROM categories WHERE name='Food')",
        "INSERT INTO categories (name, description) SELECT 'Travel', 'Travel content' WHERE NOT EXISTS (SELECT 1 FROM categories WHERE name='Travel')",
        "INSERT INTO categories (name, description) SELECT 'Fitness', 'Fitness content' WHERE NOT EXISTS (SELECT 1 FROM categories WHERE name='Fitness')",
        "INSERT INTO categories (name, description) SELECT 'Lifestyle', 'Lifestyle content' WHERE NOT EXISTS (SELECT 1 FROM categories WHERE name='Lifestyle')",
    ]

    results = []
    try:
        with engine.connect() as conn:
            for sql in statements:
                try:
                    conn.execute(text(sql))
                    results.append({"sql": sql[:80], "status": "OK"})
                except Exception as exc:
                    results.append({"sql": sql[:80], "status": f"Error: {str(exc)[:120]}"})
            conn.commit()
        return {"message": "Database fix attempted", "results": results}
    except Exception as exc:
        return {"error": str(exc)}

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
    performance_router,
    setup_router
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
    - Brand voice analysis
    - AI avatar/influencer creation via LoRA training
    - Caption and hashtag generation
    - Image generation with custom avatars
    - Video content creation
    - Trend monitoring and content suggestions
    - Social media scheduling
    """,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Setup Sentry middleware
if settings.sentry_dsn:
    setup_sentry_middleware(app)

# Setup rate limiting
if settings.enable_rate_limiting:
    setup_rate_limiting(app)
    logger.info("Rate limiting enabled")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:3000",
        "http://localhost:5173",
        "https://ai-content-platform-1-iogw.onrender.com",
        "*",  # Allow all origins for now
    ],
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
app.include_router(setup_router, prefix="/api/v1")
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
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version
    }


# Utility endpoints for debugging/maintenance
@app.get("/delete-all-projects")
async def delete_all_studio_projects():
    """Delete all studio projects - for testing/development"""
    from app.studio.models import StudioProject, StudioAsset
    
    db = SessionLocal()
    try:
        # Delete all assets first (foreign key constraint)
        db.query(StudioAsset).delete()
        db.query(StudioProject).delete()
        db.commit()
        return {"message": "All studio projects deleted"}
    except Exception as e:
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()


@app.get("/fix-studio-assets")
async def fix_studio_assets_table():
    """Add missing columns to studio_assets table"""
    from sqlalchemy import text
    
    db = SessionLocal()
    try:
        # Add missing columns if they don't exist
        db.execute(text("""
            ALTER TABLE studio_assets 
            ADD COLUMN IF NOT EXISTS platform_optimized TEXT;
        """))
        db.execute(text("""
            ALTER TABLE studio_assets 
            ADD COLUMN IF NOT EXISTS generation_params TEXT;
        """))
        db.commit()
        return {"message": "studio_assets table fixed"}
    except Exception as e:
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()

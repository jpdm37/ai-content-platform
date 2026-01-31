"""
AI Content Platform - Main Application
FastAPI application for AI-powered social media content generation
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import get_settings
from app.core.database import engine, Base
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
    assistant_router
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup: Create database tables
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown: Cleanup if needed
    pass


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
    
    Built for testing and prototyping AI influencer content.
    """,
    version=settings.api_version,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI Content Platform API",
        "version": settings.api_version,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for Render"""
    from app.core.database import SessionLocal
    
    try:
        # Test database connection
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "version": settings.api_version,
        "database": db_status
    }


@app.get("/api/v1/status")
async def api_status():
    """API status and configuration check"""
    return {
        "api_version": settings.api_version,
        "openai_configured": bool(settings.openai_api_key),
        "replicate_configured": bool(settings.replicate_api_token),
        "news_api_configured": bool(settings.news_api_key),
        "endpoints": {
            "brands": "/api/v1/brands",
            "categories": "/api/v1/categories",
            "trends": "/api/v1/trends",
            "generate": "/api/v1/generate"
        }
    }

"""
Trend API Routes

Handles trending topics scraped from various sources.
Trends are linked to categories and used for content inspiration.
"""
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime, timedelta
from pydantic import BaseModel, field_validator
import logging
import json

from app.core.database import get_db
from app.auth.dependencies import get_current_user, get_current_verified_user
from app.models.user import User
from app.models import Trend, Category

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/trends", tags=["trends"])


# ============ Pydantic Schemas ============
class TrendCreate(BaseModel):
    """Schema for creating a trend"""
    category_id: int
    title: str
    description: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    popularity_score: Optional[int] = 50
    related_keywords: Optional[List[str]] = None


class TrendResponse(BaseModel):
    """Schema for trend response"""
    id: int
    category_id: int
    title: str
    description: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    popularity_score: int = 0
    related_keywords: Optional[List[str]] = None
    scraped_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    @field_validator('related_keywords', mode='before')
    @classmethod
    def parse_related_keywords(cls, v: Any) -> Optional[List[str]]:
        """Handle related_keywords stored as JSON string or list"""
        if v is None:
            return None
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
                return [str(parsed)]
            except (json.JSONDecodeError, TypeError):
                # If it's not valid JSON, treat as single keyword
                return [v] if v else None
        return None
    
    class Config:
        from_attributes = True


class ScrapeRequest(BaseModel):
    """Schema for scrape request"""
    category_id: Optional[int] = None


class ScrapeResponse(BaseModel):
    """Schema for scrape response"""
    message: str
    trends_found: int
    category_id: Optional[int] = None


# Sample trending topics for demo/testing
SAMPLE_TRENDS = [
    {
        "title": "AI-Generated Content Revolution",
        "description": "How AI is transforming content creation for brands and influencers",
        "source": "demo",
        "popularity_score": 95,
        "related_keywords": ["ai", "content creation", "automation"],
        "category_name": "Technology"
    },
    {
        "title": "Sustainable Fashion Movement",
        "description": "The rise of eco-conscious fashion choices among Gen Z",
        "source": "demo",
        "popularity_score": 88,
        "related_keywords": ["sustainable", "eco-friendly", "fashion"],
        "category_name": "Fashion"
    },
    {
        "title": "Home Workout Trends 2026",
        "description": "The best home fitness routines trending this year",
        "source": "demo",
        "popularity_score": 82,
        "related_keywords": ["fitness", "home workout", "health"],
        "category_name": "Fitness"
    },
    {
        "title": "Plant-Based Food Innovations",
        "description": "New plant-based products taking the food industry by storm",
        "source": "demo",
        "popularity_score": 79,
        "related_keywords": ["plant-based", "vegan", "food innovation"],
        "category_name": "Food & Drink"
    },
    {
        "title": "Digital Nomad Destinations",
        "description": "Top destinations for remote workers in 2026",
        "source": "demo",
        "popularity_score": 85,
        "related_keywords": ["digital nomad", "remote work", "travel"],
        "category_name": "Travel"
    },
    {
        "title": "Mindfulness and Self-Care",
        "description": "The growing importance of mental wellness in daily routines",
        "source": "demo",
        "popularity_score": 90,
        "related_keywords": ["mindfulness", "self-care", "wellness"],
        "category_name": "Lifestyle"
    },
    {
        "title": "Clean Beauty Revolution",
        "description": "The shift towards natural and clean beauty products",
        "source": "demo",
        "popularity_score": 86,
        "related_keywords": ["clean beauty", "natural", "skincare"],
        "category_name": "Beauty"
    },
    {
        "title": "Creator Economy Growth",
        "description": "How content creators are building sustainable businesses",
        "source": "demo",
        "popularity_score": 92,
        "related_keywords": ["creator economy", "influencer", "business"],
        "category_name": "Business"
    }
]


@router.get("/", response_model=List[TrendResponse])
async def list_trends(
    category_id: Optional[int] = None,
    source: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List trends, optionally filtered by category or source"""
    query = db.query(Trend)
    
    if category_id:
        query = query.filter(Trend.category_id == category_id)
    if source:
        query = query.filter(Trend.source == source)
    
    # Order by popularity and recency
    query = query.order_by(
        Trend.popularity_score.desc(),
        Trend.scraped_at.desc()
    )
    
    trends = query.offset(skip).limit(limit).all()
    return trends


@router.get("/recent", response_model=List[TrendResponse])
async def get_recent_trends(
    hours: int = 24,
    category_id: Optional[int] = None,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get trends from the last N hours"""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    
    query = db.query(Trend).filter(Trend.scraped_at >= cutoff)
    
    if category_id:
        query = query.filter(Trend.category_id == category_id)
    
    trends = query.order_by(
        Trend.popularity_score.desc()
    ).limit(limit).all()
    
    return trends


@router.get("/top", response_model=List[TrendResponse])
async def get_top_trends(
    category_id: Optional[int] = None,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get top trending topics by popularity score"""
    query = db.query(Trend)
    
    if category_id:
        query = query.filter(Trend.category_id == category_id)
    
    # Only get non-expired trends
    query = query.filter(
        or_(
            Trend.expires_at == None,
            Trend.expires_at > datetime.utcnow()
        )
    )
    
    trends = query.order_by(
        Trend.popularity_score.desc()
    ).limit(limit).all()
    
    return trends


@router.get("/{trend_id}", response_model=TrendResponse)
async def get_trend(
    trend_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific trend by ID"""
    trend = db.query(Trend).filter(Trend.id == trend_id).first()
    if not trend:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trend not found"
        )
    return trend


@router.post("/scrape")
async def scrape_trends(
    category_id: Optional[int] = None,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user)
):
    """
    Trigger trend scraping.
    In production, this would scrape from Google Trends, RSS feeds, etc.
    For demo purposes, we'll add sample trends.
    """
    try:
        # Try to import and use the real scraper
        from app.services.scraper import get_trend_scraper
        scraper = await get_trend_scraper(db)
        trends = await scraper.scrape_all(category_id=category_id)
        return {
            "message": "Scraping completed",
            "trends_found": len(trends),
            "category_id": category_id
        }
    except ImportError:
        logger.warning("Trend scraper not available, using demo data")
    except Exception as e:
        logger.warning(f"Trend scraping failed: {e}, falling back to demo data")
    
    # Fallback: seed with sample trends
    created_count = 0
    
    for trend_data in SAMPLE_TRENDS:
        # Find the category
        category_name = trend_data.get("category_name")
        category = None
        
        if category_name:
            category = db.query(Category).filter(
                Category.name == category_name
            ).first()
        
        if not category and category_id:
            category = db.query(Category).filter(
                Category.id == category_id
            ).first()
        
        if not category:
            continue
        
        # Check if trend already exists
        existing = db.query(Trend).filter(
            Trend.title == trend_data["title"],
            Trend.category_id == category.id
        ).first()
        
        if existing:
            continue
        
        # Create trend
        trend = Trend(
            category_id=category.id,
            title=trend_data["title"],
            description=trend_data.get("description"),
            source=trend_data.get("source", "demo"),
            popularity_score=trend_data.get("popularity_score", 50),
            related_keywords=trend_data.get("related_keywords", []),
            scraped_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        
        db.add(trend)
        created_count += 1
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save trends: {str(e)}"
        )
    
    return {
        "message": "Demo trends seeded",
        "trends_found": created_count,
        "category_id": category_id
    }


@router.post("/seed")
async def seed_demo_trends(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Seed demo trends for all categories.
    Requires categories to be seeded first.
    """
    # First check if categories exist
    categories = db.query(Category).all()
    if not categories:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please seed categories first using POST /categories/seed"
        )
    
    created = []
    category_map = {c.name: c.id for c in categories}
    
    for trend_data in SAMPLE_TRENDS:
        category_name = trend_data.get("category_name")
        cat_id = category_map.get(category_name)
        
        if not cat_id:
            continue
        
        # Check if trend already exists
        existing = db.query(Trend).filter(
            Trend.title == trend_data["title"],
            Trend.category_id == cat_id
        ).first()
        
        if existing:
            created.append(existing)
            continue
        
        trend = Trend(
            category_id=cat_id,
            title=trend_data["title"],
            description=trend_data.get("description"),
            source=trend_data.get("source", "demo"),
            popularity_score=trend_data.get("popularity_score", 50),
            related_keywords=trend_data.get("related_keywords", []),
            scraped_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        
        db.add(trend)
        created.append(trend)
    
    try:
        db.commit()
        for t in created:
            db.refresh(t)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to seed trends: {str(e)}"
        )
    
    return {
        "message": f"Seeded {len(created)} trends",
        "trends": [{"id": t.id, "title": t.title} for t in created if hasattr(t, 'id')]
    }


@router.delete("/expired", status_code=status.HTTP_200_OK)
async def cleanup_expired_trends(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user)
):
    """Remove expired trends from the database"""
    deleted = db.query(Trend).filter(
        Trend.expires_at < datetime.utcnow()
    ).delete()
    
    db.commit()
    
    return {"message": f"Deleted {deleted} expired trends"}


@router.get("/category/{category_id}", response_model=List[TrendResponse])
async def get_trends_by_category(
    category_id: int,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all trends for a specific category"""
    # Verify category exists
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    trends = db.query(Trend).filter(
        Trend.category_id == category_id
    ).order_by(
        Trend.popularity_score.desc(),
        Trend.scraped_at.desc()
    ).limit(limit).all()
    
    return trends


@router.post("/", response_model=TrendResponse, status_code=status.HTTP_201_CREATED)
async def create_trend(
    trend_data: TrendCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user)
):
    """Manually create a trend (for custom/branded trends)"""
    # Verify category exists
    category = db.query(Category).filter(Category.id == trend_data.category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    trend = Trend(
        category_id=trend_data.category_id,
        title=trend_data.title,
        description=trend_data.description,
        source=trend_data.source or "manual",
        source_url=trend_data.source_url,
        popularity_score=trend_data.popularity_score or 50,
        related_keywords=trend_data.related_keywords or [],
        scraped_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    
    db.add(trend)
    db.commit()
    db.refresh(trend)
    
    return trend

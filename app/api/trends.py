"""
Trend API Routes
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.models import Trend, Category, TrendResponse, ScrapeRequest, ScrapeResponse, Brand
from app.services.scraper import get_trend_scraper
from app.auth.dependencies import get_current_user, get_current_active_user
from app.models.user import User

router = APIRouter(prefix="/trends", tags=["trends"])


@router.get("/", response_model=List[TrendResponse])
async def list_trends(
    category_id: Optional[int] = None,
    source: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List trends, optionally filtered by category or source - requires authentication"""
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
    current_user: User = Depends(get_current_active_user)
):
    """Get trends from the last N hours - requires authentication"""
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
    current_user: User = Depends(get_current_active_user)
):
    """Get top trending topics by popularity score - requires authentication"""
    query = db.query(Trend)
    
    if category_id:
        query = query.filter(Trend.category_id == category_id)
    
    # Only get non-expired trends
    query = query.filter(
        (Trend.expires_at == None) | (Trend.expires_at > datetime.utcnow())
    )
    
    trends = query.order_by(
        Trend.popularity_score.desc()
    ).limit(limit).all()
    
    return trends


@router.get("/{trend_id}", response_model=TrendResponse)
async def get_trend(
    trend_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific trend by ID - requires authentication"""
    trend = db.query(Trend).filter(Trend.id == trend_id).first()
    if not trend:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trend not found"
        )
    return trend


@router.post("/scrape", response_model=ScrapeResponse)
@limiter.limit("5/minute")  # Rate limit scraping - expensive operation
async def scrape_trends(
    request: Request,
    scrape_request: ScrapeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Trigger trend scraping - requires authentication.
    Can optionally specify category_id to scrape only one category.
    Rate limited to prevent abuse.
    """
    scraper = await get_trend_scraper(db)
    
    # Run scraping
    trends = await scraper.scrape_all(category_id=scrape_request.category_id)
    
    return ScrapeResponse(
        message="Scraping completed",
        trends_found=len(trends),
        category_id=scrape_request.category_id
    )


@router.delete("/expired", status_code=status.HTTP_200_OK)
async def cleanup_expired_trends(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Remove expired trends from the database - requires admin"""
    # Check if user is admin
    if not current_user.is_admin and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can cleanup trends"
        )
    
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
    current_user: User = Depends(get_current_active_user)
):
    """Get all trends for a specific category - requires authentication"""
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


@router.get("/suggestions/{brand_id}")
async def get_content_suggestions(
    brand_id: int,
    limit: int = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get AI-powered content suggestions based on trending topics relevant to a brand.
    
    This helps brands stay timely without constant manual monitoring by:
    - Analyzing trends in the brand's niche categories
    - Suggesting content ideas based on what's gaining traction
    - Providing recommended hashtags and posting times
    """
    from app.models import Brand
    
    # Verify brand belongs to user
    brand = db.query(Brand).filter(
        Brand.id == brand_id,
        Brand.user_id == current_user.id
    ).first()
    
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )
    
    scraper = await get_trend_scraper(db)
    suggestions = await scraper.get_content_suggestions(brand_id, limit)
    
    return {
        "brand_id": brand_id,
        "brand_name": brand.name,
        "suggestions": suggestions,
        "generated_at": datetime.utcnow().isoformat()
    }

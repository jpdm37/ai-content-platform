"""
Analytics Dashboard API Routes

Comprehensive performance tracking and insights.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.auth.dependencies import get_current_user
from app.analytics.service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview")
async def get_overview(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get high-level overview stats."""
    service = AnalyticsService(db)
    return service.get_overview(current_user.id, days)


@router.get("/content")
async def get_content_analytics(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get content generation analytics."""
    service = AnalyticsService(db)
    return service.get_content_analytics(current_user.id, days)


@router.get("/social")
async def get_social_analytics(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get social media posting analytics."""
    service = AnalyticsService(db)
    return service.get_social_analytics(current_user.id, days)


@router.get("/videos")
async def get_video_analytics(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get video generation analytics."""
    service = AnalyticsService(db)
    return service.get_video_analytics(current_user.id, days)


@router.get("/studio")
async def get_studio_analytics(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get Content Studio analytics."""
    service = AnalyticsService(db)
    return service.get_studio_analytics(current_user.id, days)


@router.get("/costs")
async def get_cost_analytics(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get cost breakdown analytics."""
    service = AnalyticsService(db)
    return service.get_cost_analytics(current_user.id, days)


@router.get("/best-times")
async def get_best_posting_times(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get best posting times based on engagement analysis."""
    service = AnalyticsService(db)
    return service.get_best_posting_times(current_user.id)


@router.get("/dashboard")
async def get_full_dashboard(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get complete dashboard data in one call."""
    service = AnalyticsService(db)
    
    return {
        "overview": service.get_overview(current_user.id, days),
        "content": service.get_content_analytics(current_user.id, days),
        "social": service.get_social_analytics(current_user.id, days),
        "videos": service.get_video_analytics(current_user.id, days),
        "costs": service.get_cost_analytics(current_user.id, days),
        "best_times": service.get_best_posting_times(current_user.id)
    }

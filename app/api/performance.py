"""
Performance Tracking API Routes
===============================

Endpoints for tracking and analyzing content performance.
"""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.models.user import User
from app.auth.dependencies import get_current_user
from app.performance.service import PerformanceTrackingService, get_performance_service

router = APIRouter(prefix="/performance", tags=["performance"])


# ==================== Schemas ====================

class SyncResult(BaseModel):
    synced: int
    failed: int
    accounts_processed: int


class MetricsSummary(BaseModel):
    likes: int
    comments: int
    shares: int
    total_engagements: int
    reach: int
    impressions: int


class OverviewResponse(BaseModel):
    period_days: int
    total_posts: int
    metrics: MetricsSummary
    averages: dict
    trends: dict


# ==================== Endpoints ====================

@router.post("/sync")
@limiter.limit("5/minute")
async def sync_metrics(
    request: Request,
    background_tasks: BackgroundTasks,
    platform: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Sync engagement metrics from connected social accounts.
    Fetches latest data from platform APIs.
    """
    
    service = get_performance_service(db)
    
    # Run sync in background for better UX
    async def do_sync():
        return await service.sync_post_metrics(current_user.id, platform)
    
    result = await service.sync_post_metrics(current_user.id, platform)
    
    return {
        "message": "Metrics sync completed",
        "result": result
    }


@router.get("/overview")
async def get_performance_overview(
    days: int = Query(default=30, ge=1, le=365),
    brand_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get overall performance metrics summary."""
    
    service = get_performance_service(db)
    return service.get_performance_overview(current_user.id, days, brand_id)


@router.get("/platforms")
async def get_platform_breakdown(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get performance breakdown by social platform."""
    
    service = get_performance_service(db)
    return service.get_platform_breakdown(current_user.id, days)


@router.get("/top-posts")
async def get_top_posts(
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=10, ge=1, le=50),
    metric: str = Query(default="engagements", pattern="^(engagements|likes|comments|reach|engagement_rate)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get top performing posts ranked by a specific metric."""
    
    service = get_performance_service(db)
    posts = service.get_top_performing_posts(current_user.id, days, limit, metric)
    
    return {
        "period_days": days,
        "metric": metric,
        "posts": posts
    }


@router.get("/trends")
async def get_engagement_trends(
    days: int = Query(default=30, ge=1, le=365),
    granularity: str = Query(default="day", pattern="^(day|week|month)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get engagement trends over time."""
    
    service = get_performance_service(db)
    return service.get_engagement_trends(current_user.id, days, granularity)


@router.get("/best-times")
async def get_best_posting_times(
    days: int = Query(default=90, ge=30, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Analyze best posting times based on historical engagement data."""
    
    service = get_performance_service(db)
    return service.get_best_posting_times(current_user.id, days)


@router.get("/content-analysis")
async def analyze_content(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Analyze what types of content perform best."""
    
    service = get_performance_service(db)
    return service.analyze_content_performance(current_user.id, days)


@router.get("/report")
async def generate_report(
    days: int = Query(default=30, ge=7, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a comprehensive performance report."""
    
    service = get_performance_service(db)
    return service.generate_performance_report(current_user.id, days)


@router.get("/post/{post_id}/metrics")
async def get_post_metrics(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed metrics for a specific post."""
    
    from app.social.models import PublishingLog
    
    post = db.query(PublishingLog).filter(
        PublishingLog.id == post_id,
        PublishingLog.user_id == current_user.id
    ).first()
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    return {
        "post_id": post.id,
        "platform": post.platform.value if post.platform else None,
        "published_at": post.published_at.isoformat() if post.published_at else None,
        "post_url": post.post_url,
        "metrics": post.engagement_data or {},
        "metrics_updated_at": post.metrics_updated_at.isoformat() if hasattr(post, 'metrics_updated_at') and post.metrics_updated_at else None
    }


@router.get("/comparison")
async def compare_periods(
    current_days: int = Query(default=30, ge=7, le=180),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Compare current period performance with previous period."""
    
    service = get_performance_service(db)
    
    current = service.get_performance_overview(current_user.id, current_days)
    
    # The overview already includes comparison with previous period
    return {
        "current_period": {
            "days": current_days,
            "metrics": current["metrics"],
            "averages": current["averages"]
        },
        "change": current["trends"],
        "summary": _generate_comparison_summary(current)
    }


def _generate_comparison_summary(data: dict) -> str:
    """Generate a human-readable comparison summary."""
    
    change = data["trends"]["engagement_change_percent"]
    
    if change > 20:
        return f"🚀 Great job! Your engagement is up {change}% compared to the previous period."
    elif change > 5:
        return f"📈 Nice progress! Engagement increased by {change}%."
    elif change > -5:
        return "📊 Your engagement is holding steady."
    elif change > -20:
        return f"📉 Engagement is down {abs(change)}%. Try experimenting with different content types."
    else:
        return f"⚠️ Engagement dropped {abs(change)}%. Consider reviewing your content strategy."


@router.get("/insights")
async def get_performance_insights(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get AI-generated insights about performance."""
    
    service = get_performance_service(db)
    
    # Gather data
    overview = service.get_performance_overview(current_user.id, 30)
    content_analysis = service.analyze_content_performance(current_user.id, 30)
    best_times = service.get_best_posting_times(current_user.id, 90)
    
    insights = []
    
    # Engagement trend insight
    change = overview["trends"]["engagement_change_percent"]
    if change > 10:
        insights.append({
            "type": "positive",
            "title": "Engagement Growing",
            "message": f"Your engagement is up {change}% - keep up the great work!",
            "action": None
        })
    elif change < -10:
        insights.append({
            "type": "warning",
            "title": "Engagement Declining",
            "message": f"Engagement is down {abs(change)}%. Consider trying new content formats.",
            "action": "Browse Templates",
            "action_link": "/templates"
        })
    
    # Content insights
    for insight in content_analysis.get("insights", []):
        insights.append({
            "type": "info",
            "title": "Content Pattern",
            "message": insight,
            "action": None
        })
    
    # Timing insight
    if best_times.get("recommendation"):
        insights.append({
            "type": "tip",
            "title": "Best Posting Time",
            "message": best_times["recommendation"],
            "action": "View Calendar",
            "action_link": "/calendar"
        })
    
    # Posting frequency
    avg_posts_per_week = overview["total_posts"] / 4  # 30 days ≈ 4 weeks
    if avg_posts_per_week < 3:
        insights.append({
            "type": "suggestion",
            "title": "Post More Often",
            "message": f"You're posting {round(avg_posts_per_week, 1)} times per week. Try increasing to 5+ for better reach.",
            "action": "Create Content",
            "action_link": "/studio/create"
        })
    
    return {
        "insights": insights,
        "generated_at": datetime.utcnow().isoformat()
    }

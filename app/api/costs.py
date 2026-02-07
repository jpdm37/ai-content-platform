"""
Cost Dashboard API
==================

API endpoints for cost monitoring and usage analytics.
Available to admin users and individual users for their own data.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from datetime import datetime, timedelta, date
from pydantic import BaseModel

from app.core.database import get_db
from app.models.user import User
from app.models.models import GeneratedContent
from app.video.models import GeneratedVideo
from app.billing.models import Subscription, Payment
from app.auth.dependencies import get_current_user
from app.services.cost_optimizer import (
    UsageTracker, TIER_QUOTAS, MODEL_COSTS,
    get_usage_tracker
)

router = APIRouter(prefix="/costs", tags=["costs"])


# ==================== Response Models ====================

class UsageSummary(BaseModel):
    period: str
    generations: int
    images: int
    videos: int
    estimated_cost: float
    cost_limit: float
    usage_percent: float


class QuotaStatus(BaseModel):
    tier: str
    daily_generations_used: int
    daily_generations_limit: int
    daily_images_used: int
    daily_images_limit: int
    daily_videos_used: int
    daily_videos_limit: int
    daily_cost_used: float
    daily_cost_limit: float
    monthly_cost_used: float
    monthly_cost_limit: float
    can_generate: bool
    upgrade_benefits: Optional[dict] = None


class CostBreakdown(BaseModel):
    category: str
    count: int
    cost: float
    percent_of_total: float


class DailyUsage(BaseModel):
    date: str
    generations: int
    images: int
    videos: int
    cost: float


class ModelUsage(BaseModel):
    model: str
    count: int
    total_cost: float
    avg_cost_per_use: float


# ==================== User Endpoints ====================

@router.get("/my-usage", response_model=QuotaStatus)
async def get_my_usage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's usage and quota status."""
    tracker = get_usage_tracker(db)
    
    tier = tracker.get_user_tier(current_user.id)
    quotas = tracker.get_tier_quotas(tier)
    usage_today = tracker.get_usage_today(current_user.id)
    usage_month = tracker.get_usage_month(current_user.id)
    
    # Check if user can still generate
    can_generate = (
        usage_today["generations"] < quotas["daily_generations"] and
        usage_today["estimated_cost"] < quotas["daily_cost_limit"] and
        usage_month["estimated_cost"] < quotas["monthly_cost_limit"]
    )
    
    # Show upgrade benefits if on lower tier
    upgrade_benefits = None
    if tier == "free":
        upgrade_benefits = {
            "next_tier": "creator",
            "price": "$19/month",
            "benefits": [
                f"{TIER_QUOTAS['creator']['daily_generations']}x more daily generations",
                f"{TIER_QUOTAS['creator']['daily_images']} images per day",
                f"{TIER_QUOTAS['creator']['daily_videos']} videos per day",
                "Batch processing for 50% savings"
            ]
        }
    elif tier == "creator":
        upgrade_benefits = {
            "next_tier": "pro",
            "price": "$49/month",
            "benefits": [
                f"{TIER_QUOTAS['pro']['daily_generations']} daily generations",
                f"{TIER_QUOTAS['pro']['daily_images']} images per day",
                f"{TIER_QUOTAS['pro']['daily_videos']} videos per day"
            ]
        }
    
    return QuotaStatus(
        tier=tier,
        daily_generations_used=usage_today["generations"],
        daily_generations_limit=quotas["daily_generations"],
        daily_images_used=usage_today["images"],
        daily_images_limit=quotas["daily_images"],
        daily_videos_used=usage_today["videos"],
        daily_videos_limit=quotas["daily_videos"],
        daily_cost_used=usage_today["estimated_cost"],
        daily_cost_limit=quotas["daily_cost_limit"],
        monthly_cost_used=usage_month["estimated_cost"],
        monthly_cost_limit=quotas["monthly_cost_limit"],
        can_generate=can_generate,
        upgrade_benefits=upgrade_benefits
    )


@router.get("/my-history")
async def get_my_usage_history(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's usage history for the past N days."""
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get daily breakdown
    daily_usage = []
    
    for i in range(days):
        day = date.today() - timedelta(days=i)
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(day, datetime.max.time())
        
        generations = db.query(GeneratedContent).filter(
            GeneratedContent.user_id == current_user.id,
            GeneratedContent.created_at >= day_start,
            GeneratedContent.created_at <= day_end
        ).count()
        
        images = db.query(GeneratedContent).filter(
            GeneratedContent.user_id == current_user.id,
            GeneratedContent.created_at >= day_start,
            GeneratedContent.created_at <= day_end,
            GeneratedContent.content_type == "image"
        ).count()
        
        videos = db.query(GeneratedVideo).filter(
            GeneratedVideo.user_id == current_user.id,
            GeneratedVideo.created_at >= day_start,
            GeneratedVideo.created_at <= day_end
        ).count()
        
        estimated_cost = (generations * 0.001) + (images * 0.002) + (videos * 0.05)
        
        daily_usage.append({
            "date": day.isoformat(),
            "generations": generations,
            "images": images,
            "videos": videos,
            "cost": round(estimated_cost, 4)
        })
    
    return {
        "days": days,
        "daily_usage": daily_usage,
        "total_generations": sum(d["generations"] for d in daily_usage),
        "total_images": sum(d["images"] for d in daily_usage),
        "total_videos": sum(d["videos"] for d in daily_usage),
        "total_cost": round(sum(d["cost"] for d in daily_usage), 2)
    }


@router.get("/estimate")
async def estimate_cost(
    content_types: str,  # comma-separated: "caption,image,video"
    platforms: str = "instagram",  # comma-separated
    variations: int = 3,
    include_video: bool = False,
    video_duration: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Estimate cost for a content generation project."""
    
    from app.services.cost_optimizer import CostOptimizer
    
    optimizer = CostOptimizer(db)
    
    content_list = [c.strip() for c in content_types.split(",")]
    platform_list = [p.strip() for p in platforms.split(",")]
    
    estimate = optimizer.estimate_project_cost(
        platforms=platform_list,
        content_types=content_list,
        num_variations=variations,
        include_video=include_video,
        video_duration=video_duration
    )
    
    # Check quota
    tracker = get_usage_tracker(db)
    allowed, message, quota_info = tracker.check_quota(
        current_user.id,
        "text",
        count=len(platform_list) * variations
    )
    
    return {
        "estimate": estimate,
        "quota_check": {
            "allowed": allowed,
            "message": message,
            "tier": quota_info["tier"]
        }
    }


# ==================== Admin Endpoints ====================

@router.get("/admin/overview")
async def admin_cost_overview(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Admin: Get platform-wide cost overview."""
    
    # Simple admin check (in production, use proper admin auth)
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Total generations
    total_generations = db.query(GeneratedContent).filter(
        GeneratedContent.created_at >= start_date
    ).count()
    
    total_images = db.query(GeneratedContent).filter(
        GeneratedContent.created_at >= start_date,
        GeneratedContent.content_type == "image"
    ).count()
    
    total_videos = db.query(GeneratedVideo).filter(
        GeneratedVideo.created_at >= start_date
    ).count()
    
    # Estimated costs
    estimated_text_cost = (total_generations - total_images) * 0.0006  # gpt-4o-mini
    estimated_image_cost = total_images * 0.002  # SDXL-Lightning
    estimated_video_cost = total_videos * 0.05
    total_cost = estimated_text_cost + estimated_image_cost + estimated_video_cost
    
    # Revenue
    total_revenue = db.query(func.sum(Payment.amount)).filter(
        Payment.created_at >= start_date,
        Payment.status == "succeeded"
    ).scalar() or 0
    total_revenue = total_revenue / 100  # Convert cents to dollars
    
    # Users by tier
    tier_counts = db.query(
        Subscription.tier,
        func.count(Subscription.id)
    ).filter(
        Subscription.status == "active"
    ).group_by(Subscription.tier).all()
    
    users_by_tier = {tier: count for tier, count in tier_counts}
    
    # Daily breakdown
    daily_stats = []
    for i in range(min(days, 14)):  # Last 14 days detail
        day = date.today() - timedelta(days=i)
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(day, datetime.max.time())
        
        day_gens = db.query(GeneratedContent).filter(
            GeneratedContent.created_at >= day_start,
            GeneratedContent.created_at <= day_end
        ).count()
        
        daily_stats.append({
            "date": day.isoformat(),
            "generations": day_gens,
            "estimated_cost": round(day_gens * 0.001, 2)
        })
    
    return {
        "period_days": days,
        "totals": {
            "generations": total_generations,
            "images": total_images,
            "videos": total_videos
        },
        "costs": {
            "text_generation": round(estimated_text_cost, 2),
            "image_generation": round(estimated_image_cost, 2),
            "video_generation": round(estimated_video_cost, 2),
            "total": round(total_cost, 2)
        },
        "revenue": round(total_revenue, 2),
        "profit_margin": round((total_revenue - total_cost) / max(total_revenue, 1) * 100, 1),
        "users_by_tier": users_by_tier,
        "daily_stats": daily_stats
    }


@router.get("/admin/top-users")
async def admin_top_users(
    days: int = 30,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Admin: Get top users by usage."""
    
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get top users by generation count
    top_users = db.query(
        GeneratedContent.user_id,
        func.count(GeneratedContent.id).label("count")
    ).filter(
        GeneratedContent.created_at >= start_date
    ).group_by(
        GeneratedContent.user_id
    ).order_by(
        func.count(GeneratedContent.id).desc()
    ).limit(limit).all()
    
    # Enrich with user details
    result = []
    for user_id, count in top_users:
        user = db.query(User).filter(User.id == user_id).first()
        subscription = db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status == "active"
        ).first()
        
        result.append({
            "user_id": user_id,
            "email": user.email if user else "Unknown",
            "tier": subscription.tier if subscription else "free",
            "generations": count,
            "estimated_cost": round(count * 0.001, 2)
        })
    
    return {"top_users": result, "period_days": days}


@router.get("/admin/model-usage")
async def admin_model_usage(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Admin: Get usage breakdown by AI model."""
    
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # In a full implementation, this would query a usage_logs table
    # For now, return estimated data based on content types
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    text_count = db.query(GeneratedContent).filter(
        GeneratedContent.created_at >= start_date,
        GeneratedContent.content_type != "image"
    ).count()
    
    image_count = db.query(GeneratedContent).filter(
        GeneratedContent.created_at >= start_date,
        GeneratedContent.content_type == "image"
    ).count()
    
    video_count = db.query(GeneratedVideo).filter(
        GeneratedVideo.created_at >= start_date
    ).count()
    
    return {
        "period_days": days,
        "models": [
            {
                "model": "gpt-4o-mini",
                "type": "text",
                "count": text_count,
                "cost_per_use": 0.0006,
                "total_cost": round(text_count * 0.0006, 2)
            },
            {
                "model": "sdxl-lightning",
                "type": "image",
                "count": image_count,
                "cost_per_use": 0.002,
                "total_cost": round(image_count * 0.002, 2)
            },
            {
                "model": "sadtalker",
                "type": "video",
                "count": video_count,
                "cost_per_use": 0.05,
                "total_cost": round(video_count * 0.05, 2)
            }
        ],
        "total_cost": round(
            text_count * 0.0006 + image_count * 0.002 + video_count * 0.05, 2
        )
    }


@router.get("/pricing-info")
async def get_pricing_info():
    """Get current model pricing information."""
    return {
        "text_models": {
            "gpt-4o-mini": {
                "input_per_1m": MODEL_COSTS["gpt-4o-mini"]["input"],
                "output_per_1m": MODEL_COSTS["gpt-4o-mini"]["output"],
                "typical_cost_per_caption": 0.0006
            },
            "gpt-4o": {
                "input_per_1m": MODEL_COSTS["gpt-4o"]["input"],
                "output_per_1m": MODEL_COSTS["gpt-4o"]["output"],
                "typical_cost_per_caption": 0.01
            }
        },
        "image_models": {
            "sdxl-lightning": {
                "per_image": MODEL_COSTS["sdxl-lightning"]["per_image"],
                "speed": "fast (4 steps)"
            },
            "sdxl": {
                "per_image": MODEL_COSTS["sdxl"]["per_image"],
                "speed": "slow (30 steps)"
            },
            "flux-dev": {
                "per_image": MODEL_COSTS["flux-dev"]["per_image"],
                "speed": "slow (highest quality)"
            }
        },
        "tier_quotas": TIER_QUOTAS
    }

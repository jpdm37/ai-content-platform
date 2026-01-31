"""
Analytics Dashboard Models and Service

Comprehensive performance tracking for content, social media, and platform usage.
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import func, and_, or_, desc
from sqlalchemy.orm import Session

from app.models.models import Brand, GeneratedContent
from app.social.models import ScheduledSocialPost, SocialAccount, PostStatus
from app.video.models import GeneratedVideo, VideoStatus
from app.studio.models import StudioProject, StudioAsset
from app.billing.models import UsageRecord


class AnalyticsService:
    """
    Analytics service for tracking content performance and usage.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    # ==================== Overview Stats ====================
    
    def get_overview(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get high-level overview stats."""
        since = datetime.utcnow() - timedelta(days=days)
        
        # Content generated
        content_count = self.db.query(GeneratedContent).filter(
            GeneratedContent.user_id == user_id,
            GeneratedContent.created_at >= since
        ).count()
        
        # Videos generated
        video_count = self.db.query(GeneratedVideo).filter(
            GeneratedVideo.user_id == user_id,
            GeneratedVideo.created_at >= since,
            GeneratedVideo.status == VideoStatus.COMPLETED
        ).count()
        
        # Posts published
        posts_published = self.db.query(ScheduledSocialPost).join(SocialAccount).filter(
            SocialAccount.user_id == user_id,
            ScheduledSocialPost.status == PostStatus.PUBLISHED,
            ScheduledSocialPost.published_at >= since
        ).count()
        
        # Total engagement (if tracked)
        engagement = self._get_total_engagement(user_id, since)
        
        # Cost
        total_cost = self.db.query(func.sum(UsageRecord.cost_credits)).filter(
            UsageRecord.user_id == user_id,
            UsageRecord.created_at >= since
        ).scalar() or 0
        
        # Previous period for comparison
        prev_since = since - timedelta(days=days)
        prev_content = self.db.query(GeneratedContent).filter(
            GeneratedContent.user_id == user_id,
            GeneratedContent.created_at >= prev_since,
            GeneratedContent.created_at < since
        ).count()
        
        return {
            "period_days": days,
            "content_generated": content_count,
            "videos_generated": video_count,
            "posts_published": posts_published,
            "total_engagement": engagement,
            "total_cost_usd": round(total_cost, 2),
            "content_change_percent": self._calc_change(content_count, prev_content),
            "generated_at": datetime.utcnow().isoformat()
        }
    
    def _get_total_engagement(self, user_id: int, since: datetime) -> Dict[str, int]:
        """Sum up engagement metrics from published posts."""
        posts = self.db.query(ScheduledSocialPost).join(SocialAccount).filter(
            SocialAccount.user_id == user_id,
            ScheduledSocialPost.status == PostStatus.PUBLISHED,
            ScheduledSocialPost.published_at >= since
        ).all()
        
        totals = {"likes": 0, "comments": 0, "shares": 0, "views": 0}
        for post in posts:
            if post.engagement_data:
                totals["likes"] += post.engagement_data.get("likes", 0)
                totals["comments"] += post.engagement_data.get("comments", 0)
                totals["shares"] += post.engagement_data.get("shares", 0)
                totals["views"] += post.engagement_data.get("views", 0)
        
        return totals
    
    def _calc_change(self, current: int, previous: int) -> float:
        """Calculate percentage change."""
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return round(((current - previous) / previous) * 100, 1)
    
    # ==================== Content Analytics ====================
    
    def get_content_analytics(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get content generation analytics."""
        since = datetime.utcnow() - timedelta(days=days)
        
        # Daily content generation
        daily_content = self.db.query(
            func.date(GeneratedContent.created_at).label('date'),
            func.count(GeneratedContent.id).label('count')
        ).filter(
            GeneratedContent.user_id == user_id,
            GeneratedContent.created_at >= since
        ).group_by(func.date(GeneratedContent.created_at)).all()
        
        # Content by type
        by_type = self.db.query(
            GeneratedContent.content_type,
            func.count(GeneratedContent.id)
        ).filter(
            GeneratedContent.user_id == user_id,
            GeneratedContent.created_at >= since
        ).group_by(GeneratedContent.content_type).all()
        
        # Content by brand
        by_brand = self.db.query(
            Brand.name,
            func.count(GeneratedContent.id)
        ).join(Brand, GeneratedContent.brand_id == Brand.id).filter(
            GeneratedContent.user_id == user_id,
            GeneratedContent.created_at >= since
        ).group_by(Brand.name).all()
        
        return {
            "daily_generation": [{"date": str(d.date), "count": d.count} for d in daily_content],
            "by_type": {t: c for t, c in by_type},
            "by_brand": {n: c for n, c in by_brand},
            "total": sum(d.count for d in daily_content)
        }
    
    # ==================== Social Media Analytics ====================
    
    def get_social_analytics(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get social media posting analytics."""
        since = datetime.utcnow() - timedelta(days=days)
        
        # Posts by platform
        by_platform = self.db.query(
            SocialAccount.platform,
            func.count(ScheduledSocialPost.id)
        ).join(ScheduledSocialPost).filter(
            SocialAccount.user_id == user_id,
            ScheduledSocialPost.status == PostStatus.PUBLISHED,
            ScheduledSocialPost.published_at >= since
        ).group_by(SocialAccount.platform).all()
        
        # Posts by status
        by_status = self.db.query(
            ScheduledSocialPost.status,
            func.count(ScheduledSocialPost.id)
        ).join(SocialAccount).filter(
            SocialAccount.user_id == user_id,
            ScheduledSocialPost.created_at >= since
        ).group_by(ScheduledSocialPost.status).all()
        
        # Daily posting
        daily_posts = self.db.query(
            func.date(ScheduledSocialPost.published_at).label('date'),
            func.count(ScheduledSocialPost.id).label('count')
        ).join(SocialAccount).filter(
            SocialAccount.user_id == user_id,
            ScheduledSocialPost.status == PostStatus.PUBLISHED,
            ScheduledSocialPost.published_at >= since
        ).group_by(func.date(ScheduledSocialPost.published_at)).all()
        
        # Best performing posts
        top_posts = self._get_top_performing_posts(user_id, since, limit=5)
        
        # Engagement by platform
        engagement_by_platform = self._get_engagement_by_platform(user_id, since)
        
        return {
            "by_platform": {p.value: c for p, c in by_platform},
            "by_status": {s.value: c for s, c in by_status},
            "daily_posts": [{"date": str(d.date), "count": d.count} for d in daily_posts],
            "top_posts": top_posts,
            "engagement_by_platform": engagement_by_platform,
            "total_published": sum(c for _, c in by_platform)
        }
    
    def _get_top_performing_posts(self, user_id: int, since: datetime, limit: int = 5) -> List[Dict]:
        """Get top performing posts by engagement."""
        posts = self.db.query(ScheduledSocialPost).join(SocialAccount).filter(
            SocialAccount.user_id == user_id,
            ScheduledSocialPost.status == PostStatus.PUBLISHED,
            ScheduledSocialPost.published_at >= since,
            ScheduledSocialPost.engagement_data.isnot(None)
        ).all()
        
        # Sort by total engagement
        def engagement_score(post):
            if not post.engagement_data:
                return 0
            return (
                post.engagement_data.get("likes", 0) +
                post.engagement_data.get("comments", 0) * 2 +
                post.engagement_data.get("shares", 0) * 3
            )
        
        sorted_posts = sorted(posts, key=engagement_score, reverse=True)[:limit]
        
        return [{
            "id": p.id,
            "caption": p.caption[:100] + "..." if len(p.caption or "") > 100 else p.caption,
            "platform": p.social_account.platform.value,
            "published_at": p.published_at.isoformat() if p.published_at else None,
            "engagement": p.engagement_data,
            "score": engagement_score(p)
        } for p in sorted_posts]
    
    def _get_engagement_by_platform(self, user_id: int, since: datetime) -> Dict[str, Dict]:
        """Get engagement metrics grouped by platform."""
        posts = self.db.query(ScheduledSocialPost).join(SocialAccount).filter(
            SocialAccount.user_id == user_id,
            ScheduledSocialPost.status == PostStatus.PUBLISHED,
            ScheduledSocialPost.published_at >= since
        ).all()
        
        by_platform = {}
        for post in posts:
            platform = post.social_account.platform.value
            if platform not in by_platform:
                by_platform[platform] = {"likes": 0, "comments": 0, "shares": 0, "posts": 0}
            
            by_platform[platform]["posts"] += 1
            if post.engagement_data:
                by_platform[platform]["likes"] += post.engagement_data.get("likes", 0)
                by_platform[platform]["comments"] += post.engagement_data.get("comments", 0)
                by_platform[platform]["shares"] += post.engagement_data.get("shares", 0)
        
        return by_platform
    
    # ==================== Video Analytics ====================
    
    def get_video_analytics(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get video generation analytics."""
        since = datetime.utcnow() - timedelta(days=days)
        
        # Videos by status
        by_status = self.db.query(
            GeneratedVideo.status,
            func.count(GeneratedVideo.id)
        ).filter(
            GeneratedVideo.user_id == user_id,
            GeneratedVideo.created_at >= since
        ).group_by(GeneratedVideo.status).all()
        
        # Daily video generation
        daily_videos = self.db.query(
            func.date(GeneratedVideo.created_at).label('date'),
            func.count(GeneratedVideo.id).label('count')
        ).filter(
            GeneratedVideo.user_id == user_id,
            GeneratedVideo.created_at >= since
        ).group_by(func.date(GeneratedVideo.created_at)).all()
        
        # Total video cost
        total_cost = self.db.query(func.sum(GeneratedVideo.total_cost_usd)).filter(
            GeneratedVideo.user_id == user_id,
            GeneratedVideo.created_at >= since
        ).scalar() or 0
        
        # Average video duration
        avg_duration = self.db.query(func.avg(GeneratedVideo.audio_duration_seconds)).filter(
            GeneratedVideo.user_id == user_id,
            GeneratedVideo.status == VideoStatus.COMPLETED,
            GeneratedVideo.created_at >= since
        ).scalar() or 0
        
        return {
            "by_status": {s.value: c for s, c in by_status},
            "daily_generation": [{"date": str(d.date), "count": d.count} for d in daily_videos],
            "total_cost_usd": round(total_cost, 2),
            "avg_duration_seconds": round(avg_duration, 1),
            "total_videos": sum(c for _, c in by_status)
        }
    
    # ==================== Studio Analytics ====================
    
    def get_studio_analytics(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get Content Studio analytics."""
        since = datetime.utcnow() - timedelta(days=days)
        
        # Projects by status
        by_status = self.db.query(
            StudioProject.status,
            func.count(StudioProject.id)
        ).filter(
            StudioProject.user_id == user_id,
            StudioProject.created_at >= since
        ).group_by(StudioProject.status).all()
        
        # Assets generated
        assets = self.db.query(
            StudioAsset.content_type,
            func.count(StudioAsset.id)
        ).join(StudioProject).filter(
            StudioProject.user_id == user_id,
            StudioProject.created_at >= since
        ).group_by(StudioAsset.content_type).all()
        
        # Favorite rate
        total_assets = self.db.query(StudioAsset).join(StudioProject).filter(
            StudioProject.user_id == user_id,
            StudioProject.created_at >= since
        ).count()
        
        favorites = self.db.query(StudioAsset).join(StudioProject).filter(
            StudioProject.user_id == user_id,
            StudioProject.created_at >= since,
            StudioAsset.is_favorite == True
        ).count()
        
        return {
            "by_status": {s.value: c for s, c in by_status},
            "assets_by_type": {t.value: c for t, c in assets},
            "total_projects": sum(c for _, c in by_status),
            "total_assets": total_assets,
            "favorites": favorites,
            "favorite_rate": round(favorites / max(total_assets, 1) * 100, 1)
        }
    
    # ==================== Cost Analytics ====================
    
    def get_cost_analytics(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get cost breakdown analytics."""
        since = datetime.utcnow() - timedelta(days=days)
        
        # Cost by feature
        by_feature = self.db.query(
            UsageRecord.feature,
            func.sum(UsageRecord.cost_credits)
        ).filter(
            UsageRecord.user_id == user_id,
            UsageRecord.created_at >= since
        ).group_by(UsageRecord.feature).all()
        
        # Daily cost
        daily_cost = self.db.query(
            func.date(UsageRecord.created_at).label('date'),
            func.sum(UsageRecord.cost_credits).label('cost')
        ).filter(
            UsageRecord.user_id == user_id,
            UsageRecord.created_at >= since
        ).group_by(func.date(UsageRecord.created_at)).all()
        
        return {
            "by_feature": {f: round(c or 0, 2) for f, c in by_feature},
            "daily_cost": [{"date": str(d.date), "cost": round(d.cost or 0, 2)} for d in daily_cost],
            "total_cost_usd": round(sum(c or 0 for _, c in by_feature), 2)
        }
    
    # ==================== Best Times Analysis ====================
    
    def get_best_posting_times(self, user_id: int) -> Dict[str, Any]:
        """Analyze best posting times based on engagement."""
        # Get all published posts with engagement
        posts = self.db.query(ScheduledSocialPost).join(SocialAccount).filter(
            SocialAccount.user_id == user_id,
            ScheduledSocialPost.status == PostStatus.PUBLISHED,
            ScheduledSocialPost.engagement_data.isnot(None)
        ).all()
        
        if len(posts) < 10:
            return {"message": "Need more published posts for analysis", "data": None}
        
        # Analyze by day of week
        by_day = {i: {"posts": 0, "engagement": 0} for i in range(7)}
        # Analyze by hour
        by_hour = {i: {"posts": 0, "engagement": 0} for i in range(24)}
        
        for post in posts:
            if not post.published_at:
                continue
            
            day = post.published_at.weekday()
            hour = post.published_at.hour
            
            engagement = sum([
                post.engagement_data.get("likes", 0),
                post.engagement_data.get("comments", 0) * 2,
                post.engagement_data.get("shares", 0) * 3
            ])
            
            by_day[day]["posts"] += 1
            by_day[day]["engagement"] += engagement
            by_hour[hour]["posts"] += 1
            by_hour[hour]["engagement"] += engagement
        
        # Calculate averages
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        best_days = []
        for i, name in enumerate(day_names):
            if by_day[i]["posts"] > 0:
                avg = by_day[i]["engagement"] / by_day[i]["posts"]
                best_days.append({"day": name, "avg_engagement": round(avg, 1), "posts": by_day[i]["posts"]})
        
        best_hours = []
        for hour in range(24):
            if by_hour[hour]["posts"] > 0:
                avg = by_hour[hour]["engagement"] / by_hour[hour]["posts"]
                best_hours.append({"hour": hour, "avg_engagement": round(avg, 1), "posts": by_hour[hour]["posts"]})
        
        # Sort by engagement
        best_days.sort(key=lambda x: x["avg_engagement"], reverse=True)
        best_hours.sort(key=lambda x: x["avg_engagement"], reverse=True)
        
        return {
            "best_days": best_days[:3],
            "best_hours": best_hours[:5],
            "total_posts_analyzed": len(posts)
        }


def get_analytics_service(db: Session) -> AnalyticsService:
    return AnalyticsService(db)

"""
Performance Tracking Service
============================

Pulls engagement metrics from connected social media accounts
and provides analytics on content performance.

Features:
- Fetch engagement data from social platforms
- Track metrics per post (likes, comments, shares, reach)
- Calculate engagement rates and trends
- Identify top performing content
- Generate performance reports
- ROI tracking
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc

from app.core.config import get_settings
from app.models.user import User
from app.models.models import Brand, GeneratedContent
from app.social.models import (
    SocialAccount, ScheduledSocialPost, PublishingLog,
    SocialPlatform, PostStatus
)

logger = logging.getLogger(__name__)
settings = get_settings()


class PerformanceTrackingService:
    """Service for tracking and analyzing content performance."""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ==================== Fetch Engagement Data ====================
    
    async def sync_post_metrics(self, user_id: int, platform: str = None) -> Dict[str, Any]:
        """
        Sync engagement metrics for all published posts.
        Fetches latest data from social platform APIs.
        """
        
        # Get connected accounts
        query = self.db.query(SocialAccount).filter(
            SocialAccount.user_id == user_id,
            SocialAccount.is_active == True
        )
        
        if platform:
            query = query.filter(SocialAccount.platform == SocialPlatform(platform))
        
        accounts = query.all()
        
        synced = 0
        failed = 0
        
        for account in accounts:
            try:
                # Get published posts for this account
                posts = self.db.query(PublishingLog).filter(
                    PublishingLog.account_id == account.id,
                    PublishingLog.success == True,
                    PublishingLog.platform_post_id.isnot(None)
                ).all()
                
                for post in posts:
                    try:
                        metrics = await self._fetch_post_metrics(account, post.platform_post_id)
                        if metrics:
                            post.engagement_data = metrics
                            post.metrics_updated_at = datetime.utcnow()
                            synced += 1
                    except Exception as e:
                        logger.error(f"Failed to fetch metrics for post {post.id}: {e}")
                        failed += 1
                
                self.db.commit()
                
            except Exception as e:
                logger.error(f"Failed to sync account {account.id}: {e}")
                failed += 1
        
        return {
            "synced": synced,
            "failed": failed,
            "accounts_processed": len(accounts)
        }
    
    async def _fetch_post_metrics(
        self,
        account: SocialAccount,
        post_id: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch metrics for a specific post from the platform API."""
        
        # Platform-specific API calls
        # In production, these would make actual API calls
        
        if account.platform == SocialPlatform.INSTAGRAM:
            return await self._fetch_instagram_metrics(account, post_id)
        elif account.platform == SocialPlatform.TWITTER:
            return await self._fetch_twitter_metrics(account, post_id)
        elif account.platform == SocialPlatform.LINKEDIN:
            return await self._fetch_linkedin_metrics(account, post_id)
        elif account.platform == SocialPlatform.FACEBOOK:
            return await self._fetch_facebook_metrics(account, post_id)
        
        return None
    
    async def _fetch_instagram_metrics(
        self,
        account: SocialAccount,
        post_id: str
    ) -> Dict[str, Any]:
        """Fetch Instagram post metrics via Graph API."""
        
        import httpx
        
        try:
            async with httpx.AsyncClient() as client:
                # Instagram Graph API endpoint
                url = f"https://graph.instagram.com/{post_id}"
                params = {
                    "fields": "like_count,comments_count,reach,impressions,saved,shares",
                    "access_token": account.access_token
                }
                
                response = await client.get(url, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "likes": data.get("like_count", 0),
                        "comments": data.get("comments_count", 0),
                        "reach": data.get("reach", 0),
                        "impressions": data.get("impressions", 0),
                        "saves": data.get("saved", 0),
                        "shares": data.get("shares", 0),
                        "fetched_at": datetime.utcnow().isoformat()
                    }
        except Exception as e:
            logger.error(f"Instagram API error: {e}")
        
        return None
    
    async def _fetch_twitter_metrics(
        self,
        account: SocialAccount,
        post_id: str
    ) -> Dict[str, Any]:
        """Fetch Twitter/X post metrics."""
        
        import httpx
        
        try:
            async with httpx.AsyncClient() as client:
                url = f"https://api.twitter.com/2/tweets/{post_id}"
                params = {
                    "tweet.fields": "public_metrics,non_public_metrics"
                }
                headers = {
                    "Authorization": f"Bearer {account.access_token}"
                }
                
                response = await client.get(url, params=params, headers=headers)
                
                if response.status_code == 200:
                    data = response.json().get("data", {})
                    metrics = data.get("public_metrics", {})
                    return {
                        "likes": metrics.get("like_count", 0),
                        "comments": metrics.get("reply_count", 0),
                        "retweets": metrics.get("retweet_count", 0),
                        "quotes": metrics.get("quote_count", 0),
                        "impressions": metrics.get("impression_count", 0),
                        "fetched_at": datetime.utcnow().isoformat()
                    }
        except Exception as e:
            logger.error(f"Twitter API error: {e}")
        
        return None
    
    async def _fetch_linkedin_metrics(
        self,
        account: SocialAccount,
        post_id: str
    ) -> Dict[str, Any]:
        """Fetch LinkedIn post metrics."""
        
        import httpx
        
        try:
            async with httpx.AsyncClient() as client:
                url = f"https://api.linkedin.com/v2/socialActions/{post_id}"
                headers = {
                    "Authorization": f"Bearer {account.access_token}"
                }
                
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "likes": data.get("likesSummary", {}).get("totalLikes", 0),
                        "comments": data.get("commentsSummary", {}).get("totalFirstLevelComments", 0),
                        "shares": data.get("sharesSummary", {}).get("totalShares", 0),
                        "fetched_at": datetime.utcnow().isoformat()
                    }
        except Exception as e:
            logger.error(f"LinkedIn API error: {e}")
        
        return None
    
    async def _fetch_facebook_metrics(
        self,
        account: SocialAccount,
        post_id: str
    ) -> Dict[str, Any]:
        """Fetch Facebook post metrics."""
        
        import httpx
        
        try:
            async with httpx.AsyncClient() as client:
                url = f"https://graph.facebook.com/v18.0/{post_id}"
                params = {
                    "fields": "likes.summary(true),comments.summary(true),shares,reach",
                    "access_token": account.access_token
                }
                
                response = await client.get(url, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "likes": data.get("likes", {}).get("summary", {}).get("total_count", 0),
                        "comments": data.get("comments", {}).get("summary", {}).get("total_count", 0),
                        "shares": data.get("shares", {}).get("count", 0) if data.get("shares") else 0,
                        "reach": data.get("reach", 0),
                        "fetched_at": datetime.utcnow().isoformat()
                    }
        except Exception as e:
            logger.error(f"Facebook API error: {e}")
        
        return None
    
    # ==================== Performance Analytics ====================
    
    def get_performance_overview(
        self,
        user_id: int,
        days: int = 30,
        brand_id: int = None
    ) -> Dict[str, Any]:
        """Get overall performance metrics for a time period."""
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get published posts
        query = self.db.query(PublishingLog).filter(
            PublishingLog.user_id == user_id,
            PublishingLog.published_at >= start_date,
            PublishingLog.success == True
        )
        
        posts = query.all()
        
        # Aggregate metrics
        total_posts = len(posts)
        total_likes = 0
        total_comments = 0
        total_shares = 0
        total_reach = 0
        total_impressions = 0
        
        for post in posts:
            if post.engagement_data:
                total_likes += post.engagement_data.get("likes", 0)
                total_comments += post.engagement_data.get("comments", 0)
                total_shares += post.engagement_data.get("shares", 0) + post.engagement_data.get("retweets", 0)
                total_reach += post.engagement_data.get("reach", 0)
                total_impressions += post.engagement_data.get("impressions", 0)
        
        total_engagements = total_likes + total_comments + total_shares
        avg_engagement_rate = (total_engagements / total_impressions * 100) if total_impressions > 0 else 0
        
        # Get previous period for comparison
        prev_start = start_date - timedelta(days=days)
        prev_posts = self.db.query(PublishingLog).filter(
            PublishingLog.user_id == user_id,
            PublishingLog.published_at >= prev_start,
            PublishingLog.published_at < start_date,
            PublishingLog.success == True
        ).all()
        
        prev_engagements = sum(
            (p.engagement_data.get("likes", 0) + 
             p.engagement_data.get("comments", 0) + 
             p.engagement_data.get("shares", 0))
            for p in prev_posts if p.engagement_data
        )
        
        engagement_change = ((total_engagements - prev_engagements) / prev_engagements * 100) if prev_engagements > 0 else 0
        
        return {
            "period_days": days,
            "total_posts": total_posts,
            "metrics": {
                "likes": total_likes,
                "comments": total_comments,
                "shares": total_shares,
                "total_engagements": total_engagements,
                "reach": total_reach,
                "impressions": total_impressions
            },
            "averages": {
                "likes_per_post": round(total_likes / total_posts, 1) if total_posts > 0 else 0,
                "comments_per_post": round(total_comments / total_posts, 1) if total_posts > 0 else 0,
                "engagement_rate": round(avg_engagement_rate, 2)
            },
            "trends": {
                "engagement_change_percent": round(engagement_change, 1),
                "post_count_change": total_posts - len(prev_posts)
            }
        }
    
    def get_platform_breakdown(
        self,
        user_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get performance breakdown by platform."""
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        posts = self.db.query(PublishingLog).filter(
            PublishingLog.user_id == user_id,
            PublishingLog.published_at >= start_date,
            PublishingLog.success == True
        ).all()
        
        platforms = defaultdict(lambda: {
            "posts": 0,
            "likes": 0,
            "comments": 0,
            "shares": 0,
            "impressions": 0,
            "reach": 0
        })
        
        for post in posts:
            platform = post.platform.value if post.platform else "unknown"
            platforms[platform]["posts"] += 1
            
            if post.engagement_data:
                platforms[platform]["likes"] += post.engagement_data.get("likes", 0)
                platforms[platform]["comments"] += post.engagement_data.get("comments", 0)
                platforms[platform]["shares"] += post.engagement_data.get("shares", 0) + post.engagement_data.get("retweets", 0)
                platforms[platform]["impressions"] += post.engagement_data.get("impressions", 0)
                platforms[platform]["reach"] += post.engagement_data.get("reach", 0)
        
        # Calculate engagement rates
        result = {}
        for platform, data in platforms.items():
            total_engagements = data["likes"] + data["comments"] + data["shares"]
            engagement_rate = (total_engagements / data["impressions"] * 100) if data["impressions"] > 0 else 0
            
            result[platform] = {
                **data,
                "total_engagements": total_engagements,
                "engagement_rate": round(engagement_rate, 2)
            }
        
        return {
            "period_days": days,
            "platforms": result
        }
    
    def get_top_performing_posts(
        self,
        user_id: int,
        days: int = 30,
        limit: int = 10,
        metric: str = "engagements"
    ) -> List[Dict[str, Any]]:
        """Get top performing posts by a specific metric."""
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        posts = self.db.query(PublishingLog).filter(
            PublishingLog.user_id == user_id,
            PublishingLog.published_at >= start_date,
            PublishingLog.success == True,
            PublishingLog.engagement_data.isnot(None)
        ).all()
        
        # Score posts
        scored_posts = []
        for post in posts:
            if not post.engagement_data:
                continue
            
            engagement = post.engagement_data
            
            if metric == "engagements":
                score = (engagement.get("likes", 0) + 
                        engagement.get("comments", 0) + 
                        engagement.get("shares", 0))
            elif metric == "likes":
                score = engagement.get("likes", 0)
            elif metric == "comments":
                score = engagement.get("comments", 0)
            elif metric == "reach":
                score = engagement.get("reach", 0)
            elif metric == "engagement_rate":
                impressions = engagement.get("impressions", 0)
                total = engagement.get("likes", 0) + engagement.get("comments", 0) + engagement.get("shares", 0)
                score = (total / impressions * 100) if impressions > 0 else 0
            else:
                score = 0
            
            scored_posts.append({
                "id": post.id,
                "platform": post.platform.value if post.platform else None,
                "published_at": post.published_at.isoformat(),
                "post_url": post.post_url,
                "caption_preview": post.caption[:100] + "..." if post.caption and len(post.caption) > 100 else post.caption,
                "metrics": {
                    "likes": engagement.get("likes", 0),
                    "comments": engagement.get("comments", 0),
                    "shares": engagement.get("shares", 0) + engagement.get("retweets", 0),
                    "reach": engagement.get("reach", 0),
                    "impressions": engagement.get("impressions", 0)
                },
                "score": round(score, 2)
            })
        
        # Sort and limit
        scored_posts.sort(key=lambda x: x["score"], reverse=True)
        
        return scored_posts[:limit]
    
    def get_engagement_trends(
        self,
        user_id: int,
        days: int = 30,
        granularity: str = "day"
    ) -> Dict[str, Any]:
        """Get engagement trends over time."""
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        posts = self.db.query(PublishingLog).filter(
            PublishingLog.user_id == user_id,
            PublishingLog.published_at >= start_date,
            PublishingLog.success == True
        ).order_by(PublishingLog.published_at).all()
        
        # Group by time period
        if granularity == "day":
            format_str = "%Y-%m-%d"
        elif granularity == "week":
            format_str = "%Y-W%W"
        else:
            format_str = "%Y-%m"
        
        trends = defaultdict(lambda: {
            "posts": 0,
            "likes": 0,
            "comments": 0,
            "shares": 0,
            "engagements": 0
        })
        
        for post in posts:
            period = post.published_at.strftime(format_str)
            trends[period]["posts"] += 1
            
            if post.engagement_data:
                likes = post.engagement_data.get("likes", 0)
                comments = post.engagement_data.get("comments", 0)
                shares = post.engagement_data.get("shares", 0) + post.engagement_data.get("retweets", 0)
                
                trends[period]["likes"] += likes
                trends[period]["comments"] += comments
                trends[period]["shares"] += shares
                trends[period]["engagements"] += likes + comments + shares
        
        # Convert to list
        trend_list = [
            {"period": period, **data}
            for period, data in sorted(trends.items())
        ]
        
        return {
            "granularity": granularity,
            "period_days": days,
            "trends": trend_list
        }
    
    def get_best_posting_times(
        self,
        user_id: int,
        days: int = 90
    ) -> Dict[str, Any]:
        """Analyze best posting times based on engagement data."""
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        posts = self.db.query(PublishingLog).filter(
            PublishingLog.user_id == user_id,
            PublishingLog.published_at >= start_date,
            PublishingLog.success == True,
            PublishingLog.engagement_data.isnot(None)
        ).all()
        
        # Group by day of week and hour
        by_day = defaultdict(lambda: {"engagements": 0, "posts": 0})
        by_hour = defaultdict(lambda: {"engagements": 0, "posts": 0})
        by_day_hour = defaultdict(lambda: {"engagements": 0, "posts": 0})
        
        for post in posts:
            day = post.published_at.strftime("%A")
            hour = post.published_at.hour
            day_hour = f"{day}_{hour}"
            
            engagements = 0
            if post.engagement_data:
                engagements = (
                    post.engagement_data.get("likes", 0) +
                    post.engagement_data.get("comments", 0) +
                    post.engagement_data.get("shares", 0)
                )
            
            by_day[day]["engagements"] += engagements
            by_day[day]["posts"] += 1
            
            by_hour[hour]["engagements"] += engagements
            by_hour[hour]["posts"] += 1
            
            by_day_hour[day_hour]["engagements"] += engagements
            by_day_hour[day_hour]["posts"] += 1
        
        # Calculate averages and find best times
        best_days = sorted(
            [
                {"day": day, "avg_engagement": data["engagements"] / data["posts"] if data["posts"] > 0 else 0}
                for day, data in by_day.items()
            ],
            key=lambda x: x["avg_engagement"],
            reverse=True
        )
        
        best_hours = sorted(
            [
                {"hour": hour, "avg_engagement": data["engagements"] / data["posts"] if data["posts"] > 0 else 0}
                for hour, data in by_hour.items()
            ],
            key=lambda x: x["avg_engagement"],
            reverse=True
        )
        
        return {
            "analysis_period_days": days,
            "posts_analyzed": len(posts),
            "best_days": best_days[:3],
            "best_hours": best_hours[:5],
            "recommendation": self._generate_timing_recommendation(best_days, best_hours)
        }
    
    def _generate_timing_recommendation(
        self,
        best_days: List[Dict],
        best_hours: List[Dict]
    ) -> str:
        """Generate a human-readable timing recommendation."""
        
        if not best_days or not best_hours:
            return "Not enough data to generate recommendations. Keep posting to gather more insights!"
        
        top_day = best_days[0]["day"] if best_days else "weekdays"
        top_hour = best_hours[0]["hour"] if best_hours else 12
        
        hour_str = f"{top_hour}:00" if top_hour < 12 else f"{top_hour - 12 if top_hour > 12 else 12}:00 PM"
        if top_hour < 12:
            hour_str = f"{top_hour}:00 AM" if top_hour > 0 else "12:00 AM"
        
        return f"Based on your data, {top_day}s around {hour_str} tend to get the best engagement."
    
    # ==================== Content Analysis ====================
    
    def analyze_content_performance(
        self,
        user_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """Analyze what types of content perform best."""
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        posts = self.db.query(PublishingLog).filter(
            PublishingLog.user_id == user_id,
            PublishingLog.published_at >= start_date,
            PublishingLog.success == True,
            PublishingLog.engagement_data.isnot(None)
        ).all()
        
        # Analyze patterns
        with_emoji = {"engagements": 0, "count": 0}
        without_emoji = {"engagements": 0, "count": 0}
        with_hashtags = {"engagements": 0, "count": 0}
        without_hashtags = {"engagements": 0, "count": 0}
        with_question = {"engagements": 0, "count": 0}
        without_question = {"engagements": 0, "count": 0}
        short_caption = {"engagements": 0, "count": 0}  # < 100 chars
        long_caption = {"engagements": 0, "count": 0}   # > 200 chars
        
        for post in posts:
            engagements = 0
            if post.engagement_data:
                engagements = (
                    post.engagement_data.get("likes", 0) +
                    post.engagement_data.get("comments", 0) +
                    post.engagement_data.get("shares", 0)
                )
            
            caption = post.caption or ""
            
            # Check for emojis (simple check)
            has_emoji = any(ord(c) > 127462 for c in caption)
            if has_emoji:
                with_emoji["engagements"] += engagements
                with_emoji["count"] += 1
            else:
                without_emoji["engagements"] += engagements
                without_emoji["count"] += 1
            
            # Check for hashtags
            has_hashtags = "#" in caption
            if has_hashtags:
                with_hashtags["engagements"] += engagements
                with_hashtags["count"] += 1
            else:
                without_hashtags["engagements"] += engagements
                without_hashtags["count"] += 1
            
            # Check for questions
            has_question = "?" in caption
            if has_question:
                with_question["engagements"] += engagements
                with_question["count"] += 1
            else:
                without_question["engagements"] += engagements
                without_question["count"] += 1
            
            # Caption length
            if len(caption) < 100:
                short_caption["engagements"] += engagements
                short_caption["count"] += 1
            elif len(caption) > 200:
                long_caption["engagements"] += engagements
                long_caption["count"] += 1
        
        def calc_avg(data):
            return round(data["engagements"] / data["count"], 1) if data["count"] > 0 else 0
        
        insights = []
        
        # Generate insights
        emoji_avg = calc_avg(with_emoji)
        no_emoji_avg = calc_avg(without_emoji)
        if emoji_avg > no_emoji_avg * 1.1:
            insights.append(f"Posts with emojis get {round((emoji_avg/no_emoji_avg - 1) * 100)}% more engagement")
        elif no_emoji_avg > emoji_avg * 1.1:
            insights.append(f"Posts without emojis perform better for your audience")
        
        question_avg = calc_avg(with_question)
        no_question_avg = calc_avg(without_question)
        if question_avg > no_question_avg * 1.1:
            insights.append(f"Questions boost your engagement by {round((question_avg/no_question_avg - 1) * 100)}%")
        
        return {
            "period_days": days,
            "posts_analyzed": len(posts),
            "patterns": {
                "emoji_effect": {
                    "with_emoji_avg": emoji_avg,
                    "without_emoji_avg": no_emoji_avg,
                    "with_emoji_count": with_emoji["count"],
                    "without_emoji_count": without_emoji["count"]
                },
                "hashtag_effect": {
                    "with_hashtags_avg": calc_avg(with_hashtags),
                    "without_hashtags_avg": calc_avg(without_hashtags)
                },
                "question_effect": {
                    "with_question_avg": question_avg,
                    "without_question_avg": no_question_avg
                },
                "caption_length": {
                    "short_avg": calc_avg(short_caption),
                    "long_avg": calc_avg(long_caption)
                }
            },
            "insights": insights
        }
    
    # ==================== Reports ====================
    
    def generate_performance_report(
        self,
        user_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """Generate a comprehensive performance report."""
        
        overview = self.get_performance_overview(user_id, days)
        platform_breakdown = self.get_platform_breakdown(user_id, days)
        top_posts = self.get_top_performing_posts(user_id, days, limit=5)
        trends = self.get_engagement_trends(user_id, days, "day")
        best_times = self.get_best_posting_times(user_id, min(days, 90))
        content_analysis = self.analyze_content_performance(user_id, days)
        
        # Calculate ROI estimate (time saved)
        posts_count = overview["total_posts"]
        time_saved_minutes = posts_count * 15  # Estimate 15 min per post
        
        return {
            "generated_at": datetime.utcnow().isoformat(),
            "period_days": days,
            "overview": overview,
            "platform_breakdown": platform_breakdown["platforms"],
            "top_posts": top_posts,
            "trends": trends["trends"],
            "best_times": best_times,
            "content_analysis": content_analysis,
            "roi_estimate": {
                "posts_created": posts_count,
                "time_saved_minutes": time_saved_minutes,
                "time_saved_display": f"{time_saved_minutes // 60}h {time_saved_minutes % 60}m"
            }
        }


def get_performance_service(db: Session) -> PerformanceTrackingService:
    return PerformanceTrackingService(db)

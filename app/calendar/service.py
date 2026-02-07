"""
Content Calendar Service
========================

Provides a visual calendar view for content planning and scheduling.

Features:
- Calendar view of scheduled/published content
- Gap detection (days without content)
- One-click content generation for gaps
- Drag-and-drop rescheduling
- Best time recommendations
- Recurring content support
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from collections import defaultdict

from app.core.config import get_settings
from app.models.user import User
from app.models.models import Brand, GeneratedContent, ContentType
from app.social.models import ScheduledSocialPost, PublishingLog, PostStatus, SocialPlatform

logger = logging.getLogger(__name__)
settings = get_settings()


# ==================== Best Times to Post ====================

BEST_TIMES_BY_PLATFORM = {
    "instagram": [
        {"day": "monday", "times": ["11:00", "14:00", "19:00"]},
        {"day": "tuesday", "times": ["10:00", "14:00", "19:00"]},
        {"day": "wednesday", "times": ["11:00", "14:00", "19:00"]},
        {"day": "thursday", "times": ["10:00", "14:00", "20:00"]},
        {"day": "friday", "times": ["10:00", "14:00", "19:00"]},
        {"day": "saturday", "times": ["10:00", "13:00"]},
        {"day": "sunday", "times": ["10:00", "13:00", "19:00"]},
    ],
    "twitter": [
        {"day": "monday", "times": ["08:00", "12:00", "17:00"]},
        {"day": "tuesday", "times": ["09:00", "12:00", "17:00"]},
        {"day": "wednesday", "times": ["09:00", "12:00", "17:00"]},
        {"day": "thursday", "times": ["09:00", "12:00", "17:00"]},
        {"day": "friday", "times": ["09:00", "12:00", "16:00"]},
        {"day": "saturday", "times": ["10:00", "13:00"]},
        {"day": "sunday", "times": ["10:00", "14:00"]},
    ],
    "linkedin": [
        {"day": "monday", "times": ["07:30", "12:00", "17:00"]},
        {"day": "tuesday", "times": ["07:30", "10:00", "17:00"]},
        {"day": "wednesday", "times": ["07:30", "12:00", "17:00"]},
        {"day": "thursday", "times": ["07:30", "10:00", "14:00"]},
        {"day": "friday", "times": ["07:30", "12:00", "15:00"]},
        {"day": "saturday", "times": ["10:00"]},
        {"day": "sunday", "times": ["10:00"]},
    ],
    "facebook": [
        {"day": "monday", "times": ["09:00", "13:00", "16:00"]},
        {"day": "tuesday", "times": ["09:00", "13:00", "16:00"]},
        {"day": "wednesday", "times": ["09:00", "13:00", "15:00"]},
        {"day": "thursday", "times": ["09:00", "12:00", "14:00"]},
        {"day": "friday", "times": ["09:00", "11:00", "14:00"]},
        {"day": "saturday", "times": ["10:00", "12:00"]},
        {"day": "sunday", "times": ["10:00", "13:00"]},
    ],
    "tiktok": [
        {"day": "monday", "times": ["06:00", "10:00", "22:00"]},
        {"day": "tuesday", "times": ["02:00", "04:00", "09:00"]},
        {"day": "wednesday", "times": ["07:00", "08:00", "23:00"]},
        {"day": "thursday", "times": ["09:00", "12:00", "19:00"]},
        {"day": "friday", "times": ["05:00", "13:00", "15:00"]},
        {"day": "saturday", "times": ["11:00", "19:00", "20:00"]},
        {"day": "sunday", "times": ["07:00", "08:00", "16:00"]},
    ],
}


class ContentCalendarService:
    """Service for managing content calendar."""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ==================== Calendar Data ====================
    
    def get_calendar_data(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
        brand_id: int = None,
        platform: str = None
    ) -> Dict[str, Any]:
        """Get calendar data for date range."""
        
        # Get scheduled posts
        scheduled_query = self.db.query(ScheduledSocialPost).filter(
            ScheduledSocialPost.user_id == user_id,
            ScheduledSocialPost.scheduled_time >= datetime.combine(start_date, datetime.min.time()),
            ScheduledSocialPost.scheduled_time <= datetime.combine(end_date, datetime.max.time())
        )
        
        if brand_id:
            scheduled_query = scheduled_query.filter(ScheduledSocialPost.brand_id == brand_id)
        if platform:
            scheduled_query = scheduled_query.filter(ScheduledSocialPost.platform == platform)
        
        scheduled_posts = scheduled_query.all()
        
        # Get published posts
        published_query = self.db.query(PublishingLog).filter(
            PublishingLog.user_id == user_id,
            PublishingLog.published_at >= datetime.combine(start_date, datetime.min.time()),
            PublishingLog.published_at <= datetime.combine(end_date, datetime.max.time()),
            PublishingLog.success == True
        )
        
        if platform:
            published_query = published_query.filter(PublishingLog.platform == platform)
        
        published_posts = published_query.all()
        
        # Organize by date
        calendar_items = defaultdict(list)
        
        for post in scheduled_posts:
            date_key = post.scheduled_time.strftime("%Y-%m-%d")
            calendar_items[date_key].append({
                "id": post.id,
                "type": "scheduled",
                "platform": post.platform.value if hasattr(post.platform, 'value') else post.platform,
                "time": post.scheduled_time.strftime("%H:%M"),
                "datetime": post.scheduled_time.isoformat(),
                "caption_preview": post.caption[:100] + "..." if post.caption and len(post.caption) > 100 else post.caption,
                "status": post.status.value if hasattr(post.status, 'value') else post.status,
                "brand_id": post.brand_id,
                "content_id": post.content_id,
                "has_media": bool(post.media_urls)
            })
        
        for log in published_posts:
            date_key = log.published_at.strftime("%Y-%m-%d")
            calendar_items[date_key].append({
                "id": log.id,
                "type": "published",
                "platform": log.platform.value if hasattr(log.platform, 'value') else log.platform,
                "time": log.published_at.strftime("%H:%M"),
                "datetime": log.published_at.isoformat(),
                "post_url": log.post_url,
                "post_id": log.platform_post_id,
                "engagement": log.engagement_data
            })
        
        # Find gaps
        gaps = self._find_content_gaps(user_id, start_date, end_date, calendar_items)
        
        # Get stats
        stats = self._calculate_calendar_stats(calendar_items, start_date, end_date)
        
        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "items": dict(calendar_items),
            "gaps": gaps,
            "stats": stats
        }
    
    def _find_content_gaps(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
        calendar_items: Dict
    ) -> List[Dict[str, Any]]:
        """Find days without scheduled or published content."""
        
        gaps = []
        current_date = start_date
        
        while current_date <= end_date:
            date_key = current_date.strftime("%Y-%m-%d")
            
            # Skip past dates
            if current_date < date.today():
                current_date += timedelta(days=1)
                continue
            
            items = calendar_items.get(date_key, [])
            
            if not items:
                # This is a gap
                day_name = current_date.strftime("%A").lower()
                suggested_times = self._get_best_times_for_day(day_name)
                
                gaps.append({
                    "date": date_key,
                    "day_name": current_date.strftime("%A"),
                    "suggested_times": suggested_times,
                    "suggestion": self._get_content_suggestion_for_day(day_name)
                })
            
            current_date += timedelta(days=1)
        
        return gaps
    
    def _get_best_times_for_day(self, day_name: str, platform: str = "instagram") -> List[str]:
        """Get best posting times for a specific day."""
        
        platform_times = BEST_TIMES_BY_PLATFORM.get(platform, BEST_TIMES_BY_PLATFORM["instagram"])
        
        for day_data in platform_times:
            if day_data["day"] == day_name:
                return day_data["times"]
        
        return ["10:00", "14:00", "19:00"]  # Default times
    
    def _get_content_suggestion_for_day(self, day_name: str) -> str:
        """Get content suggestion based on day of week."""
        
        suggestions = {
            "monday": "Start the week with motivation or goals",
            "tuesday": "Share a tutorial or tip",
            "wednesday": "Mid-week engagement post or poll",
            "thursday": "Throwback or behind-the-scenes",
            "friday": "Celebrate wins or weekend plans",
            "saturday": "Relaxed, personal content",
            "sunday": "Inspirational or reflective post"
        }
        
        return suggestions.get(day_name, "Share something valuable with your audience")
    
    def _calculate_calendar_stats(
        self,
        calendar_items: Dict,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Calculate calendar statistics."""
        
        total_days = (end_date - start_date).days + 1
        days_with_content = len([d for d in calendar_items.values() if d])
        
        total_scheduled = sum(
            1 for items in calendar_items.values() 
            for item in items if item["type"] == "scheduled"
        )
        
        total_published = sum(
            1 for items in calendar_items.values() 
            for item in items if item["type"] == "published"
        )
        
        # Platform breakdown
        platform_counts = defaultdict(int)
        for items in calendar_items.values():
            for item in items:
                platform_counts[item["platform"]] += 1
        
        return {
            "total_days": total_days,
            "days_with_content": days_with_content,
            "coverage_percent": round((days_with_content / total_days) * 100) if total_days > 0 else 0,
            "total_scheduled": total_scheduled,
            "total_published": total_published,
            "by_platform": dict(platform_counts)
        }
    
    # ==================== Scheduling ====================
    
    def schedule_content(
        self,
        user_id: int,
        content_id: int,
        platform: str,
        scheduled_time: datetime,
        brand_id: int = None,
        caption: str = None,
        hashtags: List[str] = None
    ) -> ScheduledSocialPost:
        """Schedule content for posting."""
        
        # Get the content
        content = self.db.query(GeneratedContent).filter(
            GeneratedContent.id == content_id,
            GeneratedContent.user_id == user_id
        ).first()
        
        if not content:
            raise ValueError("Content not found")
        
        # Create scheduled post
        post = ScheduledSocialPost(
            user_id=user_id,
            brand_id=brand_id or content.brand_id,
            content_id=content_id,
            platform=platform,
            scheduled_time=scheduled_time,
            caption=caption or content.caption,
            hashtags=hashtags or content.hashtags,
            media_urls=[content.result_url] if content.result_url else [],
            status=PostStatus.SCHEDULED
        )
        
        self.db.add(post)
        self.db.commit()
        self.db.refresh(post)
        
        return post
    
    def reschedule_post(
        self,
        user_id: int,
        post_id: int,
        new_time: datetime
    ) -> ScheduledSocialPost:
        """Reschedule an existing post."""
        
        post = self.db.query(ScheduledSocialPost).filter(
            ScheduledSocialPost.id == post_id,
            ScheduledSocialPost.user_id == user_id,
            ScheduledSocialPost.status == PostStatus.SCHEDULED
        ).first()
        
        if not post:
            raise ValueError("Post not found or cannot be rescheduled")
        
        post.scheduled_time = new_time
        self.db.commit()
        self.db.refresh(post)
        
        return post
    
    def cancel_scheduled_post(self, user_id: int, post_id: int) -> bool:
        """Cancel a scheduled post."""
        
        post = self.db.query(ScheduledSocialPost).filter(
            ScheduledSocialPost.id == post_id,
            ScheduledSocialPost.user_id == user_id,
            ScheduledSocialPost.status == PostStatus.SCHEDULED
        ).first()
        
        if not post:
            return False
        
        post.status = PostStatus.CANCELLED
        self.db.commit()
        
        return True
    
    # ==================== Quick Actions ====================
    
    def get_suggested_slots(
        self,
        user_id: int,
        days_ahead: int = 7,
        platform: str = "instagram"
    ) -> List[Dict[str, Any]]:
        """Get suggested open slots for scheduling."""
        
        start_date = date.today()
        end_date = start_date + timedelta(days=days_ahead)
        
        # Get existing scheduled posts
        existing = self.db.query(ScheduledSocialPost).filter(
            ScheduledSocialPost.user_id == user_id,
            ScheduledSocialPost.scheduled_time >= datetime.combine(start_date, datetime.min.time()),
            ScheduledSocialPost.scheduled_time <= datetime.combine(end_date, datetime.max.time()),
            ScheduledSocialPost.status == PostStatus.SCHEDULED
        ).all()
        
        # Get scheduled times
        scheduled_times = set()
        for post in existing:
            scheduled_times.add(post.scheduled_time.strftime("%Y-%m-%d %H:%M"))
        
        # Generate suggestions
        suggestions = []
        current_date = start_date
        
        while current_date <= end_date:
            day_name = current_date.strftime("%A").lower()
            best_times = self._get_best_times_for_day(day_name, platform)
            
            for time_str in best_times:
                slot_datetime = datetime.strptime(
                    f"{current_date.isoformat()} {time_str}",
                    "%Y-%m-%d %H:%M"
                )
                
                # Skip past times
                if slot_datetime <= datetime.now():
                    continue
                
                slot_key = slot_datetime.strftime("%Y-%m-%d %H:%M")
                
                if slot_key not in scheduled_times:
                    suggestions.append({
                        "datetime": slot_datetime.isoformat(),
                        "date": current_date.isoformat(),
                        "time": time_str,
                        "day_name": current_date.strftime("%A"),
                        "platform": platform,
                        "is_optimal": True
                    })
            
            current_date += timedelta(days=1)
        
        return suggestions[:20]  # Limit to 20 suggestions
    
    def fill_gap_with_content(
        self,
        user_id: int,
        gap_date: date,
        brand_id: int,
        platform: str = "instagram",
        time_str: str = None
    ) -> Dict[str, Any]:
        """Generate and schedule content for a gap."""
        
        from app.services.generator import ContentGeneratorService
        
        # Get brand
        brand = self.db.query(Brand).filter(
            Brand.id == brand_id,
            Brand.user_id == user_id
        ).first()
        
        if not brand:
            raise ValueError("Brand not found")
        
        # Determine time
        if not time_str:
            day_name = gap_date.strftime("%A").lower()
            best_times = self._get_best_times_for_day(day_name, platform)
            time_str = best_times[0] if best_times else "10:00"
        
        scheduled_time = datetime.strptime(
            f"{gap_date.isoformat()} {time_str}",
            "%Y-%m-%d %H:%M"
        )
        
        # Generate content
        generator = ContentGeneratorService(
            self.db,
            settings.openai_api_key,
            settings.replicate_api_token
        )
        
        # Get suggestion for the day
        day_name = gap_date.strftime("%A").lower()
        suggestion = self._get_content_suggestion_for_day(day_name)
        
        content = generator.generate_content(
            brand=brand,
            user_id=user_id,
            content_type=ContentType.TEXT,
            custom_prompt=f"Create a {platform} post for {day_name}. Theme: {suggestion}"
        )
        
        # Schedule it
        post = self.schedule_content(
            user_id=user_id,
            content_id=content.id,
            platform=platform,
            scheduled_time=scheduled_time,
            brand_id=brand_id
        )
        
        return {
            "content": {
                "id": content.id,
                "caption": content.caption,
                "hashtags": content.hashtags
            },
            "scheduled_post": {
                "id": post.id,
                "scheduled_time": scheduled_time.isoformat(),
                "platform": platform
            }
        }
    
    # ==================== Recurring Posts ====================
    
    def create_recurring_schedule(
        self,
        user_id: int,
        brand_id: int,
        platform: str,
        frequency: str,  # daily, weekly, weekdays
        times: List[str],
        start_date: date,
        end_date: date = None
    ) -> Dict[str, Any]:
        """Create a recurring posting schedule."""
        
        if not end_date:
            end_date = start_date + timedelta(days=30)  # Default 30 days
        
        slots_created = []
        current_date = start_date
        
        while current_date <= end_date:
            should_post = False
            
            if frequency == "daily":
                should_post = True
            elif frequency == "weekdays":
                should_post = current_date.weekday() < 5
            elif frequency == "weekly":
                should_post = current_date.weekday() == start_date.weekday()
            
            if should_post:
                for time_str in times:
                    slot_datetime = datetime.strptime(
                        f"{current_date.isoformat()} {time_str}",
                        "%Y-%m-%d %H:%M"
                    )
                    
                    if slot_datetime > datetime.now():
                        slots_created.append({
                            "date": current_date.isoformat(),
                            "time": time_str,
                            "datetime": slot_datetime.isoformat()
                        })
            
            current_date += timedelta(days=1)
        
        return {
            "frequency": frequency,
            "times": times,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "slots_created": len(slots_created),
            "slots": slots_created
        }


def get_calendar_service(db: Session) -> ContentCalendarService:
    return ContentCalendarService(db)

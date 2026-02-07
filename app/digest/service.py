"""
Email Digest Service
====================

Sends weekly email digests to users with:
- Content performance summary
- Content suggestions based on trends
- Personalized recommendations
- Tips and best practices

Also handles other transactional emails like:
- Welcome emails
- Inactivity nudges
- Feature announcements
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.core.config import get_settings
from app.models.user import User
from app.models.models import Brand, GeneratedContent, ContentType
from app.social.models import ScheduledSocialPost, PublishingLog

logger = logging.getLogger(__name__)
settings = get_settings()


# ==================== Weekly Tips Pool ====================

WEEKLY_TIPS = [
    {
        "title": "Post Consistently",
        "content": "Posting 3-5 times per week keeps your audience engaged. Use our scheduling feature to plan ahead!",
        "cta": "Schedule Posts",
        "cta_link": "/social/schedule"
    },
    {
        "title": "Use Hashtags Strategically",
        "content": "Mix popular hashtags with niche ones. Our AI suggests the perfect combination for each post.",
        "cta": "Try AI Hashtags",
        "cta_link": "/assistant"
    },
    {
        "title": "Engage with Your Audience",
        "content": "Posts with questions get 2x more comments. Ask your audience for their opinions!",
        "cta": "Browse Question Templates",
        "cta_link": "/templates?category=engagement"
    },
    {
        "title": "Repurpose Your Best Content",
        "content": "Your top-performing content can be adapted for different platforms. Turn a carousel into a thread!",
        "cta": "View Analytics",
        "cta_link": "/analytics"
    },
    {
        "title": "Train Your Brand Voice",
        "content": "A consistent brand voice increases recognition by 80%. Train our AI to write just like you.",
        "cta": "Train Brand Voice",
        "cta_link": "/brandvoice"
    },
    {
        "title": "Batch Your Content Creation",
        "content": "Create a week's worth of content in one session. It's more efficient and keeps your messaging consistent.",
        "cta": "Open Content Studio",
        "cta_link": "/studio"
    },
    {
        "title": "Leverage Trending Topics",
        "content": "Posts about trending topics get 3x more reach. Check our trends dashboard for inspiration.",
        "cta": "View Trends",
        "cta_link": "/trends"
    },
    {
        "title": "Optimize Post Timing",
        "content": "The best time to post varies by platform. Test different times and track what works for your audience.",
        "cta": "Schedule Smart",
        "cta_link": "/social/schedule"
    }
]


# ==================== Content Suggestions ====================

CONTENT_SUGGESTIONS = {
    "monday": [
        "Start the week strong with a motivational quote",
        "Share your weekly goals with your audience",
        "Behind-the-scenes of your Monday morning routine"
    ],
    "tuesday": [
        "Tutorial Tuesday - teach something valuable",
        "Share a tip related to your niche",
        "Product spotlight or feature highlight"
    ],
    "wednesday": [
        "Mid-week check-in with your audience",
        "Share a customer success story",
        "Ask a poll question to boost engagement"
    ],
    "thursday": [
        "Throwback Thursday - share your journey",
        "Industry news or trends discussion",
        "Expert interview or collaboration"
    ],
    "friday": [
        "Friday wins - celebrate achievements",
        "Weekend plans or recommendations",
        "Fun, lighthearted content"
    ],
    "weekend": [
        "Personal story or behind-the-scenes",
        "User-generated content feature",
        "Relaxed, authentic content"
    ]
}


class EmailDigestService:
    """Service for generating and sending email digests."""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ==================== Weekly Digest ====================
    
    def generate_weekly_digest(self, user: User) -> Dict[str, Any]:
        """Generate weekly digest content for a user."""
        
        # Get date range (last 7 days)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)
        
        # Get user's brands
        brands = self.db.query(Brand).filter(
            Brand.user_id == user.id,
            Brand.is_demo == False
        ).all()
        
        # Get content stats
        content_stats = self._get_content_stats(user.id, start_date, end_date)
        
        # Get top performing content
        top_content = self._get_top_content(user.id, start_date, end_date)
        
        # Get posting stats
        posting_stats = self._get_posting_stats(user.id, start_date, end_date)
        
        # Get suggested content ideas
        suggestions = self._get_content_suggestions(user, brands)
        
        # Get weekly tip
        weekly_tip = self._get_weekly_tip()
        
        # Calculate time saved (estimate: 15 min per content piece)
        time_saved_minutes = content_stats.get("total_content", 0) * 15
        
        return {
            "user_name": user.full_name or user.email.split('@')[0],
            "user_email": user.email,
            "period": {
                "start": start_date.strftime("%b %d"),
                "end": end_date.strftime("%b %d, %Y")
            },
            "brands_count": len(brands),
            "stats": {
                "content_created": content_stats.get("total_content", 0),
                "images_generated": content_stats.get("images", 0),
                "captions_written": content_stats.get("captions", 0),
                "posts_scheduled": posting_stats.get("scheduled", 0),
                "posts_published": posting_stats.get("published", 0),
                "time_saved_minutes": time_saved_minutes,
                "time_saved_display": f"{time_saved_minutes // 60}h {time_saved_minutes % 60}m" if time_saved_minutes >= 60 else f"{time_saved_minutes}m"
            },
            "top_content": top_content,
            "suggestions": suggestions,
            "weekly_tip": weekly_tip,
            "has_activity": content_stats.get("total_content", 0) > 0 or posting_stats.get("published", 0) > 0
        }
    
    def _get_content_stats(self, user_id: int, start_date: datetime, end_date: datetime) -> Dict[str, int]:
        """Get content creation stats for the period."""
        
        content = self.db.query(GeneratedContent).filter(
            GeneratedContent.user_id == user_id,
            GeneratedContent.created_at >= start_date,
            GeneratedContent.created_at <= end_date
        ).all()
        
        return {
            "total_content": len(content),
            "images": len([c for c in content if c.content_type == ContentType.IMAGE]),
            "captions": len([c for c in content if c.caption]),
            "videos": len([c for c in content if c.content_type == ContentType.VIDEO])
        }
    
    def _get_top_content(self, user_id: int, start_date: datetime, end_date: datetime, limit: int = 3) -> List[Dict[str, Any]]:
        """Get top performing content (based on engagement if available, otherwise most recent)."""
        
        # For now, return most recent content
        # In production, this would use engagement metrics from social platforms
        content = self.db.query(GeneratedContent).filter(
            GeneratedContent.user_id == user_id,
            GeneratedContent.created_at >= start_date,
            GeneratedContent.created_at <= end_date,
            GeneratedContent.caption.isnot(None)
        ).order_by(GeneratedContent.created_at.desc()).limit(limit).all()
        
        return [
            {
                "id": c.id,
                "type": c.content_type.value if c.content_type else "text",
                "caption_preview": c.caption[:100] + "..." if c.caption and len(c.caption) > 100 else c.caption,
                "created_at": c.created_at.strftime("%b %d")
            }
            for c in content
        ]
    
    def _get_posting_stats(self, user_id: int, start_date: datetime, end_date: datetime) -> Dict[str, int]:
        """Get social posting stats for the period."""
        
        try:
            scheduled = self.db.query(ScheduledSocialPost).filter(
                ScheduledSocialPost.user_id == user_id,
                ScheduledSocialPost.created_at >= start_date,
                ScheduledSocialPost.created_at <= end_date
            ).count()
            
            published = self.db.query(PublishingLog).filter(
                PublishingLog.user_id == user_id,
                PublishingLog.published_at >= start_date,
                PublishingLog.published_at <= end_date,
                PublishingLog.success == True
            ).count()
        except Exception:
            # Tables might not exist yet
            scheduled = 0
            published = 0
        
        return {
            "scheduled": scheduled,
            "published": published
        }
    
    def _get_content_suggestions(self, user: User, brands: List[Brand]) -> List[Dict[str, str]]:
        """Get personalized content suggestions."""
        
        suggestions = []
        
        # Get day of week for relevant suggestions
        today = datetime.utcnow().strftime("%A").lower()
        day_key = today if today in CONTENT_SUGGESTIONS else "weekend"
        day_suggestions = CONTENT_SUGGESTIONS[day_key]
        
        for i, suggestion in enumerate(day_suggestions[:3]):
            brand_name = brands[i % len(brands)].name if brands else "your brand"
            suggestions.append({
                "idea": suggestion,
                "for_brand": brand_name
            })
        
        return suggestions
    
    def _get_weekly_tip(self) -> Dict[str, str]:
        """Get a weekly tip (rotates based on week number)."""
        
        week_number = datetime.utcnow().isocalendar()[1]
        tip_index = week_number % len(WEEKLY_TIPS)
        return WEEKLY_TIPS[tip_index]
    
    # ==================== Email Generation ====================
    
    def generate_digest_html(self, digest_data: Dict[str, Any]) -> str:
        """Generate HTML email content for the digest."""
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Your Weekly Content Digest</title>
</head>
<body style="margin: 0; padding: 0; background-color: #0f0f13; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #0f0f13;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #1a1a23; border-radius: 16px; overflow: hidden;">
                    
                    <!-- Header -->
                    <tr>
                        <td style="padding: 40px 40px 20px; text-align: center;">
                            <h1 style="color: #e8e8ef; margin: 0; font-size: 28px;">📊 Your Weekly Digest</h1>
                            <p style="color: #8a8a9a; margin: 10px 0 0; font-size: 14px;">
                                {digest_data['period']['start']} - {digest_data['period']['end']}
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Greeting -->
                    <tr>
                        <td style="padding: 0 40px 30px;">
                            <p style="color: #e8e8ef; font-size: 16px; margin: 0;">
                                Hey {digest_data['user_name']}! 👋
                            </p>
                            <p style="color: #8a8a9a; font-size: 14px; margin: 10px 0 0;">
                                Here's what you accomplished this week:
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Stats Grid -->
                    <tr>
                        <td style="padding: 0 40px 30px;">
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td width="33%" style="text-align: center; padding: 20px; background-color: #252530; border-radius: 12px;">
                                        <div style="font-size: 32px; font-weight: bold; color: #6366f1;">{digest_data['stats']['content_created']}</div>
                                        <div style="font-size: 12px; color: #8a8a9a; margin-top: 5px;">Content Created</div>
                                    </td>
                                    <td width="10"></td>
                                    <td width="33%" style="text-align: center; padding: 20px; background-color: #252530; border-radius: 12px;">
                                        <div style="font-size: 32px; font-weight: bold; color: #10b981;">{digest_data['stats']['posts_published']}</div>
                                        <div style="font-size: 12px; color: #8a8a9a; margin-top: 5px;">Posts Published</div>
                                    </td>
                                    <td width="10"></td>
                                    <td width="33%" style="text-align: center; padding: 20px; background-color: #252530; border-radius: 12px;">
                                        <div style="font-size: 32px; font-weight: bold; color: #f59e0b;">{digest_data['stats']['time_saved_display']}</div>
                                        <div style="font-size: 12px; color: #8a8a9a; margin-top: 5px;">Time Saved</div>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Content Suggestions -->
                    <tr>
                        <td style="padding: 0 40px 30px;">
                            <h2 style="color: #e8e8ef; font-size: 18px; margin: 0 0 15px;">💡 Content Ideas for This Week</h2>
                            <table width="100%" cellpadding="0" cellspacing="0">
                                {"".join([f'''
                                <tr>
                                    <td style="padding: 12px 16px; background-color: #252530; border-radius: 8px; margin-bottom: 8px;">
                                        <p style="color: #e8e8ef; margin: 0; font-size: 14px;">{s['idea']}</p>
                                        <p style="color: #6366f1; margin: 5px 0 0; font-size: 12px;">For: {s['for_brand']}</p>
                                    </td>
                                </tr>
                                <tr><td height="8"></td></tr>
                                ''' for s in digest_data['suggestions']])}
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Weekly Tip -->
                    <tr>
                        <td style="padding: 0 40px 30px;">
                            <table width="100%" cellpadding="0" cellspacing="0" style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); border-radius: 12px;">
                                <tr>
                                    <td style="padding: 25px;">
                                        <h3 style="color: #ffffff; margin: 0 0 10px; font-size: 16px;">💎 Pro Tip: {digest_data['weekly_tip']['title']}</h3>
                                        <p style="color: rgba(255,255,255,0.9); margin: 0 0 15px; font-size: 14px;">{digest_data['weekly_tip']['content']}</p>
                                        <a href="{settings.frontend_url}{digest_data['weekly_tip']['cta_link']}" 
                                           style="display: inline-block; background-color: #ffffff; color: #6366f1; padding: 10px 20px; border-radius: 6px; text-decoration: none; font-size: 14px; font-weight: 600;">
                                            {digest_data['weekly_tip']['cta']} →
                                        </a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- CTA -->
                    <tr>
                        <td style="padding: 0 40px 40px; text-align: center;">
                            <a href="{settings.frontend_url}/studio" 
                               style="display: inline-block; background-color: #6366f1; color: #ffffff; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-size: 16px; font-weight: 600;">
                                Create Content Now
                            </a>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 30px 40px; background-color: #151519; text-align: center;">
                            <p style="color: #8a8a9a; font-size: 12px; margin: 0;">
                                You're receiving this because you're subscribed to weekly digests.
                            </p>
                            <p style="color: #8a8a9a; font-size: 12px; margin: 10px 0 0;">
                                <a href="{settings.frontend_url}/settings" style="color: #6366f1; text-decoration: none;">Manage preferences</a>
                                &nbsp;•&nbsp;
                                <a href="{settings.frontend_url}/settings" style="color: #6366f1; text-decoration: none;">Unsubscribe</a>
                            </p>
                        </td>
                    </tr>
                    
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
        """
        
        return html
    
    def generate_digest_text(self, digest_data: Dict[str, Any]) -> str:
        """Generate plain text email content for the digest."""
        
        text = f"""
Your Weekly Content Digest
{digest_data['period']['start']} - {digest_data['period']['end']}

Hey {digest_data['user_name']}! 👋

Here's what you accomplished this week:

📊 YOUR STATS
• Content Created: {digest_data['stats']['content_created']}
• Posts Published: {digest_data['stats']['posts_published']}
• Time Saved: {digest_data['stats']['time_saved_display']}

💡 CONTENT IDEAS FOR THIS WEEK
"""
        
        for s in digest_data['suggestions']:
            text += f"• {s['idea']} (For: {s['for_brand']})\n"
        
        text += f"""
💎 PRO TIP: {digest_data['weekly_tip']['title']}
{digest_data['weekly_tip']['content']}

Ready to create? Visit: {settings.frontend_url}/studio

---
You're receiving this because you're subscribed to weekly digests.
Manage preferences: {settings.frontend_url}/settings
        """
        
        return text
    
    # ==================== Send Emails ====================
    
    async def send_weekly_digest(self, user: User) -> bool:
        """Send weekly digest email to a user."""
        
        # Check if user wants weekly digests
        email_prefs = user.email_preferences or {}
        if not email_prefs.get("weekly_digest", True):
            logger.info(f"User {user.id} has disabled weekly digests")
            return False
        
        # Generate digest content
        digest_data = self.generate_weekly_digest(user)
        
        # Skip if no activity
        if not digest_data["has_activity"]:
            logger.info(f"User {user.id} has no activity, sending encouragement email instead")
            return await self.send_inactivity_nudge(user)
        
        # Generate email content
        html_content = self.generate_digest_html(digest_data)
        text_content = self.generate_digest_text(digest_data)
        
        # Send email
        from app.auth.email import EmailService
        email_service = EmailService()
        
        try:
            await email_service.send_email(
                to_email=user.email,
                subject=f"📊 Your Weekly Content Digest - {digest_data['stats']['content_created']} pieces created!",
                html_content=html_content,
                text_content=text_content
            )
            logger.info(f"Sent weekly digest to user {user.id}")
            return True
        except Exception as e:
            logger.error(f"Failed to send weekly digest to user {user.id}: {e}")
            return False
    
    async def send_inactivity_nudge(self, user: User) -> bool:
        """Send encouragement email to inactive users."""
        
        # Check preferences
        email_prefs = user.email_preferences or {}
        if not email_prefs.get("content_suggestions", True):
            return False
        
        from app.auth.email import EmailService
        email_service = EmailService()
        
        user_name = user.full_name or user.email.split('@')[0]
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>We miss you!</title>
</head>
<body style="margin: 0; padding: 0; background-color: #0f0f13; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #0f0f13;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #1a1a23; border-radius: 16px; overflow: hidden;">
                    <tr>
                        <td style="padding: 40px; text-align: center;">
                            <h1 style="color: #e8e8ef; margin: 0; font-size: 28px;">We miss you, {user_name}! 👋</h1>
                            <p style="color: #8a8a9a; font-size: 16px; margin: 20px 0;">
                                It's been a while since you created content. Your audience is waiting!
                            </p>
                            <p style="color: #8a8a9a; font-size: 14px; margin: 20px 0;">
                                Here are some quick wins to get you started:
                            </p>
                            <ul style="color: #e8e8ef; text-align: left; font-size: 14px; margin: 20px 40px;">
                                <li style="margin: 10px 0;">Generate a quick caption with AI in 30 seconds</li>
                                <li style="margin: 10px 0;">Browse our new content templates</li>
                                <li style="margin: 10px 0;">Schedule posts for the week ahead</li>
                            </ul>
                            <a href="{settings.frontend_url}/studio" 
                               style="display: inline-block; background-color: #6366f1; color: #ffffff; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-size: 16px; font-weight: 600; margin-top: 20px;">
                                Create Something Now →
                            </a>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
        """
        
        try:
            await email_service.send_email(
                to_email=user.email,
                subject=f"We miss you, {user_name}! Your audience is waiting 👋",
                html_content=html_content,
                text_content=f"Hey {user_name}, it's been a while! Visit {settings.frontend_url} to create some amazing content."
            )
            logger.info(f"Sent inactivity nudge to user {user.id}")
            return True
        except Exception as e:
            logger.error(f"Failed to send inactivity nudge to user {user.id}: {e}")
            return False
    
    # ==================== Batch Processing ====================
    
    def get_users_for_weekly_digest(self) -> List[User]:
        """Get all users who should receive weekly digest."""
        
        # Get active users who haven't disabled digests
        users = self.db.query(User).filter(
            User.is_active == True,
            User.is_verified == True
        ).all()
        
        # Filter by email preferences
        eligible_users = []
        for user in users:
            prefs = user.email_preferences or {}
            if prefs.get("weekly_digest", True):
                eligible_users.append(user)
        
        return eligible_users
    
    async def send_all_weekly_digests(self) -> Dict[str, int]:
        """Send weekly digests to all eligible users."""
        
        users = self.get_users_for_weekly_digest()
        
        sent = 0
        failed = 0
        skipped = 0
        
        for user in users:
            try:
                success = await self.send_weekly_digest(user)
                if success:
                    sent += 1
                else:
                    skipped += 1
            except Exception as e:
                logger.error(f"Error sending digest to user {user.id}: {e}")
                failed += 1
        
        return {
            "total_users": len(users),
            "sent": sent,
            "failed": failed,
            "skipped": skipped
        }


def get_digest_service(db: Session) -> EmailDigestService:
    return EmailDigestService(db)

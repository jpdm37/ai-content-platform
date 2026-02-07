"""
Enhanced Admin Service
======================
Comprehensive platform management for administrators.

Features:
- Feature flags management
- Usage/quota management
- User management (suspend, verify, reset)
- Subscription management
- Content moderation
- System health monitoring
- Announcement system
- Bulk operations
"""

from datetime import datetime, timedelta
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_, desc
import json

from app.admin.models import AdminUser, AdminRole, AuditLog, SystemSetting, DEFAULT_SETTINGS
from app.models.user import User
from app.models.models import Brand, GeneratedContent
from app.social.models import SocialAccount, ScheduledSocialPost, PublishingLog
from app.billing.models import Subscription, UsageRecord
from app.abtesting.service import ABTest
from app.auth.security import get_password_hash, verify_password, create_access_token


# Extended feature flags
FEATURE_FLAGS = {
    # Core Features
    "feature_content_generation": {
        "default": True,
        "description": "AI content/caption generation",
        "category": "core"
    },
    "feature_image_generation": {
        "default": True,
        "description": "AI image generation (Replicate)",
        "category": "core"
    },
    "feature_video_generation": {
        "default": True,
        "description": "AI video generation",
        "category": "core"
    },
    "feature_brand_voice": {
        "default": True,
        "description": "Brand voice training",
        "category": "core"
    },
    
    # Social Features
    "feature_social_posting": {
        "default": True,
        "description": "Social media posting/scheduling",
        "category": "social"
    },
    "feature_social_analytics": {
        "default": True,
        "description": "Social media analytics sync",
        "category": "social"
    },
    "feature_content_calendar": {
        "default": True,
        "description": "Content calendar & scheduling",
        "category": "social"
    },
    
    # Advanced Features
    "feature_ab_testing": {
        "default": True,
        "description": "A/B testing for content",
        "category": "advanced"
    },
    "feature_performance_tracking": {
        "default": True,
        "description": "Performance analytics dashboard",
        "category": "advanced"
    },
    "feature_ai_assistant": {
        "default": True,
        "description": "AI chat assistant",
        "category": "advanced"
    },
    "feature_templates": {
        "default": True,
        "description": "Content templates library",
        "category": "advanced"
    },
    
    # User Features
    "feature_oauth_login": {
        "default": True,
        "description": "Google/GitHub OAuth login",
        "category": "auth"
    },
    "feature_email_verification": {
        "default": True,
        "description": "Require email verification",
        "category": "auth"
    },
    "feature_onboarding": {
        "default": True,
        "description": "New user onboarding wizard",
        "category": "auth"
    },
    
    # System
    "maintenance_mode": {
        "default": False,
        "description": "Block all non-admin access",
        "category": "system"
    },
    "registration_enabled": {
        "default": True,
        "description": "Allow new user registrations",
        "category": "system"
    },
    "api_rate_limiting": {
        "default": True,
        "description": "Enable API rate limiting",
        "category": "system"
    },
}

# Tier limits configuration
TIER_LIMITS = {
    "free": {
        "monthly_generations": 10,
        "monthly_images": 5,
        "monthly_videos": 0,
        "brands": 1,
        "social_accounts": 1,
        "scheduled_posts": 10,
        "ab_tests": 0,
        "team_members": 0,
    },
    "creator": {
        "monthly_generations": 100,
        "monthly_images": 50,
        "monthly_videos": 5,
        "brands": 3,
        "social_accounts": 5,
        "scheduled_posts": 100,
        "ab_tests": 3,
        "team_members": 0,
    },
    "pro": {
        "monthly_generations": 500,
        "monthly_images": 250,
        "monthly_videos": 25,
        "brands": 10,
        "social_accounts": 15,
        "scheduled_posts": 500,
        "ab_tests": 10,
        "team_members": 3,
    },
    "agency": {
        "monthly_generations": 2000,
        "monthly_images": 1000,
        "monthly_videos": 100,
        "brands": 50,
        "social_accounts": 50,
        "scheduled_posts": 2000,
        "ab_tests": 50,
        "team_members": 10,
    },
}


class EnhancedAdminService:
    """Enhanced admin service with full platform management."""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ==================== Feature Flags ====================
    
    def get_all_feature_flags(self) -> List[Dict[str, Any]]:
        """Get all feature flags with current values."""
        result = []
        
        for key, config in FEATURE_FLAGS.items():
            # Check if overridden in database
            setting = self.db.query(SystemSetting).filter(
                SystemSetting.key == key
            ).first()
            
            current_value = config["default"]
            if setting:
                current_value = setting.value.lower() == "true"
            
            result.append({
                "key": key,
                "enabled": current_value,
                "default": config["default"],
                "description": config["description"],
                "category": config["category"],
                "overridden": setting is not None
            })
        
        return result
    
    def set_feature_flag(self, key: str, enabled: bool, admin_id: int) -> Dict[str, Any]:
        """Enable or disable a feature flag."""
        if key not in FEATURE_FLAGS:
            raise ValueError(f"Unknown feature flag: {key}")
        
        setting = self.db.query(SystemSetting).filter(
            SystemSetting.key == key
        ).first()
        
        if setting:
            setting.value = str(enabled).lower()
            setting.updated_by = admin_id
        else:
            setting = SystemSetting(
                key=key,
                value=str(enabled).lower(),
                description=FEATURE_FLAGS[key]["description"],
                updated_by=admin_id
            )
            self.db.add(setting)
        
        self.db.commit()
        
        return {
            "key": key,
            "enabled": enabled,
            "description": FEATURE_FLAGS[key]["description"]
        }
    
    def is_feature_enabled(self, key: str) -> bool:
        """Check if a feature is enabled."""
        if key not in FEATURE_FLAGS:
            return True  # Unknown features default to enabled
        
        setting = self.db.query(SystemSetting).filter(
            SystemSetting.key == key
        ).first()
        
        if setting:
            return setting.value.lower() == "true"
        
        return FEATURE_FLAGS[key]["default"]
    
    def bulk_set_features(self, features: Dict[str, bool], admin_id: int) -> int:
        """Set multiple feature flags at once."""
        count = 0
        for key, enabled in features.items():
            if key in FEATURE_FLAGS:
                self.set_feature_flag(key, enabled, admin_id)
                count += 1
        return count
    
    # ==================== Usage & Quota Management ====================
    
    def get_user_usage(self, user_id: int) -> Dict[str, Any]:
        """Get detailed usage statistics for a user."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")
        
        # Get subscription tier
        subscription = self.db.query(Subscription).filter(
            Subscription.user_id == user_id
        ).first()
        tier = subscription.tier if subscription else "free"
        limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
        
        # Calculate current month usage
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Content generations this month
        generations = self.db.query(func.count(GeneratedContent.id)).filter(
            GeneratedContent.user_id == user_id,
            GeneratedContent.created_at >= month_start
        ).scalar() or 0
        
        # Images generated
        images = self.db.query(func.count(GeneratedContent.id)).filter(
            GeneratedContent.user_id == user_id,
            GeneratedContent.created_at >= month_start,
            GeneratedContent.content_type == "image"
        ).scalar() or 0
        
        # Videos generated
        from app.video.models import VideoProject
        videos = self.db.query(func.count(VideoProject.id)).filter(
            VideoProject.user_id == user_id,
            VideoProject.created_at >= month_start
        ).scalar() or 0
        
        # Brands count
        brands = self.db.query(func.count(Brand.id)).filter(
            Brand.user_id == user_id,
            Brand.is_active == True
        ).scalar() or 0
        
        # Social accounts
        social_accounts = self.db.query(func.count(SocialAccount.id)).filter(
            SocialAccount.user_id == user_id,
            SocialAccount.is_active == True
        ).scalar() or 0
        
        # Scheduled posts
        scheduled_posts = self.db.query(func.count(ScheduledSocialPost.id)).filter(
            ScheduledSocialPost.user_id == user_id,
            ScheduledSocialPost.status == "scheduled"
        ).scalar() or 0
        
        # A/B tests
        ab_tests = self.db.query(func.count(ABTest.id)).filter(
            ABTest.user_id == user_id,
            ABTest.status.in_(["draft", "running"])
        ).scalar() or 0
        
        return {
            "user_id": user_id,
            "tier": tier,
            "period_start": month_start.isoformat(),
            "usage": {
                "generations": {"used": generations, "limit": limits["monthly_generations"]},
                "images": {"used": images, "limit": limits["monthly_images"]},
                "videos": {"used": videos, "limit": limits["monthly_videos"]},
                "brands": {"used": brands, "limit": limits["brands"]},
                "social_accounts": {"used": social_accounts, "limit": limits["social_accounts"]},
                "scheduled_posts": {"used": scheduled_posts, "limit": limits["scheduled_posts"]},
                "ab_tests": {"used": ab_tests, "limit": limits["ab_tests"]},
            },
            "overages": self._get_user_overages(user_id)
        }
    
    def _get_user_overages(self, user_id: int) -> Dict[str, int]:
        """Get any additional usage granted to user."""
        # Check for overage records in system settings or a dedicated table
        setting = self.db.query(SystemSetting).filter(
            SystemSetting.key == f"user_overage_{user_id}"
        ).first()
        
        if setting:
            try:
                return json.loads(setting.value)
            except:
                pass
        
        return {}
    
    def add_user_usage(
        self,
        user_id: int,
        usage_type: str,
        amount: int,
        admin_id: int,
        reason: str = None
    ) -> Dict[str, Any]:
        """Add additional usage/quota to a user's account."""
        valid_types = ["generations", "images", "videos", "brands", "social_accounts", "scheduled_posts", "ab_tests"]
        
        if usage_type not in valid_types:
            raise ValueError(f"Invalid usage type. Valid types: {valid_types}")
        
        # Get current overages
        key = f"user_overage_{user_id}"
        setting = self.db.query(SystemSetting).filter(
            SystemSetting.key == key
        ).first()
        
        overages = {}
        if setting:
            try:
                overages = json.loads(setting.value)
            except:
                overages = {}
        
        # Add to overages
        current = overages.get(usage_type, 0)
        overages[usage_type] = current + amount
        
        # Save
        if setting:
            setting.value = json.dumps(overages)
            setting.updated_by = admin_id
        else:
            setting = SystemSetting(
                key=key,
                value=json.dumps(overages),
                description=f"Usage overages for user {user_id}",
                updated_by=admin_id
            )
            self.db.add(setting)
        
        self.db.commit()
        
        # Log action
        self._log_action(
            admin_id=admin_id,
            action="usage.add",
            target_type="user",
            target_id=user_id,
            details={
                "usage_type": usage_type,
                "amount": amount,
                "reason": reason,
                "new_total": overages[usage_type]
            }
        )
        
        return {
            "user_id": user_id,
            "usage_type": usage_type,
            "added": amount,
            "total_overage": overages[usage_type]
        }
    
    def reset_user_usage(self, user_id: int, admin_id: int) -> Dict[str, Any]:
        """Reset a user's usage counters (for the current period)."""
        # This would typically be handled by deleting usage records for current period
        # For now, we'll just log the action
        self._log_action(
            admin_id=admin_id,
            action="usage.reset",
            target_type="user",
            target_id=user_id
        )
        
        return {"message": "Usage reset", "user_id": user_id}
    
    # ==================== User Management ====================
    
    def suspend_user(self, user_id: int, admin_id: int, reason: str = None) -> User:
        """Suspend a user account."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")
        
        user.is_active = False
        self.db.commit()
        
        self._log_action(
            admin_id=admin_id,
            action="user.suspend",
            target_type="user",
            target_id=user_id,
            details={"reason": reason}
        )
        
        return user
    
    def unsuspend_user(self, user_id: int, admin_id: int) -> User:
        """Reactivate a suspended user account."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")
        
        user.is_active = True
        self.db.commit()
        
        self._log_action(
            admin_id=admin_id,
            action="user.unsuspend",
            target_type="user",
            target_id=user_id
        )
        
        return user
    
    def verify_user_email(self, user_id: int, admin_id: int) -> User:
        """Manually verify a user's email."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")
        
        user.is_verified = True
        user.verification_token = None
        self.db.commit()
        
        self._log_action(
            admin_id=admin_id,
            action="user.verify_email",
            target_type="user",
            target_id=user_id
        )
        
        return user
    
    def reset_user_password(self, user_id: int, new_password: str, admin_id: int) -> User:
        """Reset a user's password."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")
        
        user.hashed_password = get_password_hash(new_password)
        user.reset_token = None
        self.db.commit()
        
        self._log_action(
            admin_id=admin_id,
            action="user.reset_password",
            target_type="user",
            target_id=user_id
        )
        
        return user
    
    def delete_user(self, user_id: int, admin_id: int, hard_delete: bool = False) -> Dict[str, Any]:
        """Delete a user account."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")
        
        email = user.email
        
        if hard_delete:
            # Cascade delete will handle related records
            self.db.delete(user)
            action = "user.hard_delete"
        else:
            # Soft delete - just deactivate
            user.is_active = False
            user.email = f"deleted_{user_id}_{user.email}"
            action = "user.soft_delete"
        
        self.db.commit()
        
        self._log_action(
            admin_id=admin_id,
            action=action,
            target_type="user",
            target_id=user_id,
            details={"email": email}
        )
        
        return {"message": "User deleted", "user_id": user_id, "hard_delete": hard_delete}
    
    def bulk_action_users(
        self,
        user_ids: List[int],
        action: str,
        admin_id: int
    ) -> Dict[str, Any]:
        """Perform bulk action on multiple users."""
        valid_actions = ["suspend", "unsuspend", "verify_email"]
        
        if action not in valid_actions:
            raise ValueError(f"Invalid action. Valid actions: {valid_actions}")
        
        success = 0
        failed = 0
        
        for user_id in user_ids:
            try:
                if action == "suspend":
                    self.suspend_user(user_id, admin_id)
                elif action == "unsuspend":
                    self.unsuspend_user(user_id, admin_id)
                elif action == "verify_email":
                    self.verify_user_email(user_id, admin_id)
                success += 1
            except:
                failed += 1
        
        return {
            "action": action,
            "total": len(user_ids),
            "success": success,
            "failed": failed
        }
    
    # ==================== Subscription Management ====================
    
    def change_user_tier(
        self,
        user_id: int,
        new_tier: str,
        admin_id: int,
        duration_days: int = None,
        reason: str = None
    ) -> Subscription:
        """Change a user's subscription tier."""
        valid_tiers = ["free", "creator", "pro", "agency"]
        if new_tier not in valid_tiers:
            raise ValueError(f"Invalid tier. Valid tiers: {valid_tiers}")
        
        subscription = self.db.query(Subscription).filter(
            Subscription.user_id == user_id
        ).first()
        
        old_tier = subscription.tier if subscription else "free"
        
        if subscription:
            subscription.tier = new_tier
            subscription.status = "active"
            if duration_days:
                subscription.current_period_end = datetime.utcnow() + timedelta(days=duration_days)
        else:
            subscription = Subscription(
                user_id=user_id,
                tier=new_tier,
                status="active",
                current_period_start=datetime.utcnow(),
                current_period_end=datetime.utcnow() + timedelta(days=duration_days or 365)
            )
            self.db.add(subscription)
        
        self.db.commit()
        self.db.refresh(subscription)
        
        self._log_action(
            admin_id=admin_id,
            action="subscription.change_tier",
            target_type="user",
            target_id=user_id,
            details={
                "old_tier": old_tier,
                "new_tier": new_tier,
                "duration_days": duration_days,
                "reason": reason
            }
        )
        
        return subscription
    
    def extend_subscription(
        self,
        user_id: int,
        days: int,
        admin_id: int,
        reason: str = None
    ) -> Subscription:
        """Extend a user's subscription period."""
        subscription = self.db.query(Subscription).filter(
            Subscription.user_id == user_id
        ).first()
        
        if not subscription:
            raise ValueError("User has no subscription")
        
        old_end = subscription.current_period_end
        subscription.current_period_end = (old_end or datetime.utcnow()) + timedelta(days=days)
        
        self.db.commit()
        self.db.refresh(subscription)
        
        self._log_action(
            admin_id=admin_id,
            action="subscription.extend",
            target_type="user",
            target_id=user_id,
            details={
                "days_added": days,
                "new_end_date": subscription.current_period_end.isoformat(),
                "reason": reason
            }
        )
        
        return subscription
    
    def cancel_subscription(self, user_id: int, admin_id: int, immediate: bool = False) -> Subscription:
        """Cancel a user's subscription."""
        subscription = self.db.query(Subscription).filter(
            Subscription.user_id == user_id
        ).first()
        
        if not subscription:
            raise ValueError("User has no subscription")
        
        if immediate:
            subscription.status = "cancelled"
            subscription.tier = "free"
        else:
            subscription.cancel_at_period_end = True
        
        self.db.commit()
        self.db.refresh(subscription)
        
        self._log_action(
            admin_id=admin_id,
            action="subscription.cancel",
            target_type="user",
            target_id=user_id,
            details={"immediate": immediate}
        )
        
        return subscription
    
    # ==================== Tier Limits Configuration ====================
    
    def get_tier_limits(self) -> Dict[str, Any]:
        """Get current tier limits configuration."""
        # Check for custom limits in settings
        setting = self.db.query(SystemSetting).filter(
            SystemSetting.key == "tier_limits"
        ).first()
        
        if setting:
            try:
                return json.loads(setting.value)
            except:
                pass
        
        return TIER_LIMITS
    
    def update_tier_limits(self, tier: str, limits: Dict[str, int], admin_id: int) -> Dict[str, Any]:
        """Update limits for a specific tier."""
        current_limits = self.get_tier_limits()
        
        if tier not in current_limits:
            raise ValueError(f"Invalid tier: {tier}")
        
        # Merge new limits
        current_limits[tier].update(limits)
        
        # Save to database
        setting = self.db.query(SystemSetting).filter(
            SystemSetting.key == "tier_limits"
        ).first()
        
        if setting:
            setting.value = json.dumps(current_limits)
            setting.updated_by = admin_id
        else:
            setting = SystemSetting(
                key="tier_limits",
                value=json.dumps(current_limits),
                description="Subscription tier limits",
                updated_by=admin_id
            )
            self.db.add(setting)
        
        self.db.commit()
        
        self._log_action(
            admin_id=admin_id,
            action="tier_limits.update",
            details={"tier": tier, "limits": limits}
        )
        
        return current_limits[tier]
    
    # ==================== System Health ====================
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get system health metrics."""
        now = datetime.utcnow()
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)
        
        # Recent errors (from publishing logs as proxy)
        recent_errors = self.db.query(func.count(PublishingLog.id)).filter(
            PublishingLog.success == False,
            PublishingLog.attempted_at >= hour_ago
        ).scalar() or 0
        
        # Recent successful posts
        recent_success = self.db.query(func.count(PublishingLog.id)).filter(
            PublishingLog.success == True,
            PublishingLog.attempted_at >= hour_ago
        ).scalar() or 0
        
        # Active users (last 24h)
        active_users = self.db.query(func.count(User.id)).filter(
            User.last_login >= day_ago
        ).scalar() or 0
        
        # Pending scheduled posts
        pending_posts = self.db.query(func.count(ScheduledSocialPost.id)).filter(
            ScheduledSocialPost.status == "scheduled",
            ScheduledSocialPost.scheduled_time <= now + timedelta(hours=1)
        ).scalar() or 0
        
        # Database size estimate (row counts)
        table_counts = {
            "users": self.db.query(func.count(User.id)).scalar() or 0,
            "brands": self.db.query(func.count(Brand.id)).scalar() or 0,
            "content": self.db.query(func.count(GeneratedContent.id)).scalar() or 0,
            "social_accounts": self.db.query(func.count(SocialAccount.id)).scalar() or 0,
            "scheduled_posts": self.db.query(func.count(ScheduledSocialPost.id)).scalar() or 0,
        }
        
        # Feature flags status
        maintenance_mode = self.is_feature_enabled("maintenance_mode")
        registration_enabled = self.is_feature_enabled("registration_enabled")
        
        return {
            "status": "healthy" if recent_errors < 10 else "degraded",
            "timestamp": now.isoformat(),
            "metrics": {
                "errors_last_hour": recent_errors,
                "success_last_hour": recent_success,
                "error_rate": round(recent_errors / max(recent_success + recent_errors, 1) * 100, 2),
                "active_users_24h": active_users,
                "pending_posts": pending_posts
            },
            "database": table_counts,
            "flags": {
                "maintenance_mode": maintenance_mode,
                "registration_enabled": registration_enabled
            }
        }
    
    # ==================== Announcements ====================
    
    def create_announcement(
        self,
        title: str,
        message: str,
        announcement_type: str,
        admin_id: int,
        expires_at: datetime = None
    ) -> Dict[str, Any]:
        """Create a system announcement."""
        announcement = {
            "id": int(datetime.utcnow().timestamp()),
            "title": title,
            "message": message,
            "type": announcement_type,  # info, warning, maintenance
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": expires_at.isoformat() if expires_at else None,
            "created_by": admin_id
        }
        
        # Get existing announcements
        setting = self.db.query(SystemSetting).filter(
            SystemSetting.key == "announcements"
        ).first()
        
        announcements = []
        if setting:
            try:
                announcements = json.loads(setting.value)
            except:
                announcements = []
        
        announcements.append(announcement)
        
        # Keep only last 10
        announcements = announcements[-10:]
        
        if setting:
            setting.value = json.dumps(announcements)
        else:
            setting = SystemSetting(
                key="announcements",
                value=json.dumps(announcements),
                description="System announcements"
            )
            self.db.add(setting)
        
        self.db.commit()
        
        return announcement
    
    def get_announcements(self, include_expired: bool = False) -> List[Dict[str, Any]]:
        """Get system announcements."""
        setting = self.db.query(SystemSetting).filter(
            SystemSetting.key == "announcements"
        ).first()
        
        if not setting:
            return []
        
        try:
            announcements = json.loads(setting.value)
        except:
            return []
        
        if not include_expired:
            now = datetime.utcnow().isoformat()
            announcements = [
                a for a in announcements
                if not a.get("expires_at") or a["expires_at"] > now
            ]
        
        return announcements
    
    def delete_announcement(self, announcement_id: int, admin_id: int) -> bool:
        """Delete an announcement."""
        setting = self.db.query(SystemSetting).filter(
            SystemSetting.key == "announcements"
        ).first()
        
        if not setting:
            return False
        
        try:
            announcements = json.loads(setting.value)
            announcements = [a for a in announcements if a.get("id") != announcement_id]
            setting.value = json.dumps(announcements)
            self.db.commit()
            return True
        except:
            return False
    
    # ==================== Content Moderation ====================
    
    def get_flagged_content(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get content that may need moderation."""
        # For now, return recent content for review
        # In production, this would filter by moderation flags
        content = self.db.query(GeneratedContent).order_by(
            desc(GeneratedContent.created_at)
        ).limit(limit).all()
        
        return [
            {
                "id": c.id,
                "user_id": c.user_id,
                "content_type": c.content_type,
                "caption": c.caption[:200] if c.caption else None,
                "result_url": c.result_url,
                "created_at": c.created_at.isoformat()
            }
            for c in content
        ]
    
    def delete_content(self, content_id: int, admin_id: int, reason: str = None) -> bool:
        """Delete content item."""
        content = self.db.query(GeneratedContent).filter(
            GeneratedContent.id == content_id
        ).first()
        
        if not content:
            return False
        
        user_id = content.user_id
        self.db.delete(content)
        self.db.commit()
        
        self._log_action(
            admin_id=admin_id,
            action="content.delete",
            target_type="content",
            target_id=content_id,
            details={"user_id": user_id, "reason": reason}
        )
        
        return True
    
    # ==================== Reports & Analytics ====================
    
    def get_usage_report(self, days: int = 30) -> Dict[str, Any]:
        """Get usage report for the platform."""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Daily signups
        daily_signups = self.db.query(
            func.date(User.created_at).label("date"),
            func.count(User.id).label("count")
        ).filter(
            User.created_at >= start_date
        ).group_by(func.date(User.created_at)).all()
        
        # Daily content
        daily_content = self.db.query(
            func.date(GeneratedContent.created_at).label("date"),
            func.count(GeneratedContent.id).label("count")
        ).filter(
            GeneratedContent.created_at >= start_date
        ).group_by(func.date(GeneratedContent.created_at)).all()
        
        # Revenue by day (if available)
        # This would come from payment records
        
        return {
            "period_days": days,
            "signups": [{"date": str(d.date), "count": d.count} for d in daily_signups],
            "content_generated": [{"date": str(d.date), "count": d.count} for d in daily_content],
            "summary": {
                "total_signups": sum(d.count for d in daily_signups),
                "total_content": sum(d.count for d in daily_content),
            }
        }
    
    # ==================== Helper Methods ====================
    
    def _log_action(
        self,
        admin_id: int,
        action: str,
        target_type: str = None,
        target_id: int = None,
        details: Dict = None,
        ip_address: str = None
    ):
        """Log an admin action."""
        log = AuditLog(
            admin_id=admin_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details,
            ip_address=ip_address
        )
        self.db.add(log)
        self.db.commit()


def get_enhanced_admin_service(db: Session) -> EnhancedAdminService:
    return EnhancedAdminService(db)

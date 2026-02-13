"""
Billing Service

Handles subscription management, usage tracking, and limit enforcement.
"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
import logging

from app.billing.models import (
    Subscription, Payment, UsageRecord, Coupon,
    SubscriptionTier, SubscriptionStatus, PaymentStatus,
    PLAN_LIMITS
)
from app.models.user import User

logger = logging.getLogger(__name__)


class BillingService:
    """Service for billing and subscription operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ==================== Subscription Management ====================
    
    def get_or_create_subscription(self, user_id: int) -> Subscription:
        """Get existing subscription or create a free one"""
        subscription = self.db.query(Subscription).filter(
            Subscription.user_id == user_id
        ).first()
        
        if not subscription:
            subscription = Subscription(
                user_id=user_id,
                tier=SubscriptionTier.FREE,
                status=SubscriptionStatus.ACTIVE,
                generations_used=0,
                generations_reset_at=datetime.utcnow()
            )
            self.db.add(subscription)
            self.db.commit()
            self.db.refresh(subscription)
        
        return subscription
    
    def get_user_limits(self, user_id: int) -> Dict[str, Any]:
        """Get current limits for user based on subscription tier"""
        subscription = self.get_or_create_subscription(user_id)
        tier_limits = PLAN_LIMITS.get(subscription.tier, PLAN_LIMITS[SubscriptionTier.FREE])
        
        return {
            "tier": subscription.tier.value,
            "tier_name": tier_limits.get("name", "Free"),
            "status": subscription.status.value,
            **tier_limits
        }
    
    def get_user_usage(self, user_id: int) -> Dict[str, int]:
        """Get current usage counts for user"""
        subscription = self.get_or_create_subscription(user_id)
        
        # Check if usage needs reset (monthly)
        self._check_usage_reset(subscription)
        
        # Count resources
        from app.models import Brand, SocialAccount
        
        brands_count = self.db.query(Brand).filter(Brand.user_id == user_id).count()
        
        try:
            social_accounts_count = self.db.query(SocialAccount).filter(
                SocialAccount.user_id == user_id
            ).count()
        except:
            social_accounts_count = 0
        
        try:
            from app.lora.models import LoraModel
            lora_count = self.db.query(LoraModel).filter(
                LoraModel.user_id == user_id
            ).count()
        except:
            lora_count = 0
        
        try:
            from app.models import ScheduledPost
            scheduled_count = self.db.query(ScheduledPost).filter(
                ScheduledPost.user_id == user_id,
                ScheduledPost.status == 'pending'
            ).count()
        except:
            scheduled_count = 0
        
        return {
            "generations_used": subscription.generations_used,
            "brands_count": brands_count,
            "social_accounts_count": social_accounts_count,
            "lora_models_count": lora_count,
            "scheduled_posts_count": scheduled_count
        }
    
    # ==================== Limit Checking ====================
    
    def check_generation_limit(self, user_id: int) -> Dict[str, Any]:
        """Check if user can generate more content"""
        subscription = self.get_or_create_subscription(user_id)
        self._check_usage_reset(subscription)
        
        limits = PLAN_LIMITS.get(subscription.tier, PLAN_LIMITS[SubscriptionTier.FREE])
        max_generations = limits.get("generations_per_month", 10)
        
        if max_generations == -1:  # Unlimited
            return {
                "allowed": True,
                "used": subscription.generations_used,
                "limit": "unlimited",
                "remaining": "unlimited"
            }
        
        allowed = subscription.generations_used < max_generations
        
        return {
            "allowed": allowed,
            "used": subscription.generations_used,
            "limit": max_generations,
            "remaining": max(0, max_generations - subscription.generations_used),
            "message": None if allowed else f"You've reached your monthly limit of {max_generations} generations. Upgrade to continue."
        }
    
    def check_brand_limit(self, user_id: int) -> Dict[str, Any]:
        """Check if user can create more brands"""
        from app.models import Brand
        
        limits = self.get_user_limits(user_id)
        max_brands = limits.get("brands", 1)
        
        current_count = self.db.query(Brand).filter(Brand.user_id == user_id).count()
        allowed = current_count < max_brands
        
        return {
            "allowed": allowed,
            "used": current_count,
            "limit": max_brands,
            "remaining": max(0, max_brands - current_count),
            "message": None if allowed else f"You've reached your limit of {max_brands} brands. Upgrade to create more."
        }
    
    def check_lora_limit(self, user_id: int) -> Dict[str, Any]:
        """Check if user can create more LoRA avatars"""
        limits = self.get_user_limits(user_id)
        max_lora = limits.get("lora_models", 0)
        
        try:
            from app.lora.models import LoraModel
            current_count = self.db.query(LoraModel).filter(
                LoraModel.user_id == user_id
            ).count()
        except:
            current_count = 0
        
        allowed = current_count < max_lora
        
        return {
            "allowed": allowed,
            "used": current_count,
            "limit": max_lora,
            "remaining": max(0, max_lora - current_count),
            "message": None if allowed else f"You've reached your limit of {max_lora} avatars. Upgrade to create more."
        }
    
    def check_social_account_limit(self, user_id: int) -> Dict[str, Any]:
        """Check if user can connect more social accounts"""
        limits = self.get_user_limits(user_id)
        max_accounts = limits.get("social_accounts", 0)
        
        try:
            from app.models import SocialAccount
            current_count = self.db.query(SocialAccount).filter(
                SocialAccount.user_id == user_id
            ).count()
        except:
            current_count = 0
        
        allowed = current_count < max_accounts
        
        return {
            "allowed": allowed,
            "used": current_count,
            "limit": max_accounts,
            "remaining": max(0, max_accounts - current_count),
            "message": None if allowed else f"You've reached your limit of {max_accounts} social accounts. Upgrade to connect more."
        }
    
    def check_scheduled_post_limit(self, user_id: int) -> Dict[str, Any]:
        """Check if user can schedule more posts"""
        limits = self.get_user_limits(user_id)
        max_scheduled = limits.get("scheduled_posts", 0)
        
        if max_scheduled == -1:  # Unlimited
            return {
                "allowed": True,
                "used": 0,
                "limit": "unlimited",
                "remaining": "unlimited"
            }
        
        try:
            from app.models import ScheduledPost
            current_count = self.db.query(ScheduledPost).filter(
                ScheduledPost.user_id == user_id,
                ScheduledPost.status == 'pending'
            ).count()
        except:
            current_count = 0
        
        allowed = current_count < max_scheduled
        
        return {
            "allowed": allowed,
            "used": current_count,
            "limit": max_scheduled,
            "remaining": max(0, max_scheduled - current_count),
            "message": None if allowed else f"You've reached your limit of {max_scheduled} scheduled posts. Upgrade to schedule more."
        }
    
    # ==================== Usage Recording ====================
    
    def record_generation(self, user_id: int, count: int = 1) -> bool:
        """Record generation usage"""
        subscription = self.get_or_create_subscription(user_id)
        self._check_usage_reset(subscription)
        
        subscription.generations_used += count
        self.db.commit()
        
        # Create usage record
        self._create_usage_record(
            subscription_id=subscription.id,
            user_id=user_id,
            usage_type="generation",
            quantity=count
        )
        
        return True
    
    def record_lora_training(self, user_id: int, cost_usd: float = 0) -> bool:
        """Record LoRA training usage"""
        subscription = self.get_or_create_subscription(user_id)
        
        self._create_usage_record(
            subscription_id=subscription.id,
            user_id=user_id,
            usage_type="lora_training",
            quantity=1,
            usage_metadata={"cost_usd": cost_usd}
        )
        
        return True
    
    def record_scheduled_post(self, user_id: int) -> bool:
        """Record scheduled post usage"""
        subscription = self.get_or_create_subscription(user_id)
        
        self._create_usage_record(
            subscription_id=subscription.id,
            user_id=user_id,
            usage_type="scheduled_post",
            quantity=1
        )
        
        return True
    
    # ==================== Dashboard / Stats ====================
    
    def get_usage_dashboard(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive usage dashboard data"""
        limits = self.get_user_limits(user_id)
        usage = self.get_user_usage(user_id)
        
        # Calculate percentages
        def calc_percent(used, limit):
            if limit == "unlimited" or limit == -1:
                return 0
            if limit == 0:
                return 100 if used > 0 else 0
            return min(100, round((used / limit) * 100))
        
        return {
            "subscription": {
                "tier": limits["tier"],
                "tier_name": limits["tier_name"],
                "status": limits["status"]
            },
            "usage": {
                "generations": {
                    "used": usage["generations_used"],
                    "limit": limits["generations_per_month"],
                    "percent": calc_percent(usage["generations_used"], limits["generations_per_month"])
                },
                "brands": {
                    "used": usage["brands_count"],
                    "limit": limits["brands"],
                    "percent": calc_percent(usage["brands_count"], limits["brands"])
                },
                "social_accounts": {
                    "used": usage["social_accounts_count"],
                    "limit": limits["social_accounts"],
                    "percent": calc_percent(usage["social_accounts_count"], limits["social_accounts"])
                },
                "avatars": {
                    "used": usage["lora_models_count"],
                    "limit": limits["lora_models"],
                    "percent": calc_percent(usage["lora_models_count"], limits["lora_models"])
                },
                "scheduled_posts": {
                    "used": usage["scheduled_posts_count"],
                    "limit": limits["scheduled_posts"],
                    "percent": calc_percent(usage["scheduled_posts_count"], limits["scheduled_posts"])
                }
            },
            "features": limits.get("features", []),
            "upgrade_available": limits["tier"] != "agency"
        }
    
    # ==================== Helper Methods ====================
    
    def _check_usage_reset(self, subscription: Subscription):
        """Reset usage counters if new billing period"""
        if subscription.generations_reset_at is None:
            subscription.generations_reset_at = datetime.utcnow()
            subscription.generations_used = 0
            self.db.commit()
            return
        
        # Check if 30 days have passed since last reset
        days_since_reset = (datetime.utcnow() - subscription.generations_reset_at).days
        if days_since_reset >= 30:
            subscription.generations_used = 0
            subscription.generations_reset_at = datetime.utcnow()
            self.db.commit()
            logger.info(f"Reset usage counters for user {subscription.user_id}")
    
    def _create_usage_record(
        self,
        subscription_id: int,
        user_id: int,
        usage_type: str,
        quantity: int = 1,
        usage_metadata: Optional[Dict] = None
    ):
        """Create a usage record for tracking"""
        try:
            record = UsageRecord(
                subscription_id=subscription_id,
                user_id=user_id,
                usage_type=usage_type,
                quantity=quantity,
                usage_metadata=usage_metadata
            )
            self.db.add(record)
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to create usage record: {e}")
            # Don't fail the main operation if usage tracking fails
    
    # ==================== Plan Upgrade ====================
    
    def can_upgrade_to(self, user_id: int, target_tier: SubscriptionTier) -> Dict[str, Any]:
        """Check if user can upgrade to a specific tier"""
        subscription = self.get_or_create_subscription(user_id)
        
        tier_order = [SubscriptionTier.FREE, SubscriptionTier.CREATOR, 
                      SubscriptionTier.PRO, SubscriptionTier.AGENCY]
        
        current_index = tier_order.index(subscription.tier)
        target_index = tier_order.index(target_tier)
        
        if target_index <= current_index:
            return {
                "allowed": False,
                "reason": "Target tier is same or lower than current tier"
            }
        
        target_limits = PLAN_LIMITS.get(target_tier)
        
        return {
            "allowed": True,
            "current_tier": subscription.tier.value,
            "target_tier": target_tier.value,
            "price_monthly": target_limits.get("price_monthly", 0),
            "new_features": target_limits.get("features", [])
        }
    
    def get_available_plans(self) -> Dict[str, Any]:
        """Get all available subscription plans"""
        plans = []
        for tier, limits in PLAN_LIMITS.items():
            plans.append({
                "tier": tier.value,
                "name": limits["name"],
                "price_monthly": limits["price_monthly"],
                "features": limits["features"],
                "limits": {
                    "generations_per_month": limits["generations_per_month"],
                    "brands": limits["brands"],
                    "lora_models": limits["lora_models"],
                    "social_accounts": limits["social_accounts"],
                    "scheduled_posts": limits["scheduled_posts"]
                }
            })
        return {"plans": plans}


# Factory function
def get_billing_service(db: Session) -> BillingService:
    return BillingService(db)

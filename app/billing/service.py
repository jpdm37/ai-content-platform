"""
Stripe Billing Service

Handles:
- Customer creation
- Subscription management
- Checkout sessions
- Billing portal
- Webhooks
- Usage tracking
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import stripe
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.config import get_settings
from app.models.user import User
from app.billing.models import (
    Subscription, Payment, UsageRecord, Coupon,
    SubscriptionTier, SubscriptionStatus, PaymentStatus,
    PLAN_LIMITS
)

logger = logging.getLogger(__name__)
settings = get_settings()

# Initialize Stripe
if settings.stripe_secret_key:
    stripe.api_key = settings.stripe_secret_key


class BillingService:
    """Service for managing subscriptions and billing via Stripe"""
    
    def __init__(self, db: Session):
        self.db = db
        
        # Map tiers to Stripe price IDs
        self.price_ids = {
            SubscriptionTier.CREATOR: settings.stripe_price_id_creator,
            SubscriptionTier.PRO: settings.stripe_price_id_pro,
            SubscriptionTier.AGENCY: settings.stripe_price_id_agency,
        }
    
    # ==================== Customer Management ====================
    
    def get_or_create_customer(self, user: User) -> str:
        """Get or create Stripe customer for user"""
        subscription = self.db.query(Subscription).filter(
            Subscription.user_id == user.id
        ).first()
        
        if subscription and subscription.stripe_customer_id:
            return subscription.stripe_customer_id
        
        # Create Stripe customer
        customer = stripe.Customer.create(
            email=user.email,
            name=user.full_name,
            metadata={"user_id": str(user.id)}
        )
        
        # Create or update subscription record
        if not subscription:
            subscription = Subscription(
                user_id=user.id,
                tier=SubscriptionTier.FREE,
                status=SubscriptionStatus.ACTIVE,
                stripe_customer_id=customer.id
            )
            self.db.add(subscription)
        else:
            subscription.stripe_customer_id = customer.id
        
        self.db.commit()
        return customer.id
    
    def get_subscription(self, user: User) -> Optional[Subscription]:
        """Get user's subscription"""
        return self.db.query(Subscription).filter(
            Subscription.user_id == user.id
        ).first()
    
    def ensure_subscription(self, user: User) -> Subscription:
        """Ensure user has a subscription record (at least free tier)"""
        subscription = self.get_subscription(user)
        if not subscription:
            subscription = Subscription(
                user_id=user.id,
                tier=SubscriptionTier.FREE,
                status=SubscriptionStatus.ACTIVE
            )
            self.db.add(subscription)
            self.db.commit()
            self.db.refresh(subscription)
        return subscription
    
    # ==================== Checkout ====================
    
    def create_checkout_session(
        self,
        user: User,
        tier: SubscriptionTier,
        success_url: str,
        cancel_url: str,
        coupon_code: Optional[str] = None
    ) -> Dict[str, str]:
        """Create Stripe checkout session for subscription"""
        if tier == SubscriptionTier.FREE:
            raise ValueError("Cannot checkout for free tier")
        
        price_id = self.price_ids.get(tier)
        if not price_id:
            raise ValueError(f"No price configured for tier: {tier}")
        
        customer_id = self.get_or_create_customer(user)
        
        # Build checkout params
        checkout_params = {
            "customer": customer_id,
            "payment_method_types": ["card"],
            "line_items": [{
                "price": price_id,
                "quantity": 1,
            }],
            "mode": "subscription",
            "success_url": success_url + "?session_id={CHECKOUT_SESSION_ID}",
            "cancel_url": cancel_url,
            "subscription_data": {
                "metadata": {
                    "user_id": str(user.id),
                    "tier": tier.value
                }
            },
            "allow_promotion_codes": True,
            "billing_address_collection": "auto",
        }
        
        # Apply coupon if provided
        if coupon_code:
            coupon = self._validate_coupon(coupon_code, tier)
            if coupon and coupon.stripe_coupon_id:
                checkout_params["discounts"] = [{"coupon": coupon.stripe_coupon_id}]
        
        session = stripe.checkout.Session.create(**checkout_params)
        
        return {
            "checkout_url": session.url,
            "session_id": session.id
        }
    
    def create_billing_portal_session(
        self,
        user: User,
        return_url: str
    ) -> str:
        """Create Stripe billing portal session"""
        subscription = self.get_subscription(user)
        if not subscription or not subscription.stripe_customer_id:
            raise ValueError("No billing account found")
        
        session = stripe.billing_portal.Session.create(
            customer=subscription.stripe_customer_id,
            return_url=return_url
        )
        
        return session.url
    
    # ==================== Subscription Management ====================
    
    def change_plan(
        self,
        user: User,
        new_tier: SubscriptionTier,
        prorate: bool = True
    ) -> Dict[str, Any]:
        """Change subscription plan (upgrade/downgrade)"""
        subscription = self.get_subscription(user)
        if not subscription or not subscription.stripe_subscription_id:
            raise ValueError("No active subscription to change")
        
        if new_tier == SubscriptionTier.FREE:
            # Downgrade to free = cancel
            return self.cancel_subscription(user)
        
        new_price_id = self.price_ids.get(new_tier)
        if not new_price_id:
            raise ValueError(f"No price configured for tier: {new_tier}")
        
        # Get current Stripe subscription
        stripe_sub = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
        
        # Update subscription
        updated_sub = stripe.Subscription.modify(
            subscription.stripe_subscription_id,
            items=[{
                "id": stripe_sub["items"]["data"][0]["id"],
                "price": new_price_id,
            }],
            proration_behavior="create_prorations" if prorate else "none",
            metadata={"tier": new_tier.value}
        )
        
        # Update local record
        subscription.tier = new_tier
        subscription.stripe_price_id = new_price_id
        self.db.commit()
        
        return {
            "success": True,
            "message": f"Plan changed to {new_tier.value}",
            "new_tier": new_tier,
            "effective_date": datetime.utcnow()
        }
    
    def cancel_subscription(
        self,
        user: User,
        at_period_end: bool = True
    ) -> Dict[str, Any]:
        """Cancel subscription"""
        subscription = self.get_subscription(user)
        if not subscription or not subscription.stripe_subscription_id:
            raise ValueError("No active subscription to cancel")
        
        if at_period_end:
            # Cancel at end of period
            stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=True
            )
            subscription.cancel_at_period_end = True
        else:
            # Cancel immediately
            stripe.Subscription.delete(subscription.stripe_subscription_id)
            subscription.status = SubscriptionStatus.CANCELED
            subscription.canceled_at = datetime.utcnow()
            subscription.tier = SubscriptionTier.FREE
        
        self.db.commit()
        
        return {
            "success": True,
            "message": "Subscription cancelled",
            "effective_date": subscription.current_period_end if at_period_end else datetime.utcnow()
        }
    
    def reactivate_subscription(self, user: User) -> Dict[str, Any]:
        """Reactivate a subscription that's set to cancel"""
        subscription = self.get_subscription(user)
        if not subscription or not subscription.stripe_subscription_id:
            raise ValueError("No subscription to reactivate")
        
        if not subscription.cancel_at_period_end:
            raise ValueError("Subscription is not set to cancel")
        
        stripe.Subscription.modify(
            subscription.stripe_subscription_id,
            cancel_at_period_end=False
        )
        
        subscription.cancel_at_period_end = False
        self.db.commit()
        
        return {"success": True, "message": "Subscription reactivated"}
    
    # ==================== Webhook Handling ====================
    
    def handle_webhook(self, payload: bytes, sig_header: str) -> Dict[str, Any]:
        """Handle Stripe webhook events"""
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.stripe_webhook_secret
            )
        except ValueError:
            raise ValueError("Invalid payload")
        except stripe.error.SignatureVerificationError:
            raise ValueError("Invalid signature")
        
        event_type = event["type"]
        data = event["data"]["object"]
        
        handlers = {
            "checkout.session.completed": self._handle_checkout_completed,
            "customer.subscription.created": self._handle_subscription_created,
            "customer.subscription.updated": self._handle_subscription_updated,
            "customer.subscription.deleted": self._handle_subscription_deleted,
            "invoice.paid": self._handle_invoice_paid,
            "invoice.payment_failed": self._handle_payment_failed,
        }
        
        handler = handlers.get(event_type)
        if handler:
            return handler(data)
        
        return {"received": True, "handled": False}
    
    def _handle_checkout_completed(self, session: dict) -> Dict:
        """Handle successful checkout"""
        customer_id = session.get("customer")
        subscription_id = session.get("subscription")
        
        if not subscription_id:
            return {"handled": False, "reason": "No subscription in session"}
        
        # Find user by customer ID
        subscription = self.db.query(Subscription).filter(
            Subscription.stripe_customer_id == customer_id
        ).first()
        
        if subscription:
            subscription.stripe_subscription_id = subscription_id
            self.db.commit()
        
        return {"handled": True}
    
    def _handle_subscription_created(self, stripe_sub: dict) -> Dict:
        """Handle new subscription"""
        return self._sync_subscription(stripe_sub)
    
    def _handle_subscription_updated(self, stripe_sub: dict) -> Dict:
        """Handle subscription update"""
        return self._sync_subscription(stripe_sub)
    
    def _handle_subscription_deleted(self, stripe_sub: dict) -> Dict:
        """Handle subscription cancellation"""
        subscription = self.db.query(Subscription).filter(
            Subscription.stripe_subscription_id == stripe_sub["id"]
        ).first()
        
        if subscription:
            subscription.status = SubscriptionStatus.CANCELED
            subscription.tier = SubscriptionTier.FREE
            subscription.canceled_at = datetime.utcnow()
            self.db.commit()
        
        return {"handled": True}
    
    def _handle_invoice_paid(self, invoice: dict) -> Dict:
        """Handle successful payment"""
        subscription = self.db.query(Subscription).filter(
            Subscription.stripe_customer_id == invoice.get("customer")
        ).first()
        
        if subscription:
            # Record payment
            payment = Payment(
                subscription_id=subscription.id,
                user_id=subscription.user_id,
                stripe_invoice_id=invoice["id"],
                stripe_payment_intent_id=invoice.get("payment_intent"),
                amount=invoice["amount_paid"],
                currency=invoice["currency"],
                status=PaymentStatus.SUCCEEDED,
                paid_at=datetime.utcnow()
            )
            self.db.add(payment)
            
            # Reset usage on new billing period
            subscription.generations_used = 0
            subscription.generations_reset_at = datetime.utcnow()
            
            self.db.commit()
        
        return {"handled": True}
    
    def _handle_payment_failed(self, invoice: dict) -> Dict:
        """Handle failed payment"""
        subscription = self.db.query(Subscription).filter(
            Subscription.stripe_customer_id == invoice.get("customer")
        ).first()
        
        if subscription:
            subscription.status = SubscriptionStatus.PAST_DUE
            
            payment = Payment(
                subscription_id=subscription.id,
                user_id=subscription.user_id,
                stripe_invoice_id=invoice["id"],
                amount=invoice["amount_due"],
                currency=invoice["currency"],
                status=PaymentStatus.FAILED
            )
            self.db.add(payment)
            self.db.commit()
        
        return {"handled": True}
    
    def _sync_subscription(self, stripe_sub: dict) -> Dict:
        """Sync Stripe subscription to local database"""
        subscription = self.db.query(Subscription).filter(
            Subscription.stripe_subscription_id == stripe_sub["id"]
        ).first()
        
        if not subscription:
            subscription = self.db.query(Subscription).filter(
                Subscription.stripe_customer_id == stripe_sub["customer"]
            ).first()
        
        if not subscription:
            return {"handled": False, "reason": "Subscription not found"}
        
        # Map Stripe status
        status_map = {
            "active": SubscriptionStatus.ACTIVE,
            "past_due": SubscriptionStatus.PAST_DUE,
            "canceled": SubscriptionStatus.CANCELED,
            "incomplete": SubscriptionStatus.INCOMPLETE,
            "trialing": SubscriptionStatus.TRIALING,
            "unpaid": SubscriptionStatus.UNPAID,
        }
        
        # Get tier from metadata or price
        tier_str = stripe_sub.get("metadata", {}).get("tier", "creator")
        tier = SubscriptionTier(tier_str) if tier_str in [t.value for t in SubscriptionTier] else SubscriptionTier.CREATOR
        
        # Update subscription
        subscription.stripe_subscription_id = stripe_sub["id"]
        subscription.tier = tier
        subscription.status = status_map.get(stripe_sub["status"], SubscriptionStatus.ACTIVE)
        subscription.current_period_start = datetime.fromtimestamp(stripe_sub["current_period_start"])
        subscription.current_period_end = datetime.fromtimestamp(stripe_sub["current_period_end"])
        subscription.cancel_at_period_end = stripe_sub.get("cancel_at_period_end", False)
        
        if stripe_sub.get("trial_end"):
            subscription.trial_end = datetime.fromtimestamp(stripe_sub["trial_end"])
        
        self.db.commit()
        return {"handled": True}
    
    # ==================== Usage Tracking ====================
    
    def check_limit(self, user: User, feature: str) -> Dict[str, Any]:
        """Check if user is within limits for a feature"""
        subscription = self.ensure_subscription(user)
        limits = PLAN_LIMITS.get(subscription.tier, PLAN_LIMITS[SubscriptionTier.FREE])
        
        # Count current usage
        if feature == "generations":
            used = subscription.generations_used
            limit = limits["generations_per_month"]
        elif feature == "brands":
            from app.models import Brand
            used = self.db.query(Brand).filter(Brand.user_id == user.id).count()
            limit = limits["brands"]
        elif feature == "lora_models":
            from app.lora.models import LoraModel
            used = self.db.query(LoraModel).filter(LoraModel.user_id == user.id).count()
            limit = limits["lora_models"]
        elif feature == "social_accounts":
            from app.social.models import SocialAccount
            used = self.db.query(SocialAccount).filter(SocialAccount.user_id == user.id).count()
            limit = limits["social_accounts"]
        else:
            return {"allowed": True, "used": 0, "limit": -1}
        
        allowed = limit == -1 or used < limit
        
        return {
            "allowed": allowed,
            "used": used,
            "limit": limit,
            "remaining": max(0, limit - used) if limit != -1 else -1
        }
    
    def record_usage(
        self,
        user: User,
        usage_type: str,
        quantity: int = 1,
        metadata: Optional[Dict] = None
    ):
        """Record feature usage"""
        subscription = self.ensure_subscription(user)
        
        # Update generation count
        if usage_type == "generation":
            subscription.generations_used += quantity
        
        # Create usage record
        record = UsageRecord(
            subscription_id=subscription.id,
            user_id=user.id,
            usage_type=usage_type,
            quantity=quantity,
            metadata=metadata
        )
        self.db.add(record)
        self.db.commit()
    
    def get_usage_summary(self, user: User) -> Dict[str, Any]:
        """Get user's usage summary"""
        subscription = self.ensure_subscription(user)
        limits = PLAN_LIMITS.get(subscription.tier, PLAN_LIMITS[SubscriptionTier.FREE])
        
        from app.models import Brand
        from app.lora.models import LoraModel
        
        brands_count = self.db.query(Brand).filter(Brand.user_id == user.id).count()
        lora_count = self.db.query(LoraModel).filter(LoraModel.user_id == user.id).count()
        
        # Try to get social accounts count
        try:
            from app.social.models import SocialAccount, ScheduledPost
            social_count = self.db.query(SocialAccount).filter(SocialAccount.user_id == user.id).count()
            scheduled_count = self.db.query(ScheduledPost).filter(
                ScheduledPost.user_id == user.id,
                ScheduledPost.status == "scheduled"
            ).count()
        except:
            social_count = 0
            scheduled_count = 0
        
        return {
            "generations_used": subscription.generations_used,
            "generations_limit": limits["generations_per_month"],
            "generations_remaining": max(0, limits["generations_per_month"] - subscription.generations_used),
            "brands_used": brands_count,
            "brands_limit": limits["brands"],
            "lora_models_used": lora_count,
            "lora_models_limit": limits["lora_models"],
            "social_accounts_used": social_count,
            "social_accounts_limit": limits["social_accounts"],
            "scheduled_posts_used": scheduled_count,
            "scheduled_posts_limit": limits["scheduled_posts"],
            "reset_date": subscription.current_period_end
        }
    
    # ==================== Coupons ====================
    
    def _validate_coupon(
        self,
        code: str,
        tier: SubscriptionTier
    ) -> Optional[Coupon]:
        """Validate a coupon code"""
        coupon = self.db.query(Coupon).filter(
            Coupon.code == code.upper(),
            Coupon.is_active == True
        ).first()
        
        if not coupon:
            return None
        
        # Check validity
        now = datetime.utcnow()
        if coupon.valid_until and coupon.valid_until < now:
            return None
        
        if coupon.max_redemptions and coupon.times_redeemed >= coupon.max_redemptions:
            return None
        
        # Check tier restriction
        if coupon.applicable_tiers:
            if tier.value not in coupon.applicable_tiers:
                return None
        
        return coupon
    
    def apply_coupon(self, code: str, tier: SubscriptionTier) -> Dict[str, Any]:
        """Validate and return coupon details"""
        coupon = self._validate_coupon(code, tier)
        
        if not coupon:
            return {
                "valid": False,
                "message": "Invalid or expired coupon code"
            }
        
        return {
            "valid": True,
            "code": coupon.code,
            "percent_off": coupon.percent_off,
            "amount_off": coupon.amount_off,
            "duration": coupon.duration,
            "message": f"Coupon applied: {coupon.percent_off}% off" if coupon.percent_off else f"Coupon applied: ${coupon.amount_off/100} off"
        }


def get_billing_service(db: Session) -> BillingService:
    return BillingService(db)

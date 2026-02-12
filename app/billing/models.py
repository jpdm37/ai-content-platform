"""
Billing and Subscription Database Models

Updated FREE tier limits to allow basic functionality for testing/demo.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey,
    Boolean, Float, Enum, JSON, BigInteger
)
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class SubscriptionTier(enum.Enum):
    """Subscription tiers"""
    FREE = "free"
    CREATOR = "creator"
    PRO = "pro"
    AGENCY = "agency"


class SubscriptionStatus(enum.Enum):
    """Subscription status"""
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"
    TRIALING = "trialing"
    UNPAID = "unpaid"


class PaymentStatus(enum.Enum):
    """Payment status"""
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"


# Plan limits configuration
# Updated FREE tier to allow basic testing/demo functionality
PLAN_LIMITS = {
    SubscriptionTier.FREE: {
        "name": "Free",
        "price_monthly": 0,
        "generations_per_month": 50,     # Increased from 10
        "brands": 2,                      # Increased from 1
        "lora_models": 1,                 # Increased from 0 - allow 1 avatar
        "scheduled_posts": 10,            # Increased from 0
        "social_accounts": 2,             # Increased from 0 - allow 2 accounts
        "team_members": 1,
        "api_access": False,
        "priority_support": False,
        "features": [
            "50 generations/month",
            "2 brands",
            "1 AI avatar",
            "2 social accounts",
            "10 scheduled posts",
            "Community support"
        ]
    },
    SubscriptionTier.CREATOR: {
        "name": "Creator",
        "price_monthly": 19,
        "generations_per_month": 200,
        "brands": 3,
        "lora_models": 1,
        "scheduled_posts": 50,
        "social_accounts": 3,
        "team_members": 1,
        "api_access": False,
        "priority_support": False,
        "features": [
            "200 generations/month",
            "3 brands",
            "1 LoRA avatar",
            "3 social accounts",
            "50 scheduled posts",
            "Basic analytics"
        ]
    },
    SubscriptionTier.PRO: {
        "name": "Pro",
        "price_monthly": 49,
        "generations_per_month": 1000,
        "brands": 10,
        "lora_models": 5,
        "scheduled_posts": 500,
        "social_accounts": 10,
        "team_members": 3,
        "api_access": True,
        "priority_support": True,
        "features": [
            "1,000 generations/month",
            "10 brands",
            "5 LoRA avatars",
            "10 social accounts",
            "Unlimited scheduled posts",
            "Advanced analytics",
            "API access",
            "Priority support"
        ]
    },
    SubscriptionTier.AGENCY: {
        "name": "Agency",
        "price_monthly": 149,
        "generations_per_month": 5000,
        "brands": 50,
        "lora_models": 20,
        "scheduled_posts": -1,  # Unlimited
        "social_accounts": 50,
        "team_members": 10,
        "api_access": True,
        "priority_support": True,
        "features": [
            "5,000 generations/month",
            "50 brands",
            "20 LoRA avatars",
            "50 social accounts",
            "Unlimited scheduling",
            "White-label reports",
            "Team collaboration",
            "Dedicated support",
            "Custom integrations"
        ]
    }
}


class Subscription(Base):
    """User subscription"""
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    
    # Subscription details
    tier = Column(Enum(SubscriptionTier), default=SubscriptionTier.FREE)
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE)
    
    # Stripe IDs
    stripe_customer_id = Column(String(255), nullable=True, index=True)
    stripe_subscription_id = Column(String(255), nullable=True, unique=True)
    stripe_price_id = Column(String(255), nullable=True)
    
    # Billing cycle
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    cancel_at_period_end = Column(Boolean, default=False)
    canceled_at = Column(DateTime, nullable=True)
    
    # Trial
    trial_start = Column(DateTime, nullable=True)
    trial_end = Column(DateTime, nullable=True)
    
    # Usage tracking
    generations_used = Column(Integer, default=0)
    generations_reset_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", backref="subscription")
    payments = relationship("Payment", back_populates="subscription", cascade="all, delete-orphan")
    usage_records = relationship("UsageRecord", back_populates="subscription", cascade="all, delete-orphan")


class Payment(Base):
    """Payment history"""
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, ForeignKey('subscriptions.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    # Stripe IDs
    stripe_payment_intent_id = Column(String(255), nullable=True, unique=True)
    stripe_invoice_id = Column(String(255), nullable=True)
    stripe_charge_id = Column(String(255), nullable=True)
    
    # Payment details
    amount = Column(Integer, nullable=False)  # In cents
    currency = Column(String(3), default="usd")
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    
    # Description
    description = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)
    
    # Relationships
    subscription = relationship("Subscription", back_populates="payments")
    user = relationship("User")


class UsageRecord(Base):
    """Track feature usage for billing"""
    __tablename__ = "usage_records"
    
    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, ForeignKey('subscriptions.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    # Usage type
    usage_type = Column(String(50), nullable=False)  # generation, lora_training, scheduled_post, etc.
    quantity = Column(Integer, default=1)
    
    # Cost tracking
    cost_credits = Column(Integer, default=1)  # Internal credit cost
    
    # Metadata
    metadata = Column(JSON, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    subscription = relationship("Subscription", back_populates="usage_records")
    user = relationship("User")


class Coupon(Base):
    """Discount coupons"""
    __tablename__ = "coupons"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    
    # Discount
    percent_off = Column(Integer, nullable=True)  # 10 = 10% off
    amount_off = Column(Integer, nullable=True)   # In cents
    
    # Limits
    max_redemptions = Column(Integer, nullable=True)
    times_redeemed = Column(Integer, default=0)
    
    # Duration
    duration = Column(String(20), default="once")  # once, forever, repeating
    duration_months = Column(Integer, nullable=True)
    
    # Validity
    valid_from = Column(DateTime, default=datetime.utcnow)
    valid_until = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Restrictions
    applicable_tiers = Column(JSON, nullable=True)  # List of tier names
    
    # Stripe
    stripe_coupon_id = Column(String(255), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

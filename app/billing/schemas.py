"""
Billing and Subscription Pydantic Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class SubscriptionTierEnum(str, Enum):
    FREE = "free"
    CREATOR = "creator"
    PRO = "pro"
    AGENCY = "agency"


class SubscriptionStatusEnum(str, Enum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"
    TRIALING = "trialing"
    UNPAID = "unpaid"


# ========== Plan Schemas ==========

class PlanFeatures(BaseModel):
    generations_per_month: int
    brands: int
    lora_models: int
    scheduled_posts: int
    social_accounts: int
    team_members: int
    api_access: bool
    priority_support: bool
    features: List[str]


class PlanResponse(BaseModel):
    tier: SubscriptionTierEnum
    name: str
    price_monthly: int
    features: PlanFeatures
    stripe_price_id: Optional[str] = None


class PlansListResponse(BaseModel):
    plans: List[PlanResponse]


# ========== Subscription Schemas ==========

class SubscriptionResponse(BaseModel):
    id: int
    tier: SubscriptionTierEnum
    status: SubscriptionStatusEnum
    current_period_start: Optional[datetime]
    current_period_end: Optional[datetime]
    cancel_at_period_end: bool
    trial_end: Optional[datetime]
    generations_used: int
    generations_limit: int
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class SubscriptionDetailResponse(SubscriptionResponse):
    stripe_customer_id: Optional[str]
    stripe_subscription_id: Optional[str]
    plan: PlanFeatures


class UsageSummary(BaseModel):
    generations_used: int
    generations_limit: int
    generations_remaining: int
    brands_used: int
    brands_limit: int
    lora_models_used: int
    lora_models_limit: int
    scheduled_posts_used: int
    scheduled_posts_limit: int
    social_accounts_used: int
    social_accounts_limit: int
    reset_date: Optional[datetime]


# ========== Checkout Schemas ==========

class CreateCheckoutRequest(BaseModel):
    tier: SubscriptionTierEnum
    success_url: str
    cancel_url: str
    coupon_code: Optional[str] = None


class CheckoutSessionResponse(BaseModel):
    checkout_url: str
    session_id: str


class CreatePortalRequest(BaseModel):
    return_url: str


class PortalSessionResponse(BaseModel):
    portal_url: str


# ========== Payment Schemas ==========

class PaymentResponse(BaseModel):
    id: int
    amount: int
    currency: str
    status: str
    description: Optional[str]
    created_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class PaymentHistoryResponse(BaseModel):
    payments: List[PaymentResponse]
    total_paid: int


# ========== Coupon Schemas ==========

class ApplyCouponRequest(BaseModel):
    code: str


class CouponResponse(BaseModel):
    code: str
    percent_off: Optional[int]
    amount_off: Optional[int]
    duration: str
    valid: bool
    message: str


# ========== Webhook Schemas ==========

class WebhookEvent(BaseModel):
    type: str
    data: dict


# ========== Upgrade/Downgrade ==========

class ChangePlanRequest(BaseModel):
    new_tier: SubscriptionTierEnum
    prorate: bool = True


class ChangePlanResponse(BaseModel):
    success: bool
    message: str
    new_tier: SubscriptionTierEnum
    effective_date: datetime
    prorated_amount: Optional[int] = None

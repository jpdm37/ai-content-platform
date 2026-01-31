"""
Billing API Routes

Handles subscription management, checkout, and usage tracking.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import get_settings
from app.models.user import User
from app.auth.dependencies import get_current_user, get_current_verified_user

from app.billing.models import PLAN_LIMITS, SubscriptionTier, SubscriptionStatus
from app.billing.schemas import (
    PlanResponse, PlanFeatures, PlansListResponse,
    SubscriptionResponse, SubscriptionDetailResponse, UsageSummary,
    CreateCheckoutRequest, CheckoutSessionResponse,
    CreatePortalRequest, PortalSessionResponse,
    PaymentResponse, PaymentHistoryResponse,
    ApplyCouponRequest, CouponResponse,
    ChangePlanRequest, ChangePlanResponse
)
from app.billing.service import BillingService

settings = get_settings()
router = APIRouter(prefix="/billing", tags=["billing"])


# ==================== Plans ====================

@router.get("/plans", response_model=PlansListResponse)
async def list_plans():
    """List all available subscription plans"""
    plans = []
    
    price_ids = {
        SubscriptionTier.FREE: None,
        SubscriptionTier.CREATOR: settings.stripe_price_id_creator,
        SubscriptionTier.PRO: settings.stripe_price_id_pro,
        SubscriptionTier.AGENCY: settings.stripe_price_id_agency,
    }
    
    for tier, limits in PLAN_LIMITS.items():
        plans.append(PlanResponse(
            tier=tier.value,
            name=limits["name"],
            price_monthly=limits["price_monthly"],
            stripe_price_id=price_ids.get(tier),
            features=PlanFeatures(
                generations_per_month=limits["generations_per_month"],
                brands=limits["brands"],
                lora_models=limits["lora_models"],
                scheduled_posts=limits["scheduled_posts"],
                social_accounts=limits["social_accounts"],
                team_members=limits["team_members"],
                api_access=limits["api_access"],
                priority_support=limits["priority_support"],
                features=limits["features"]
            )
        ))
    
    return PlansListResponse(plans=plans)


@router.get("/plans/{tier}", response_model=PlanResponse)
async def get_plan(tier: str):
    """Get details for a specific plan"""
    try:
        subscription_tier = SubscriptionTier(tier)
    except ValueError:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    limits = PLAN_LIMITS.get(subscription_tier)
    if not limits:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    price_ids = {
        SubscriptionTier.CREATOR: settings.stripe_price_id_creator,
        SubscriptionTier.PRO: settings.stripe_price_id_pro,
        SubscriptionTier.AGENCY: settings.stripe_price_id_agency,
    }
    
    return PlanResponse(
        tier=tier,
        name=limits["name"],
        price_monthly=limits["price_monthly"],
        stripe_price_id=price_ids.get(subscription_tier),
        features=PlanFeatures(
            generations_per_month=limits["generations_per_month"],
            brands=limits["brands"],
            lora_models=limits["lora_models"],
            scheduled_posts=limits["scheduled_posts"],
            social_accounts=limits["social_accounts"],
            team_members=limits["team_members"],
            api_access=limits["api_access"],
            priority_support=limits["priority_support"],
            features=limits["features"]
        )
    )


# ==================== Subscription ====================

@router.get("/subscription", response_model=SubscriptionDetailResponse)
async def get_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's subscription"""
    service = BillingService(db)
    subscription = service.ensure_subscription(current_user)
    limits = PLAN_LIMITS.get(subscription.tier, PLAN_LIMITS[SubscriptionTier.FREE])
    
    return SubscriptionDetailResponse(
        id=subscription.id,
        tier=subscription.tier.value,
        status=subscription.status.value,
        current_period_start=subscription.current_period_start,
        current_period_end=subscription.current_period_end,
        cancel_at_period_end=subscription.cancel_at_period_end,
        trial_end=subscription.trial_end,
        generations_used=subscription.generations_used,
        generations_limit=limits["generations_per_month"],
        created_at=subscription.created_at,
        stripe_customer_id=subscription.stripe_customer_id,
        stripe_subscription_id=subscription.stripe_subscription_id,
        plan=PlanFeatures(
            generations_per_month=limits["generations_per_month"],
            brands=limits["brands"],
            lora_models=limits["lora_models"],
            scheduled_posts=limits["scheduled_posts"],
            social_accounts=limits["social_accounts"],
            team_members=limits["team_members"],
            api_access=limits["api_access"],
            priority_support=limits["priority_support"],
            features=limits["features"]
        )
    )


@router.get("/usage", response_model=UsageSummary)
async def get_usage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current usage summary"""
    service = BillingService(db)
    return service.get_usage_summary(current_user)


# ==================== Checkout ====================

@router.post("/checkout", response_model=CheckoutSessionResponse)
async def create_checkout(
    request: CreateCheckoutRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Create Stripe checkout session for subscription"""
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    
    service = BillingService(db)
    
    try:
        tier = SubscriptionTier(request.tier)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tier")
    
    try:
        result = service.create_checkout_session(
            user=current_user,
            tier=tier,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            coupon_code=request.coupon_code
        )
        return CheckoutSessionResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/portal", response_model=PortalSessionResponse)
async def create_portal_session(
    request: CreatePortalRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create Stripe billing portal session"""
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    
    service = BillingService(db)
    
    try:
        portal_url = service.create_billing_portal_session(
            user=current_user,
            return_url=request.return_url
        )
        return PortalSessionResponse(portal_url=portal_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== Plan Changes ====================

@router.post("/change-plan", response_model=ChangePlanResponse)
async def change_plan(
    request: ChangePlanRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Change subscription plan"""
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    
    service = BillingService(db)
    
    try:
        tier = SubscriptionTier(request.new_tier)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tier")
    
    try:
        result = service.change_plan(current_user, tier, request.prorate)
        return ChangePlanResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cancel")
async def cancel_subscription(
    at_period_end: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel subscription"""
    service = BillingService(db)
    
    try:
        result = service.cancel_subscription(current_user, at_period_end)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reactivate")
async def reactivate_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reactivate a cancelled subscription"""
    service = BillingService(db)
    
    try:
        result = service.reactivate_subscription(current_user)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== Payment History ====================

@router.get("/payments", response_model=PaymentHistoryResponse)
async def get_payment_history(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get payment history"""
    from app.billing.models import Payment
    
    payments = db.query(Payment).filter(
        Payment.user_id == current_user.id
    ).order_by(Payment.created_at.desc()).offset(skip).limit(limit).all()
    
    total = sum(p.amount for p in payments if p.status.value == "succeeded")
    
    return PaymentHistoryResponse(
        payments=[PaymentResponse.model_validate(p) for p in payments],
        total_paid=total
    )


# ==================== Coupons ====================

@router.post("/coupon/validate", response_model=CouponResponse)
async def validate_coupon(
    request: ApplyCouponRequest,
    tier: str = "creator",
    db: Session = Depends(get_db)
):
    """Validate a coupon code"""
    service = BillingService(db)
    
    try:
        subscription_tier = SubscriptionTier(tier)
    except ValueError:
        subscription_tier = SubscriptionTier.CREATOR
    
    result = service.apply_coupon(request.code, subscription_tier)
    return CouponResponse(**result)


# ==================== Webhooks ====================

@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
    db: Session = Depends(get_db)
):
    """Handle Stripe webhooks"""
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Webhook not configured")
    
    payload = await request.body()
    
    service = BillingService(db)
    
    try:
        result = service.handle_webhook(payload, stripe_signature)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== Usage Check (Internal) ====================

@router.get("/check-limit/{feature}")
async def check_feature_limit(
    feature: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if user is within limits for a feature"""
    service = BillingService(db)
    return service.check_limit(current_user, feature)

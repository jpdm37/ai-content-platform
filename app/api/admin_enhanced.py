"""
Enhanced Admin API Routes
=========================
Comprehensive admin management endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.admin.models import AdminUser
from app.api.admin import get_current_admin, require_superadmin
from app.admin.enhanced_service import EnhancedAdminService, get_enhanced_admin_service


router = APIRouter(prefix="/admin/manage", tags=["admin-management"])


# ==================== Schemas ====================

class FeatureFlagResponse(BaseModel):
    key: str
    enabled: bool
    default: bool
    description: str
    category: str
    overridden: bool


class FeatureFlagUpdate(BaseModel):
    enabled: bool


class BulkFeatureUpdate(BaseModel):
    features: dict  # {feature_key: bool}


class UsageAddRequest(BaseModel):
    usage_type: str
    amount: int
    reason: Optional[str] = None


class UserActionRequest(BaseModel):
    reason: Optional[str] = None


class BulkUserActionRequest(BaseModel):
    user_ids: List[int]
    action: str  # suspend, unsuspend, verify_email


class TierChangeRequest(BaseModel):
    new_tier: str
    duration_days: Optional[int] = None
    reason: Optional[str] = None


class SubscriptionExtendRequest(BaseModel):
    days: int
    reason: Optional[str] = None


class TierLimitsUpdate(BaseModel):
    limits: dict  # {limit_name: value}


class AnnouncementCreate(BaseModel):
    title: str
    message: str
    announcement_type: str = "info"  # info, warning, maintenance
    expires_at: Optional[datetime] = None


class PasswordResetRequest(BaseModel):
    new_password: str


# ==================== Feature Flags ====================

@router.get("/features", response_model=List[FeatureFlagResponse])
async def get_feature_flags(
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Get all feature flags with current status."""
    service = get_enhanced_admin_service(db)
    return service.get_all_feature_flags()


@router.put("/features/{feature_key}")
async def update_feature_flag(
    feature_key: str,
    request: FeatureFlagUpdate,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_superadmin)
):
    """Enable or disable a feature flag."""
    service = get_enhanced_admin_service(db)
    
    try:
        result = service.set_feature_flag(feature_key, request.enabled, admin.id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/features/bulk")
async def bulk_update_features(
    request: BulkFeatureUpdate,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_superadmin)
):
    """Update multiple feature flags at once."""
    service = get_enhanced_admin_service(db)
    count = service.bulk_set_features(request.features, admin.id)
    return {"message": f"Updated {count} features", "updated": count}


# ==================== Usage Management ====================

@router.get("/users/{user_id}/usage")
async def get_user_usage(
    user_id: int,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Get detailed usage statistics for a user."""
    service = get_enhanced_admin_service(db)
    
    try:
        return service.get_user_usage(user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/users/{user_id}/usage/add")
async def add_user_usage(
    user_id: int,
    request: UsageAddRequest,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Add additional usage quota to a user's account."""
    service = get_enhanced_admin_service(db)
    
    try:
        return service.add_user_usage(
            user_id=user_id,
            usage_type=request.usage_type,
            amount=request.amount,
            admin_id=admin.id,
            reason=request.reason
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/users/{user_id}/usage/reset")
async def reset_user_usage(
    user_id: int,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_superadmin)
):
    """Reset a user's usage counters."""
    service = get_enhanced_admin_service(db)
    return service.reset_user_usage(user_id, admin.id)


# ==================== User Management ====================

@router.post("/users/{user_id}/suspend")
async def suspend_user(
    user_id: int,
    request: UserActionRequest,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Suspend a user account."""
    service = get_enhanced_admin_service(db)
    
    try:
        user = service.suspend_user(user_id, admin.id, request.reason)
        return {"message": "User suspended", "user_id": user_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/users/{user_id}/unsuspend")
async def unsuspend_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Reactivate a suspended user account."""
    service = get_enhanced_admin_service(db)
    
    try:
        user = service.unsuspend_user(user_id, admin.id)
        return {"message": "User reactivated", "user_id": user_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/users/{user_id}/verify-email")
async def verify_user_email(
    user_id: int,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Manually verify a user's email."""
    service = get_enhanced_admin_service(db)
    
    try:
        user = service.verify_user_email(user_id, admin.id)
        return {"message": "Email verified", "user_id": user_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: int,
    request: PasswordResetRequest,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_superadmin)
):
    """Reset a user's password."""
    service = get_enhanced_admin_service(db)
    
    try:
        user = service.reset_user_password(user_id, request.new_password, admin.id)
        return {"message": "Password reset", "user_id": user_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    hard_delete: bool = False,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_superadmin)
):
    """Delete a user account."""
    service = get_enhanced_admin_service(db)
    
    try:
        return service.delete_user(user_id, admin.id, hard_delete)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/users/bulk-action")
async def bulk_user_action(
    request: BulkUserActionRequest,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Perform bulk action on multiple users."""
    service = get_enhanced_admin_service(db)
    
    try:
        return service.bulk_action_users(request.user_ids, request.action, admin.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== Subscription Management ====================

@router.post("/users/{user_id}/subscription/change-tier")
async def change_user_tier(
    user_id: int,
    request: TierChangeRequest,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Change a user's subscription tier."""
    service = get_enhanced_admin_service(db)
    
    try:
        subscription = service.change_user_tier(
            user_id=user_id,
            new_tier=request.new_tier,
            admin_id=admin.id,
            duration_days=request.duration_days,
            reason=request.reason
        )
        return {
            "message": "Tier changed",
            "user_id": user_id,
            "new_tier": subscription.tier,
            "expires": subscription.current_period_end.isoformat() if subscription.current_period_end else None
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/users/{user_id}/subscription/extend")
async def extend_subscription(
    user_id: int,
    request: SubscriptionExtendRequest,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Extend a user's subscription."""
    service = get_enhanced_admin_service(db)
    
    try:
        subscription = service.extend_subscription(
            user_id=user_id,
            days=request.days,
            admin_id=admin.id,
            reason=request.reason
        )
        return {
            "message": "Subscription extended",
            "user_id": user_id,
            "new_end_date": subscription.current_period_end.isoformat()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/users/{user_id}/subscription/cancel")
async def cancel_subscription(
    user_id: int,
    immediate: bool = False,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Cancel a user's subscription."""
    service = get_enhanced_admin_service(db)
    
    try:
        subscription = service.cancel_subscription(user_id, admin.id, immediate)
        return {
            "message": "Subscription cancelled",
            "user_id": user_id,
            "immediate": immediate
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== Tier Limits ====================

@router.get("/tier-limits")
async def get_tier_limits(
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Get current tier limits configuration."""
    service = get_enhanced_admin_service(db)
    return service.get_tier_limits()


@router.put("/tier-limits/{tier}")
async def update_tier_limits(
    tier: str,
    request: TierLimitsUpdate,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_superadmin)
):
    """Update limits for a specific tier."""
    service = get_enhanced_admin_service(db)
    
    try:
        return service.update_tier_limits(tier, request.limits, admin.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== System Health ====================

@router.get("/health")
async def get_system_health(
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Get system health metrics."""
    service = get_enhanced_admin_service(db)
    return service.get_system_health()


# ==================== Announcements ====================

@router.get("/announcements")
async def get_announcements(
    include_expired: bool = False,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Get system announcements."""
    service = get_enhanced_admin_service(db)
    return service.get_announcements(include_expired)


@router.post("/announcements")
async def create_announcement(
    request: AnnouncementCreate,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Create a system announcement."""
    service = get_enhanced_admin_service(db)
    return service.create_announcement(
        title=request.title,
        message=request.message,
        announcement_type=request.announcement_type,
        admin_id=admin.id,
        expires_at=request.expires_at
    )


@router.delete("/announcements/{announcement_id}")
async def delete_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Delete an announcement."""
    service = get_enhanced_admin_service(db)
    if service.delete_announcement(announcement_id, admin.id):
        return {"message": "Announcement deleted"}
    raise HTTPException(status_code=404, detail="Announcement not found")


# ==================== Content Moderation ====================

@router.get("/content/flagged")
async def get_flagged_content(
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Get content that may need moderation."""
    service = get_enhanced_admin_service(db)
    return service.get_flagged_content(limit)


@router.delete("/content/{content_id}")
async def delete_content(
    content_id: int,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Delete a content item."""
    service = get_enhanced_admin_service(db)
    if service.delete_content(content_id, admin.id, reason):
        return {"message": "Content deleted"}
    raise HTTPException(status_code=404, detail="Content not found")


# ==================== Reports ====================

@router.get("/reports/usage")
async def get_usage_report(
    days: int = Query(default=30, le=365),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Get platform usage report."""
    service = get_enhanced_admin_service(db)
    return service.get_usage_report(days)

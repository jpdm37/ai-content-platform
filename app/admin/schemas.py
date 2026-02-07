"""
Admin Schemas
=============
Request/Response models for admin API.
"""

from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum


class AdminRole(str, Enum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    SUPPORT = "support"


# ============ Request Schemas ============

class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


class AdminCreateRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: AdminRole = AdminRole.ADMIN


class AdminUpdateRequest(BaseModel):
    name: Optional[str] = None
    role: Optional[AdminRole] = None
    is_active: Optional[bool] = None


class UserUpdateByAdmin(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None


class GrantSubscriptionRequest(BaseModel):
    tier: str  # free, creator, pro, agency
    duration_days: int = 365


class ImpersonateRequest(BaseModel):
    reason: str


class TestBrandRequest(BaseModel):
    name: str
    niche: str
    description: Optional[str] = None


class SystemSettingUpdate(BaseModel):
    value: str


# ============ Response Schemas ============

class AdminResponse(BaseModel):
    id: int
    email: str
    name: str
    role: AdminRole
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin: AdminResponse


class UserListItem(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    is_active: bool
    is_verified: bool
    subscription_tier: str
    subscription_status: str
    brands_count: int
    content_count: int
    created_at: datetime
    last_login: Optional[datetime]


class UserListResponse(BaseModel):
    users: List[UserListItem]
    total: int
    page: int
    per_page: int


class UserDetailResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime]
    subscription: Optional[dict]
    stats: dict
    recent_activity: List[dict]


class ImpersonateResponse(BaseModel):
    access_token: str
    expires_in: int = 3600
    user_email: str


class SystemStatsResponse(BaseModel):
    total_users: int
    active_users_24h: int
    active_users_7d: int
    total_brands: int
    total_content: int
    total_videos: int
    total_posts: int
    total_revenue: float
    users_by_tier: dict
    signups_today: int
    signups_this_week: int
    signups_this_month: int


class SystemSettingResponse(BaseModel):
    key: str
    value: str
    description: Optional[str]
    updated_at: Optional[datetime]


class AuditLogResponse(BaseModel):
    id: int
    admin_id: int
    action: str
    target_type: Optional[str]
    target_id: Optional[int]
    details: Optional[dict]
    ip_address: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

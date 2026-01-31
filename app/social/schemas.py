"""
Social Media Integration Pydantic Schemas
"""
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class SocialPlatformEnum(str, Enum):
    TWITTER = "twitter"
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    TIKTOK = "tiktok"
    FACEBOOK = "facebook"
    THREADS = "threads"


class PostStatusEnum(str, Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ========== Social Account Schemas ==========

class SocialAccountBase(BaseModel):
    brand_id: Optional[int] = None


class SocialAccountResponse(BaseModel):
    id: int
    platform: SocialPlatformEnum
    platform_username: Optional[str]
    platform_display_name: Optional[str]
    profile_image_url: Optional[str]
    brand_id: Optional[int]
    is_active: bool
    last_synced_at: Optional[datetime]
    last_error: Optional[str]
    platform_data: Optional[Dict[str, Any]]
    created_at: datetime
    
    class Config:
        from_attributes = True


class SocialAccountDetailResponse(SocialAccountResponse):
    posts_count: int = 0
    scheduled_count: int = 0
    published_count: int = 0


class ConnectAccountRequest(BaseModel):
    platform: SocialPlatformEnum
    brand_id: Optional[int] = None


class OAuthCallbackData(BaseModel):
    code: str
    state: Optional[str] = None


# ========== Scheduled Post Schemas ==========

class ScheduledPostBase(BaseModel):
    caption: Optional[str] = None
    hashtags: Optional[List[str]] = None
    media_urls: Optional[List[str]] = None
    scheduled_for: datetime
    timezone: str = "UTC"


class ScheduledPostCreate(ScheduledPostBase):
    social_account_id: int
    brand_id: Optional[int] = None
    generated_content_id: Optional[int] = None
    platform_specific: Optional[Dict[str, Any]] = None


class ScheduledPostUpdate(BaseModel):
    caption: Optional[str] = None
    hashtags: Optional[List[str]] = None
    media_urls: Optional[List[str]] = None
    scheduled_for: Optional[datetime] = None
    timezone: Optional[str] = None
    platform_specific: Optional[Dict[str, Any]] = None


class ScheduledPostResponse(ScheduledPostBase):
    id: int
    social_account_id: int
    brand_id: Optional[int]
    generated_content_id: Optional[int]
    status: PostStatusEnum
    published_at: Optional[datetime]
    platform_post_id: Optional[str]
    platform_post_url: Optional[str]
    error_message: Optional[str]
    engagement_data: Optional[Dict[str, Any]]
    created_at: datetime
    
    # Include account info
    platform: Optional[SocialPlatformEnum] = None
    account_username: Optional[str] = None
    
    class Config:
        from_attributes = True


class ScheduledPostDetailResponse(ScheduledPostResponse):
    social_account: Optional[SocialAccountResponse] = None
    retry_count: int = 0


# ========== Bulk Scheduling ==========

class BulkScheduleRequest(BaseModel):
    """Schedule same content to multiple accounts"""
    social_account_ids: List[int]
    caption: str
    hashtags: Optional[List[str]] = None
    media_urls: Optional[List[str]] = None
    scheduled_for: datetime
    timezone: str = "UTC"
    brand_id: Optional[int] = None


class BulkScheduleResponse(BaseModel):
    scheduled: int
    failed: int
    posts: List[ScheduledPostResponse]
    errors: List[Dict[str, Any]]


# ========== Quick Post (Immediate) ==========

class QuickPostRequest(BaseModel):
    """Post immediately to a social account"""
    social_account_id: int
    caption: str
    hashtags: Optional[List[str]] = None
    media_urls: Optional[List[str]] = None
    platform_specific: Optional[Dict[str, Any]] = None


class QuickPostResponse(BaseModel):
    success: bool
    post_id: Optional[str]
    post_url: Optional[str]
    error: Optional[str]


# ========== Calendar View ==========

class CalendarPostResponse(BaseModel):
    id: int
    scheduled_for: datetime
    status: PostStatusEnum
    platform: SocialPlatformEnum
    account_username: Optional[str]
    caption_preview: Optional[str]
    media_count: int = 0


class CalendarDayResponse(BaseModel):
    date: str
    posts: List[CalendarPostResponse]
    total: int


# ========== Post Templates ==========

class PostTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    caption_template: str
    default_hashtags: Optional[List[str]] = None
    platforms: Optional[List[SocialPlatformEnum]] = None
    brand_id: Optional[int] = None


class PostTemplateResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    caption_template: str
    default_hashtags: Optional[List[str]]
    platforms: Optional[List[str]]
    brand_id: Optional[int]
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# ========== Analytics ==========

class PostEngagementResponse(BaseModel):
    post_id: int
    platform: SocialPlatformEnum
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    impressions: int = 0
    reach: int = 0
    engagement_rate: float = 0.0
    last_updated: Optional[datetime]


class AccountAnalyticsResponse(BaseModel):
    account_id: int
    platform: SocialPlatformEnum
    followers: int = 0
    following: int = 0
    posts_count: int = 0
    total_engagement: int = 0
    avg_engagement_rate: float = 0.0
    best_posting_times: List[str] = []


# ========== Best Time to Post ==========

class BestTimeResponse(BaseModel):
    platform: SocialPlatformEnum
    day_of_week: str
    hour: int
    engagement_score: float
    recommendation: str


class BestTimesResponse(BaseModel):
    account_id: int
    platform: SocialPlatformEnum
    times: List[BestTimeResponse]
    timezone: str

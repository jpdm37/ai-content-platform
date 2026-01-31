"""
AI Content Studio Pydantic Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ProjectStatusEnum(str, Enum):
    DRAFT = "draft"
    GENERATING = "generating"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class ContentTypeEnum(str, Enum):
    CAPTION = "caption"
    IMAGE = "image"
    VIDEO = "video"
    HASHTAGS = "hashtags"
    HOOK = "hook"
    CTA = "cta"


class ToneEnum(str, Enum):
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    HUMOROUS = "humorous"
    INSPIRATIONAL = "inspirational"
    EDUCATIONAL = "educational"
    URGENT = "urgent"
    STORYTELLING = "storytelling"


class PlatformEnum(str, Enum):
    TWITTER = "twitter"
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    TIKTOK = "tiktok"
    FACEBOOK = "facebook"


# ========== Create Project ==========

class CreateProjectRequest(BaseModel):
    """Request to create a new studio project"""
    brief: str = Field(..., min_length=10, max_length=2000, description="Content brief/topic")
    name: Optional[str] = Field(None, max_length=255)
    
    target_platforms: List[PlatformEnum] = Field(default=["instagram"], min_length=1)
    content_types: List[ContentTypeEnum] = Field(
        default=["caption", "hashtags", "image"],
        description="Types of content to generate"
    )
    
    brand_id: Optional[int] = None
    tone: ToneEnum = ToneEnum.PROFESSIONAL
    num_variations: int = Field(default=3, ge=1, le=5)
    
    # Video options
    include_video: bool = False
    lora_model_id: Optional[int] = None
    video_duration: str = Field(default="30s", pattern="^(15s|30s|60s|90s)$")


class CreateFromTemplateRequest(BaseModel):
    """Create project from a template"""
    template_id: int
    brief: str = Field(..., min_length=10, max_length=2000)
    variables: Optional[Dict[str, str]] = None
    brand_id: Optional[int] = None


# ========== Asset Schemas ==========

class AssetResponse(BaseModel):
    id: int
    content_type: ContentTypeEnum
    text_content: Optional[str]
    media_url: Optional[str]
    thumbnail_url: Optional[str]
    platform: Optional[str]
    platform_optimized: Optional[Dict[str, Any]]
    variation_number: int
    is_favorite: bool
    is_selected: bool
    user_rating: Optional[int]
    cost_usd: float
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class UpdateAssetRequest(BaseModel):
    is_favorite: Optional[bool] = None
    is_selected: Optional[bool] = None
    user_rating: Optional[int] = Field(None, ge=1, le=5)


# ========== Project Schemas ==========

class ProjectResponse(BaseModel):
    id: int
    name: Optional[str]
    brief: str
    target_platforms: List[str]
    content_types: List[str]
    tone: str
    num_variations: int
    include_video: bool
    
    status: ProjectStatusEnum
    progress_percent: int
    current_step: Optional[str]
    
    captions_generated: int
    images_generated: int
    videos_generated: int
    total_cost_usd: float
    
    error_message: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class ProjectDetailResponse(ProjectResponse):
    brand_id: Optional[int]
    lora_model_id: Optional[int]
    video_duration: Optional[str]
    assets: List[AssetResponse] = []


class ProjectListResponse(BaseModel):
    projects: List[ProjectResponse]
    total: int
    page: int
    per_page: int


class ProjectProgressResponse(BaseModel):
    id: int
    status: ProjectStatusEnum
    progress_percent: int
    current_step: Optional[str]
    captions_generated: int
    images_generated: int
    videos_generated: int
    error_message: Optional[str]


# ========== Template Schemas ==========

class CreateTemplateRequest(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    category: Optional[str] = None
    brief_template: Optional[str] = None
    target_platforms: List[PlatformEnum] = ["instagram"]
    content_types: List[ContentTypeEnum] = ["caption", "hashtags"]
    tone: ToneEnum = ToneEnum.PROFESSIONAL
    num_variations: int = 3
    include_video: bool = False
    is_public: bool = False


class TemplateResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    category: Optional[str]
    brief_template: Optional[str]
    target_platforms: List[str]
    content_types: List[str]
    tone: str
    num_variations: int
    include_video: bool
    preview_image_url: Optional[str]
    is_public: bool
    times_used: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# ========== Quick Generate ==========

class QuickGenerateRequest(BaseModel):
    """Quick generation without full project"""
    brief: str = Field(..., min_length=10, max_length=1000)
    content_type: ContentTypeEnum
    platform: PlatformEnum = PlatformEnum.INSTAGRAM
    tone: ToneEnum = ToneEnum.PROFESSIONAL
    brand_id: Optional[int] = None
    num_results: int = Field(default=3, ge=1, le=5)


class QuickGenerateResponse(BaseModel):
    content_type: ContentTypeEnum
    results: List[str]
    platform: str
    cost_usd: float


# ========== Regenerate ==========

class RegenerateAssetRequest(BaseModel):
    """Regenerate a single asset with modifications"""
    asset_id: int
    modification: Optional[str] = Field(None, description="How to modify the regeneration")


# ========== Export ==========

class ExportProjectRequest(BaseModel):
    """Export project assets"""
    format: str = Field(default="json", pattern="^(json|csv|zip)$")
    include_media: bool = True
    selected_only: bool = False  # Only export selected assets

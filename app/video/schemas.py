"""
Video Generation Pydantic Schemas
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import json


def parse_json_dict(v: Any):
    if v is None:
        return None
    if isinstance(v, dict):
        return v
    if isinstance(v, str):
        try:
            parsed = json.loads(v)
            return parsed if isinstance(parsed, dict) else None
        except (json.JSONDecodeError, TypeError):
            return None
    return None


class VideoStatusEnum(str, Enum):
    PENDING = "pending"
    GENERATING_AUDIO = "generating_audio"
    GENERATING_AVATAR = "generating_avatar"
    GENERATING_VIDEO = "generating_video"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class VoiceProviderEnum(str, Enum):
    ELEVENLABS = "elevenlabs"
    OPENAI = "openai"
    AZURE = "azure"


class AspectRatioEnum(str, Enum):
    SQUARE = "1:1"
    PORTRAIT = "9:16"
    LANDSCAPE = "16:9"
    VERTICAL = "4:5"


class ExpressionEnum(str, Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SERIOUS = "serious"
    EXCITED = "excited"
    CONCERNED = "concerned"
    CONFIDENT = "confident"


class HeadMovementEnum(str, Enum):
    NONE = "none"
    SUBTLE = "subtle"
    NATURAL = "natural"
    DYNAMIC = "dynamic"


# ========== Voice Schemas ==========

class VoiceSettings(BaseModel):
    stability: float = Field(default=0.5, ge=0, le=1)
    similarity_boost: float = Field(default=0.75, ge=0, le=1)
    style: float = Field(default=0.0, ge=0, le=1)
    speed: float = Field(default=1.0, ge=0.5, le=2.0)


class VoicePreset(BaseModel):
    id: str
    name: str
    gender: Optional[str]
    accent: Optional[str] = None
    style: Optional[str] = None
    provider: VoiceProviderEnum


class VoiceListResponse(BaseModel):
    provider: VoiceProviderEnum
    voices: List[VoicePreset]


class VoiceCloneCreate(BaseModel):
    name: str
    description: Optional[str] = None
    sample_audio_urls: List[str] = Field(..., min_length=1, max_length=5)
    gender: Optional[str] = None
    accent: Optional[str] = None


class VoiceCloneResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    provider: VoiceProviderEnum
    provider_voice_id: Optional[str]
    gender: Optional[str]
    is_ready: bool
    times_used: int
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ========== Video Generation Schemas ==========

class VideoGenerateRequest(BaseModel):
    """Request to generate a talking head video"""
    # Required
    script: str = Field(..., min_length=1, max_length=5000)
    
    # Avatar source (one required)
    lora_model_id: Optional[int] = None
    avatar_image_url: Optional[str] = None
    avatar_prompt: Optional[str] = None
    
    # Voice settings
    voice_provider: VoiceProviderEnum = VoiceProviderEnum.ELEVENLABS
    voice_id: Optional[str] = None  # If None, uses default
    voice_clone_id: Optional[int] = None  # Custom cloned voice
    voice_settings: Optional[VoiceSettings] = None
    
    # Video settings
    title: Optional[str] = None
    aspect_ratio: AspectRatioEnum = AspectRatioEnum.PORTRAIT
    expression: ExpressionEnum = ExpressionEnum.NEUTRAL
    head_movement: HeadMovementEnum = HeadMovementEnum.NATURAL
    eye_contact: bool = True
    
    # Background
    background_color: str = "#000000"
    background_image_url: Optional[str] = None
    
    # Optional
    brand_id: Optional[int] = None


class VideoGenerateFromTemplateRequest(BaseModel):
    """Generate video from a template"""
    template_id: int
    script: str = Field(..., min_length=1, max_length=5000)
    lora_model_id: Optional[int] = None
    avatar_image_url: Optional[str] = None
    variables: Optional[Dict[str, str]] = None  # For script template variables
    brand_id: Optional[int] = None


class VideoResponse(BaseModel):
    id: int
    title: Optional[str]
    script: str
    status: VideoStatusEnum
    progress_percent: int
    
    # Voice
    voice_provider: VoiceProviderEnum
    voice_name: Optional[str]
    
    # Video settings
    aspect_ratio: AspectRatioEnum
    expression: Optional[str]
    
    # Outputs
    audio_url: Optional[str]
    audio_duration_seconds: Optional[float]
    video_url: Optional[str]
    thumbnail_url: Optional[str]
    
    # Cost
    total_cost_usd: float
    
    # Timing
    error_message: Optional[str]
    created_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class VideoDetailResponse(VideoResponse):
    brand_id: Optional[int]
    lora_model_id: Optional[int]
    avatar_image_url: Optional[str]
    avatar_image_generated_url: Optional[str]
    background_color: Optional[str]
    background_image_url: Optional[str]
    resolution: str
    fps: int
    head_movement: Optional[str]
    eye_contact: bool
    audio_cost_usd: float
    video_cost_usd: float
    metadata: Optional[Dict[str, Any]]


    @field_validator('metadata', mode='before')
    @classmethod
    def parse_metadata(cls, v):
        return parse_json_dict(v)

class VideoProgressResponse(BaseModel):
    id: int
    status: VideoStatusEnum
    progress_percent: int
    current_step: str
    estimated_time_remaining: Optional[int]  # seconds
    error_message: Optional[str]


class VideoListResponse(BaseModel):
    videos: List[VideoResponse]
    total: int
    page: int
    per_page: int


# ========== Video Template Schemas ==========

class VideoTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    
    voice_provider: VoiceProviderEnum = VoiceProviderEnum.ELEVENLABS
    voice_id: Optional[str] = None
    voice_settings: Optional[VoiceSettings] = None
    
    aspect_ratio: AspectRatioEnum = AspectRatioEnum.PORTRAIT
    resolution: str = "1080x1920"
    
    expression: ExpressionEnum = ExpressionEnum.NEUTRAL
    head_movement: HeadMovementEnum = HeadMovementEnum.NATURAL
    
    background_color: str = "#000000"
    background_image_url: Optional[str] = None
    
    script_template: Optional[str] = None
    is_public: bool = False


class VideoTemplateResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    category: Optional[str]
    
    voice_provider: VoiceProviderEnum
    voice_id: Optional[str]
    
    aspect_ratio: AspectRatioEnum
    expression: Optional[str]
    head_movement: Optional[str]
    
    background_color: Optional[str]
    
    script_template: Optional[str]
    preview_thumbnail_url: Optional[str]
    preview_video_url: Optional[str]
    
    is_public: bool
    is_active: bool
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ========== Cost Estimation ==========

class VideoCostEstimate(BaseModel):
    script_length: int
    estimated_duration_seconds: float
    audio_cost: float
    avatar_cost: float
    video_cost: float
    processing_cost: float
    total_cost: float
    
    breakdown: Dict[str, Any]


class EstimateCostRequest(BaseModel):
    script: str
    generate_avatar: bool = False


# ========== Batch Generation ==========

class BatchVideoRequest(BaseModel):
    """Generate multiple videos with different scripts"""
    scripts: List[str] = Field(..., min_length=1, max_length=10)
    
    # Shared settings
    lora_model_id: Optional[int] = None
    avatar_image_url: Optional[str] = None
    voice_provider: VoiceProviderEnum = VoiceProviderEnum.ELEVENLABS
    voice_id: Optional[str] = None
    aspect_ratio: AspectRatioEnum = AspectRatioEnum.PORTRAIT
    brand_id: Optional[int] = None


class BatchVideoResponse(BaseModel):
    queued: int
    video_ids: List[int]
    estimated_total_cost: float

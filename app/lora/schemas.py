"""
LoRA Training and Avatar Consistency API Schemas
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum
import json


def parse_json_list(v: Any):
    if v is None:
        return None
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        try:
            parsed = json.loads(v)
            return parsed if isinstance(parsed, list) else None
        except (json.JSONDecodeError, TypeError):
            return None
    return None


# ========== Enums ==========

class TrainingStatusEnum(str, Enum):
    PENDING = "pending"
    VALIDATING = "validating"
    UPLOADING = "uploading"
    TRAINING = "training"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BaseModelEnum(str, Enum):
    FLUX_DEV = "flux-dev"
    FLUX_SCHNELL = "flux-schnell"
    SDXL = "sdxl"


class ImageTypeEnum(str, Enum):
    HEADSHOT = "headshot"
    FULL_BODY = "full_body"
    PROFILE = "profile"
    THREE_QUARTER = "three_quarter"
    ACTION = "action"
    LIFESTYLE = "lifestyle"


# ========== Reference Image Schemas ==========

class ReferenceImageBase(BaseModel):
    caption: Optional[str] = None
    custom_caption: Optional[str] = None
    image_type: Optional[ImageTypeEnum] = None
    is_included_in_training: bool = True


class ReferenceImageCreate(ReferenceImageBase):
    """For creating reference image via URL"""
    image_url: str


class ReferenceImageUploadResponse(BaseModel):
    """Response after uploading reference image"""
    id: int
    original_url: str
    processed_url: Optional[str]
    face_detected: bool
    face_confidence: Optional[float]
    quality_score: Optional[float]
    validation_status: str
    validation_errors: Optional[List[str]]
    auto_caption: Optional[str]
    
    @field_validator('validation_errors', mode='before')
    @classmethod
    def parse_validation_errors(cls, v):
        return parse_json_list(v)

    class Config:
        from_attributes = True


class ReferenceImageResponse(ReferenceImageBase):
    id: int
    original_url: str
    processed_url: Optional[str]
    face_detected: bool
    face_confidence: Optional[float]
    quality_score: Optional[float]
    validation_status: str
    validation_errors: Optional[List[str]]
    created_at: Optional[datetime] = None
    
    @field_validator('validation_errors', mode='before')
    @classmethod
    def parse_validation_errors(cls, v):
        return parse_json_list(v)

    class Config:
        from_attributes = True


# ========== LoRA Model Schemas ==========

class LoraModelBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    trigger_word: str = Field(default="AVATAR", min_length=2, max_length=50)


class LoraTrainingConfig(BaseModel):
    """Configuration for LoRA training"""
    base_model: BaseModelEnum = BaseModelEnum.FLUX_DEV
    training_steps: int = Field(default=1000, ge=100, le=4000)
    learning_rate: float = Field(default=0.0004, ge=0.00001, le=0.01)
    lora_rank: int = Field(default=16, ge=4, le=128)
    resolution: int = Field(default=1024, ge=512, le=2048)
    
    # Advanced options
    batch_size: int = Field(default=1, ge=1, le=4)
    use_face_detection: bool = True
    autocaption: bool = True
    caption_dropout_rate: float = Field(default=0.05, ge=0, le=0.5)


class LoraModelCreate(LoraModelBase):
    """Create a new LoRA model (training job)"""
    brand_id: int
    config: Optional[LoraTrainingConfig] = None


class LoraModelUpdate(BaseModel):
    """Update LoRA model settings"""
    name: Optional[str] = None
    trigger_word: Optional[str] = None
    is_active: Optional[bool] = None
    is_public: Optional[bool] = None


class LoraModelResponse(LoraModelBase):
    id: int
    brand_id: int
    version: int
    base_model: str
    status: TrainingStatusEnum
    progress_percent: int
    
    # Quality
    consistency_score: Optional[float]
    test_images_generated: int
    
    # Cost
    training_cost_usd: Optional[float]
    training_duration_seconds: Optional[int]
    
    # Settings
    is_active: bool
    is_public: bool
    
    # Config
    training_steps: int
    learning_rate: float
    lora_rank: int
    resolution: int
    
    # Replicate
    replicate_model_name: Optional[str]
    lora_weights_url: Optional[str]
    
    # Timestamps
    created_at: Optional[datetime] = None
    training_started_at: Optional[datetime]
    training_completed_at: Optional[datetime]
    
    # Counts
    reference_image_count: int = 0
    
    class Config:
        from_attributes = True


class LoraModelDetailResponse(LoraModelResponse):
    """Detailed response including reference images and samples"""
    reference_images: List[ReferenceImageResponse] = []
    recent_samples: List["GeneratedSampleResponse"] = []
    error_message: Optional[str]


# ========== Training Schemas ==========

class StartTrainingRequest(BaseModel):
    """Request to start training"""
    config: Optional[LoraTrainingConfig] = None


class TrainingProgressResponse(BaseModel):
    """Training progress update"""
    lora_model_id: int
    status: TrainingStatusEnum
    progress_percent: int
    current_step: Optional[int]
    total_steps: Optional[int]
    eta_seconds: Optional[int]
    error_message: Optional[str]
    logs: Optional[List[str]]


class TrainingQueueResponse(BaseModel):
    """Queue status"""
    position: int
    estimated_start: Optional[datetime]
    estimated_completion: Optional[datetime]
    users_ahead: int


# ========== Generation Schemas ==========

class GenerateWithLoraRequest(BaseModel):
    """Generate image using trained LoRA"""
    lora_model_id: int
    prompt: str = Field(..., min_length=1, max_length=2000)
    negative_prompt: Optional[str] = None
    
    # Generation settings
    lora_scale: float = Field(default=1.0, ge=0.1, le=2.0)
    guidance_scale: float = Field(default=3.5, ge=1.0, le=20.0)
    num_inference_steps: int = Field(default=28, ge=1, le=50)
    seed: Optional[int] = None
    
    # Output settings
    aspect_ratio: str = Field(default="1:1")  # 1:1, 16:9, 9:16, 4:3, 3:4
    num_outputs: int = Field(default=1, ge=1, le=4)


class GeneratedSampleResponse(BaseModel):
    id: int
    prompt: str
    image_url: str
    consistency_score: Optional[float]
    face_similarity_score: Optional[float]
    lora_scale: float
    seed: Optional[int]
    user_rating: Optional[int]
    is_test_sample: bool
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class GenerateWithLoraResponse(BaseModel):
    """Response from generation"""
    samples: List[GeneratedSampleResponse]
    generation_time_seconds: float
    cost_usd: float


# ========== Batch Generation Schemas ==========

class BatchGenerateRequest(BaseModel):
    """Generate multiple images with different prompts"""
    lora_model_id: int
    prompts: List[str] = Field(..., min_items=1, max_items=10)
    
    # Shared settings
    lora_scale: float = Field(default=1.0, ge=0.1, le=2.0)
    guidance_scale: float = Field(default=3.5, ge=1.0, le=20.0)
    aspect_ratio: str = Field(default="1:1")


class ScenarioGenerateRequest(BaseModel):
    """Generate avatar in predefined scenarios"""
    lora_model_id: int
    scenario: str  # "professional", "casual", "outdoor", "studio", etc.
    custom_details: Optional[str] = None
    num_variations: int = Field(default=4, ge=1, le=8)


# ========== Quality Assessment Schemas ==========

class ConsistencyCheckRequest(BaseModel):
    """Check consistency of generated image against reference"""
    generated_image_url: str
    lora_model_id: int


class ConsistencyCheckResponse(BaseModel):
    overall_score: float  # 0-100
    face_similarity: float
    style_consistency: float
    prompt_adherence: float
    quality_score: float
    issues: List[str]
    recommendations: List[str]


class RateSampleRequest(BaseModel):
    """User rating for a generated sample"""
    rating: int = Field(..., ge=1, le=5)
    feedback: Optional[str] = None


# ========== Statistics Schemas ==========

class LoraUsageStats(BaseModel):
    """Usage statistics for a LoRA model"""
    total_generations: int
    total_cost_usd: float
    average_consistency_score: float
    average_user_rating: Optional[float]
    generations_this_month: int
    most_used_prompts: List[str]


class UserLoraStats(BaseModel):
    """User's LoRA training statistics"""
    total_models: int
    active_models: int
    total_training_cost: float
    total_generation_cost: float
    total_generations: int
    average_consistency: float


# Forward reference update
LoraModelDetailResponse.model_rebuild()

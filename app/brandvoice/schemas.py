"""
Brand Voice AI Pydantic Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ========== Examples ==========

class AddExampleRequest(BaseModel):
    content: str = Field(..., min_length=20, max_length=5000)
    content_type: Optional[str] = None  # social_post, blog, email, etc.
    platform: Optional[str] = None  # twitter, instagram, linkedin, etc.


class AddExamplesBulkRequest(BaseModel):
    examples: List[AddExampleRequest] = Field(..., min_length=1, max_length=50)


class ExampleResponse(BaseModel):
    id: int
    content: str
    content_type: Optional[str]
    platform: Optional[str]
    analysis: Optional[Dict[str, Any]]
    is_high_quality: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# ========== Voice Profile ==========

class VoiceResponse(BaseModel):
    brand_id: int
    is_trained: bool
    training_status: str
    example_count: int
    characteristics: Optional[Dict[str, Any]]
    default_strength: float
    times_used: int
    last_used_at: Optional[datetime]
    trained_at: Optional[datetime]
    user_satisfaction_avg: Optional[float]
    
    class Config:
        from_attributes = True


class VoiceStatsResponse(BaseModel):
    trained: bool
    training_status: str
    example_count: int
    times_used: int
    last_used_at: Optional[str]
    trained_at: Optional[str]
    avg_satisfaction: Optional[float]
    total_generations: int
    rated_generations: int
    characteristics: Optional[Dict[str, Any]]


# ========== Training ==========

class TrainVoiceRequest(BaseModel):
    """Request to train/retrain voice"""
    pass  # No additional params needed, uses existing examples


class TrainVoiceResponse(BaseModel):
    success: bool
    message: str
    characteristics: Optional[Dict[str, Any]]


# ========== Generation ==========

class GenerateWithVoiceRequest(BaseModel):
    prompt: str = Field(..., min_length=5, max_length=2000)
    content_type: str = Field(default="social_post")
    platform: Optional[str] = None
    voice_strength: float = Field(default=0.8, ge=0.0, le=1.0)
    max_length: Optional[int] = Field(None, ge=50, le=10000)


class GenerateVariationsRequest(BaseModel):
    prompt: str = Field(..., min_length=5, max_length=2000)
    num_variations: int = Field(default=3, ge=1, le=5)
    platform: Optional[str] = None


class GenerationResponse(BaseModel):
    content: str
    voice_strength: float
    content_type: str
    platform: Optional[str]
    generation_id: int
    characteristics_applied: List[str]


class VariationsResponse(BaseModel):
    variations: List[GenerationResponse]
    count: int


# ========== Feedback ==========

class RecordFeedbackRequest(BaseModel):
    generation_id: int
    rating: int = Field(..., ge=1, le=5)
    voice_match_score: Optional[int] = Field(None, ge=1, le=5)
    notes: Optional[str] = Field(None, max_length=500)


class FeedbackResponse(BaseModel):
    success: bool
    generation_id: int
    rating: int
    voice_match_score: Optional[int]


# ========== Analysis ==========

class AnalyzeTextRequest(BaseModel):
    """Analyze text without adding as example"""
    content: str = Field(..., min_length=20, max_length=5000)


class TextAnalysisResponse(BaseModel):
    word_count: int
    char_count: int
    sentence_count: int
    avg_sentence_length: float
    emoji_count: int
    hashtag_count: int
    question_count: int
    exclamation_count: int
    has_cta: bool
    readability_score: Optional[float] = None

"""
Video Generation Database Models

Supports:
- Talking head videos with LoRA avatars
- Text-to-speech with multiple voices
- Lip-sync animation
- Video templates and presets
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey,
    Boolean, Float, Enum, JSON
)
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class VideoStatus(enum.Enum):
    """Video generation status"""
    PENDING = "pending"
    GENERATING_AUDIO = "generating_audio"
    GENERATING_AVATAR = "generating_avatar"
    GENERATING_VIDEO = "generating_video"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class VoiceProvider(enum.Enum):
    """Text-to-speech providers"""
    ELEVENLABS = "elevenlabs"
    OPENAI = "openai"
    AZURE = "azure"


class VideoAspectRatio(enum.Enum):
    """Video aspect ratios"""
    SQUARE = "1:1"       # Instagram, Facebook
    PORTRAIT = "9:16"    # TikTok, Reels, Shorts
    LANDSCAPE = "16:9"   # YouTube, LinkedIn
    VERTICAL = "4:5"     # Instagram Feed


class GeneratedVideo(Base):
    """Generated talking head video"""
    __tablename__ = "generated_videos"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    brand_id = Column(Integer, ForeignKey('brands.id', ondelete='SET NULL'), nullable=True)
    lora_model_id = Column(Integer, ForeignKey('lora_models.id', ondelete='SET NULL'), nullable=True)
    
    # Content
    title = Column(String(255), nullable=True)
    script = Column(Text, nullable=False)  # The text to speak
    
    # Voice settings
    voice_provider = Column(Enum(VoiceProvider), default=VoiceProvider.ELEVENLABS)
    voice_id = Column(String(100), nullable=True)  # Provider-specific voice ID
    voice_name = Column(String(100), nullable=True)
    voice_settings = Column(JSON, nullable=True)  # stability, similarity, speed, etc.
    
    # Avatar settings
    avatar_image_url = Column(Text, nullable=True)  # Base image for animation
    avatar_prompt = Column(Text, nullable=True)  # If generating new avatar image
    use_lora = Column(Boolean, default=True)
    
    # Video settings
    aspect_ratio = Column(Enum(VideoAspectRatio), default=VideoAspectRatio.PORTRAIT)
    resolution = Column(String(20), default="1080x1920")  # WxH
    fps = Column(Integer, default=30)
    background_color = Column(String(20), default="#000000")
    background_image_url = Column(Text, nullable=True)
    
    # Animation settings
    expression = Column(String(50), default="neutral")  # neutral, happy, serious, excited
    head_movement = Column(String(50), default="natural")  # none, subtle, natural, dynamic
    eye_contact = Column(Boolean, default=True)
    
    # Output
    status = Column(Enum(VideoStatus), default=VideoStatus.PENDING)
    progress_percent = Column(Integer, default=0)
    
    # Generated assets
    audio_url = Column(Text, nullable=True)
    audio_duration_seconds = Column(Float, nullable=True)
    avatar_image_generated_url = Column(Text, nullable=True)
    video_url = Column(Text, nullable=True)
    thumbnail_url = Column(Text, nullable=True)
    
    # Processing info
    error_message = Column(Text, nullable=True)
    processing_started_at = Column(DateTime, nullable=True)
    processing_completed_at = Column(DateTime, nullable=True)
    
    # External IDs
    replicate_audio_id = Column(String(255), nullable=True)
    replicate_video_id = Column(String(255), nullable=True)
    
    # Cost tracking
    audio_cost_usd = Column(Float, default=0.0)
    video_cost_usd = Column(Float, default=0.0)
    total_cost_usd = Column(Float, default=0.0)
    
    # Metadata
    metadata = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    owner = relationship("User")
    brand = relationship("Brand")
    lora_model = relationship("LoraModel")


class VideoTemplate(Base):
    """Reusable video templates/presets"""
    __tablename__ = "video_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=True)  # NULL = system template
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True)  # marketing, educational, social, etc.
    
    # Template settings
    voice_provider = Column(Enum(VoiceProvider), default=VoiceProvider.ELEVENLABS)
    voice_id = Column(String(100), nullable=True)
    voice_settings = Column(JSON, nullable=True)
    
    aspect_ratio = Column(Enum(VideoAspectRatio), default=VideoAspectRatio.PORTRAIT)
    resolution = Column(String(20), default="1080x1920")
    
    expression = Column(String(50), default="neutral")
    head_movement = Column(String(50), default="natural")
    
    background_color = Column(String(20), default="#000000")
    background_image_url = Column(Text, nullable=True)
    
    # Script template (with placeholders like {{product_name}})
    script_template = Column(Text, nullable=True)
    
    # Preview
    preview_thumbnail_url = Column(Text, nullable=True)
    preview_video_url = Column(Text, nullable=True)
    
    is_public = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    owner = relationship("User")


class VoiceClone(Base):
    """Custom cloned voices"""
    __tablename__ = "voice_clones"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Provider info
    provider = Column(Enum(VoiceProvider), default=VoiceProvider.ELEVENLABS)
    provider_voice_id = Column(String(255), nullable=True)
    
    # Sample audio used for cloning
    sample_audio_urls = Column(JSON, nullable=True)  # List of audio file URLs
    
    # Voice characteristics
    gender = Column(String(20), nullable=True)
    age_range = Column(String(20), nullable=True)  # young, middle, mature
    accent = Column(String(50), nullable=True)
    
    # Status
    is_ready = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Usage stats
    times_used = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    owner = relationship("User")


# Voice presets for quick selection
PRESET_VOICES = {
    "elevenlabs": [
        {"id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel", "gender": "female", "accent": "American", "style": "calm"},
        {"id": "AZnzlk1XvdvUeBnXmlld", "name": "Domi", "gender": "female", "accent": "American", "style": "confident"},
        {"id": "EXAVITQu4vr4xnSDxMaL", "name": "Bella", "gender": "female", "accent": "American", "style": "soft"},
        {"id": "ErXwobaYiN019PkySvjV", "name": "Antoni", "gender": "male", "accent": "American", "style": "friendly"},
        {"id": "MF3mGyEYCl7XYWbV9V6O", "name": "Elli", "gender": "female", "accent": "American", "style": "young"},
        {"id": "TxGEqnHWrfWFTfGW9XjX", "name": "Josh", "gender": "male", "accent": "American", "style": "deep"},
        {"id": "VR6AewLTigWG4xSOukaG", "name": "Arnold", "gender": "male", "accent": "American", "style": "bold"},
        {"id": "pNInz6obpgDQGcFmaJgB", "name": "Adam", "gender": "male", "accent": "American", "style": "deep"},
        {"id": "yoZ06aMxZJJ28mfd3POQ", "name": "Sam", "gender": "male", "accent": "American", "style": "raspy"},
    ],
    "openai": [
        {"id": "alloy", "name": "Alloy", "gender": "neutral", "style": "balanced"},
        {"id": "echo", "name": "Echo", "gender": "male", "style": "natural"},
        {"id": "fable", "name": "Fable", "gender": "male", "style": "expressive"},
        {"id": "onyx", "name": "Onyx", "gender": "male", "style": "deep"},
        {"id": "nova", "name": "Nova", "gender": "female", "style": "friendly"},
        {"id": "shimmer", "name": "Shimmer", "gender": "female", "style": "warm"},
    ]
}

# Expression presets
EXPRESSION_PRESETS = {
    "neutral": {"description": "Natural, professional expression"},
    "happy": {"description": "Warm smile, friendly demeanor"},
    "serious": {"description": "Professional, authoritative look"},
    "excited": {"description": "Enthusiastic, energetic expression"},
    "concerned": {"description": "Thoughtful, empathetic expression"},
    "confident": {"description": "Self-assured, bold expression"},
}

# Video cost estimates (per second)
VIDEO_COSTS = {
    "audio_per_char": 0.00003,  # ~$0.03 per 1000 chars (ElevenLabs)
    "avatar_generation": 0.003,  # Per image via Replicate
    "video_per_second": 0.05,   # Lip-sync generation
    "processing_base": 0.10,    # Base processing fee
}

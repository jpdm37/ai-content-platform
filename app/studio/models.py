"""
AI Content Studio Models

The Content Studio is a unified workflow that generates multiple content types
from a single brief: text variations, images, videos, and platform-optimized versions.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey,
    Boolean, Float, Enum, JSON
)
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class StudioProjectStatus(enum.Enum):
    """Project generation status"""
    DRAFT = "draft"
    GENERATING = "generating"
    COMPLETED = "completed"
    PARTIAL = "partial"  # Some assets failed
    FAILED = "failed"


class ContentType(enum.Enum):
    """Types of content that can be generated"""
    CAPTION = "caption"
    IMAGE = "image"
    VIDEO = "video"
    HASHTAGS = "hashtags"
    HOOK = "hook"
    CTA = "cta"


class StudioProject(Base):
    """
    A Content Studio project - generates multiple assets from one brief.
    
    User provides:
    - Brief/topic
    - Brand (optional)
    - Target platforms
    - Content preferences
    
    System generates:
    - Multiple caption variations
    - Multiple image options
    - Video (if requested)
    - Platform-specific versions
    - Hashtag suggestions
    - Best posting times
    """
    __tablename__ = "studio_projects"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    brand_id = Column(Integer, ForeignKey('brands.id', ondelete='SET NULL'), nullable=True)
    
    # Project info
    name = Column(String(255), nullable=True)
    brief = Column(Text, nullable=False)  # User's content brief/topic
    
    # Generation settings
    target_platforms = Column(JSON, default=list)  # ["twitter", "instagram", "linkedin"]
    content_types = Column(JSON, default=list)  # ["caption", "image", "video"]
    tone = Column(String(50), default="professional")  # professional, casual, humorous, etc.
    num_variations = Column(Integer, default=3)  # Number of caption variations
    
    # LoRA/Avatar settings (for video)
    lora_model_id = Column(Integer, ForeignKey('lora_models.id', ondelete='SET NULL'), nullable=True)
    include_video = Column(Boolean, default=False)
    video_duration = Column(String(20), default="30s")  # 15s, 30s, 60s
    
    # Status
    status = Column(Enum(StudioProjectStatus), default=StudioProjectStatus.DRAFT)
    progress_percent = Column(Integer, default=0)
    current_step = Column(String(100), nullable=True)
    
    # Generated content summary
    captions_generated = Column(Integer, default=0)
    images_generated = Column(Integer, default=0)
    videos_generated = Column(Integer, default=0)
    
    # Cost tracking
    total_cost_usd = Column(Float, default=0.0)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    owner = relationship("User")
    brand = relationship("Brand")
    lora_model = relationship("LoraModel")
    assets = relationship("StudioAsset", back_populates="project", cascade="all, delete-orphan")


class StudioAsset(Base):
    """
    Individual generated asset within a project.
    """
    __tablename__ = "studio_assets"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('studio_projects.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Asset type and content
    content_type = Column(Enum(ContentType), nullable=False)
    
    # For text content (captions, hashtags, hooks, CTAs)
    text_content = Column(Text, nullable=True)
    
    # For media content (images, videos)
    media_url = Column(Text, nullable=True)
    thumbnail_url = Column(Text, nullable=True)
    
    # Platform-specific versions
    platform = Column(String(50), nullable=True)  # twitter, instagram, linkedin, tiktok
    platform_optimized = Column(JSON, nullable=True)  # Platform-specific adjustments
    
    # Variation tracking
    variation_number = Column(Integer, default=1)
    
    # User feedback
    is_favorite = Column(Boolean, default=False)
    is_selected = Column(Boolean, default=False)  # Selected for use
    user_rating = Column(Integer, nullable=True)  # 1-5 stars
    
    # AI metadata
    ai_model_used = Column(String(100), nullable=True)
    prompt_used = Column(Text, nullable=True)
    generation_params = Column(JSON, nullable=True)
    
    # Cost
    cost_usd = Column(Float, default=0.0)
    
    # Status
    status = Column(String(20), default="completed")  # pending, completed, failed
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    project = relationship("StudioProject", back_populates="assets")


class StudioTemplate(Base):
    """
    Reusable studio templates for common content types.
    """
    __tablename__ = "studio_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=True)  # NULL = system template
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True)  # product_launch, announcement, educational, etc.
    
    # Template configuration
    brief_template = Column(Text, nullable=True)  # Template with {{variables}}
    target_platforms = Column(JSON, default=list)
    content_types = Column(JSON, default=list)
    tone = Column(String(50), default="professional")
    num_variations = Column(Integer, default=3)
    include_video = Column(Boolean, default=False)
    
    # Preview
    preview_image_url = Column(Text, nullable=True)
    
    is_public = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    times_used = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    owner = relationship("User")


# Content generation prompts
STUDIO_PROMPTS = {
    "caption": {
        "professional": "Write a professional, engaging social media caption for: {brief}. Brand voice: {brand_voice}. Platform: {platform}. Keep it concise and include a clear call-to-action.",
        "casual": "Write a casual, friendly social media caption for: {brief}. Brand voice: {brand_voice}. Platform: {platform}. Use conversational language and emojis where appropriate.",
        "humorous": "Write a witty, humorous social media caption for: {brief}. Brand voice: {brand_voice}. Platform: {platform}. Be clever but keep it brand-appropriate.",
        "inspirational": "Write an inspirational, motivating social media caption for: {brief}. Brand voice: {brand_voice}. Platform: {platform}. Connect emotionally with the audience.",
    },
    "hashtags": "Generate 10-15 relevant hashtags for this content: {brief}. Platform: {platform}. Mix popular and niche hashtags. Return only hashtags, one per line.",
    "hook": "Write 3 attention-grabbing opening hooks for: {brief}. These should stop the scroll and make people want to read more. One per line.",
    "cta": "Write 3 compelling call-to-action phrases for: {brief}. These should drive engagement or conversions. One per line.",
    "image_prompt": "Create a detailed image generation prompt for: {brief}. Style: professional, modern, visually striking. The image should work well on social media.",
    "video_script": "Write a {duration} video script for: {brief}. Brand voice: {brand_voice}. Include: hook (first 3 seconds), main content, and call-to-action. Keep it conversational and engaging.",
}

# Platform-specific adjustments
PLATFORM_SPECS = {
    "twitter": {
        "max_chars": 280,
        "hashtag_limit": 3,
        "image_ratio": "16:9",
        "video_max_duration": 140,
    },
    "instagram": {
        "max_chars": 2200,
        "hashtag_limit": 30,
        "image_ratio": "1:1",
        "video_max_duration": 60,
    },
    "linkedin": {
        "max_chars": 3000,
        "hashtag_limit": 5,
        "image_ratio": "1.91:1",
        "video_max_duration": 600,
    },
    "tiktok": {
        "max_chars": 2200,
        "hashtag_limit": 5,
        "image_ratio": "9:16",
        "video_max_duration": 180,
    },
    "facebook": {
        "max_chars": 63206,
        "hashtag_limit": 5,
        "image_ratio": "1.91:1",
        "video_max_duration": 240,
    },
}

# Tone descriptions for AI
TONE_DESCRIPTIONS = {
    "professional": "formal, authoritative, trustworthy, industry-expert",
    "casual": "friendly, approachable, conversational, relatable",
    "humorous": "witty, playful, clever, entertaining",
    "inspirational": "motivating, uplifting, empowering, emotional",
    "educational": "informative, clear, helpful, teacher-like",
    "urgent": "time-sensitive, action-oriented, compelling, FOMO-inducing",
    "storytelling": "narrative, engaging, personal, journey-focused",
}

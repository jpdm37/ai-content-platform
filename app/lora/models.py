"""
LoRA Training and Avatar Consistency Database Models
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, 
    Boolean, Float, Enum, JSON
)
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class TrainingStatus(enum.Enum):
    """Status of a LoRA training job"""
    PENDING = "pending"           # Waiting to start
    VALIDATING = "validating"     # Validating images
    UPLOADING = "uploading"       # Uploading to Replicate
    TRAINING = "training"         # Training in progress
    COMPLETED = "completed"       # Successfully completed
    FAILED = "failed"             # Training failed
    CANCELLED = "cancelled"       # Cancelled by user


class ImageValidationStatus(enum.Enum):
    """Status of reference image validation"""
    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"
    PROCESSING = "processing"


class LoraModel(Base):
    """
    Trained LoRA model for consistent avatar generation.
    Each brand can have multiple LoRA versions.
    """
    __tablename__ = "lora_models"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    brand_id = Column(Integer, ForeignKey('brands.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Model identification
    name = Column(String(255), nullable=False)
    version = Column(Integer, default=1)
    trigger_word = Column(String(100), nullable=False)  # e.g., "TOK", "AVATAR_JANE"
    
    # Training configuration
    base_model = Column(String(100), default="flux-dev")  # flux-dev, flux-schnell, sdxl
    training_steps = Column(Integer, default=1000)
    learning_rate = Column(Float, default=0.0004)
    lora_rank = Column(Integer, default=16)
    resolution = Column(Integer, default=1024)
    
    # Replicate-specific
    replicate_training_id = Column(String(255), nullable=True)
    replicate_model_owner = Column(String(255), nullable=True)
    replicate_model_name = Column(String(255), nullable=True)
    replicate_version = Column(String(255), nullable=True)
    
    # LoRA weights storage
    lora_weights_url = Column(Text, nullable=True)  # URL to download weights
    lora_weights_size_mb = Column(Float, nullable=True)
    
    # Training status
    status = Column(Enum(TrainingStatus), default=TrainingStatus.PENDING)
    progress_percent = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    
    # Quality metrics
    consistency_score = Column(Float, nullable=True)  # 0-100 score
    test_images_generated = Column(Integer, default=0)
    
    # Cost tracking
    training_cost_usd = Column(Float, nullable=True)
    training_duration_seconds = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    training_started_at = Column(DateTime, nullable=True)
    training_completed_at = Column(DateTime, nullable=True)
    
    # Settings
    is_active = Column(Boolean, default=False)  # Only one active per brand
    is_public = Column(Boolean, default=False)  # Allow others to use
    
    # Relationships
    owner = relationship("User")
    brand = relationship("Brand")
    reference_images = relationship("LoraReferenceImage", back_populates="lora_model", cascade="all, delete-orphan")
    generated_samples = relationship("LoraGeneratedSample", back_populates="lora_model", cascade="all, delete-orphan")


class LoraReferenceImage(Base):
    """
    Reference images used to train a LoRA model.
    Typically 10-30 images of the avatar/person.
    """
    __tablename__ = "lora_reference_images"
    
    id = Column(Integer, primary_key=True, index=True)
    lora_model_id = Column(Integer, ForeignKey('lora_models.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Original upload
    original_url = Column(Text, nullable=False)
    original_filename = Column(String(255))
    original_size_bytes = Column(Integer)
    
    # Processed version (cropped, resized)
    processed_url = Column(Text, nullable=True)
    processed_width = Column(Integer, nullable=True)
    processed_height = Column(Integer, nullable=True)
    
    # Auto-generated caption
    caption = Column(Text, nullable=True)
    custom_caption = Column(Text, nullable=True)  # User override
    
    # Face detection results
    face_detected = Column(Boolean, default=False)
    face_confidence = Column(Float, nullable=True)
    face_bbox = Column(JSON, nullable=True)  # {x, y, width, height}
    
    # Validation
    validation_status = Column(Enum(ImageValidationStatus), default=ImageValidationStatus.PENDING)
    validation_errors = Column(JSON, nullable=True)  # List of error messages
    quality_score = Column(Float, nullable=True)  # 0-100
    
    # Metadata
    image_type = Column(String(50), nullable=True)  # headshot, full_body, profile, etc.
    is_included_in_training = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    lora_model = relationship("LoraModel", back_populates="reference_images")


class LoraGeneratedSample(Base):
    """
    Sample images generated during/after training for quality assessment.
    """
    __tablename__ = "lora_generated_samples"
    
    id = Column(Integer, primary_key=True, index=True)
    lora_model_id = Column(Integer, ForeignKey('lora_models.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Generation details
    prompt = Column(Text, nullable=False)
    negative_prompt = Column(Text, nullable=True)
    seed = Column(Integer, nullable=True)
    
    # Result
    image_url = Column(Text, nullable=False)
    
    # Quality assessment
    consistency_score = Column(Float, nullable=True)  # 0-100 similarity to reference
    face_similarity_score = Column(Float, nullable=True)
    style_score = Column(Float, nullable=True)
    
    # Generation params
    lora_scale = Column(Float, default=1.0)
    guidance_scale = Column(Float, default=3.5)
    num_inference_steps = Column(Integer, default=28)
    
    # User feedback
    user_rating = Column(Integer, nullable=True)  # 1-5 stars
    user_feedback = Column(Text, nullable=True)
    
    is_test_sample = Column(Boolean, default=False)  # Generated during training
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    lora_model = relationship("LoraModel", back_populates="generated_samples")


class LoraTrainingQueue(Base):
    """
    Queue for managing LoRA training jobs.
    Prevents too many concurrent trainings.
    """
    __tablename__ = "lora_training_queue"
    
    id = Column(Integer, primary_key=True, index=True)
    lora_model_id = Column(Integer, ForeignKey('lora_models.id', ondelete='CASCADE'), nullable=False, unique=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Queue position
    priority = Column(Integer, default=0)  # Higher = more priority
    position = Column(Integer, nullable=True)
    
    # Timing
    queued_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    estimated_completion = Column(DateTime, nullable=True)
    
    # Status
    is_processing = Column(Boolean, default=False)
    
    # Relationships
    lora_model = relationship("LoraModel")
    user = relationship("User")


class LoraUsageLog(Base):
    """
    Track usage of LoRA models for billing and analytics.
    """
    __tablename__ = "lora_usage_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    lora_model_id = Column(Integer, ForeignKey('lora_models.id', ondelete='SET NULL'), nullable=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Usage type
    usage_type = Column(String(50), nullable=False)  # "generation", "training", "test"
    
    # Generation details
    prompt = Column(Text, nullable=True)
    result_url = Column(Text, nullable=True)
    
    # Cost
    cost_usd = Column(Float, nullable=True)
    compute_seconds = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    lora_model = relationship("LoraModel")
    user = relationship("User")

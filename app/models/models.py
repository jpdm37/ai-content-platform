"""
SQLAlchemy Database Models
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, 
    Enum, JSON, Boolean, Table
)
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class ContentType(enum.Enum):
    IMAGE = "image"
    TEXT = "text"
    VIDEO = "video"


class ContentStatus(enum.Enum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


# Association table for many-to-many relationship
brand_categories = Table(
    'brand_categories',
    Base.metadata,
    Column('brand_id', Integer, ForeignKey('brands.id'), primary_key=True),
    Column('category_id', Integer, ForeignKey('categories.id'), primary_key=True)
)


class Brand(Base):
    """Brand/Company with AI avatar configuration"""
    __tablename__ = "brands"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    
    # AI Persona configuration
    persona_name = Column(String(255))
    persona_age = Column(String(50))
    persona_gender = Column(String(50))
    persona_style = Column(Text)  # Visual style description
    persona_voice = Column(Text)  # Writing style/tone
    persona_traits = Column(JSON)  # List of personality traits
    
    # Reference image URL (for consistency)
    reference_image_url = Column(Text)
    
    # Brand colors/style
    brand_colors = Column(JSON)  # List of hex colors
    brand_keywords = Column(JSON)  # Keywords for content
    
    # Target audience
    target_audience = Column(Text)
    
    # Template/Demo flags
    is_demo = Column(Boolean, default=False)  # Demo brand for new users
    is_template = Column(Boolean, default=False)  # Template brand
    template_id = Column(String(100), nullable=True)  # Which template was used
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    owner = relationship("User", back_populates="brands")
    categories = relationship("Category", secondary=brand_categories, back_populates="brands")
    generated_content = relationship("GeneratedContent", back_populates="brand")


class Category(Base):
    """Content categories (lifestyle, travel, etc.)"""
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text)
    keywords = Column(JSON)  # Keywords for trend scraping
    
    # Prompt templates for this category
    image_prompt_template = Column(Text)
    caption_prompt_template = Column(Text)
    
    # Ownership - if user_id is NULL, it's a global category (admin-managed)
    # if user_id is set, it's a custom niche owned by that user
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)
    is_global = Column(Boolean, default=True)  # True = admin category, False = user custom niche
    
    # For custom niches - additional customization
    custom_rss_feeds = Column(JSON, nullable=True)  # User can add their own RSS feeds
    custom_google_news_query = Column(Text, nullable=True)  # Custom Google News search query
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    owner = relationship("User", foreign_keys=[user_id])
    brands = relationship("Brand", secondary=brand_categories, back_populates="categories")
    trends = relationship("Trend", back_populates="category")
    generated_content = relationship("GeneratedContent", back_populates="category")


class Trend(Base):
    """Scraped trending topics"""
    __tablename__ = "trends"
    
    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    
    title = Column(String(500), nullable=False)
    description = Column(Text)
    source = Column(String(100))  # google_trends, news_api, rss, etc.
    source_url = Column(Text)
    
    # Trend metrics
    popularity_score = Column(Integer, default=0)
    related_keywords = Column(JSON)
    
    scraped_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)  # When this trend data is stale
    
    # Relationships
    category = relationship("Category", back_populates="trends")
    generated_content = relationship("GeneratedContent", back_populates="trend")


class GeneratedContent(Base):
    """Generated images, text, and videos"""
    __tablename__ = "generated_content"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    brand_id = Column(Integer, ForeignKey('brands.id'), nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id'))
    trend_id = Column(Integer, ForeignKey('trends.id'))
    
    content_type = Column(Enum(ContentType), nullable=False)
    status = Column(Enum(ContentStatus), default=ContentStatus.PENDING)
    
    # Generation details
    prompt_used = Column(Text)
    negative_prompt = Column(Text)
    
    # Results
    result_url = Column(Text)  # URL to generated image/video
    caption = Column(Text)  # Generated caption/post text
    hashtags = Column(JSON)  # Generated hashtags
    
    # Metadata
    generation_params = Column(JSON)  # Model params used
    error_message = Column(Text)  # If failed
    
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # Relationships
    owner = relationship("User", back_populates="generated_content")
    brand = relationship("Brand", back_populates="generated_content")
    category = relationship("Category", back_populates="generated_content")
    trend = relationship("Trend", back_populates="generated_content")


class ScheduledPost(Base):
    """Posts scheduled for social media"""
    __tablename__ = "scheduled_posts"
    
    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(Integer, ForeignKey('generated_content.id'), nullable=False)
    
    platform = Column(String(50))  # instagram, tiktok, twitter, etc.
    scheduled_time = Column(DateTime)
    
    is_posted = Column(Boolean, default=False)
    posted_at = Column(DateTime)
    post_url = Column(Text)  # URL to the live post
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    content = relationship("GeneratedContent")

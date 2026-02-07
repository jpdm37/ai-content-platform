"""
Social Media Integration Database Models
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey,
    Boolean, Enum, JSON
)
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class SocialPlatform(enum.Enum):
    """Supported social media platforms"""
    TWITTER = "twitter"
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    TIKTOK = "tiktok"
    FACEBOOK = "facebook"
    THREADS = "threads"


class PostStatus(enum.Enum):
    """Status of a scheduled/published post"""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SocialAccount(Base):
    """Connected social media account"""
    __tablename__ = "social_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    brand_id = Column(Integer, ForeignKey('brands.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # Platform info
    platform = Column(Enum(SocialPlatform), nullable=False)
    platform_user_id = Column(String(255), nullable=False)
    platform_username = Column(String(255), nullable=True)
    platform_display_name = Column(String(255), nullable=True)
    profile_image_url = Column(Text, nullable=True)
    
    # OAuth tokens - ENCRYPTED AT REST
    _access_token = Column('access_token', Text, nullable=True)
    _refresh_token = Column('refresh_token', Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    
    @property
    def access_token(self) -> str:
        """Decrypt and return the access token."""
        from app.core.encryption import decrypt_field
        return decrypt_field(self._access_token)
    
    @access_token.setter
    def access_token(self, value: str):
        """Encrypt and store the access token."""
        from app.core.encryption import encrypt_field
        self._access_token = encrypt_field(value)
    
    @property
    def refresh_token(self) -> str:
        """Decrypt and return the refresh token."""
        from app.core.encryption import decrypt_field
        return decrypt_field(self._refresh_token)
    
    @refresh_token.setter
    def refresh_token(self, value: str):
        """Encrypt and store the refresh token."""
        from app.core.encryption import encrypt_field
        self._refresh_token = encrypt_field(value)
    
    # Account status
    is_active = Column(Boolean, default=True)
    last_synced_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    
    # Platform-specific data
    platform_data = Column(JSON, nullable=True)  # Followers, etc.
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    owner = relationship("User")
    brand = relationship("Brand")
    scheduled_posts = relationship("ScheduledSocialPost", back_populates="social_account", cascade="all, delete-orphan")


class ScheduledSocialPost(Base):
    """Scheduled social media post"""
    __tablename__ = "scheduled_social_posts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    social_account_id = Column(Integer, ForeignKey('social_accounts.id', ondelete='CASCADE'), nullable=False, index=True)
    brand_id = Column(Integer, ForeignKey('brands.id', ondelete='SET NULL'), nullable=True)
    
    # Content reference (optional - can be standalone)
    generated_content_id = Column(Integer, ForeignKey('generated_content.id', ondelete='SET NULL'), nullable=True)
    
    # Post content
    caption = Column(Text, nullable=True)
    hashtags = Column(JSON, nullable=True)  # List of hashtags
    media_urls = Column(JSON, nullable=True)  # List of image/video URLs
    
    # Platform-specific content
    platform_specific = Column(JSON, nullable=True)  # Alt text, location, etc.
    
    # Scheduling
    scheduled_for = Column(DateTime, nullable=False, index=True)
    timezone = Column(String(50), default="UTC")
    
    # Status
    status = Column(Enum(PostStatus), default=PostStatus.SCHEDULED)
    
    # Publishing results
    published_at = Column(DateTime, nullable=True)
    platform_post_id = Column(String(255), nullable=True)
    platform_post_url = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Engagement tracking
    engagement_data = Column(JSON, nullable=True)  # Likes, comments, shares
    last_engagement_sync = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    owner = relationship("User")
    social_account = relationship("SocialAccount", back_populates="scheduled_posts")
    brand = relationship("Brand")
    generated_content = relationship("GeneratedContent")


class PostTemplate(Base):
    """Reusable post templates"""
    __tablename__ = "post_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    brand_id = Column(Integer, ForeignKey('brands.id', ondelete='SET NULL'), nullable=True)
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Template content
    caption_template = Column(Text, nullable=True)  # With {{variables}}
    default_hashtags = Column(JSON, nullable=True)
    
    # Settings
    platforms = Column(JSON, nullable=True)  # List of applicable platforms
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    owner = relationship("User")
    brand = relationship("Brand")


class PublishingLog(Base):
    """Log of all publishing attempts and engagement tracking"""
    __tablename__ = "publishing_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    scheduled_post_id = Column(Integer, ForeignKey('scheduled_social_posts.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)
    account_id = Column(Integer, ForeignKey('social_accounts.id', ondelete='SET NULL'), nullable=True)
    
    # Platform info
    platform = Column(Enum(SocialPlatform), nullable=True)
    platform_post_id = Column(String(255), nullable=True)
    post_url = Column(Text, nullable=True)
    
    # Post content (for reference)
    caption = Column(Text, nullable=True)
    
    # Attempt details
    attempt_number = Column(Integer, default=1)
    attempted_at = Column(DateTime, default=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)
    
    # Result
    success = Column(Boolean, default=False)
    error_code = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    response_data = Column(JSON, nullable=True)
    
    # Engagement tracking
    engagement_data = Column(JSON, nullable=True)  # likes, comments, shares, reach, impressions
    metrics_updated_at = Column(DateTime, nullable=True)
    
    # Relationships
    scheduled_post = relationship("ScheduledSocialPost")
    owner = relationship("User")
    account = relationship("SocialAccount")

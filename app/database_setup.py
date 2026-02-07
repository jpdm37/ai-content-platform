"""
Complete Database Schema
========================

This file creates all database tables in a single migration.
Run this for fresh installations - no need for incremental migrations.

Usage:
    python -c "from app.database_setup import create_all_tables; create_all_tables()"
    
Or via alembic:
    alembic upgrade head
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey,
    Boolean, Float, JSON, Enum, Index, UniqueConstraint,
    create_engine, MetaData
)
from sqlalchemy.orm import relationship, declarative_base
import enum

Base = declarative_base()


# ==================== Enums ====================

class ContentType(enum.Enum):
    IMAGE = "image"
    VIDEO = "video"
    TEXT = "text"
    CAROUSEL = "carousel"


class SocialPlatform(enum.Enum):
    TWITTER = "twitter"
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    TIKTOK = "tiktok"
    FACEBOOK = "facebook"
    THREADS = "threads"


class PostStatus(enum.Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PENDING = "pending"


class SubscriptionTier(enum.Enum):
    FREE = "free"
    CREATOR = "creator"
    PRO = "pro"
    AGENCY = "agency"


class LoraStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    TRAINING = "training"
    COMPLETED = "completed"
    FAILED = "failed"


class VideoStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TestStatus(enum.Enum):
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TestType(enum.Enum):
    CAPTION = "caption"
    HASHTAGS = "hashtags"
    IMAGE = "image"
    POSTING_TIME = "posting_time"
    CTA = "cta"


# ==================== User & Auth Tables ====================

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)
    
    # OAuth
    oauth_provider = Column(String(50), nullable=True)
    oauth_id = Column(String(255), nullable=True)
    
    # Verification
    verification_token = Column(String(255), nullable=True)
    verification_token_expires = Column(DateTime, nullable=True)
    
    # Password reset
    reset_token = Column(String(255), nullable=True)
    reset_token_expires = Column(DateTime, nullable=True)
    
    # Onboarding
    onboarding_data = Column(JSON, nullable=True)
    onboarding_completed = Column(Boolean, default=False)
    email_preferences = Column(JSON, nullable=True)
    
    # Usage tracking
    api_calls_today = Column(Integer, default=0)
    api_calls_reset_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    revoked = Column(Boolean, default=False)


# ==================== Core Content Tables ====================

class Category(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    keywords = Column(JSON, nullable=True)  # Keywords for trend scraping
    prompt_template = Column(Text, nullable=True)
    image_prompt_template = Column(Text, nullable=True)
    caption_prompt_template = Column(Text, nullable=True)
    image_style = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Ownership - if user_id is NULL, it's a global category (admin-managed)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)
    is_global = Column(Boolean, default=True)  # True = admin category, False = user custom niche
    
    # Custom niche settings
    custom_rss_feeds = Column(JSON, nullable=True)  # User can add their own RSS feeds
    custom_google_news_query = Column(Text, nullable=True)  # Custom Google News search
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Brand(Base):
    __tablename__ = "brands"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    personality = Column(Text, nullable=True)
    target_audience = Column(Text, nullable=True)
    visual_style = Column(Text, nullable=True)
    color_palette = Column(JSON, nullable=True)
    
    # Template flags
    is_demo = Column(Boolean, default=False)
    is_template = Column(Boolean, default=False)
    template_id = Column(String(100), nullable=True)
    
    # Avatar
    avatar_url = Column(Text, nullable=True)
    lora_model_id = Column(String(255), nullable=True)
    avatar_seed = Column(Integer, nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GeneratedContent(Base):
    __tablename__ = "generated_content"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    brand_id = Column(Integer, ForeignKey('brands.id', ondelete='SET NULL'), nullable=True, index=True)
    category_id = Column(Integer, ForeignKey('categories.id', ondelete='SET NULL'), nullable=True)
    
    content_type = Column(Enum(ContentType), default=ContentType.IMAGE)
    prompt = Column(Text, nullable=True)
    result_url = Column(Text, nullable=True)
    thumbnail_url = Column(Text, nullable=True)
    
    caption = Column(Text, nullable=True)
    hashtags = Column(JSON, nullable=True)
    
    # Generation details
    model_used = Column(String(100), nullable=True)
    generation_params = Column(JSON, nullable=True)
    cost_credits = Column(Float, default=0)
    
    is_published = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Trend(Base):
    __tablename__ = "trends"
    
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(50), nullable=False)
    title = Column(String(500), nullable=False)
    url = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    rank = Column(Integer, nullable=True)
    trend_metadata = Column(JSON, nullable=True)  # Renamed from 'metadata' (reserved word)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)


# ==================== LoRA Training Tables ====================

class LoraModel(Base):
    __tablename__ = "lora_models"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    brand_id = Column(Integer, ForeignKey('brands.id', ondelete='SET NULL'), nullable=True)
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    trigger_word = Column(String(100), nullable=False)
    
    status = Column(Enum(LoraStatus), default=LoraStatus.PENDING)
    replicate_model_id = Column(String(255), nullable=True)
    replicate_version = Column(String(255), nullable=True)
    replicate_training_id = Column(String(255), nullable=True)
    
    training_params = Column(JSON, nullable=True)
    training_started_at = Column(DateTime, nullable=True)
    training_completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    
    sample_images = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LoraTrainingImage(Base):
    __tablename__ = "lora_training_images"
    
    id = Column(Integer, primary_key=True, index=True)
    lora_model_id = Column(Integer, ForeignKey('lora_models.id', ondelete='CASCADE'), nullable=False)
    
    original_url = Column(Text, nullable=False)
    processed_url = Column(Text, nullable=True)
    caption = Column(Text, nullable=True)
    is_valid = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


# ==================== Billing Tables ====================

class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    tier = Column(Enum(SubscriptionTier), default=SubscriptionTier.FREE)
    stripe_customer_id = Column(String(255), nullable=True, index=True)
    stripe_subscription_id = Column(String(255), nullable=True, index=True)
    stripe_price_id = Column(String(255), nullable=True)
    
    status = Column(String(50), default="active")
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    cancel_at_period_end = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UsageRecord(Base):
    __tablename__ = "usage_records"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    usage_type = Column(String(50), nullable=False)
    quantity = Column(Integer, default=1)
    cost_credits = Column(Float, default=0)
    usage_metadata = Column(JSON, nullable=True)  # Renamed from 'metadata' (reserved word)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class PaymentHistory(Base):
    __tablename__ = "payment_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    stripe_payment_intent_id = Column(String(255), nullable=True)
    stripe_invoice_id = Column(String(255), nullable=True)
    
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="usd")
    status = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


# ==================== Social Media Tables ====================

class SocialAccount(Base):
    __tablename__ = "social_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    brand_id = Column(Integer, ForeignKey('brands.id', ondelete='SET NULL'), nullable=True)
    
    platform = Column(Enum(SocialPlatform), nullable=False)
    platform_user_id = Column(String(255), nullable=False)
    platform_username = Column(String(255), nullable=True)
    platform_display_name = Column(String(255), nullable=True)
    profile_image_url = Column(Text, nullable=True)
    
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    
    is_active = Column(Boolean, default=True)
    last_synced_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    platform_data = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ScheduledSocialPost(Base):
    __tablename__ = "scheduled_social_posts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    social_account_id = Column(Integer, ForeignKey('social_accounts.id', ondelete='CASCADE'), nullable=True)
    brand_id = Column(Integer, ForeignKey('brands.id', ondelete='SET NULL'), nullable=True)
    content_id = Column(Integer, ForeignKey('generated_content.id', ondelete='SET NULL'), nullable=True)
    
    platform = Column(Enum(SocialPlatform), nullable=True)
    caption = Column(Text, nullable=True)
    hashtags = Column(JSON, nullable=True)
    media_urls = Column(JSON, nullable=True)
    platform_specific = Column(JSON, nullable=True)
    
    scheduled_time = Column(DateTime, nullable=False, index=True)
    scheduled_for = Column(DateTime, nullable=True)
    timezone = Column(String(50), default="UTC")
    
    status = Column(Enum(PostStatus), default=PostStatus.SCHEDULED)
    
    published_at = Column(DateTime, nullable=True)
    platform_post_id = Column(String(255), nullable=True)
    platform_post_url = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    engagement_data = Column(JSON, nullable=True)
    last_engagement_sync = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PublishingLog(Base):
    __tablename__ = "publishing_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    scheduled_post_id = Column(Integer, ForeignKey('scheduled_social_posts.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)
    account_id = Column(Integer, ForeignKey('social_accounts.id', ondelete='SET NULL'), nullable=True)
    
    platform = Column(Enum(SocialPlatform), nullable=True)
    platform_post_id = Column(String(255), nullable=True)
    post_url = Column(Text, nullable=True)
    caption = Column(Text, nullable=True)
    
    attempt_number = Column(Integer, default=1)
    attempted_at = Column(DateTime, default=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)
    
    success = Column(Boolean, default=False)
    error_code = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    response_data = Column(JSON, nullable=True)
    
    engagement_data = Column(JSON, nullable=True)
    metrics_updated_at = Column(DateTime, nullable=True)


# ==================== Video Tables ====================

class VideoProject(Base):
    __tablename__ = "video_projects"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    brand_id = Column(Integer, ForeignKey('brands.id', ondelete='SET NULL'), nullable=True)
    
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    script = Column(Text, nullable=True)
    
    status = Column(Enum(VideoStatus), default=VideoStatus.PENDING)
    
    video_url = Column(Text, nullable=True)
    thumbnail_url = Column(Text, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    replicate_prediction_id = Column(String(255), nullable=True)
    generation_params = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ==================== Studio Tables ====================

class StudioProject(Base):
    __tablename__ = "studio_projects"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    brand_id = Column(Integer, ForeignKey('brands.id', ondelete='SET NULL'), nullable=True)
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    project_type = Column(String(50), default="general")
    
    content_data = Column(JSON, nullable=True)
    settings = Column(JSON, nullable=True)
    
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ==================== Brand Voice Tables ====================

class BrandVoiceProfile(Base):
    __tablename__ = "brand_voice_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey('brands.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    tone = Column(JSON, nullable=True)
    vocabulary = Column(JSON, nullable=True)
    writing_style = Column(JSON, nullable=True)
    dos_and_donts = Column(JSON, nullable=True)
    example_posts = Column(JSON, nullable=True)
    
    training_samples = Column(JSON, nullable=True)
    is_trained = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ==================== A/B Testing Tables ====================

class ABTest(Base):
    __tablename__ = "ab_tests"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    brand_id = Column(Integer, ForeignKey('brands.id', ondelete='SET NULL'), nullable=True)
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    test_type = Column(String(50), nullable=False)
    status = Column(String(50), default="draft")
    
    goal_metric = Column(String(50), default="engagement_rate")
    min_sample_size = Column(Integer, default=100)
    confidence_level = Column(Float, default=0.95)
    
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    auto_end_on_significance = Column(Boolean, default=True)
    
    winner_variation_id = Column(Integer, nullable=True)
    is_significant = Column(Boolean, default=False)
    p_value = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ABTestVariation(Base):
    __tablename__ = "ab_test_variations"
    
    id = Column(Integer, primary_key=True, index=True)
    test_id = Column(Integer, ForeignKey('ab_tests.id', ondelete='CASCADE'), nullable=False, index=True)
    
    name = Column(String(100), nullable=False)
    is_control = Column(Boolean, default=False)
    content = Column(Text, nullable=True)
    content_data = Column(JSON, nullable=True)
    
    impressions = Column(Integer, default=0)
    engagements = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    conversions = Column(Integer, default=0)
    
    engagement_rate = Column(Float, default=0.0)
    click_rate = Column(Float, default=0.0)
    conversion_rate = Column(Float, default=0.0)
    traffic_percent = Column(Integer, default=50)
    
    created_at = Column(DateTime, default=datetime.utcnow)


# ==================== Admin Tables ====================

class AdminUser(Base):
    __tablename__ = "admin_users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(String(50), default="admin")
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey('admin_users.id', ondelete='SET NULL'), nullable=True)
    
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(Integer, nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(50), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class SystemSetting(Base):
    __tablename__ = "system_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(JSON, nullable=True)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ==================== Database Setup Functions ====================

def create_all_tables(database_url: str = None):
    """Create all database tables."""
    from app.core.config import get_settings
    
    if database_url is None:
        settings = get_settings()
        database_url = settings.database_url
    
    engine = create_engine(database_url)
    Base.metadata.create_all(bind=engine)
    print("✅ All database tables created successfully!")
    return engine


def drop_all_tables(database_url: str = None):
    """Drop all database tables (use with caution!)."""
    from app.core.config import get_settings
    
    if database_url is None:
        settings = get_settings()
        database_url = settings.database_url
    
    engine = create_engine(database_url)
    Base.metadata.drop_all(bind=engine)
    print("⚠️ All database tables dropped!")
    return engine


def seed_default_data(database_url: str = None):
    """Seed default categories and settings."""
    from sqlalchemy.orm import sessionmaker
    from app.core.config import get_settings
    
    if database_url is None:
        settings = get_settings()
        database_url = settings.database_url
    
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Default categories
    default_categories = [
        {"name": "Lifestyle", "slug": "lifestyle", "description": "General lifestyle content"},
        {"name": "Travel", "slug": "travel", "description": "Travel and adventure content"},
        {"name": "Food", "slug": "food", "description": "Food and culinary content"},
        {"name": "Fashion", "slug": "fashion", "description": "Fashion and style content"},
        {"name": "Fitness", "slug": "fitness", "description": "Health and fitness content"},
        {"name": "Tech", "slug": "tech", "description": "Technology content"},
        {"name": "Business", "slug": "business", "description": "Business and professional content"},
        {"name": "Education", "slug": "education", "description": "Educational content"},
    ]
    
    for cat_data in default_categories:
        existing = session.query(Category).filter_by(slug=cat_data["slug"]).first()
        if not existing:
            category = Category(**cat_data)
            session.add(category)
    
    # Default system settings
    default_settings = [
        {"key": "maintenance_mode", "value": False, "description": "Enable maintenance mode"},
        {"key": "new_registrations_enabled", "value": True, "description": "Allow new user registrations"},
        {"key": "default_user_tier", "value": "free", "description": "Default subscription tier for new users"},
    ]
    
    for setting_data in default_settings:
        existing = session.query(SystemSetting).filter_by(key=setting_data["key"]).first()
        if not existing:
            setting = SystemSetting(**setting_data)
            session.add(setting)
    
    session.commit()
    session.close()
    print("✅ Default data seeded successfully!")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "create":
            create_all_tables()
        elif command == "drop":
            confirm = input("Are you sure you want to drop all tables? (yes/no): ")
            if confirm.lower() == "yes":
                drop_all_tables()
        elif command == "seed":
            seed_default_data()
        elif command == "setup":
            create_all_tables()
            seed_default_data()
        else:
            print(f"Unknown command: {command}")
            print("Usage: python database_setup.py [create|drop|seed|setup]")
    else:
        print("Usage: python database_setup.py [create|drop|seed|setup]")
        print("  create - Create all database tables")
        print("  drop   - Drop all database tables")
        print("  seed   - Seed default data")
        print("  setup  - Create tables and seed data")

# Alias for compatibility
create_tables = create_all_tables

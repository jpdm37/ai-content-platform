"""
Application configuration using Pydantic Settings
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # Application
    app_name: str = "AI Content Platform"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"  # development, staging, production
    api_version: str = "v1"
    frontend_url: str = "http://localhost:3000"
    
    # Database
    database_url: str = "postgresql://localhost/ai_content"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"  # Cost-effective for testing
    
    # Replicate
    replicate_api_token: str = ""
    replicate_image_model: str = "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b"
    
    # News API (optional)
    news_api_key: Optional[str] = None
    
    # Content settings
    default_image_width: int = 1024
    default_image_height: int = 1024
    
    # Authentication
    secret_key: str = "your-super-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    email_verification_expire_hours: int = 24
    password_reset_expire_hours: int = 1
    
    # Email (SMTP)
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_email: str = "noreply@aicontentplatform.com"
    smtp_from_name: str = "AI Content Platform"
    smtp_tls: bool = True
    
    # OAuth - Google
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    
    # OAuth - GitHub
    github_client_id: Optional[str] = None
    github_client_secret: Optional[str] = None
    
    # Stripe
    stripe_secret_key: Optional[str] = None
    stripe_publishable_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None
    stripe_price_id_creator: Optional[str] = None  # $19/mo
    stripe_price_id_pro: Optional[str] = None      # $49/mo
    stripe_price_id_agency: Optional[str] = None   # $149/mo
    
    # Social Media - Twitter/X
    twitter_client_id: Optional[str] = None
    twitter_client_secret: Optional[str] = None
    
    # Social Media - Instagram (via Facebook)
    instagram_app_id: Optional[str] = None
    instagram_app_secret: Optional[str] = None
    
    # Social Media - LinkedIn
    linkedin_client_id: Optional[str] = None
    linkedin_client_secret: Optional[str] = None
    
    # Social Media - TikTok
    tiktok_client_key: Optional[str] = None
    tiktok_client_secret: Optional[str] = None
    
    # Video Generation - ElevenLabs
    elevenlabs_api_key: Optional[str] = None
    
    # Error Tracking - Sentry
    sentry_dsn: Optional[str] = None
    
    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 60
    
    # Admin setup security
    admin_setup_token: Optional[str] = None  # Set to require token for initial admin setup
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()

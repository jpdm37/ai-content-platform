"""
User and Authentication Database Models
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, 
    Boolean, Enum, JSON
)
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class AuthProvider(enum.Enum):
    LOCAL = "local"
    GOOGLE = "google"
    GITHUB = "github"


class User(Base):
    """User account model"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)  # Nullable for OAuth users
    
    # Profile
    name = Column(String(255))  # Added for compatibility
    full_name = Column(String(255))
    avatar_url = Column(Text)
    
    # Account status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)
    
    # Admin access
    is_admin = Column(Boolean, default=False)
    admin_role = Column(String(50), nullable=True)  # super_admin, admin, support
    
    # OAuth
    auth_provider = Column(Enum(AuthProvider), default=AuthProvider.LOCAL)
    oauth_id = Column(String(255), nullable=True)  # Provider's user ID
    
    # API Keys (user can store their own keys) - ENCRYPTED AT REST
    _openai_api_key = Column('openai_api_key', Text, nullable=True)
    _replicate_api_token = Column('replicate_api_token', Text, nullable=True)
    
    @property
    def openai_api_key(self) -> str:
        """Decrypt and return the OpenAI API key."""
        from app.core.encryption import decrypt_field
        return decrypt_field(self._openai_api_key)
    
    @openai_api_key.setter
    def openai_api_key(self, value: str):
        """Encrypt and store the OpenAI API key."""
        from app.core.encryption import encrypt_field
        self._openai_api_key = encrypt_field(value)
    
    @property
    def replicate_api_token(self) -> str:
        """Decrypt and return the Replicate API token."""
        from app.core.encryption import decrypt_field
        return decrypt_field(self._replicate_api_token)
    
    @replicate_api_token.setter
    def replicate_api_token(self, value: str):
        """Encrypt and store the Replicate API token."""
        from app.core.encryption import encrypt_field
        self._replicate_api_token = encrypt_field(value)
    
    # Onboarding tracking
    onboarding_data = Column(JSON, nullable=True, default=dict)
    onboarding_completed = Column(Boolean, default=False)
    
    # Email preferences
    email_preferences = Column(JSON, nullable=True, default=lambda: {
        "weekly_digest": True,
        "content_suggestions": True,
        "product_updates": True,
        "tips_and_tricks": True
    })
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    brands = relationship("Brand", back_populates="owner", cascade="all, delete-orphan")
    generated_content = relationship("GeneratedContent", back_populates="owner", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")


class RefreshToken(Base):
    """Refresh tokens for JWT authentication"""
    __tablename__ = "refresh_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token = Column(String(500), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Device/session info
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="refresh_tokens")


class EmailVerificationToken(Base):
    """Email verification tokens"""
    __tablename__ = "email_verification_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token = Column(String(500), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User")


class PasswordResetToken(Base):
    """Password reset tokens"""
    __tablename__ = "password_reset_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token = Column(String(500), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User")

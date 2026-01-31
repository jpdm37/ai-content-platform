"""
Authentication Pydantic Schemas
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum


class AuthProvider(str, Enum):
    LOCAL = "local"
    GOOGLE = "google"
    GITHUB = "github"


# ========== User Schemas ==========

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None


class UserUpdatePassword(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


class UserApiKeys(BaseModel):
    openai_api_key: Optional[str] = None
    replicate_api_token: Optional[str] = None


class UserResponse(UserBase):
    id: int
    avatar_url: Optional[str]
    is_active: bool
    is_verified: bool
    auth_provider: AuthProvider
    has_openai_key: bool = False
    has_replicate_key: bool = False
    created_at: datetime
    last_login: Optional[datetime]

    class Config:
        from_attributes = True


class UserProfileResponse(UserResponse):
    """Extended user profile with stats"""
    brands_count: int = 0
    content_count: int = 0


# ========== Token Schemas ==========

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenRefresh(BaseModel):
    refresh_token: str


class TokenPayload(BaseModel):
    sub: int  # user_id
    exp: datetime
    type: str  # "access" or "refresh"


# ========== Email Verification ==========

class EmailVerificationRequest(BaseModel):
    email: EmailStr


class EmailVerificationConfirm(BaseModel):
    token: str


# ========== Password Reset ==========

class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


# ========== OAuth Schemas ==========

class OAuthCallback(BaseModel):
    code: str
    state: Optional[str] = None


class OAuthUserInfo(BaseModel):
    """Normalized user info from OAuth providers"""
    id: str
    email: EmailStr
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    provider: AuthProvider


# ========== Response Schemas ==========

class MessageResponse(BaseModel):
    message: str


class AuthStatusResponse(BaseModel):
    authenticated: bool
    user: Optional[UserResponse] = None

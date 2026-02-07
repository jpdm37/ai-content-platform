"""
Authentication API Routes
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.models.user import User, RefreshToken, AuthProvider
from app.models.auth_schemas import (
    UserCreate, UserLogin, UserResponse, UserUpdate, UserUpdatePassword,
    UserApiKeys, UserProfileResponse,
    Token, TokenRefresh,
    EmailVerificationRequest, EmailVerificationConfirm,
    PasswordResetRequest, PasswordResetConfirm,
    MessageResponse, AuthStatusResponse
)
from app.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
    create_email_verification_token,
    verify_email_verification_token,
    create_password_reset_token,
    verify_password_reset_token,
    get_current_user,
    get_current_user_optional,
    email_service,
    oauth_service,
)

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["authentication"])


# ========== Registration & Login ==========

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")  # Prevent mass registration
async def register(request: Request, user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user with email and password"""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email.lower()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    user = User(
        email=user_data.email.lower(),
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        auth_provider=AuthProvider.LOCAL,
        is_verified=False
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Send verification email
    token = create_email_verification_token(user.id)
    await email_service.send_verification_email(user.email, token, user.full_name)
    
    return _user_to_response(user)


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")  # Prevent brute force
async def login(
    user_data: UserLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    """Login with email and password"""
    user = db.query(User).filter(User.email == user_data.email.lower()).first()
    
    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create tokens
    access_token = create_access_token(user.id)
    refresh_token, refresh_expires = create_refresh_token(user.id)
    
    # Store refresh token
    db_refresh_token = RefreshToken(
        user_id=user.id,
        token=refresh_token,
        expires_at=refresh_expires,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None
    )
    db.add(db_refresh_token)
    db.commit()
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_data: TokenRefresh,
    request: Request,
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token"""
    user_id = verify_refresh_token(token_data.refresh_token)
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    # Check if token exists and is not revoked
    db_token = db.query(RefreshToken).filter(
        RefreshToken.token == token_data.refresh_token,
        RefreshToken.revoked == False
    ).first()
    
    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Revoke old refresh token
    db_token.revoked = True
    
    # Create new tokens
    access_token = create_access_token(user.id)
    new_refresh_token, refresh_expires = create_refresh_token(user.id)
    
    # Store new refresh token
    new_db_token = RefreshToken(
        user_id=user.id,
        token=new_refresh_token,
        expires_at=refresh_expires,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None
    )
    db.add(new_db_token)
    db.commit()
    
    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    token_data: TokenRefresh,
    db: Session = Depends(get_db)
):
    """Logout by revoking refresh token"""
    db_token = db.query(RefreshToken).filter(
        RefreshToken.token == token_data.refresh_token
    ).first()
    
    if db_token:
        db_token.revoked = True
        db.commit()
    
    return MessageResponse(message="Logged out successfully")


# ========== Email Verification ==========

@router.post("/verify-email/send", response_model=MessageResponse)
async def send_verification_email(
    request: EmailVerificationRequest,
    db: Session = Depends(get_db)
):
    """Send or resend verification email"""
    user = db.query(User).filter(User.email == request.email.lower()).first()
    
    if not user:
        # Don't reveal if user exists
        return MessageResponse(message="If an account exists, a verification email has been sent")
    
    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified"
        )
    
    token = create_email_verification_token(user.id)
    await email_service.send_verification_email(user.email, token, user.full_name)
    
    return MessageResponse(message="Verification email sent")


@router.post("/verify-email/confirm", response_model=MessageResponse)
async def confirm_email_verification(
    data: EmailVerificationConfirm,
    db: Session = Depends(get_db)
):
    """Verify email with token"""
    user_id = verify_email_verification_token(
        data.token,
        max_age_hours=settings.email_verification_expire_hours
    )
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.is_verified:
        return MessageResponse(message="Email already verified")
    
    user.is_verified = True
    db.commit()
    
    # Send welcome email
    await email_service.send_welcome_email(user.email, user.full_name)
    
    return MessageResponse(message="Email verified successfully")


# ========== Password Reset ==========

@router.post("/password-reset/request", response_model=MessageResponse)
@limiter.limit("3/minute")  # Strict limit to prevent abuse
async def request_password_reset(
    request: Request,
    data: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """Request password reset email"""
    user = db.query(User).filter(User.email == data.email.lower()).first()
    
    # Always return success to prevent email enumeration
    if not user:
        return MessageResponse(message="If an account exists, a password reset email has been sent")
    
    # Only allow password reset for local auth users
    if user.auth_provider != AuthProvider.LOCAL:
        return MessageResponse(
            message=f"This account uses {user.auth_provider.value} login. Please sign in with {user.auth_provider.value}."
        )
    
    token = create_password_reset_token(user.id)
    await email_service.send_password_reset_email(user.email, token, user.full_name)
    
    return MessageResponse(message="If an account exists, a password reset email has been sent")


@router.post("/password-reset/confirm", response_model=MessageResponse)
@limiter.limit("5/minute")  # Prevent brute force token guessing
async def confirm_password_reset(
    request: Request,
    data: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """Reset password with token"""
    user_id = verify_password_reset_token(
        data.token,
        max_age_hours=settings.password_reset_expire_hours
    )
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update password
    user.hashed_password = get_password_hash(data.new_password)
    
    # Revoke all refresh tokens for security
    db.query(RefreshToken).filter(RefreshToken.user_id == user.id).update({"revoked": True})
    
    db.commit()
    
    return MessageResponse(message="Password reset successfully")


# ========== OAuth ==========

@router.get("/oauth/{provider}")
async def oauth_login(provider: str, request: Request):
    """Initiate OAuth login flow"""
    redirect_uri = f"{settings.frontend_url}/auth/callback/{provider}"
    
    if provider == "google":
        if not oauth_service.is_google_configured():
            raise HTTPException(status_code=400, detail="Google OAuth not configured")
        auth_url = oauth_service.get_google_auth_url(redirect_uri)
        return {"auth_url": auth_url}
    
    elif provider == "github":
        if not oauth_service.is_github_configured():
            raise HTTPException(status_code=400, detail="GitHub OAuth not configured")
        auth_url = oauth_service.get_github_auth_url(redirect_uri)
        return {"auth_url": auth_url}
    
    else:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")


@router.post("/oauth/{provider}/callback", response_model=Token)
async def oauth_callback(
    provider: str,
    code: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Handle OAuth callback and create/login user"""
    redirect_uri = f"{settings.frontend_url}/auth/callback/{provider}"
    
    # Get user info from provider
    if provider == "google":
        user_info = await oauth_service.get_google_user_info(code, redirect_uri)
    elif provider == "github":
        user_info = await oauth_service.get_github_user_info(code, redirect_uri)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
    
    if not user_info:
        raise HTTPException(status_code=400, detail="Failed to get user info from provider")
    
    # Find or create user
    user = db.query(User).filter(User.email == user_info.email.lower()).first()
    
    if user:
        # Update OAuth info if needed
        if user.auth_provider == AuthProvider.LOCAL:
            # User registered with email, now linking OAuth
            user.oauth_id = user_info.id
            user.auth_provider = user_info.provider
            if not user.avatar_url and user_info.avatar_url:
                user.avatar_url = user_info.avatar_url
    else:
        # Create new user
        user = User(
            email=user_info.email.lower(),
            full_name=user_info.name,
            avatar_url=user_info.avatar_url,
            auth_provider=user_info.provider,
            oauth_id=user_info.id,
            is_verified=True,  # OAuth users are auto-verified
            is_active=True
        )
        db.add(user)
    
    user.last_login = datetime.utcnow()
    db.commit()
    db.refresh(user)
    
    # Create tokens
    access_token = create_access_token(user.id)
    refresh_token, refresh_expires = create_refresh_token(user.id)
    
    # Store refresh token
    db_refresh_token = RefreshToken(
        user_id=user.id,
        token=refresh_token,
        expires_at=refresh_expires,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None
    )
    db.add(db_refresh_token)
    db.commit()
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60
    )


@router.get("/oauth/providers")
async def get_oauth_providers():
    """Get available OAuth providers"""
    return {
        "google": oauth_service.is_google_configured(),
        "github": oauth_service.is_github_configured()
    }


# ========== User Profile ==========

@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user profile"""
    from app.models import Brand, GeneratedContent
    
    brands_count = db.query(Brand).filter(Brand.user_id == current_user.id).count()
    content_count = db.query(GeneratedContent).filter(GeneratedContent.user_id == current_user.id).count()
    
    response = _user_to_response(current_user)
    return UserProfileResponse(
        **response.model_dump(),
        brands_count=brands_count,
        content_count=content_count
    )


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user profile"""
    if user_data.full_name is not None:
        current_user.full_name = user_data.full_name
    if user_data.avatar_url is not None:
        current_user.avatar_url = user_data.avatar_url
    
    db.commit()
    db.refresh(current_user)
    
    return _user_to_response(current_user)


@router.put("/me/password", response_model=MessageResponse)
async def update_password(
    data: UserUpdatePassword,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user's password"""
    if current_user.auth_provider != AuthProvider.LOCAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot change password for {current_user.auth_provider.value} accounts"
        )
    
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    current_user.hashed_password = get_password_hash(data.new_password)
    db.commit()
    
    return MessageResponse(message="Password updated successfully")


@router.put("/me/api-keys", response_model=MessageResponse)
async def update_api_keys(
    data: UserApiKeys,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user's personal API keys"""
    if data.openai_api_key is not None:
        current_user.openai_api_key = data.openai_api_key if data.openai_api_key else None
    if data.replicate_api_token is not None:
        current_user.replicate_api_token = data.replicate_api_token if data.replicate_api_token else None
    
    db.commit()
    
    return MessageResponse(message="API keys updated successfully")


@router.get("/status", response_model=AuthStatusResponse)
async def get_auth_status(
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Check authentication status"""
    if current_user:
        return AuthStatusResponse(
            authenticated=True,
            user=_user_to_response(current_user)
        )
    return AuthStatusResponse(authenticated=False)


# ========== Helper Functions ==========

def _user_to_response(user: User) -> UserResponse:
    """Convert User model to UserResponse"""
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        is_verified=user.is_verified,
        auth_provider=user.auth_provider,
        has_openai_key=bool(user.openai_api_key),
        has_replicate_key=bool(user.replicate_api_token),
        created_at=user.created_at,
        last_login=user.last_login
    )

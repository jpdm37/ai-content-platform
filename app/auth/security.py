"""
Security utilities for password hashing and JWT tokens
"""
from datetime import datetime, timedelta
from typing import Optional, Union
from jose import jwt, JWTError
from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer
import secrets

from app.core.config import get_settings

settings = get_settings()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Token serializer for email verification and password reset
serializer = URLSafeTimedSerializer(settings.secret_key)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(
    user_id: int = None, 
    expires_delta: Optional[timedelta] = None,
    data: dict = None
) -> str:
    """Create a JWT access token"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    # Support both user_id and data dict approaches
    if data:
        to_encode = data.copy()
        to_encode["exp"] = expire
        to_encode["iat"] = datetime.utcnow()
    else:
        to_encode = {
            "sub": str(user_id),
            "exp": expire,
            "type": "access",
            "iat": datetime.utcnow()
        }
    
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def create_refresh_token(user_id: int, expires_delta: Optional[timedelta] = None) -> tuple[str, datetime]:
    """Create a JWT refresh token and return with expiry"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    
    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "type": "refresh",
        "iat": datetime.utcnow(),
        "jti": secrets.token_urlsafe(32)  # Unique token ID
    }
    
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt, expire


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None


def verify_access_token(token: str) -> Optional[int]:
    """Verify an access token and return user_id"""
    payload = decode_token(token)
    if payload is None:
        return None
    
    if payload.get("type") != "access":
        return None
    
    user_id = payload.get("sub")
    if user_id is None:
        return None
    
    return int(user_id)


def verify_refresh_token(token: str) -> Optional[int]:
    """Verify a refresh token and return user_id"""
    payload = decode_token(token)
    if payload is None:
        return None
    
    if payload.get("type") != "refresh":
        return None
    
    user_id = payload.get("sub")
    if user_id is None:
        return None
    
    return int(user_id)


def create_email_verification_token(user_id: int) -> str:
    """Create a token for email verification"""
    return serializer.dumps({"user_id": user_id, "purpose": "email_verification"})


def verify_email_verification_token(token: str, max_age_hours: int = 24) -> Optional[int]:
    """Verify an email verification token and return user_id"""
    try:
        data = serializer.loads(token, max_age=max_age_hours * 3600)
        if data.get("purpose") != "email_verification":
            return None
        return data.get("user_id")
    except Exception:
        return None


def create_password_reset_token(user_id: int) -> str:
    """Create a token for password reset"""
    return serializer.dumps({"user_id": user_id, "purpose": "password_reset"})


def verify_password_reset_token(token: str, max_age_hours: int = 1) -> Optional[int]:
    """Verify a password reset token and return user_id"""
    try:
        data = serializer.loads(token, max_age=max_age_hours * 3600)
        if data.get("purpose") != "password_reset":
            return None
        return data.get("user_id")
    except Exception:
        return None


def generate_random_token(length: int = 32) -> str:
    """Generate a random token"""
    return secrets.token_urlsafe(length)

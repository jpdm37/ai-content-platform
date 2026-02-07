"""
Admin Database Models
=====================
Admin users, audit logs, and system settings.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base


class AdminRole(str, enum.Enum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    SUPPORT = "support"


class AdminUser(Base):
    """Admin users separate from regular users"""
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(SQLEnum(AdminRole), default=AdminRole.ADMIN, nullable=False)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    audit_logs = relationship("AuditLog", back_populates="admin")


class AuditLog(Base):
    """Track all admin actions for security"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("admin_users.id"), nullable=False)
    action = Column(String(100), nullable=False)  # e.g., "user.update", "user.impersonate"
    target_type = Column(String(50), nullable=True)  # e.g., "user", "brand"
    target_id = Column(Integer, nullable=True)
    details = Column(JSON, nullable=True)  # Additional context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    admin = relationship("AdminUser", back_populates="audit_logs")


class SystemSetting(Base):
    """System-wide configuration settings"""
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True, nullable=False)
    value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    is_secret = Column(Boolean, default=False)  # Don't expose in API
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(Integer, ForeignKey("admin_users.id"), nullable=True)


# Default system settings
DEFAULT_SETTINGS = {
    "maintenance_mode": {
        "value": "false",
        "description": "Enable maintenance mode to block all non-admin access"
    },
    "registration_enabled": {
        "value": "true",
        "description": "Allow new user registrations"
    },
    "free_tier_enabled": {
        "value": "true",
        "description": "Allow users to use free tier"
    },
    "max_free_brands": {
        "value": "1",
        "description": "Maximum brands for free tier users"
    },
    "max_free_content_daily": {
        "value": "5",
        "description": "Maximum content generations per day for free tier"
    },
    "welcome_email_enabled": {
        "value": "true",
        "description": "Send welcome email to new users"
    },
    "admin_notification_email": {
        "value": "",
        "description": "Email to notify for important events"
    },
}

"""
Admin Service
=============
Business logic for admin operations.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.admin.models import AdminUser, AdminRole, AuditLog, SystemSetting, DEFAULT_SETTINGS
from app.models.user import User
from app.models.models import Brand, GeneratedContent
from app.video.models import GeneratedVideo
from app.social.models import ScheduledSocialPost as SocialPost  # Alias for compatibility
from app.billing.models import Subscription, Payment
from app.auth.security import get_password_hash, verify_password, create_access_token


class AdminService:
    def __init__(self, db: Session):
        self.db = db
    
    # ============ Admin User Management ============
    
    def create_admin(
        self,
        email: str,
        password: str,
        name: str,
        role: AdminRole = AdminRole.ADMIN
    ) -> AdminUser:
        """Create a new admin user"""
        existing = self.db.query(AdminUser).filter(AdminUser.email == email.lower()).first()
        if existing:
            raise ValueError("Admin with this email already exists")
        
        admin = AdminUser(
            email=email.lower(),
            hashed_password=get_password_hash(password),
            name=name,
            role=role
        )
        self.db.add(admin)
        self.db.commit()
        self.db.refresh(admin)
        return admin
    
    def authenticate_admin(self, email: str, password: str) -> Optional[AdminUser]:
        """Authenticate admin and return user if valid"""
        admin = self.db.query(AdminUser).filter(
            AdminUser.email == email.lower(),
            AdminUser.is_active == True
        ).first()
        
        if not admin or not verify_password(password, admin.hashed_password):
            return None
        
        admin.last_login = datetime.utcnow()
        self.db.commit()
        return admin
    
    def create_admin_token(self, admin: AdminUser) -> str:
        """Create JWT token for admin"""
        return create_access_token(
            data={
                "sub": f"admin:{admin.id}",
                "email": admin.email,
                "role": admin.role.value,
                "type": "admin"
            },
            expires_delta=timedelta(hours=12)
        )
    
    def get_admin_by_id(self, admin_id: int) -> Optional[AdminUser]:
        return self.db.query(AdminUser).filter(AdminUser.id == admin_id).first()
    
    def list_admins(self) -> List[AdminUser]:
        return self.db.query(AdminUser).order_by(AdminUser.created_at.desc()).all()
    
    # ============ User Management ============
    
    def list_users(
        self,
        page: int = 1,
        per_page: int = 50,
        search: Optional[str] = None,
        tier: Optional[str] = None
    ) -> Tuple[List[dict], int]:
        """List users with filtering"""
        query = self.db.query(User)
        
        if search:
            query = query.filter(
                or_(
                    User.email.ilike(f"%{search}%"),
                    User.full_name.ilike(f"%{search}%")
                )
            )
        
        total = query.count()
        users = query.order_by(User.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
        
        result = []
        for user in users:
            brands_count = self.db.query(Brand).filter(Brand.user_id == user.id).count()
            content_count = self.db.query(GeneratedContent).filter(GeneratedContent.user_id == user.id).count()
            subscription = self.db.query(Subscription).filter(Subscription.user_id == user.id).first()
            
            result.append({
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "subscription_tier": subscription.tier if subscription else "free",
                "subscription_status": subscription.status if subscription else "none",
                "brands_count": brands_count,
                "content_count": content_count,
                "created_at": user.created_at,
                "last_login": user.last_login
            })
        
        return result, total
    
    def get_user_details(self, user_id: int) -> Optional[dict]:
        """Get detailed user information"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        brands_count = self.db.query(Brand).filter(Brand.user_id == user_id).count()
        content_count = self.db.query(GeneratedContent).filter(GeneratedContent.user_id == user_id).count()
        videos_count = self.db.query(GeneratedVideo).filter(GeneratedVideo.user_id == user_id).count()
        posts_count = self.db.query(SocialPost).filter(SocialPost.user_id == user_id).count()
        
        subscription = self.db.query(Subscription).filter(Subscription.user_id == user_id).first()
        
        total_spent = self.db.query(func.sum(Payment.amount)).filter(
            Payment.user_id == user_id,
            Payment.status == "succeeded"
        ).scalar() or 0
        
        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "created_at": user.created_at,
            "last_login": user.last_login,
            "subscription": {
                "tier": subscription.tier if subscription else "free",
                "status": subscription.status if subscription else "none",
                "current_period_end": subscription.current_period_end if subscription else None
            },
            "stats": {
                "brands_count": brands_count,
                "content_count": content_count,
                "videos_count": videos_count,
                "posts_count": posts_count,
                "total_spent": float(total_spent) / 100
            },
            "recent_activity": []
        }
    
    def update_user(self, user_id: int, **kwargs) -> Optional[User]:
        """Update user details"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        for key, value in kwargs.items():
            if hasattr(user, key) and value is not None:
                setattr(user, key, value)
        
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def grant_subscription(self, user_id: int, tier: str, duration_days: int = 365) -> Subscription:
        """Grant or extend a subscription"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")
        
        subscription = self.db.query(Subscription).filter(Subscription.user_id == user_id).first()
        
        if subscription:
            subscription.tier = tier
            subscription.status = "active"
            subscription.current_period_end = datetime.utcnow() + timedelta(days=duration_days)
        else:
            subscription = Subscription(
                user_id=user_id,
                tier=tier,
                status="active",
                current_period_start=datetime.utcnow(),
                current_period_end=datetime.utcnow() + timedelta(days=duration_days)
            )
            self.db.add(subscription)
        
        self.db.commit()
        self.db.refresh(subscription)
        return subscription
    
    def impersonate_user(self, user_id: int) -> Tuple[str, str]:
        """Generate a token to impersonate a user"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")
        
        token = create_access_token(
            data={
                "sub": str(user.id),
                "email": user.email,
                "impersonated": True
            },
            expires_delta=timedelta(hours=1)
        )
        return token, user.email
    
    # ============ System Statistics ============
    
    def get_system_stats(self) -> dict:
        """Get system-wide statistics"""
        now = datetime.utcnow()
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        total_users = self.db.query(User).count()
        active_24h = self.db.query(User).filter(User.last_login >= day_ago).count()
        active_7d = self.db.query(User).filter(User.last_login >= week_ago).count()
        signups_today = self.db.query(User).filter(User.created_at >= day_ago).count()
        signups_week = self.db.query(User).filter(User.created_at >= week_ago).count()
        signups_month = self.db.query(User).filter(User.created_at >= month_ago).count()
        
        total_brands = self.db.query(Brand).count()
        total_content = self.db.query(GeneratedContent).count()
        total_videos = self.db.query(GeneratedVideo).count()
        total_posts = self.db.query(SocialPost).count()
        
        total_revenue = self.db.query(func.sum(Payment.amount)).filter(
            Payment.status == "succeeded"
        ).scalar() or 0
        
        tier_counts = self.db.query(
            Subscription.tier,
            func.count(Subscription.id)
        ).group_by(Subscription.tier).all()
        users_by_tier = {tier: count for tier, count in tier_counts}
        
        return {
            "total_users": total_users,
            "active_users_24h": active_24h,
            "active_users_7d": active_7d,
            "total_brands": total_brands,
            "total_content": total_content,
            "total_videos": total_videos,
            "total_posts": total_posts,
            "total_revenue": float(total_revenue) / 100,
            "users_by_tier": users_by_tier,
            "signups_today": signups_today,
            "signups_this_week": signups_week,
            "signups_this_month": signups_month
        }
    
    # ============ System Settings ============
    
    def get_setting(self, key: str) -> Optional[str]:
        setting = self.db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if setting:
            return setting.value
        if key in DEFAULT_SETTINGS:
            return DEFAULT_SETTINGS[key]["value"]
        return None
    
    def set_setting(self, key: str, value: str, admin_id: int) -> SystemSetting:
        setting = self.db.query(SystemSetting).filter(SystemSetting.key == key).first()
        
        if setting:
            setting.value = value
            setting.updated_by = admin_id
        else:
            description = DEFAULT_SETTINGS.get(key, {}).get("description", "")
            setting = SystemSetting(
                key=key,
                value=value,
                description=description,
                updated_by=admin_id
            )
            self.db.add(setting)
        
        self.db.commit()
        self.db.refresh(setting)
        return setting
    
    def get_all_settings(self) -> List[dict]:
        settings = self.db.query(SystemSetting).filter(SystemSetting.is_secret == False).all()
        
        result = {}
        for key, data in DEFAULT_SETTINGS.items():
            result[key] = {
                "key": key,
                "value": data["value"],
                "description": data["description"],
                "updated_at": None
            }
        
        for setting in settings:
            result[setting.key] = {
                "key": setting.key,
                "value": setting.value,
                "description": setting.description,
                "updated_at": setting.updated_at
            }
        
        return list(result.values())
    
    # ============ Audit Logging ============
    
    def log_action(
        self,
        admin_id: int,
        action: str,
        target_type: Optional[str] = None,
        target_id: Optional[int] = None,
        details: Optional[dict] = None,
        ip_address: Optional[str] = None
    ) -> AuditLog:
        log = AuditLog(
            admin_id=admin_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details,
            ip_address=ip_address
        )
        self.db.add(log)
        self.db.commit()
        return log
    
    def get_audit_logs(self, days: int = 30, limit: int = 100) -> List[AuditLog]:
        since = datetime.utcnow() - timedelta(days=days)
        return self.db.query(AuditLog).filter(
            AuditLog.created_at >= since
        ).order_by(AuditLog.created_at.desc()).limit(limit).all()
    
    # ============ Test Data ============
    
    def create_test_brand(self, user_id: int, name: str, niche: str, description: str = None) -> Brand:
        """Create a test brand"""
        brand = Brand(
            user_id=user_id,
            name=name,
            niche=niche,
            description=description or f"Test brand for {niche}",
            tone="professional",
            target_audience="General audience",
            is_active=True
        )
        self.db.add(brand)
        self.db.commit()
        self.db.refresh(brand)
        return brand


def create_initial_superadmin(db: Session, email: str, password: str, name: str = "Admin"):
    """Create the initial superadmin if none exists"""
    service = AdminService(db)
    
    existing = db.query(AdminUser).first()
    if existing:
        return None
    
    return service.create_admin(
        email=email,
        password=password,
        name=name,
        role=AdminRole.SUPERADMIN
    )

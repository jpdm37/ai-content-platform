"""
Admin API Routes
================
API endpoints for admin dashboard and management.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Optional, List
from jose import jwt, JWTError

from app.core.database import get_db
from app.core.config import settings
from app.core.rate_limit import limiter
from app.admin.service import AdminService, create_initial_superadmin
from app.admin.models import AdminUser, AdminRole
from app.admin.schemas import (
    AdminLoginRequest, AdminLoginResponse, AdminResponse, AdminCreateRequest,
    UserListResponse, UserListItem, UserDetailResponse, UserUpdateByAdmin,
    GrantSubscriptionRequest, ImpersonateRequest, ImpersonateResponse,
    SystemStatsResponse, SystemSettingResponse, SystemSettingUpdate,
    AuditLogResponse, TestBrandRequest
)

router = APIRouter(prefix="/admin", tags=["admin"])


# ============ Auth Dependency ============

async def get_current_admin(
    request: Request,
    db: Session = Depends(get_db)
) -> AdminUser:
    """Verify admin token and return admin user"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    token = auth_header.split(" ")[1]
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        
        if payload.get("type") != "admin":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not an admin token"
            )
        
        sub = payload.get("sub", "")
        if not sub.startswith("admin:"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid admin token"
            )
        
        admin_id = int(sub.split(":")[1])
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    service = AdminService(db)
    admin = service.get_admin_by_id(admin_id)
    
    if not admin or not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin not found or inactive"
        )
    
    return admin


def require_superadmin(admin: AdminUser = Depends(get_current_admin)) -> AdminUser:
    if admin.role != AdminRole.SUPERADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin access required"
        )
    return admin


# ============ Authentication ============

@router.post("/login", response_model=AdminLoginResponse)
async def admin_login(
    request: AdminLoginRequest,
    db: Session = Depends(get_db)
):
    """Admin login endpoint"""
    service = AdminService(db)
    admin = service.authenticate_admin(request.email, request.password)
    
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    token = service.create_admin_token(admin)
    
    return AdminLoginResponse(
        access_token=token,
        admin=AdminResponse.model_validate(admin)
    )


@router.get("/me", response_model=AdminResponse)
async def get_current_admin_info(admin: AdminUser = Depends(get_current_admin)):
    """Get current admin info"""
    return AdminResponse.model_validate(admin)


@router.post("/admins", response_model=AdminResponse)
async def create_admin(
    request: AdminCreateRequest,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_superadmin)
):
    """Create a new admin (superadmin only)"""
    service = AdminService(db)
    
    try:
        new_admin = service.create_admin(
            email=request.email,
            password=request.password,
            name=request.name,
            role=request.role
        )
        
        service.log_action(
            admin_id=admin.id,
            action="admin.create",
            target_type="admin",
            target_id=new_admin.id,
            details={"email": new_admin.email}
        )
        
        return AdminResponse.model_validate(new_admin)
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/admins", response_model=List[AdminResponse])
async def list_admins(
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_superadmin)
):
    """List all admins (superadmin only)"""
    service = AdminService(db)
    admins = service.list_admins()
    return [AdminResponse.model_validate(a) for a in admins]


# ============ User Management ============

@router.get("/users", response_model=UserListResponse)
async def list_users(
    page: int = 1,
    per_page: int = 50,
    search: Optional[str] = None,
    tier: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """List all users"""
    service = AdminService(db)
    users, total = service.list_users(page, per_page, search, tier)
    
    return UserListResponse(
        users=[UserListItem(**u) for u in users],
        total=total,
        page=page,
        per_page=per_page
    )


@router.get("/users/{user_id}", response_model=UserDetailResponse)
async def get_user_details(
    user_id: int,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Get detailed user information"""
    service = AdminService(db)
    user = service.get_user_details(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserDetailResponse(**user)


@router.patch("/users/{user_id}")
async def update_user(
    user_id: int,
    request: UserUpdateByAdmin,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Update user details"""
    service = AdminService(db)
    
    user = service.update_user(user_id, **request.model_dump(exclude_unset=True))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    service.log_action(
        admin_id=admin.id,
        action="user.update",
        target_type="user",
        target_id=user_id,
        details=request.model_dump(exclude_unset=True)
    )
    
    return {"message": "User updated", "user_id": user_id}


@router.post("/users/{user_id}/subscription")
async def grant_subscription(
    user_id: int,
    request: GrantSubscriptionRequest,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Grant subscription to a user"""
    service = AdminService(db)
    
    try:
        subscription = service.grant_subscription(
            user_id=user_id,
            tier=request.tier,
            duration_days=request.duration_days
        )
        
        service.log_action(
            admin_id=admin.id,
            action="subscription.grant",
            target_type="user",
            target_id=user_id,
            details={"tier": request.tier, "days": request.duration_days}
        )
        
        return {
            "message": "Subscription granted",
            "tier": subscription.tier,
            "expires": subscription.current_period_end
        }
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/users/{user_id}/impersonate", response_model=ImpersonateResponse)
async def impersonate_user(
    user_id: int,
    request: ImpersonateRequest,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Get token to impersonate a user"""
    service = AdminService(db)
    
    try:
        token, email = service.impersonate_user(user_id)
        
        service.log_action(
            admin_id=admin.id,
            action="user.impersonate",
            target_type="user",
            target_id=user_id,
            details={"reason": request.reason}
        )
        
        return ImpersonateResponse(access_token=token, user_email=email)
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/users/{user_id}/test-brand")
async def create_test_brand(
    user_id: int,
    request: TestBrandRequest,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Create a test brand for a user"""
    service = AdminService(db)
    
    brand = service.create_test_brand(
        user_id=user_id,
        name=request.name,
        niche=request.niche,
        description=request.description
    )
    
    service.log_action(
        admin_id=admin.id,
        action="brand.create_test",
        target_type="user",
        target_id=user_id,
        details={"brand_id": brand.id}
    )
    
    return {"message": "Brand created", "brand_id": brand.id, "name": brand.name}


# ============ System Stats ============

@router.get("/stats", response_model=SystemStatsResponse)
async def get_system_stats(
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Get system statistics"""
    service = AdminService(db)
    return SystemStatsResponse(**service.get_system_stats())


# ============ System Settings ============

@router.get("/settings", response_model=List[SystemSettingResponse])
async def get_settings(
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Get all system settings"""
    service = AdminService(db)
    return [SystemSettingResponse(**s) for s in service.get_all_settings()]


@router.put("/settings/{key}")
async def update_setting(
    key: str,
    request: SystemSettingUpdate,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_superadmin)
):
    """Update a setting (superadmin only)"""
    service = AdminService(db)
    
    setting = service.set_setting(key, request.value, admin.id)
    
    service.log_action(
        admin_id=admin.id,
        action="setting.update",
        details={"key": key, "value": request.value}
    )
    
    return {"message": "Setting updated", "key": key}


# ============ Audit Logs ============

@router.get("/audit-logs", response_model=List[AuditLogResponse])
async def get_audit_logs(
    days: int = 30,
    limit: int = 100,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Get audit logs"""
    service = AdminService(db)
    logs = service.get_audit_logs(days, limit)
    return [AuditLogResponse.model_validate(log) for log in logs]


# ============ Initial Setup ============

class AdminSetupRequest(AdminCreateRequest):
    """Extended request with optional setup token"""
    setup_token: Optional[str] = None


@router.post("/setup")
@limiter.limit("3/hour")  # Strict rate limiting on setup
async def initial_setup(
    http_request: Request,
    request: AdminSetupRequest,
    db: Session = Depends(get_db)
):
    """
    Create initial superadmin account.
    
    This endpoint only works if no admin accounts exist yet.
    For additional security, you can set ADMIN_SETUP_TOKEN environment
    variable to require a token for setup.
    
    Use this after first deployment to create your admin access.
    """
    from app.core.config import get_settings
    settings = get_settings()
    
    # Check if setup is already completed
    existing = db.query(AdminUser).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Setup already completed. Use /admin/login instead."
        )
    
    # Check for setup token if configured
    setup_token = getattr(settings, 'admin_setup_token', None)
    if setup_token and setup_token.strip():
        if not request.setup_token:
            raise HTTPException(
                status_code=403,
                detail="Setup token required. Include 'setup_token' in request body."
            )
        if request.setup_token != setup_token:
            raise HTTPException(
                status_code=403,
                detail="Invalid setup token."
            )
    
    admin = create_initial_superadmin(
        db=db,
        email=request.email,
        password=request.password,
        name=request.name
    )
    
    if not admin:
        raise HTTPException(status_code=400, detail="Failed to create admin")
    
    return {
        "message": "Setup complete! You can now login.",
        "admin_email": admin.email,
        "login_url": "/api/v1/admin/login"
    }

"""
Onboarding API Routes
=====================

Endpoints for guided user onboarding flow.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.models.user import User
from app.auth.dependencies import get_current_user
from app.onboarding.service import (
    OnboardingService, get_onboarding_service,
    ONBOARDING_STEPS, USER_GOALS, BRAND_TEMPLATES
)

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


# ==================== Schemas ====================

class OnboardingStatusResponse(BaseModel):
    is_complete: bool
    current_step: str
    completed_steps: List[str]
    progress_percent: int
    selected_goal: Optional[str]
    steps: List[dict]
    started_at: Optional[str]
    completed_at: Optional[str]


class SetGoalRequest(BaseModel):
    goal_id: str = Field(..., description="Selected goal ID")


class CreateBrandRequest(BaseModel):
    template_id: str = Field(..., description="Brand template ID")
    brand_name: str = Field(..., min_length=2, max_length=100)
    customizations: Optional[dict] = None


class QuickBrandRequest(BaseModel):
    brand_name: str = Field(..., min_length=2, max_length=100)
    brand_type: str = Field(default="personal", pattern="^(personal|business|ecommerce|creative|fitness|food)$")


class GenerateContentRequest(BaseModel):
    brand_id: int
    content_type: str = Field(default="caption", pattern="^(caption|image)$")


class UpdateStepRequest(BaseModel):
    step_id: str
    completed: bool = True
    data: Optional[dict] = None


class BrandResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    persona_name: Optional[str]
    persona_voice: Optional[str]
    
    class Config:
        from_attributes = True


class ContentResponse(BaseModel):
    id: int
    content_type: str
    caption: Optional[str]
    hashtags: Optional[List[str]]
    result_url: Optional[str]
    
    class Config:
        from_attributes = True


# ==================== Endpoints ====================

@router.get("/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's onboarding status and progress."""
    service = get_onboarding_service(db)
    return service.get_onboarding_status(current_user)


@router.get("/goals")
async def get_goals():
    """Get available user goals for onboarding."""
    return {
        "goals": USER_GOALS
    }


@router.post("/goals")
async def set_goal(
    request: SetGoalRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Set user's primary goal."""
    service = get_onboarding_service(db)
    try:
        return service.set_goal(current_user, request.goal_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/brand-templates")
async def get_brand_templates(
    goal_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get brand templates, optionally filtered by user's goal."""
    service = get_onboarding_service(db)
    
    # If no goal specified, try to get from user's onboarding data
    if not goal_id and current_user.onboarding_data:
        goal_id = current_user.onboarding_data.get("selected_goal")
    
    templates = service.get_brand_templates(goal_id)
    return {"templates": templates, "goal_filter": goal_id}


@router.post("/brand", response_model=BrandResponse)
@limiter.limit("5/minute")
async def create_brand_from_template(
    request_obj: Request,
    response: Response,
    request: CreateBrandRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a brand from a template during onboarding."""
    service = get_onboarding_service(db)
    try:
        brand = await service.create_brand_from_template(
            user=current_user,
            template_id=request.template_id,
            brand_name=request.brand_name,
            customizations=request.customizations
        )
        return brand
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/brand/quick", response_model=BrandResponse)
@limiter.limit("5/minute")
async def create_quick_brand(
    request_obj: Request,
    response: Response,
    request: QuickBrandRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a brand with minimal input for fastest onboarding."""
    service = get_onboarding_service(db)
    brand = await service.create_quick_brand(
        user=current_user,
        brand_name=request.brand_name,
        brand_type=request.brand_type
    )
    return brand


@router.post("/generate-content", response_model=ContentResponse)
@limiter.limit("3/minute")
async def generate_first_content(
    request_obj: Request,
    response: Response,
    request: GenerateContentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate first piece of content during onboarding."""
    from app.models.models import Brand
    
    # Verify brand belongs to user
    brand = db.query(Brand).filter(
        Brand.id == request.brand_id,
        Brand.user_id == current_user.id
    ).first()
    
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    service = get_onboarding_service(db)
    content = await service.generate_first_content(
        user=current_user,
        brand=brand,
        content_type=request.content_type
    )
    
    return ContentResponse(
        id=content.id,
        content_type=content.content_type.value if hasattr(content.content_type, 'value') else str(content.content_type),
        caption=content.caption,
        hashtags=content.hashtags,
        result_url=content.result_url
    )


@router.post("/step")
async def update_step(
    request: UpdateStepRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update onboarding step status."""
    service = get_onboarding_service(db)
    return service.update_step(
        user=current_user,
        step_id=request.step_id,
        completed=request.completed,
        data=request.data
    )


@router.post("/skip")
async def skip_onboarding(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Skip the onboarding process."""
    service = get_onboarding_service(db)
    return service.skip_onboarding(current_user)


@router.post("/demo-brand", response_model=BrandResponse)
async def create_demo_brand(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a demo brand with sample data."""
    from app.models.models import Brand
    
    # Check if user already has a demo brand
    existing_demo = db.query(Brand).filter(
        Brand.user_id == current_user.id,
        Brand.is_demo == True
    ).first()
    
    if existing_demo:
        return existing_demo
    
    service = get_onboarding_service(db)
    brand = await service.create_demo_brand(current_user)
    return brand


@router.get("/analytics")
async def get_onboarding_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get onboarding analytics (admin only)."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    service = get_onboarding_service(db)
    return service.get_onboarding_analytics()

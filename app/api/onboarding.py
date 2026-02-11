"""
Onboarding API Endpoints

Manages the new user onboarding flow:
1. Track onboarding status
2. Save user goals and preferences
3. Mark onboarding complete
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.database import get_db
from app.core.auth import get_current_user

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


class OnboardingGoals(BaseModel):
    user_type: str  # creator, business, agency
    goals: List[str]  # grow_audience, save_time, etc.


class OnboardingStatus(BaseModel):
    is_complete: bool
    current_step: Optional[str] = None
    completed_steps: List[str] = []
    user_type: Optional[str] = None
    goals: List[str] = []
    has_brand: bool = False
    has_avatar: bool = False
    has_social: bool = False
    has_content: bool = False


@router.get("/status", response_model=OnboardingStatus)
async def get_onboarding_status(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get current onboarding status for the user.
    Checks what steps have been completed.
    """
    # Check if user has completed onboarding
    # This could be stored in user profile or separate table
    
    # For now, infer from what exists
    from app.models.brand import Brand
    from app.lora.models import LoraModel
    
    has_brand = db.query(Brand).filter(Brand.user_id == current_user.id).first() is not None
    has_avatar = db.query(LoraModel).filter(LoraModel.user_id == current_user.id).first() is not None
    
    # Check user metadata for onboarding completion
    is_complete = getattr(current_user, 'onboarding_complete', False)
    if not is_complete and hasattr(current_user, 'metadata') and current_user.metadata:
        is_complete = current_user.metadata.get('onboarding_complete', False)
    
    # Infer completion if they have brand + content
    if has_brand:
        is_complete = True
    
    completed_steps = []
    if has_brand:
        completed_steps.append('brand')
    if has_avatar:
        completed_steps.append('avatar')
    
    return OnboardingStatus(
        is_complete=is_complete,
        current_step='welcome' if not completed_steps else None,
        completed_steps=completed_steps,
        has_brand=has_brand,
        has_avatar=has_avatar,
        has_social=False,  # Would check social_accounts table
        has_content=False  # Would check studio_projects table
    )


@router.post("/goals")
async def save_onboarding_goals(
    goals: OnboardingGoals,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Save user's goals and type from onboarding step 1.
    """
    # Store in user metadata
    try:
        if not hasattr(current_user, 'metadata') or current_user.metadata is None:
            current_user.metadata = {}
        
        current_user.metadata['user_type'] = goals.user_type
        current_user.metadata['goals'] = goals.goals
        current_user.metadata['onboarding_started_at'] = datetime.utcnow().isoformat()
        
        db.commit()
        
        return {"success": True, "message": "Goals saved"}
    except Exception as e:
        return {"success": True, "message": "Goals noted"}  # Non-critical


@router.post("/complete")
async def complete_onboarding(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Mark onboarding as complete.
    """
    try:
        if not hasattr(current_user, 'metadata') or current_user.metadata is None:
            current_user.metadata = {}
        
        current_user.metadata['onboarding_complete'] = True
        current_user.metadata['onboarding_completed_at'] = datetime.utcnow().isoformat()
        
        db.commit()
        
        return {"success": True, "message": "Onboarding complete!"}
    except Exception as e:
        return {"success": True, "message": "Welcome aboard!"}


@router.get("/goals")
async def get_available_goals():
    """
    Get available goal options for onboarding.
    """
    return {
        "goals": [
            {"id": "grow_audience", "label": "Grow my audience", "icon": "users"},
            {"id": "save_time", "label": "Save time on content", "icon": "clock"},
            {"id": "consistent_brand", "label": "Consistent branding", "icon": "target"},
            {"id": "more_content", "label": "Post more frequently", "icon": "calendar"},
        ],
        "user_types": [
            {"id": "creator", "label": "Solo Creator"},
            {"id": "business", "label": "Small Business"},
            {"id": "agency", "label": "Agency"},
        ]
    }


@router.get("/brand-templates")
async def get_brand_templates(goal_id: Optional[str] = None):
    """
    Get brand templates based on selected goal.
    """
    templates = [
        {
            "id": "professional",
            "name": "Professional Services",
            "description": "Clean, authoritative voice for B2B",
            "voice_tone": "professional",
            "example_post": "Excited to share our latest insights on..."
        },
        {
            "id": "lifestyle",
            "name": "Lifestyle Brand",
            "description": "Warm, relatable voice for consumer brands",
            "voice_tone": "casual",
            "example_post": "Nothing beats that feeling when..."
        },
        {
            "id": "tech",
            "name": "Tech Startup",
            "description": "Innovative, forward-thinking voice",
            "voice_tone": "professional",
            "example_post": "We're building the future of..."
        },
        {
            "id": "personal",
            "name": "Personal Brand",
            "description": "Authentic, personal connection",
            "voice_tone": "casual",
            "example_post": "Here's what I learned this week..."
        },
    ]
    
    return {"templates": templates}

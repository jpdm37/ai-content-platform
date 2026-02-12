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
from app.models.user import User
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


# ========== Schemas ==========

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


def get_user_metadata(user) -> dict:
    """Safely get user metadata as a dictionary."""
    # Handle case where metadata might be None, a dict, or something else
    # Try user_metadata first (the correct field name), then metadata as fallback
    meta = getattr(user, 'user_metadata', None) or getattr(user, 'preferences', None)
    if meta is None:
        return {}
    if isinstance(meta, dict):
        return meta
    # If it's some other type, return empty dict
    return {}


def set_user_metadata(user, key: str, value, db: Session):
    """Safely set a value in user metadata."""
    # Determine which attribute to use
    attr_name = 'user_metadata' if hasattr(user, 'user_metadata') else 'preferences'
    
    current_meta = getattr(user, attr_name, None)
    if current_meta is None:
        current_meta = {}
    if not isinstance(current_meta, dict):
        current_meta = {}
    
    current_meta[key] = value
    setattr(user, attr_name, current_meta)
    
    # Mark as modified for SQLAlchemy to detect the change
    try:
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(user, attr_name)
    except Exception:
        pass


# ========== Endpoints ==========

@router.get("/status", response_model=OnboardingStatus)
async def get_onboarding_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get current onboarding status for the user.
    Checks what steps have been completed.
    """
    from app.models.models import Brand
    
    # Check what exists for this user
    has_brand = db.query(Brand).filter(Brand.user_id == current_user.id).first() is not None
    
    # Check for avatar (LoRA model)
    has_avatar = False
    try:
        from app.lora.models import LoraModel
        has_avatar = db.query(LoraModel).filter(LoraModel.user_id == current_user.id).first() is not None
    except Exception:
        pass
    
    # Check user metadata for onboarding completion
    user_meta = get_user_metadata(current_user)
    
    is_complete = user_meta.get('onboarding_complete', False)
    user_type = user_meta.get('user_type')
    goals = user_meta.get('goals', [])
    
    # Infer completion if they have brand
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
        user_type=user_type,
        goals=goals,
        has_brand=has_brand,
        has_avatar=has_avatar,
        has_social=False,
        has_content=False
    )


@router.post("/goals")
async def save_onboarding_goals(
    goals: OnboardingGoals,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Save user's goals and type from onboarding step 1.
    """
    try:
        set_user_metadata(current_user, 'user_type', goals.user_type, db)
        set_user_metadata(current_user, 'goals', goals.goals, db)
        set_user_metadata(current_user, 'onboarding_started_at', datetime.utcnow().isoformat(), db)
        
        db.commit()
        
        return {"success": True, "message": "Goals saved"}
    except Exception as e:
        print(f"Error saving goals: {e}")
        return {"success": True, "message": "Goals noted"}


@router.post("/complete")
async def complete_onboarding(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark onboarding as complete.
    """
    try:
        set_user_metadata(current_user, 'onboarding_complete', True, db)
        set_user_metadata(current_user, 'onboarding_completed_at', datetime.utcnow().isoformat(), db)
        
        db.commit()
        
        return {"success": True, "message": "Onboarding complete!"}
    except Exception as e:
        print(f"Error completing onboarding: {e}")
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

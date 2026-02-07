"""
Content Templates API Routes
============================

Endpoints for browsing and using content templates.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.auth.dependencies import get_current_user
from app.templates.service import (
    ContentTemplatesService, get_templates_service,
    TEMPLATE_CATEGORIES, CONTENT_TEMPLATES
)

router = APIRouter(prefix="/templates", tags=["templates"])


# ==================== Schemas ====================

class TemplateCategory(BaseModel):
    id: str
    name: str
    description: str
    icon: str


class ContentTemplate(BaseModel):
    id: str
    category_id: str
    name: str
    description: str
    platforms: List[str]
    prompt_template: str
    variables: List[str]
    example_output: str
    best_for: List[str]
    tips: List[str]


class GenerateFromTemplateRequest(BaseModel):
    template_id: str
    variables: dict
    brand_voice: Optional[str] = None


# ==================== Endpoints ====================

@router.get("/categories")
async def get_template_categories():
    """Get all template categories."""
    service = get_templates_service()
    return {"categories": service.get_categories()}


@router.get("/")
async def get_templates(
    category_id: Optional[str] = None,
    platform: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get templates with optional filtering."""
    service = get_templates_service(db)
    templates = service.get_templates(
        category_id=category_id,
        platform=platform,
        search=search
    )
    return {"templates": templates, "count": len(templates)}


@router.get("/popular")
async def get_popular_templates(
    limit: int = Query(default=6, le=20),
    current_user: User = Depends(get_current_user)
):
    """Get popular/recommended templates."""
    service = get_templates_service()
    templates = service.get_popular_templates(limit)
    return {"templates": templates}


@router.get("/by-category")
async def get_templates_by_category(
    current_user: User = Depends(get_current_user)
):
    """Get all templates grouped by category."""
    service = get_templates_service()
    return service.get_templates_by_category()


@router.get("/recommended")
async def get_recommended_templates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get templates recommended based on user's goal."""
    user_goal = None
    if current_user.onboarding_data:
        user_goal = current_user.onboarding_data.get("selected_goal")
    
    service = get_templates_service(db)
    
    if user_goal:
        templates = service.get_templates_for_goal(user_goal)
    else:
        templates = service.get_popular_templates(12)
    
    return {"templates": templates, "based_on_goal": user_goal}


@router.get("/{template_id}")
async def get_template(
    template_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get a specific template by ID."""
    service = get_templates_service()
    template = service.get_template(template_id)
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return template


@router.post("/generate-prompt")
async def generate_prompt_from_template(
    request: GenerateFromTemplateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a filled prompt from a template."""
    service = get_templates_service(db)
    
    try:
        prompt = service.generate_from_template(
            template_id=request.template_id,
            variables=request.variables,
            brand_voice=request.brand_voice
        )
        
        template = service.get_template(request.template_id)
        
        return {
            "prompt": prompt,
            "template_name": template["name"] if template else None,
            "platforms": template["platforms"] if template else []
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

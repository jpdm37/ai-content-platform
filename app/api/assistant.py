"""
AI Assistant Chat API Routes

Interactive AI assistant for content creation help.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.auth.dependencies import get_current_user, get_current_verified_user
from app.assistant.service import AIAssistantService

router = APIRouter(prefix="/assistant", tags=["ai-assistant"])


# ========== Schemas ==========

class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    conversation_history: Optional[List[ChatMessage]] = None
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    response: str
    actions: List[Dict[str, Any]] = []
    tokens_used: int = 0


class ImproveRequest(BaseModel):
    content: str = Field(..., min_length=10, max_length=5000)
    improvement_type: str = Field(default="general", pattern="^(general|shorter|longer|engaging|professional|casual)$")


class HashtagRequest(BaseModel):
    content: str = Field(..., min_length=10, max_length=2000)
    platform: str = Field(default="instagram")
    count: int = Field(default=10, ge=1, le=30)


class TranslateRequest(BaseModel):
    content: str = Field(..., min_length=5, max_length=5000)
    target_language: str


class VariationsRequest(BaseModel):
    content: str = Field(..., min_length=10, max_length=2000)
    count: int = Field(default=3, ge=1, le=5)


class OptimizeRequest(BaseModel):
    content: str = Field(..., min_length=10, max_length=5000)
    platform: str


class CTARequest(BaseModel):
    content: str = Field(..., min_length=10, max_length=2000)
    goal: str = Field(default="engagement")


# ========== Endpoints ==========

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Chat with AI assistant for content help.
    
    Context options:
    - brand_id: Apply brand context
    - current_content: Content being edited
    - platform: Target platform
    """
    service = AIAssistantService(db)
    
    history = [msg.model_dump() for msg in request.conversation_history] if request.conversation_history else None
    
    result = await service.chat(
        user_id=current_user.id,
        message=request.message,
        conversation_history=history,
        context=request.context
    )
    
    return ChatResponse(**result)


@router.post("/improve")
async def improve_content(
    request: ImproveRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Quickly improve content with specified improvement type."""
    service = AIAssistantService(db)
    improved = await service.improve_content(request.content, request.improvement_type)
    
    return {
        "original": request.content,
        "improved": improved,
        "improvement_type": request.improvement_type
    }


@router.post("/hashtags")
async def generate_hashtags(
    request: HashtagRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Generate hashtags for content."""
    service = AIAssistantService(db)
    hashtags = await service.generate_hashtags(request.content, request.platform, request.count)
    
    return {
        "hashtags": hashtags,
        "platform": request.platform,
        "count": len(hashtags)
    }


@router.post("/translate")
async def translate_content(
    request: TranslateRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Translate content to another language."""
    service = AIAssistantService(db)
    translated = await service.translate_content(request.content, request.target_language)
    
    return {
        "original": request.content,
        "translated": translated,
        "target_language": request.target_language
    }


@router.post("/variations")
async def generate_variations(
    request: VariationsRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Generate content variations."""
    service = AIAssistantService(db)
    variations = await service.generate_variations(request.content, request.count)
    
    return {
        "original": request.content,
        "variations": variations,
        "count": len(variations)
    }


@router.post("/optimize")
async def optimize_for_platform(
    request: OptimizeRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Optimize content for a specific platform."""
    service = AIAssistantService(db)
    result = await service.optimize_for_platform(request.content, request.platform)
    return result


@router.post("/suggest-cta")
async def suggest_cta(
    request: CTARequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Suggest call-to-action phrases."""
    service = AIAssistantService(db)
    ctas = await service.suggest_cta(request.content, request.goal)
    
    return {
        "suggestions": ctas,
        "goal": request.goal
    }


@router.get("/capabilities")
async def get_capabilities():
    """List assistant capabilities."""
    return {
        "capabilities": [
            {"id": "chat", "name": "Chat", "description": "Interactive conversation about content"},
            {"id": "improve", "name": "Improve", "description": "Improve existing content"},
            {"id": "hashtags", "name": "Hashtags", "description": "Generate relevant hashtags"},
            {"id": "translate", "name": "Translate", "description": "Translate to other languages"},
            {"id": "variations", "name": "Variations", "description": "Create content variations"},
            {"id": "optimize", "name": "Optimize", "description": "Optimize for platforms"},
            {"id": "cta", "name": "CTA", "description": "Suggest call-to-action phrases"},
        ],
        "improvement_types": ["general", "shorter", "longer", "engaging", "professional", "casual"],
        "supported_platforms": ["twitter", "instagram", "linkedin", "tiktok", "facebook"]
    }

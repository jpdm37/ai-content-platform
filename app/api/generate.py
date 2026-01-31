"""
Content Generation API Routes - Protected by Authentication
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import get_settings
from app.models import (
    Brand, Category, Trend, GeneratedContent,
    ContentType, ContentStatus
)
from app.models.schemas import (
    GenerateContentRequest, GenerateAvatarRequest, GeneratedContentResponse,
    ContentTypeEnum
)
from app.models.user import User
from app.auth.dependencies import get_current_user, get_current_verified_user
from app.services.generator import ContentGeneratorService

settings = get_settings()
router = APIRouter(prefix="/generate", tags=["generation"])


def get_user_api_keys(user: User) -> tuple[str, str]:
    """Get API keys - use user's keys if available, otherwise fall back to system keys"""
    openai_key = user.openai_api_key or settings.openai_api_key
    replicate_key = user.replicate_api_token or settings.replicate_api_token
    return openai_key, replicate_key


@router.post("/avatar", response_model=GeneratedContentResponse)
async def generate_avatar(
    request: GenerateAvatarRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Generate an AI avatar image for a brand"""
    brand = db.query(Brand).filter(
        Brand.id == request.brand_id,
        Brand.user_id == current_user.id
    ).first()
    
    if not brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    
    openai_key, replicate_key = get_user_api_keys(current_user)
    
    if not replicate_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Replicate API key configured. Please add your key in settings."
        )
    
    generator = ContentGeneratorService(db, openai_key, replicate_key)
    
    try:
        content = await generator.generate_avatar_image(
            brand=brand,
            user_id=current_user.id,
            custom_prompt=request.custom_prompt
        )
        return content
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Generation failed: {str(e)}"
        )


@router.post("/content", response_model=GeneratedContentResponse)
async def generate_content(
    request: GenerateContentRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Generate content (image, text) for a brand"""
    brand = db.query(Brand).filter(
        Brand.id == request.brand_id,
        Brand.user_id == current_user.id
    ).first()
    
    if not brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    
    category = None
    if request.category_id:
        category = db.query(Category).filter(Category.id == request.category_id).first()
        if not category:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    
    trend = None
    if request.trend_id:
        trend = db.query(Trend).filter(Trend.id == request.trend_id).first()
        if not trend:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trend not found")
    
    content_type_map = {
        ContentTypeEnum.IMAGE: ContentType.IMAGE,
        ContentTypeEnum.TEXT: ContentType.TEXT,
        ContentTypeEnum.VIDEO: ContentType.VIDEO
    }
    content_type = content_type_map.get(request.content_type, ContentType.IMAGE)
    
    openai_key, replicate_key = get_user_api_keys(current_user)
    
    if content_type == ContentType.IMAGE and not replicate_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Replicate API key configured for image generation."
        )
    
    generator = ContentGeneratorService(db, openai_key, replicate_key)
    
    try:
        content = await generator.generate_content(
            brand=brand,
            user_id=current_user.id,
            content_type=content_type,
            category=category,
            trend=trend,
            custom_prompt=request.custom_prompt,
            include_caption=request.include_caption
        )
        return content
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Generation failed: {str(e)}"
        )


@router.get("/content", response_model=List[GeneratedContentResponse])
async def list_generated_content(
    brand_id: Optional[int] = None,
    category_id: Optional[int] = None,
    content_type: Optional[ContentTypeEnum] = None,
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all generated content for the current user"""
    query = db.query(GeneratedContent).filter(GeneratedContent.user_id == current_user.id)
    
    if brand_id:
        query = query.filter(GeneratedContent.brand_id == brand_id)
    if category_id:
        query = query.filter(GeneratedContent.category_id == category_id)
    if content_type:
        type_map = {
            ContentTypeEnum.IMAGE: ContentType.IMAGE,
            ContentTypeEnum.TEXT: ContentType.TEXT,
            ContentTypeEnum.VIDEO: ContentType.VIDEO
        }
        query = query.filter(GeneratedContent.content_type == type_map.get(content_type))
    if status_filter:
        status_map = {
            "pending": ContentStatus.PENDING,
            "generating": ContentStatus.GENERATING,
            "completed": ContentStatus.COMPLETED,
            "failed": ContentStatus.FAILED
        }
        if status_filter.lower() in status_map:
            query = query.filter(GeneratedContent.status == status_map[status_filter.lower()])
    
    query = query.order_by(GeneratedContent.created_at.desc())
    content = query.offset(skip).limit(limit).all()
    return content


@router.get("/content/{content_id}", response_model=GeneratedContentResponse)
async def get_generated_content(
    content_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific generated content item"""
    content = db.query(GeneratedContent).filter(
        GeneratedContent.id == content_id,
        GeneratedContent.user_id == current_user.id
    ).first()
    
    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")
    return content


@router.delete("/content/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_generated_content(
    content_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a generated content item"""
    content = db.query(GeneratedContent).filter(
        GeneratedContent.id == content_id,
        GeneratedContent.user_id == current_user.id
    ).first()
    
    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")
    
    db.delete(content)
    db.commit()
    return None


@router.get("/brand/{brand_id}/content", response_model=List[GeneratedContentResponse])
async def get_brand_content(
    brand_id: int,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all generated content for a specific brand"""
    brand = db.query(Brand).filter(
        Brand.id == brand_id,
        Brand.user_id == current_user.id
    ).first()
    
    if not brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    
    content = db.query(GeneratedContent).filter(
        GeneratedContent.brand_id == brand_id,
        GeneratedContent.user_id == current_user.id
    ).order_by(GeneratedContent.created_at.desc()).limit(limit).all()
    
    return content

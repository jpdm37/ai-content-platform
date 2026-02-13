"""
Category API Routes

Handles content categories for trend tracking and content organization.
Categories can be global (system) or user-specific.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel

from app.core.database import get_db
from app.auth.dependencies import get_current_user, get_current_verified_user
from app.models.user import User
from app.models import Category

router = APIRouter(prefix="/categories", tags=["categories"])


# ============ Pydantic Schemas ============
class CategoryCreate(BaseModel):
    """Schema for creating a category"""
    name: str
    description: Optional[str] = None
    keywords: Optional[List[str]] = None
    image_prompt_template: Optional[str] = None
    caption_prompt_template: Optional[str] = None


class CategoryResponse(BaseModel):
    """Schema for category response"""
    id: int
    name: str
    description: Optional[str] = None
    keywords: Optional[List[str]] = None
    image_prompt_template: Optional[str] = None
    caption_prompt_template: Optional[str] = None
    user_id: Optional[int] = None
    
    class Config:
        from_attributes = True


# Default categories to seed (these are global/system categories)
DEFAULT_CATEGORIES = [
    {
        "name": "Lifestyle",
        "description": "General lifestyle content including daily routines, home, and personal development",
        "keywords": ["lifestyle", "daily routine", "home decor", "self care", "wellness"],
        "image_prompt_template": "in a modern, aesthetic lifestyle setting with natural lighting",
        "caption_prompt_template": "Create an engaging lifestyle post about everyday moments and living well"
    },
    {
        "name": "Travel",
        "description": "Travel destinations, tips, and wanderlust content",
        "keywords": ["travel", "vacation", "destination", "adventure", "explore"],
        "image_prompt_template": "at a beautiful travel destination with scenic views",
        "caption_prompt_template": "Create a travel post that inspires wanderlust and adventure"
    },
    {
        "name": "Food & Drink",
        "description": "Food, restaurants, recipes, and culinary experiences",
        "keywords": ["food", "restaurant", "recipe", "cooking", "foodie", "cuisine"],
        "image_prompt_template": "with delicious food in an aesthetic restaurant or kitchen setting",
        "caption_prompt_template": "Create a mouth-watering food post about culinary delights"
    },
    {
        "name": "Fitness",
        "description": "Fitness, workout, health, and wellness content",
        "keywords": ["fitness", "workout", "gym", "health", "exercise", "training"],
        "image_prompt_template": "in an active fitness setting, gym or outdoor workout environment",
        "caption_prompt_template": "Create a motivational fitness post about health and exercise"
    },
    {
        "name": "Fashion",
        "description": "Fashion, style, clothing, and trends",
        "keywords": ["fashion", "style", "outfit", "clothing", "trend", "designer"],
        "image_prompt_template": "showcasing stylish fashion in an urban or studio setting",
        "caption_prompt_template": "Create a trendy fashion post about style and outfits"
    },
    {
        "name": "Technology",
        "description": "Tech gadgets, apps, and digital innovation",
        "keywords": ["tech", "technology", "gadget", "app", "digital", "innovation"],
        "image_prompt_template": "with modern technology gadgets in a sleek, minimalist setting",
        "caption_prompt_template": "Create an engaging tech post about innovation and gadgets"
    },
    {
        "name": "Beauty",
        "description": "Beauty, skincare, makeup, and self-care routines",
        "keywords": ["beauty", "skincare", "makeup", "cosmetics", "self-care"],
        "image_prompt_template": "in a beautiful vanity or bathroom setting with beauty products",
        "caption_prompt_template": "Create a beauty post about skincare routines and makeup tips"
    },
    {
        "name": "Entertainment",
        "description": "Movies, music, gaming, and pop culture",
        "keywords": ["entertainment", "movies", "music", "gaming", "pop culture"],
        "image_prompt_template": "in an entertainment setting with cozy movie night or gaming vibes",
        "caption_prompt_template": "Create an entertaining post about movies, music, or gaming"
    },
    {
        "name": "Business",
        "description": "Business, entrepreneurship, and professional development",
        "keywords": ["business", "entrepreneur", "startup", "professional", "career"],
        "image_prompt_template": "in a modern office or co-working space with professional atmosphere",
        "caption_prompt_template": "Create a business-focused post about entrepreneurship and success"
    },
    {
        "name": "Pets",
        "description": "Pets, animals, and pet care content",
        "keywords": ["pets", "dogs", "cats", "animals", "pet care"],
        "image_prompt_template": "with adorable pets in a cozy home or outdoor setting",
        "caption_prompt_template": "Create a heartwarming pet post about furry friends and animal companions"
    }
]


@router.get("/", response_model=List[CategoryResponse])
async def list_categories(
    skip: int = 0,
    limit: int = 100,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all categories.
    Returns global categories (user_id=NULL) plus user's own categories.
    """
    # Build query for global categories OR user's categories
    if current_user:
        query = db.query(Category).filter(
            or_(
                Category.user_id == None,  # Global categories
                Category.user_id == current_user.id  # User's categories
            )
        )
    else:
        # Anonymous users only see global categories
        query = db.query(Category).filter(Category.user_id == None)
    
    categories = query.offset(skip).limit(limit).all()
    return categories


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: int,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific category by ID"""
    category = db.query(Category).filter(Category.id == category_id).first()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    # Check access: must be global or owned by user
    if category.user_id is not None:
        if not current_user or category.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this category"
            )
    
    return category


@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CategoryCreate,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Create a new user-specific category"""
    # Check if user already has a category with this name
    existing = db.query(Category).filter(
        Category.name == category_data.name,
        Category.user_id == current_user.id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have a category with this name"
        )
    
    category = Category(
        name=category_data.name,
        description=category_data.description,
        keywords=category_data.keywords,
        image_prompt_template=category_data.image_prompt_template,
        caption_prompt_template=category_data.caption_prompt_template,
        user_id=current_user.id  # User-specific category
    )
    
    db.add(category)
    db.commit()
    db.refresh(category)
    
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Delete a user's category (cannot delete global categories)"""
    category = db.query(Category).filter(Category.id == category_id).first()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    # Cannot delete global categories
    if category.user_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete global categories"
        )
    
    # Can only delete own categories
    if category.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete another user's category"
        )
    
    db.delete(category)
    db.commit()
    
    return None


@router.post("/seed", response_model=List[CategoryResponse])
async def seed_default_categories(
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Seed the database with default global categories.
    Only creates categories that don't already exist.
    """
    created = []
    
    for cat_data in DEFAULT_CATEGORIES:
        # Check if global category with this name already exists
        existing = db.query(Category).filter(
            Category.name == cat_data["name"],
            Category.user_id == None  # Global category
        ).first()
        
        if existing:
            created.append(existing)
            continue
        
        # Create as global category (user_id=None)
        category = Category(
            name=cat_data["name"],
            description=cat_data["description"],
            keywords=cat_data["keywords"],
            image_prompt_template=cat_data["image_prompt_template"],
            caption_prompt_template=cat_data["caption_prompt_template"],
            user_id=None  # Global category
        )
        db.add(category)
        db.commit()
        db.refresh(category)
        created.append(category)
    
    return created


@router.get("/by-name/{name}", response_model=CategoryResponse)
async def get_category_by_name(
    name: str,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a category by name (case-insensitive)"""
    # First try to find user's category, then global
    if current_user:
        category = db.query(Category).filter(
            Category.name.ilike(name),
            Category.user_id == current_user.id
        ).first()
        
        if category:
            return category
    
    # Fall back to global category
    category = db.query(Category).filter(
        Category.name.ilike(name),
        Category.user_id == None
    ).first()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category '{name}' not found"
        )
    
    return category

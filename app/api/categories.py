"""
Category API Routes

Handles content categories for trend tracking and content organization.
Categories can be global (system) or user-specific.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.database import get_db
from app.auth.dependencies import get_current_user, get_current_verified_user
from app.models.user import User
from app.models import Category
from app.schemas import CategoryCreate, CategoryResponse

router = APIRouter(prefix="/categories", tags=["categories"])


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
        "description": "Beauty, skincare, makeup, and self-care content",
        "keywords": ["beauty", "skincare", "makeup", "cosmetics", "self-care"],
        "image_prompt_template": "in a clean, aesthetic beauty setting with soft lighting",
        "caption_prompt_template": "Create a beauty post about skincare, makeup, or self-care routines"
    },
    {
        "name": "Business",
        "description": "Business, entrepreneurship, and professional content",
        "keywords": ["business", "entrepreneur", "startup", "professional", "career"],
        "image_prompt_template": "in a modern office or professional setting",
        "caption_prompt_template": "Create a professional post about business insights and entrepreneurship"
    },
    {
        "name": "Entertainment",
        "description": "Movies, music, gaming, and pop culture",
        "keywords": ["entertainment", "movies", "music", "gaming", "pop culture"],
        "image_prompt_template": "in an entertainment or media-focused setting",
        "caption_prompt_template": "Create an engaging post about entertainment and pop culture"
    },
    {
        "name": "Education",
        "description": "Educational content, tips, and how-to guides",
        "keywords": ["education", "learning", "tutorial", "how-to", "tips"],
        "image_prompt_template": "in a clean, educational setting with visual aids",
        "caption_prompt_template": "Create an educational post that teaches or informs"
    }
]


@router.get("/", response_model=List[CategoryResponse])
async def list_categories(
    skip: int = 0,
    limit: int = 100,
    include_global: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List categories - includes global (system) categories and user's custom categories
    """
    query = db.query(Category)
    
    # Check if Category model has user_id column
    if hasattr(Category, 'user_id'):
        if include_global:
            # Get both global (user_id=None) and user's categories
            query = query.filter(
                or_(
                    Category.user_id == None,
                    Category.user_id == current_user.id
                )
            )
        else:
            # Only user's custom categories
            query = query.filter(Category.user_id == current_user.id)
    
    categories = query.order_by(Category.name).offset(skip).limit(limit).all()
    return categories


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific category by ID"""
    category = db.query(Category).filter(Category.id == category_id).first()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    # Check access if category is user-specific
    if hasattr(Category, 'user_id') and category.user_id is not None:
        if category.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this category"
            )
    
    return category


@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user)
):
    """Create a new custom category for the user"""
    # Check if category already exists for this user
    query = db.query(Category).filter(Category.name == category_data.name)
    
    if hasattr(Category, 'user_id'):
        query = query.filter(
            or_(
                Category.user_id == None,
                Category.user_id == current_user.id
            )
        )
    
    existing = query.first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this name already exists"
        )
    
    # Create category data
    category_dict = {
        "name": category_data.name,
        "description": category_data.description,
        "keywords": category_data.keywords,
        "image_prompt_template": category_data.image_prompt_template,
        "caption_prompt_template": category_data.caption_prompt_template
    }
    
    # Add user_id if the model supports it
    if hasattr(Category, 'user_id'):
        category_dict["user_id"] = current_user.id
    
    category = Category(**category_dict)
    
    db.add(category)
    db.commit()
    db.refresh(category)
    
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user)
):
    """Delete a user's custom category (cannot delete global categories)"""
    category = db.query(Category).filter(Category.id == category_id).first()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    # Check if it's a global category
    if hasattr(Category, 'user_id'):
        if category.user_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete system categories"
            )
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Seed the database with default categories.
    Creates global categories (user_id=None) that all users can access.
    This endpoint requires authentication but any user can trigger it.
    """
    created = []
    
    for cat_data in DEFAULT_CATEGORIES:
        # Check if already exists (global category)
        query = db.query(Category).filter(Category.name == cat_data["name"])
        
        if hasattr(Category, 'user_id'):
            query = query.filter(Category.user_id == None)
        
        existing = query.first()
        
        if existing:
            created.append(existing)
            continue
        
        # Create new global category
        category_dict = dict(cat_data)
        if hasattr(Category, 'user_id'):
            category_dict["user_id"] = None  # Global category
        
        try:
            category = Category(**category_dict)
            db.add(category)
            db.commit()
            db.refresh(category)
            created.append(category)
        except Exception as e:
            db.rollback()
            # If individual category fails, continue with others
            print(f"Failed to create category {cat_data['name']}: {e}")
            continue
    
    return created


@router.get("/by-name/{name}", response_model=CategoryResponse)
async def get_category_by_name(
    name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a category by name"""
    query = db.query(Category).filter(Category.name.ilike(name))
    
    if hasattr(Category, 'user_id'):
        query = query.filter(
            or_(
                Category.user_id == None,
                Category.user_id == current_user.id
            )
        )
    
    category = query.first()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    return category

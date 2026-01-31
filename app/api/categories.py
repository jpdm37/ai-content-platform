"""
Category API Routes
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Category, CategoryCreate, CategoryResponse

router = APIRouter(prefix="/categories", tags=["categories"])


# Default categories to seed
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
]


@router.get("/", response_model=List[CategoryResponse])
async def list_categories(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all categories"""
    categories = db.query(Category).offset(skip).limit(limit).all()
    return categories


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(category_id: int, db: Session = Depends(get_db)):
    """Get a specific category by ID"""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    return category


@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CategoryCreate,
    db: Session = Depends(get_db)
):
    """Create a new category"""
    # Check if category already exists
    existing = db.query(Category).filter(Category.name == category_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this name already exists"
        )
    
    category = Category(
        name=category_data.name,
        description=category_data.description,
        keywords=category_data.keywords,
        image_prompt_template=category_data.image_prompt_template,
        caption_prompt_template=category_data.caption_prompt_template
    )
    
    db.add(category)
    db.commit()
    db.refresh(category)
    
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(category_id: int, db: Session = Depends(get_db)):
    """Delete a category"""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    db.delete(category)
    db.commit()
    
    return None


@router.post("/seed", response_model=List[CategoryResponse])
async def seed_default_categories(db: Session = Depends(get_db)):
    """Seed the database with default categories"""
    created = []
    
    for cat_data in DEFAULT_CATEGORIES:
        # Check if already exists
        existing = db.query(Category).filter(Category.name == cat_data["name"]).first()
        if existing:
            created.append(existing)
            continue
        
        category = Category(**cat_data)
        db.add(category)
        db.commit()
        db.refresh(category)
        created.append(category)
    
    return created

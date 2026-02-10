"""
Setup/Initialization Endpoints

These endpoints handle one-time setup tasks that should be accessible
without requiring admin privileges (for initial setup).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models import Category

router = APIRouter(prefix="/setup", tags=["setup"])

# Default categories to seed
DEFAULT_CATEGORIES = [
    {
        "name": "Lifestyle",
        "description": "General lifestyle content including daily routines, home, and personal development",
        "keywords": ["lifestyle", "daily routine", "home decor", "self care", "wellness"],
        "is_global": True
    },
    {
        "name": "Travel",
        "description": "Travel destinations, tips, and wanderlust content",
        "keywords": ["travel", "vacation", "destination", "adventure", "explore"],
        "is_global": True
    },
    {
        "name": "Food & Drink",
        "description": "Food, restaurants, recipes, and culinary experiences",
        "keywords": ["food", "restaurant", "recipe", "cooking", "foodie", "cuisine"],
        "is_global": True
    },
    {
        "name": "Fitness",
        "description": "Fitness, workout, health, and wellness content",
        "keywords": ["fitness", "workout", "gym", "health", "exercise", "training"],
        "is_global": True
    },
    {
        "name": "Fashion",
        "description": "Fashion, style, clothing, and trends",
        "keywords": ["fashion", "style", "outfit", "clothing", "trend", "designer"],
        "is_global": True
    },
    {
        "name": "Technology",
        "description": "Tech gadgets, apps, and digital innovation",
        "keywords": ["tech", "technology", "gadget", "app", "digital", "innovation", "AI"],
        "is_global": True
    },
    {
        "name": "Business",
        "description": "Business, entrepreneurship, and professional content",
        "keywords": ["business", "entrepreneur", "startup", "leadership", "success"],
        "is_global": True
    },
    {
        "name": "Beauty",
        "description": "Beauty, skincare, makeup, and self-care",
        "keywords": ["beauty", "skincare", "makeup", "cosmetics", "self care"],
        "is_global": True
    },
    {
        "name": "Entertainment",
        "description": "Movies, TV, music, gaming, and pop culture",
        "keywords": ["entertainment", "movies", "music", "gaming", "celebrity", "pop culture"],
        "is_global": True
    },
    {
        "name": "Finance",
        "description": "Personal finance, investing, and money management",
        "keywords": ["finance", "investing", "money", "stocks", "crypto", "savings"],
        "is_global": True
    },
]


@router.post("/seed-categories")
async def seed_categories(db: Session = Depends(get_db)):
    """
    Seed default categories if they don't exist.
    This endpoint is idempotent - safe to call multiple times.
    No authentication required for initial setup.
    """
    created = []
    existing = []
    
    for cat_data in DEFAULT_CATEGORIES:
        # Check if category already exists
        existing_cat = db.query(Category).filter(
            Category.name == cat_data["name"],
            Category.is_global == True
        ).first()
        
        if existing_cat:
            existing.append(existing_cat.name)
            continue
        
        # Create new category
        category = Category(**cat_data, user_id=None)
        db.add(category)
        db.commit()
        db.refresh(category)
        created.append(category.name)
    
    return {
        "message": "Categories seeded successfully",
        "created": created,
        "already_existed": existing,
        "total_categories": len(created) + len(existing)
    }


@router.get("/status")
async def get_setup_status(db: Session = Depends(get_db)):
    """
    Check the setup status of the platform.
    Returns what has been configured and what's missing.
    """
    # Count categories
    category_count = db.query(Category).filter(Category.is_global == True).count()
    
    return {
        "categories_seeded": category_count > 0,
        "category_count": category_count,
        "recommended_actions": [
            action for action, condition in [
                ("Seed categories: POST /api/v1/setup/seed-categories", category_count == 0),
            ] if condition
        ]
    }

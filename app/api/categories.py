"""
Category/Niche API Routes

Categories can be:
1. Global (admin-managed) - Available to all users
2. Custom Niches (user-created) - Private to the user/agency
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel

from app.core.database import get_db
from app.models import Category, CategoryCreate, CategoryResponse
from app.auth.dependencies import get_current_user, get_current_active_user
from app.models.user import User

router = APIRouter(prefix="/categories", tags=["categories"])


# ============ Schemas ============

class CustomNicheCreate(BaseModel):
    """Schema for creating a custom niche"""
    name: str
    description: Optional[str] = None
    keywords: Optional[List[str]] = None
    custom_rss_feeds: Optional[List[str]] = None
    custom_google_news_query: Optional[str] = None


class CustomNicheUpdate(BaseModel):
    """Schema for updating a custom niche"""
    name: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[List[str]] = None
    custom_rss_feeds: Optional[List[str]] = None
    custom_google_news_query: Optional[str] = None


class NicheResponse(BaseModel):
    """Response schema for niche/category"""
    id: int
    name: str
    description: Optional[str]
    keywords: Optional[List[str]]
    is_global: bool
    is_owned: bool  # True if owned by requesting user
    custom_rss_feeds: Optional[List[str]] = None
    custom_google_news_query: Optional[str] = None
    
    class Config:
        from_attributes = True


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
    {
        "name": "Business",
        "description": "Business, entrepreneurship, and professional content",
        "keywords": ["business", "entrepreneur", "startup", "leadership", "success"],
        "image_prompt_template": "in a professional business environment with modern aesthetics",
        "caption_prompt_template": "Create an inspiring business post about entrepreneurship and success"
    },
    {
        "name": "Beauty",
        "description": "Beauty, skincare, makeup, and self-care",
        "keywords": ["beauty", "skincare", "makeup", "cosmetics", "self care"],
        "image_prompt_template": "in a clean, aesthetic beauty setting with soft lighting",
        "caption_prompt_template": "Create a beautiful post about skincare and beauty tips"
    },
]


# ============ Global Categories (Read by all, Write by admin) ============

@router.get("/", response_model=List[NicheResponse])
async def list_all_niches(
    include_custom: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List all available niches for the user.
    
    Returns both global categories (admin-managed) and user's custom niches.
    """
    # Build query for categories user can access
    if include_custom:
        # Global categories + user's own custom niches
        categories = db.query(Category).filter(
            or_(
                Category.is_global == True,
                Category.user_id == current_user.id
            )
        ).order_by(Category.is_global.desc(), Category.name).all()
    else:
        # Only global categories
        categories = db.query(Category).filter(
            Category.is_global == True
        ).order_by(Category.name).all()
    
    return [
        NicheResponse(
            id=c.id,
            name=c.name,
            description=c.description,
            keywords=c.keywords,
            is_global=c.is_global,
            is_owned=c.user_id == current_user.id if c.user_id else False,
            custom_rss_feeds=c.custom_rss_feeds,
            custom_google_news_query=c.custom_google_news_query
        )
        for c in categories
    ]


@router.get("/global", response_model=List[NicheResponse])
async def list_global_categories(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List only global categories - public endpoint for reading"""
    categories = db.query(Category).filter(
        Category.is_global == True
    ).offset(skip).limit(limit).all()
    
    return [
        NicheResponse(
            id=c.id,
            name=c.name,
            description=c.description,
            keywords=c.keywords,
            is_global=True,
            is_owned=False,
            custom_rss_feeds=None,
            custom_google_news_query=None
        )
        for c in categories
    ]


@router.get("/{category_id}", response_model=NicheResponse)
async def get_category(
    category_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific category/niche by ID"""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    # Check access - must be global or owned by user
    if not category.is_global and category.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this niche"
        )
    
    return NicheResponse(
        id=category.id,
        name=category.name,
        description=category.description,
        keywords=category.keywords,
        is_global=category.is_global,
        is_owned=category.user_id == current_user.id if category.user_id else False,
        custom_rss_feeds=category.custom_rss_feeds,
        custom_google_news_query=category.custom_google_news_query
    )


# ============ Custom Niches (User-created) ============

@router.post("/custom", response_model=NicheResponse, status_code=status.HTTP_201_CREATED)
async def create_custom_niche(
    niche_data: CustomNicheCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a custom niche for your brand(s).
    
    Custom niches allow you to:
    - Define your own industry/niche keywords
    - Add custom RSS feeds for trend tracking
    - Create custom Google News search queries
    
    The trend scraper will include your custom niche in its analysis.
    """
    # Check if user already has a niche with this name
    existing = db.query(Category).filter(
        Category.user_id == current_user.id,
        Category.name == niche_data.name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have a custom niche with this name"
        )
    
    # Create custom niche
    niche = Category(
        name=niche_data.name,
        description=niche_data.description,
        keywords=niche_data.keywords or [],
        user_id=current_user.id,
        is_global=False,
        custom_rss_feeds=niche_data.custom_rss_feeds,
        custom_google_news_query=niche_data.custom_google_news_query
    )
    
    db.add(niche)
    db.commit()
    db.refresh(niche)
    
    return NicheResponse(
        id=niche.id,
        name=niche.name,
        description=niche.description,
        keywords=niche.keywords,
        is_global=False,
        is_owned=True,
        custom_rss_feeds=niche.custom_rss_feeds,
        custom_google_news_query=niche.custom_google_news_query
    )


@router.get("/custom/mine", response_model=List[NicheResponse])
async def list_my_custom_niches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all custom niches created by the current user"""
    niches = db.query(Category).filter(
        Category.user_id == current_user.id,
        Category.is_global == False
    ).order_by(Category.name).all()
    
    return [
        NicheResponse(
            id=n.id,
            name=n.name,
            description=n.description,
            keywords=n.keywords,
            is_global=False,
            is_owned=True,
            custom_rss_feeds=n.custom_rss_feeds,
            custom_google_news_query=n.custom_google_news_query
        )
        for n in niches
    ]


@router.put("/custom/{niche_id}", response_model=NicheResponse)
async def update_custom_niche(
    niche_id: int,
    niche_data: CustomNicheUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a custom niche you own"""
    niche = db.query(Category).filter(
        Category.id == niche_id,
        Category.user_id == current_user.id
    ).first()
    
    if not niche:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom niche not found or you don't own it"
        )
    
    # Update fields
    if niche_data.name is not None:
        niche.name = niche_data.name
    if niche_data.description is not None:
        niche.description = niche_data.description
    if niche_data.keywords is not None:
        niche.keywords = niche_data.keywords
    if niche_data.custom_rss_feeds is not None:
        niche.custom_rss_feeds = niche_data.custom_rss_feeds
    if niche_data.custom_google_news_query is not None:
        niche.custom_google_news_query = niche_data.custom_google_news_query
    
    db.commit()
    db.refresh(niche)
    
    return NicheResponse(
        id=niche.id,
        name=niche.name,
        description=niche.description,
        keywords=niche.keywords,
        is_global=False,
        is_owned=True,
        custom_rss_feeds=niche.custom_rss_feeds,
        custom_google_news_query=niche.custom_google_news_query
    )


@router.delete("/custom/{niche_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_custom_niche(
    niche_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a custom niche you own"""
    niche = db.query(Category).filter(
        Category.id == niche_id,
        Category.user_id == current_user.id
    ).first()
    
    if not niche:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom niche not found or you don't own it"
        )
    
    db.delete(niche)
    db.commit()
    
    return None


# ============ Admin-only: Global Category Management ============

@router.post("/", response_model=NicheResponse, status_code=status.HTTP_201_CREATED)
async def create_global_category(
    category_data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new global category - requires admin privileges"""
    if not current_user.is_admin and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can create global categories"
        )
    
    existing = db.query(Category).filter(
        Category.name == category_data.name,
        Category.is_global == True
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Global category with this name already exists"
        )
    
    category = Category(
        name=category_data.name,
        description=category_data.description,
        keywords=category_data.keywords,
        image_prompt_template=category_data.image_prompt_template,
        caption_prompt_template=category_data.caption_prompt_template,
        is_global=True,
        user_id=None
    )
    
    db.add(category)
    db.commit()
    db.refresh(category)
    
    return NicheResponse(
        id=category.id,
        name=category.name,
        description=category.description,
        keywords=category.keywords,
        is_global=True,
        is_owned=False,
        custom_rss_feeds=None,
        custom_google_news_query=None
    )


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_global_category(
    category_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a global category - requires admin privileges"""
    if not current_user.is_admin and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can delete global categories"
        )
    
    category = db.query(Category).filter(
        Category.id == category_id,
        Category.is_global == True
    ).first()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Global category not found"
        )
    
    db.delete(category)
    db.commit()
    
    return None


@router.post("/seed", response_model=List[NicheResponse])
async def seed_default_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Seed the database with default global categories - requires admin privileges"""
    if not current_user.is_admin and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can seed categories"
        )
    
    created = []
    
    for cat_data in DEFAULT_CATEGORIES:
        existing = db.query(Category).filter(
            Category.name == cat_data["name"],
            Category.is_global == True
        ).first()
        
        if existing:
            created.append(NicheResponse(
                id=existing.id,
                name=existing.name,
                description=existing.description,
                keywords=existing.keywords,
                is_global=True,
                is_owned=False
            ))
            continue
        
        category = Category(**cat_data, is_global=True, user_id=None)
        db.add(category)
        db.commit()
        db.refresh(category)
        
        created.append(NicheResponse(
            id=category.id,
            name=category.name,
            description=category.description,
            keywords=category.keywords,
            is_global=True,
            is_owned=False
        ))
    
    return created

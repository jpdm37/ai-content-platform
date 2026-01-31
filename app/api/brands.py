"""
Brand API Routes - Protected by Authentication
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Brand, Category, brand_categories
from app.models.schemas import BrandCreate, BrandUpdate, BrandResponse
from app.models.user import User
from app.auth.dependencies import get_current_user, get_current_verified_user

router = APIRouter(prefix="/brands", tags=["brands"])


@router.get("/", response_model=List[BrandResponse])
async def list_brands(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all brands owned by the current user"""
    brands = db.query(Brand).filter(
        Brand.user_id == current_user.id
    ).offset(skip).limit(limit).all()
    return brands


@router.get("/{brand_id}", response_model=BrandResponse)
async def get_brand(
    brand_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific brand by ID"""
    brand = db.query(Brand).filter(
        Brand.id == brand_id,
        Brand.user_id == current_user.id
    ).first()
    
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )
    return brand


@router.post("/", response_model=BrandResponse, status_code=status.HTTP_201_CREATED)
async def create_brand(
    brand_data: BrandCreate,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Create a new brand"""
    brand = Brand(
        user_id=current_user.id,
        name=brand_data.name,
        description=brand_data.description,
        persona_name=brand_data.persona_name,
        persona_age=brand_data.persona_age,
        persona_gender=brand_data.persona_gender,
        persona_style=brand_data.persona_style,
        persona_voice=brand_data.persona_voice,
        persona_traits=brand_data.persona_traits,
        brand_colors=brand_data.brand_colors,
        brand_keywords=brand_data.brand_keywords
    )
    
    if brand_data.category_ids:
        categories = db.query(Category).filter(
            Category.id.in_(brand_data.category_ids)
        ).all()
        brand.categories = categories
    
    db.add(brand)
    db.commit()
    db.refresh(brand)
    
    return brand


@router.put("/{brand_id}", response_model=BrandResponse)
async def update_brand(
    brand_id: int,
    brand_data: BrandUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an existing brand"""
    brand = db.query(Brand).filter(
        Brand.id == brand_id,
        Brand.user_id == current_user.id
    ).first()
    
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )
    
    update_data = brand_data.model_dump(exclude_unset=True)
    category_ids = update_data.pop('category_ids', None)
    
    if category_ids is not None:
        categories = db.query(Category).filter(
            Category.id.in_(category_ids)
        ).all()
        brand.categories = categories
    
    for field, value in update_data.items():
        setattr(brand, field, value)
    
    db.commit()
    db.refresh(brand)
    
    return brand


@router.delete("/{brand_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_brand(
    brand_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a brand"""
    brand = db.query(Brand).filter(
        Brand.id == brand_id,
        Brand.user_id == current_user.id
    ).first()
    
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )
    
    db.delete(brand)
    db.commit()
    
    return None


@router.get("/{brand_id}/categories", response_model=List[dict])
async def get_brand_categories(
    brand_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get categories associated with a brand"""
    brand = db.query(Brand).filter(
        Brand.id == brand_id,
        Brand.user_id == current_user.id
    ).first()
    
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )
    
    return [{"id": c.id, "name": c.name} for c in brand.categories]


@router.post("/{brand_id}/categories/{category_id}")
async def add_category_to_brand(
    brand_id: int,
    category_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a category to a brand"""
    brand = db.query(Brand).filter(
        Brand.id == brand_id,
        Brand.user_id == current_user.id
    ).first()
    
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    if category not in brand.categories:
        brand.categories.append(category)
        db.commit()
    
    return {"message": "Category added to brand"}


@router.delete("/{brand_id}/categories/{category_id}")
async def remove_category_from_brand(
    brand_id: int,
    category_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a category from a brand"""
    brand = db.query(Brand).filter(
        Brand.id == brand_id,
        Brand.user_id == current_user.id
    ).first()
    
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    if category in brand.categories:
        brand.categories.remove(category)
        db.commit()
    
    return {"message": "Category removed from brand"}

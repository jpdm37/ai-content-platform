"""
Email Digest API Routes
=======================

Endpoints for managing email preferences and previewing digests.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.auth.dependencies import get_current_user
from app.digest.service import EmailDigestService, get_digest_service

router = APIRouter(prefix="/digest", tags=["digest"])


# ==================== Schemas ====================

class EmailPreferences(BaseModel):
    weekly_digest: bool = True
    content_suggestions: bool = True
    product_updates: bool = True
    tips_and_tricks: bool = True


class DigestPreview(BaseModel):
    user_name: str
    period: dict
    brands_count: int
    stats: dict
    top_content: list
    suggestions: list
    weekly_tip: dict
    has_activity: bool


# ==================== Endpoints ====================

@router.get("/preferences")
async def get_email_preferences(
    current_user: User = Depends(get_current_user)
):
    """Get current user's email preferences."""
    prefs = current_user.email_preferences or {
        "weekly_digest": True,
        "content_suggestions": True,
        "product_updates": True,
        "tips_and_tricks": True
    }
    return prefs


@router.put("/preferences")
async def update_email_preferences(
    preferences: EmailPreferences,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update email preferences."""
    current_user.email_preferences = preferences.dict()
    db.commit()
    return {"message": "Preferences updated", "preferences": preferences.dict()}


@router.get("/preview")
async def preview_digest(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Preview what the weekly digest would look like."""
    service = get_digest_service(db)
    digest_data = service.generate_weekly_digest(current_user)
    return digest_data


@router.get("/preview/html")
async def preview_digest_html(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Preview the HTML version of the weekly digest."""
    from fastapi.responses import HTMLResponse
    
    service = get_digest_service(db)
    digest_data = service.generate_weekly_digest(current_user)
    html = service.generate_digest_html(digest_data)
    
    return HTMLResponse(content=html)


@router.post("/send-test")
async def send_test_digest(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a test digest to the current user."""
    service = get_digest_service(db)
    
    try:
        success = await service.send_weekly_digest(current_user)
        if success:
            return {"message": "Test digest sent successfully", "email": current_user.email}
        else:
            return {"message": "Digest was skipped (no activity or disabled)", "email": current_user.email}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send digest: {str(e)}")


@router.post("/unsubscribe/{email_type}")
async def unsubscribe_from_emails(
    email_type: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Unsubscribe from specific email type."""
    valid_types = ["weekly_digest", "content_suggestions", "product_updates", "tips_and_tricks"]
    
    if email_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid email type. Must be one of: {valid_types}")
    
    prefs = current_user.email_preferences or {}
    prefs[email_type] = False
    current_user.email_preferences = prefs
    db.commit()
    
    return {"message": f"Unsubscribed from {email_type}", "preferences": prefs}


@router.get("/suggestions")
async def get_content_suggestions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get content suggestions for the current day."""
    from app.models.models import Brand
    from datetime import datetime
    from app.digest.service import CONTENT_SUGGESTIONS
    
    # Get user's brands
    brands = db.query(Brand).filter(
        Brand.user_id == current_user.id,
        Brand.is_demo == False
    ).all()
    
    # Get suggestions for today
    today = datetime.utcnow().strftime("%A").lower()
    day_key = today if today in CONTENT_SUGGESTIONS else "weekend"
    suggestions = CONTENT_SUGGESTIONS[day_key]
    
    # Pair with brands
    result = []
    for i, suggestion in enumerate(suggestions):
        brand_name = brands[i % len(brands)].name if brands else "your brand"
        result.append({
            "suggestion": suggestion,
            "for_brand": brand_name,
            "brand_id": brands[i % len(brands)].id if brands else None
        })
    
    return {
        "day": today.capitalize(),
        "suggestions": result
    }


# Admin endpoint
@router.post("/send-all")
async def trigger_all_digests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Trigger sending digests to all users (admin only)."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Queue the task
    from app.worker import send_weekly_digests
    task = send_weekly_digests.delay()
    
    return {
        "message": "Digest send task queued",
        "task_id": task.id
    }

"""
Content Calendar API Routes
===========================

Endpoints for content calendar management.
"""

from typing import Optional, List
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.models.user import User
from app.auth.dependencies import get_current_user, get_current_verified_user
from app.calendar.service import ContentCalendarService, get_calendar_service

router = APIRouter(prefix="/calendar", tags=["calendar"])


# ==================== Schemas ====================

class CalendarItemResponse(BaseModel):
    id: int
    type: str  # scheduled or published
    platform: str
    time: str
    datetime: str
    caption_preview: Optional[str] = None
    status: Optional[str] = None
    post_url: Optional[str] = None


class CalendarGap(BaseModel):
    date: str
    day_name: str
    suggested_times: List[str]
    suggestion: str


class CalendarStats(BaseModel):
    total_days: int
    days_with_content: int
    coverage_percent: int
    total_scheduled: int
    total_published: int
    by_platform: dict


class CalendarResponse(BaseModel):
    start_date: str
    end_date: str
    items: dict
    gaps: List[CalendarGap]
    stats: CalendarStats


class ScheduleContentRequest(BaseModel):
    content_id: int
    platform: str
    scheduled_time: datetime
    brand_id: Optional[int] = None
    caption: Optional[str] = None
    hashtags: Optional[List[str]] = None


class RescheduleRequest(BaseModel):
    new_time: datetime


class FillGapRequest(BaseModel):
    gap_date: date
    brand_id: int
    platform: str = "instagram"
    time: Optional[str] = None


class RecurringScheduleRequest(BaseModel):
    brand_id: int
    platform: str
    frequency: str = Field(..., pattern="^(daily|weekly|weekdays)$")
    times: List[str]
    start_date: date
    end_date: Optional[date] = None


# ==================== Endpoints ====================

@router.get("/", response_model=CalendarResponse)
async def get_calendar(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    brand_id: Optional[int] = None,
    platform: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get calendar data for a date range."""
    
    # Default to current week if not specified
    if not start_date:
        today = date.today()
        start_date = today - timedelta(days=today.weekday())  # Monday
    if not end_date:
        end_date = start_date + timedelta(days=30)  # 30 days
    
    service = get_calendar_service(db)
    return service.get_calendar_data(
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        brand_id=brand_id,
        platform=platform
    )


@router.get("/week")
async def get_week_view(
    week_offset: int = Query(default=0, ge=-52, le=52),
    brand_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get calendar data for a specific week."""
    
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())  # Monday
    start_date = start_of_week + timedelta(weeks=week_offset)
    end_date = start_date + timedelta(days=6)  # Sunday
    
    service = get_calendar_service(db)
    data = service.get_calendar_data(
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        brand_id=brand_id
    )
    
    # Add week info
    data["week_number"] = start_date.isocalendar()[1]
    data["week_offset"] = week_offset
    
    return data


@router.get("/month")
async def get_month_view(
    year: Optional[int] = None,
    month: Optional[int] = None,
    brand_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get calendar data for a specific month."""
    
    today = date.today()
    year = year or today.year
    month = month or today.month
    
    start_date = date(year, month, 1)
    
    # Get last day of month
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)
    
    service = get_calendar_service(db)
    data = service.get_calendar_data(
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        brand_id=brand_id
    )
    
    data["year"] = year
    data["month"] = month
    data["month_name"] = start_date.strftime("%B")
    
    return data


@router.get("/gaps")
async def get_content_gaps(
    days_ahead: int = Query(default=14, ge=1, le=90),
    brand_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get upcoming content gaps."""
    
    start_date = date.today()
    end_date = start_date + timedelta(days=days_ahead)
    
    service = get_calendar_service(db)
    data = service.get_calendar_data(
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        brand_id=brand_id
    )
    
    return {
        "gaps": data["gaps"],
        "days_checked": days_ahead,
        "coverage_percent": data["stats"]["coverage_percent"]
    }


@router.get("/suggested-slots")
async def get_suggested_slots(
    days_ahead: int = Query(default=7, ge=1, le=30),
    platform: str = "instagram",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get suggested open slots for scheduling."""
    
    service = get_calendar_service(db)
    slots = service.get_suggested_slots(
        user_id=current_user.id,
        days_ahead=days_ahead,
        platform=platform
    )
    
    return {"slots": slots, "platform": platform}


@router.post("/schedule")
@limiter.limit("30/minute")
async def schedule_content(
    request: ScheduleContentRequest,
    response: Response,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Schedule content for posting."""
    
    service = get_calendar_service(db)
    
    try:
        post = service.schedule_content(
            user_id=current_user.id,
            content_id=request.content_id,
            platform=request.platform,
            scheduled_time=request.scheduled_time,
            brand_id=request.brand_id,
            caption=request.caption,
            hashtags=request.hashtags
        )
        
        return {
            "message": "Content scheduled successfully",
            "post_id": post.id,
            "scheduled_time": post.scheduled_time.isoformat()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/schedule/{post_id}/reschedule")
async def reschedule_post(
    post_id: int,
    request: RescheduleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reschedule an existing post (drag-and-drop support)."""
    
    service = get_calendar_service(db)
    
    try:
        post = service.reschedule_post(
            user_id=current_user.id,
            post_id=post_id,
            new_time=request.new_time
        )
        
        return {
            "message": "Post rescheduled",
            "post_id": post.id,
            "new_time": post.scheduled_time.isoformat()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/schedule/{post_id}")
async def cancel_scheduled_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel a scheduled post."""
    
    service = get_calendar_service(db)
    success = service.cancel_scheduled_post(current_user.id, post_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Post not found or cannot be cancelled")
    
    return {"message": "Post cancelled"}


@router.post("/fill-gap")
@limiter.limit("10/minute")
async def fill_content_gap(
    request: FillGapRequest,
    response: Response,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Generate and schedule content for a gap."""
    
    service = get_calendar_service(db)
    
    try:
        result = service.fill_gap_with_content(
            user_id=current_user.id,
            gap_date=request.gap_date,
            brand_id=request.brand_id,
            platform=request.platform,
            time_str=request.time
        )
        
        return {
            "message": "Gap filled with new content",
            **result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/recurring")
async def create_recurring_schedule(
    request: RecurringScheduleRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Create a recurring posting schedule."""
    
    service = get_calendar_service(db)
    
    result = service.create_recurring_schedule(
        user_id=current_user.id,
        brand_id=request.brand_id,
        platform=request.platform,
        frequency=request.frequency,
        times=request.times,
        start_date=request.start_date,
        end_date=request.end_date
    )
    
    return {
        "message": f"Recurring schedule created with {result['slots_created']} slots",
        **result
    }


@router.get("/best-times/{platform}")
async def get_best_times(
    platform: str,
    current_user: User = Depends(get_current_user)
):
    """Get best posting times for a platform."""
    
    from app.calendar.service import BEST_TIMES_BY_PLATFORM
    
    times = BEST_TIMES_BY_PLATFORM.get(platform)
    if not times:
        raise HTTPException(status_code=404, detail=f"Platform '{platform}' not found")
    
    return {
        "platform": platform,
        "best_times": times
    }

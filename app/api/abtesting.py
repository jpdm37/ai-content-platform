"""
A/B Testing API Routes
======================

Endpoints for creating and managing A/B tests.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.models.user import User
from app.auth.dependencies import get_current_user, get_current_verified_user
from app.abtesting.service import ABTestingService, get_ab_testing_service, AB_TEST_TEMPLATES

router = APIRouter(prefix="/ab-tests", tags=["ab-testing"])


# ==================== Schemas ====================

class VariationInput(BaseModel):
    name: str
    content: Optional[str] = None
    content_data: Optional[dict] = None


class CreateTestRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=255)
    test_type: str = Field(..., pattern="^(caption|hashtags|image|posting_time|cta)$")
    variations: List[VariationInput] = Field(..., min_items=2, max_items=5)
    brand_id: Optional[int] = None
    description: Optional[str] = None
    goal_metric: str = Field(default="engagement_rate", pattern="^(engagement_rate|click_rate|conversion_rate)$")
    min_sample_size: int = Field(default=100, ge=30, le=10000)
    confidence_level: float = Field(default=0.95, ge=0.80, le=0.99)


class CreateFromTemplateRequest(BaseModel):
    template_id: str
    name: str = Field(..., min_length=3, max_length=255)
    brand_id: Optional[int] = None
    base_content: Optional[str] = None


class UpdateVariationRequest(BaseModel):
    content: Optional[str] = None
    content_data: Optional[dict] = None
    traffic_percent: Optional[int] = Field(None, ge=1, le=99)


class RecordMetricRequest(BaseModel):
    variation_id: int
    metric_type: str = Field(..., pattern="^(impression|engagement|click|conversion)$")


class VariationMetrics(BaseModel):
    impressions: int
    engagements: int
    clicks: int
    conversions: int
    engagement_rate: float
    click_rate: float
    conversion_rate: float


class VariationResponse(BaseModel):
    id: int
    name: str
    is_control: bool
    content: Optional[str]
    content_data: Optional[dict]
    metrics: VariationMetrics
    traffic_percent: int
    is_winner: bool


class TestResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    test_type: str
    status: str
    goal_metric: str
    confidence_level: float
    start_date: Optional[str]
    end_date: Optional[str]
    is_significant: bool
    p_value: Optional[float]
    winner_variation_id: Optional[int]
    variations: List[VariationResponse]
    total_impressions: int
    sample_size_reached: bool


# ==================== Endpoints ====================

@router.get("/templates")
async def get_test_templates(
    current_user: User = Depends(get_current_user)
):
    """Get available A/B test templates."""
    return {"templates": AB_TEST_TEMPLATES}


@router.get("/")
async def get_tests(
    status: Optional[str] = None,
    brand_id: Optional[int] = None,
    limit: int = Query(default=20, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's A/B tests."""
    
    service = get_ab_testing_service(db)
    tests = service.get_tests(
        user_id=current_user.id,
        status=status,
        brand_id=brand_id,
        limit=limit
    )
    
    return {
        "tests": [
            {
                "id": t.id,
                "name": t.name,
                "test_type": t.test_type.value,
                "status": t.status.value,
                "variations_count": len(t.variations),
                "created_at": t.created_at.isoformat(),
                "is_significant": t.is_significant,
                "winner_variation_id": t.winner_variation_id
            }
            for t in tests
        ],
        "count": len(tests)
    }


@router.post("/", response_model=dict)
@limiter.limit("10/minute")
async def create_test(
    request: CreateTestRequest,
    response: Response,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Create a new A/B test."""
    
    service = get_ab_testing_service(db)
    
    try:
        test = service.create_test(
            user_id=current_user.id,
            name=request.name,
            test_type=request.test_type,
            variations=[v.dict() for v in request.variations],
            brand_id=request.brand_id,
            description=request.description,
            goal_metric=request.goal_metric,
            min_sample_size=request.min_sample_size,
            confidence_level=request.confidence_level
        )
        
        return {
            "message": "A/B test created",
            "test_id": test.id,
            "status": test.status.value
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/from-template")
@limiter.limit("10/minute")
async def create_from_template(
    request: CreateFromTemplateRequest,
    response: Response,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Create a test from a template."""
    
    service = get_ab_testing_service(db)
    
    try:
        test = service.create_from_template(
            user_id=current_user.id,
            template_id=request.template_id,
            name=request.name,
            brand_id=request.brand_id,
            base_content=request.base_content
        )
        
        return {
            "message": "A/B test created from template",
            "test_id": test.id,
            "status": test.status.value
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{test_id}", response_model=TestResponse)
async def get_test_details(
    test_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed test results."""
    
    service = get_ab_testing_service(db)
    
    try:
        return service.get_test_details(current_user.id, test_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{test_id}/start")
async def start_test(
    test_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start an A/B test."""
    
    service = get_ab_testing_service(db)
    
    try:
        test = service.start_test(current_user.id, test_id)
        return {
            "message": "Test started",
            "test_id": test.id,
            "status": test.status.value,
            "start_date": test.start_date.isoformat()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{test_id}/pause")
async def pause_test(
    test_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Pause a running test."""
    
    service = get_ab_testing_service(db)
    
    try:
        test = service.pause_test(current_user.id, test_id)
        return {"message": "Test paused", "status": test.status.value}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{test_id}/resume")
async def resume_test(
    test_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Resume a paused test."""
    
    service = get_ab_testing_service(db)
    
    try:
        test = service.resume_test(current_user.id, test_id)
        return {"message": "Test resumed", "status": test.status.value}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{test_id}/end")
async def end_test(
    test_id: int,
    winner_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """End a test and declare winner."""
    
    service = get_ab_testing_service(db)
    
    try:
        test = service.end_test(current_user.id, test_id, winner_id)
        return {
            "message": "Test completed",
            "status": test.status.value,
            "winner_variation_id": test.winner_variation_id,
            "is_significant": test.is_significant
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{test_id}")
async def delete_test(
    test_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an A/B test."""
    
    from app.abtesting.service import ABTest
    
    test = db.query(ABTest).filter(
        ABTest.id == test_id,
        ABTest.user_id == current_user.id
    ).first()
    
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    
    db.delete(test)
    db.commit()
    
    return {"message": "Test deleted"}


@router.post("/{test_id}/record")
async def record_metric(
    test_id: int,
    request: RecordMetricRequest,
    db: Session = Depends(get_db)
):
    """Record a metric for a variation (called by tracking pixel/webhook)."""
    
    service = get_ab_testing_service(db)
    
    if request.metric_type == "impression":
        service.record_impression(test_id, request.variation_id)
    elif request.metric_type == "engagement":
        service.record_engagement(test_id, request.variation_id)
    elif request.metric_type == "click":
        service.record_click(test_id, request.variation_id)
    elif request.metric_type == "conversion":
        service.record_conversion(test_id, request.variation_id)
    
    return {"message": f"{request.metric_type} recorded"}


@router.get("/{test_id}/variation")
async def get_variation_for_user(
    test_id: int,
    user_identifier: str = Query(..., description="Unique user identifier for consistent assignment"),
    db: Session = Depends(get_db)
):
    """Get which variation to show a user (for content serving)."""
    
    service = get_ab_testing_service(db)
    variation = service.get_variation_for_user(test_id, user_identifier)
    
    if not variation:
        raise HTTPException(status_code=404, detail="Test not found or not running")
    
    return {
        "variation_id": variation.id,
        "variation_name": variation.name,
        "content": variation.content,
        "content_data": variation.content_data
    }

"""
Brand Voice AI API Routes

Train AI to match your brand's writing style.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.models import Brand
from app.auth.dependencies import get_current_user, get_current_verified_user

from app.brandvoice.schemas import (
    AddExampleRequest, AddExamplesBulkRequest, ExampleResponse,
    VoiceResponse, VoiceStatsResponse, TrainVoiceResponse,
    GenerateWithVoiceRequest, GenerateVariationsRequest,
    GenerationResponse, VariationsResponse,
    RecordFeedbackRequest, FeedbackResponse,
    AnalyzeTextRequest, TextAnalysisResponse
)
from app.brandvoice.service import BrandVoiceService

router = APIRouter(prefix="/voice", tags=["brand-voice"])


def verify_brand_ownership(brand_id: int, user_id: int, db: Session) -> Brand:
    brand = db.query(Brand).filter(Brand.id == brand_id, Brand.user_id == user_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    return brand


# ==================== Voice Profile ====================

@router.get("/brands/{brand_id}", response_model=VoiceResponse)
async def get_brand_voice(brand_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get brand voice profile."""
    verify_brand_ownership(brand_id, current_user.id, db)
    service = BrandVoiceService(db)
    voice = service.get_or_create_voice(brand_id)
    return VoiceResponse.model_validate(voice)


@router.get("/brands/{brand_id}/stats", response_model=VoiceStatsResponse)
async def get_voice_stats(brand_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get detailed voice statistics."""
    verify_brand_ownership(brand_id, current_user.id, db)
    service = BrandVoiceService(db)
    return VoiceStatsResponse(**service.get_voice_stats(brand_id))


# ==================== Training Examples ====================

@router.get("/brands/{brand_id}/examples", response_model=List[ExampleResponse])
async def list_examples(brand_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List all training examples."""
    verify_brand_ownership(brand_id, current_user.id, db)
    service = BrandVoiceService(db)
    return [ExampleResponse.model_validate(ex) for ex in service.get_examples(brand_id)]


@router.post("/brands/{brand_id}/examples", response_model=ExampleResponse)
async def add_example(brand_id: int, request: AddExampleRequest, current_user: User = Depends(get_current_verified_user), db: Session = Depends(get_db)):
    """Add a training example."""
    verify_brand_ownership(brand_id, current_user.id, db)
    service = BrandVoiceService(db)
    example = service.add_example(brand_id, request.content, request.content_type, request.platform)
    return ExampleResponse.model_validate(example)


@router.post("/brands/{brand_id}/examples/bulk", response_model=List[ExampleResponse])
async def add_examples_bulk(brand_id: int, request: AddExamplesBulkRequest, current_user: User = Depends(get_current_verified_user), db: Session = Depends(get_db)):
    """Add multiple training examples at once."""
    verify_brand_ownership(brand_id, current_user.id, db)
    service = BrandVoiceService(db)
    examples = service.add_examples_bulk(brand_id, [ex.model_dump() for ex in request.examples])
    return [ExampleResponse.model_validate(ex) for ex in examples]


@router.delete("/brands/{brand_id}/examples/{example_id}")
async def remove_example(brand_id: int, example_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Remove a training example."""
    verify_brand_ownership(brand_id, current_user.id, db)
    service = BrandVoiceService(db)
    if not service.remove_example(example_id, brand_id):
        raise HTTPException(status_code=404, detail="Example not found")
    return {"success": True}


# ==================== Training ====================

@router.post("/brands/{brand_id}/train", response_model=TrainVoiceResponse)
async def train_voice(brand_id: int, current_user: User = Depends(get_current_verified_user), db: Session = Depends(get_db)):
    """Train the brand voice from examples. Requires at least 5 examples."""
    verify_brand_ownership(brand_id, current_user.id, db)
    service = BrandVoiceService(db)
    
    try:
        voice = await service.train_voice(brand_id)
        return TrainVoiceResponse(success=True, message="Voice trained successfully", characteristics=voice.characteristics)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")


# ==================== Content Generation ====================

@router.post("/brands/{brand_id}/generate", response_model=GenerationResponse)
async def generate_with_voice(brand_id: int, request: GenerateWithVoiceRequest, current_user: User = Depends(get_current_verified_user), db: Session = Depends(get_db)):
    """Generate content using the trained brand voice."""
    verify_brand_ownership(brand_id, current_user.id, db)
    service = BrandVoiceService(db)
    
    try:
        result = await service.generate_content(
            brand_id=brand_id,
            prompt=request.prompt,
            content_type=request.content_type,
            platform=request.platform,
            voice_strength=request.voice_strength,
            max_length=request.max_length
        )
        return GenerationResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/brands/{brand_id}/generate/variations", response_model=VariationsResponse)
async def generate_variations(brand_id: int, request: GenerateVariationsRequest, current_user: User = Depends(get_current_verified_user), db: Session = Depends(get_db)):
    """Generate multiple content variations using brand voice."""
    verify_brand_ownership(brand_id, current_user.id, db)
    service = BrandVoiceService(db)
    
    try:
        variations = await service.generate_variations(
            brand_id=brand_id,
            prompt=request.prompt,
            num_variations=request.num_variations,
            platform=request.platform
        )
        return VariationsResponse(variations=[GenerationResponse(**v) for v in variations], count=len(variations))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== Feedback ====================

@router.post("/feedback", response_model=FeedbackResponse)
async def record_feedback(request: RecordFeedbackRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Record feedback on generated content to improve voice."""
    service = BrandVoiceService(db)
    
    try:
        service.record_feedback(
            generation_id=request.generation_id,
            user_id=current_user.id,
            rating=request.rating,
            voice_match_score=request.voice_match_score,
            notes=request.notes
        )
        return FeedbackResponse(success=True, generation_id=request.generation_id, rating=request.rating, voice_match_score=request.voice_match_score)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==================== Analysis ====================

@router.post("/analyze", response_model=TextAnalysisResponse)
async def analyze_text(request: AnalyzeTextRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Analyze text without adding as example."""
    service = BrandVoiceService(db)
    analysis = service._analyze_single_example(request.content)
    return TextAnalysisResponse(**analysis)

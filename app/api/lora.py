"""
LoRA Training API Routes

Comprehensive API for LoRA model training and avatar generation.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.config import get_settings
from app.models.user import User
from app.auth.dependencies import get_current_user, get_current_verified_user

from app.lora.models import (
    LoraModel, LoraReferenceImage, LoraGeneratedSample,
    LoraTrainingQueue, LoraUsageLog,
    TrainingStatus, ImageValidationStatus
)
from app.lora.schemas import (
    LoraModelCreate, LoraModelUpdate, LoraModelResponse, LoraModelDetailResponse,
    LoraTrainingConfig, StartTrainingRequest, TrainingProgressResponse,
    ReferenceImageCreate, ReferenceImageResponse, ReferenceImageUploadResponse,
    GenerateWithLoraRequest, GenerateWithLoraResponse, GeneratedSampleResponse,
    BatchGenerateRequest, ScenarioGenerateRequest,
    ConsistencyCheckRequest, ConsistencyCheckResponse,
    RateSampleRequest, LoraUsageStats, UserLoraStats,
    TrainingStatusEnum
)
from app.lora.training_service import LoraTrainingService

settings = get_settings()
router = APIRouter(prefix="/lora", tags=["lora-training"])


def get_user_replicate_token(user: User) -> str:
    """Get user's Replicate token or fall back to system token."""
    return user.replicate_api_token or settings.replicate_api_token


# ==================== LoRA Model Management ====================

@router.post("/models", response_model=LoraModelResponse, status_code=status.HTTP_201_CREATED)
async def create_lora_model(
    data: LoraModelCreate,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Create a new LoRA model for training."""
    from app.models import Brand
    
    # Verify brand ownership
    brand = db.query(Brand).filter(
        Brand.id == data.brand_id,
        Brand.user_id == current_user.id
    ).first()
    
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    # Check existing models for this brand
    existing_count = db.query(LoraModel).filter(
        LoraModel.brand_id == data.brand_id,
        LoraModel.user_id == current_user.id
    ).count()
    
    # Create model
    config = data.config or LoraTrainingConfig()
    
    lora_model = LoraModel(
        user_id=current_user.id,
        brand_id=data.brand_id,
        name=data.name,
        trigger_word=data.trigger_word.upper().replace(" ", "_"),
        version=existing_count + 1,
        base_model=config.base_model.value,
        training_steps=config.training_steps,
        learning_rate=config.learning_rate,
        lora_rank=config.lora_rank,
        resolution=config.resolution,
        status=TrainingStatus.PENDING
    )
    
    db.add(lora_model)
    db.commit()
    db.refresh(lora_model)
    
    return _model_to_response(lora_model, db)


@router.get("/models", response_model=List[LoraModelResponse])
async def list_lora_models(
    brand_id: Optional[int] = None,
    status_filter: Optional[TrainingStatusEnum] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List user's LoRA models."""
    query = db.query(LoraModel).filter(LoraModel.user_id == current_user.id)
    
    if brand_id:
        query = query.filter(LoraModel.brand_id == brand_id)
    if status_filter:
        query = query.filter(LoraModel.status == TrainingStatus[status_filter.value.upper()])
    
    query = query.order_by(LoraModel.created_at.desc())
    models = query.offset(skip).limit(limit).all()
    
    return [_model_to_response(m, db) for m in models]


@router.get("/models/{model_id}", response_model=LoraModelDetailResponse)
async def get_lora_model(
    model_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed LoRA model information."""
    lora_model = db.query(LoraModel).filter(
        LoraModel.id == model_id,
        LoraModel.user_id == current_user.id
    ).first()
    
    if not lora_model:
        raise HTTPException(status_code=404, detail="LoRA model not found")
    
    return _model_to_detail_response(lora_model, db)


@router.put("/models/{model_id}", response_model=LoraModelResponse)
async def update_lora_model(
    model_id: int,
    data: LoraModelUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update LoRA model settings."""
    lora_model = db.query(LoraModel).filter(
        LoraModel.id == model_id,
        LoraModel.user_id == current_user.id
    ).first()
    
    if not lora_model:
        raise HTTPException(status_code=404, detail="LoRA model not found")
    
    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    
    # If setting as active, deactivate others for this brand
    if update_data.get("is_active"):
        db.query(LoraModel).filter(
            LoraModel.brand_id == lora_model.brand_id,
            LoraModel.id != model_id
        ).update({"is_active": False})
    
    for field, value in update_data.items():
        setattr(lora_model, field, value)
    
    db.commit()
    db.refresh(lora_model)
    
    return _model_to_response(lora_model, db)


@router.delete("/models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lora_model(
    model_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a LoRA model and all associated data."""
    lora_model = db.query(LoraModel).filter(
        LoraModel.id == model_id,
        LoraModel.user_id == current_user.id
    ).first()
    
    if not lora_model:
        raise HTTPException(status_code=404, detail="LoRA model not found")
    
    # Cancel training if in progress
    if lora_model.status == TrainingStatus.TRAINING:
        service = LoraTrainingService(db, get_user_replicate_token(current_user))
        await service.cancel_training(lora_model)
    
    db.delete(lora_model)
    db.commit()


# ==================== Reference Images ====================

@router.post("/models/{model_id}/images", response_model=ReferenceImageUploadResponse)
async def add_reference_image(
    model_id: int,
    data: ReferenceImageCreate,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Add a reference image by URL."""
    lora_model = db.query(LoraModel).filter(
        LoraModel.id == model_id,
        LoraModel.user_id == current_user.id
    ).first()
    
    if not lora_model:
        raise HTTPException(status_code=404, detail="LoRA model not found")
    
    if lora_model.status not in [TrainingStatus.PENDING, TrainingStatus.VALIDATING]:
        raise HTTPException(
            status_code=400, 
            detail="Cannot add images to model that is already training or completed"
        )
    
    service = LoraTrainingService(db, get_user_replicate_token(current_user))
    ref_image = await service.add_reference_image(
        lora_model,
        data.image_url,
        data.custom_caption,
        data.image_type.value if data.image_type else None
    )
    
    return ReferenceImageUploadResponse(
        id=ref_image.id,
        original_url=ref_image.original_url,
        processed_url=ref_image.processed_url,
        face_detected=ref_image.face_detected,
        face_confidence=ref_image.face_confidence,
        quality_score=ref_image.quality_score,
        validation_status=ref_image.validation_status.value,
        validation_errors=ref_image.validation_errors,
        auto_caption=ref_image.caption
    )


@router.post("/models/{model_id}/images/bulk")
async def bulk_add_images(
    model_id: int,
    image_urls: List[str],
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Add multiple reference images at once."""
    lora_model = db.query(LoraModel).filter(
        LoraModel.id == model_id,
        LoraModel.user_id == current_user.id
    ).first()
    
    if not lora_model:
        raise HTTPException(status_code=404, detail="LoRA model not found")
    
    if len(image_urls) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 images per request")
    
    service = LoraTrainingService(db, get_user_replicate_token(current_user))
    results = await service.bulk_add_images(lora_model, image_urls)
    
    return {
        "added": len(results),
        "valid": sum(1 for r in results if r.validation_status == ImageValidationStatus.VALID),
        "invalid": sum(1 for r in results if r.validation_status == ImageValidationStatus.INVALID),
        "images": [
            {
                "id": r.id,
                "url": r.original_url,
                "status": r.validation_status.value,
                "quality_score": r.quality_score,
                "face_detected": r.face_detected
            } for r in results
        ]
    }


@router.get("/models/{model_id}/images", response_model=List[ReferenceImageResponse])
async def list_reference_images(
    model_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List reference images for a model."""
    lora_model = db.query(LoraModel).filter(
        LoraModel.id == model_id,
        LoraModel.user_id == current_user.id
    ).first()
    
    if not lora_model:
        raise HTTPException(status_code=404, detail="LoRA model not found")
    
    images = db.query(LoraReferenceImage).filter(
        LoraReferenceImage.lora_model_id == model_id
    ).order_by(LoraReferenceImage.created_at).all()
    
    return images


@router.delete("/models/{model_id}/images/{image_id}")
async def delete_reference_image(
    model_id: int,
    image_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a reference image."""
    image = db.query(LoraReferenceImage).join(LoraModel).filter(
        LoraReferenceImage.id == image_id,
        LoraReferenceImage.lora_model_id == model_id,
        LoraModel.user_id == current_user.id
    ).first()
    
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    db.delete(image)
    db.commit()
    
    return {"message": "Image deleted"}


@router.put("/models/{model_id}/images/{image_id}")
async def update_reference_image(
    model_id: int,
    image_id: int,
    caption: Optional[str] = None,
    image_type: Optional[str] = None,
    is_included: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update reference image settings."""
    image = db.query(LoraReferenceImage).join(LoraModel).filter(
        LoraReferenceImage.id == image_id,
        LoraReferenceImage.lora_model_id == model_id,
        LoraModel.user_id == current_user.id
    ).first()
    
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    if caption is not None:
        image.custom_caption = caption
    if image_type is not None:
        image.image_type = image_type
    if is_included is not None:
        image.is_included_in_training = is_included
    
    db.commit()
    return {"message": "Image updated"}


# ==================== Training ====================

@router.post("/models/{model_id}/validate")
async def validate_for_training(
    model_id: int,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Validate model is ready for training."""
    lora_model = db.query(LoraModel).filter(
        LoraModel.id == model_id,
        LoraModel.user_id == current_user.id
    ).first()
    
    if not lora_model:
        raise HTTPException(status_code=404, detail="LoRA model not found")
    
    service = LoraTrainingService(db, get_user_replicate_token(current_user))
    result = await service.validate_training_readiness(lora_model)
    
    return result


@router.post("/models/{model_id}/train")
async def start_training(
    model_id: int,
    request: StartTrainingRequest = None,
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Start LoRA training."""
    lora_model = db.query(LoraModel).filter(
        LoraModel.id == model_id,
        LoraModel.user_id == current_user.id
    ).first()
    
    if not lora_model:
        raise HTTPException(status_code=404, detail="LoRA model not found")
    
    if lora_model.status not in [TrainingStatus.PENDING, TrainingStatus.FAILED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start training. Current status: {lora_model.status.value}"
        )
    
    # Check replicate token
    token = get_user_replicate_token(current_user)
    if not token:
        raise HTTPException(
            status_code=400,
            detail="No Replicate API token configured. Please add your token in settings."
        )
    
    service = LoraTrainingService(db, token)
    
    # Validate first
    validation = await service.validate_training_readiness(lora_model)
    if not validation["is_ready"]:
        raise HTTPException(
            status_code=400,
            detail={"message": "Not ready for training", "issues": validation["issues"]}
        )
    
    # Start training
    config = request.config.model_dump() if request and request.config else None
    result = await service.start_training(lora_model, config)
    
    return result


@router.get("/models/{model_id}/progress", response_model=TrainingProgressResponse)
async def get_training_progress(
    model_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get training progress."""
    lora_model = db.query(LoraModel).filter(
        LoraModel.id == model_id,
        LoraModel.user_id == current_user.id
    ).first()
    
    if not lora_model:
        raise HTTPException(status_code=404, detail="LoRA model not found")
    
    service = LoraTrainingService(db, get_user_replicate_token(current_user))
    progress = await service.check_training_progress(lora_model)
    
    return TrainingProgressResponse(
        lora_model_id=model_id,
        status=TrainingStatusEnum(lora_model.status.value),
        progress_percent=progress.get("progress_percent", 0),
        current_step=progress.get("current_step"),
        total_steps=progress.get("total_steps"),
        eta_seconds=progress.get("eta_seconds"),
        error_message=progress.get("error_message"),
        logs=progress.get("logs")
    )


@router.post("/models/{model_id}/cancel")
async def cancel_training(
    model_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel ongoing training."""
    lora_model = db.query(LoraModel).filter(
        LoraModel.id == model_id,
        LoraModel.user_id == current_user.id
    ).first()
    
    if not lora_model:
        raise HTTPException(status_code=404, detail="LoRA model not found")
    
    if lora_model.status != TrainingStatus.TRAINING:
        raise HTTPException(status_code=400, detail="No active training to cancel")
    
    service = LoraTrainingService(db, get_user_replicate_token(current_user))
    success = await service.cancel_training(lora_model)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to cancel training")
    
    return {"message": "Training cancelled"}


# ==================== Generation ====================

@router.post("/generate", response_model=GenerateWithLoraResponse)
async def generate_with_lora(
    request: GenerateWithLoraRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Generate images using a trained LoRA model."""
    import time
    start_time = time.time()
    
    lora_model = db.query(LoraModel).filter(
        LoraModel.id == request.lora_model_id,
        LoraModel.user_id == current_user.id
    ).first()
    
    if not lora_model:
        raise HTTPException(status_code=404, detail="LoRA model not found")
    
    if lora_model.status != TrainingStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"LoRA model not ready. Status: {lora_model.status.value}"
        )
    
    token = get_user_replicate_token(current_user)
    if not token:
        raise HTTPException(status_code=400, detail="No Replicate API token configured")
    
    service = LoraTrainingService(db, token)
    
    samples = await service.generate_with_lora(
        lora_model,
        prompt=request.prompt,
        negative_prompt=request.negative_prompt,
        lora_scale=request.lora_scale,
        guidance_scale=request.guidance_scale,
        num_inference_steps=request.num_inference_steps,
        seed=request.seed,
        aspect_ratio=request.aspect_ratio,
        num_outputs=request.num_outputs
    )
    
    generation_time = time.time() - start_time
    cost = 0.003 * len(samples)
    
    return GenerateWithLoraResponse(
        samples=[GeneratedSampleResponse.model_validate(s) for s in samples],
        generation_time_seconds=round(generation_time, 2),
        cost_usd=round(cost, 4)
    )


@router.post("/generate/batch")
async def generate_batch(
    request: BatchGenerateRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Generate multiple images with different prompts."""
    lora_model = db.query(LoraModel).filter(
        LoraModel.id == request.lora_model_id,
        LoraModel.user_id == current_user.id,
        LoraModel.status == TrainingStatus.COMPLETED
    ).first()
    
    if not lora_model:
        raise HTTPException(status_code=404, detail="LoRA model not found or not ready")
    
    service = LoraTrainingService(db, get_user_replicate_token(current_user))
    
    samples = await service.generate_batch(
        lora_model,
        prompts=request.prompts,
        lora_scale=request.lora_scale,
        guidance_scale=request.guidance_scale,
        aspect_ratio=request.aspect_ratio
    )
    
    return {
        "samples": [GeneratedSampleResponse.model_validate(s) for s in samples],
        "total": len(samples),
        "cost_usd": round(0.003 * len(samples), 4)
    }


@router.post("/generate/scenario")
async def generate_scenario(
    request: ScenarioGenerateRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Generate avatar in predefined scenarios."""
    lora_model = db.query(LoraModel).filter(
        LoraModel.id == request.lora_model_id,
        LoraModel.user_id == current_user.id,
        LoraModel.status == TrainingStatus.COMPLETED
    ).first()
    
    if not lora_model:
        raise HTTPException(status_code=404, detail="LoRA model not found or not ready")
    
    service = LoraTrainingService(db, get_user_replicate_token(current_user))
    
    samples = await service.generate_scenario(
        lora_model,
        scenario=request.scenario,
        custom_details=request.custom_details,
        num_variations=request.num_variations
    )
    
    return {
        "scenario": request.scenario,
        "samples": [GeneratedSampleResponse.model_validate(s) for s in samples],
        "total": len(samples)
    }


@router.post("/models/{model_id}/test-samples")
async def generate_test_samples(
    model_id: int,
    num_samples: int = 4,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Generate test samples to evaluate model quality."""
    lora_model = db.query(LoraModel).filter(
        LoraModel.id == model_id,
        LoraModel.user_id == current_user.id,
        LoraModel.status == TrainingStatus.COMPLETED
    ).first()
    
    if not lora_model:
        raise HTTPException(status_code=404, detail="LoRA model not found or not ready")
    
    service = LoraTrainingService(db, get_user_replicate_token(current_user))
    samples = await service.generate_test_samples(lora_model, num_samples)
    
    # Calculate consistency
    consistency = await service.calculate_consistency_score(lora_model)
    
    return {
        "samples": [GeneratedSampleResponse.model_validate(s) for s in samples],
        "consistency_score": consistency,
        "test_count": len(samples)
    }


# ==================== Samples & Rating ====================

@router.get("/models/{model_id}/samples", response_model=List[GeneratedSampleResponse])
async def list_generated_samples(
    model_id: int,
    test_only: bool = False,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List generated samples for a model."""
    lora_model = db.query(LoraModel).filter(
        LoraModel.id == model_id,
        LoraModel.user_id == current_user.id
    ).first()
    
    if not lora_model:
        raise HTTPException(status_code=404, detail="LoRA model not found")
    
    query = db.query(LoraGeneratedSample).filter(
        LoraGeneratedSample.lora_model_id == model_id
    )
    
    if test_only:
        query = query.filter(LoraGeneratedSample.is_test_sample == True)
    
    query = query.order_by(LoraGeneratedSample.created_at.desc())
    samples = query.offset(skip).limit(limit).all()
    
    return samples


@router.post("/samples/{sample_id}/rate")
async def rate_sample(
    sample_id: int,
    request: RateSampleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Rate a generated sample."""
    sample = db.query(LoraGeneratedSample).join(LoraModel).filter(
        LoraGeneratedSample.id == sample_id,
        LoraModel.user_id == current_user.id
    ).first()
    
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")
    
    sample.user_rating = request.rating
    sample.user_feedback = request.feedback
    db.commit()
    
    return {"message": "Rating saved"}


@router.delete("/samples/{sample_id}")
async def delete_sample(
    sample_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a generated sample."""
    sample = db.query(LoraGeneratedSample).join(LoraModel).filter(
        LoraGeneratedSample.id == sample_id,
        LoraModel.user_id == current_user.id
    ).first()
    
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")
    
    db.delete(sample)
    db.commit()
    
    return {"message": "Sample deleted"}


# ==================== Statistics ====================

@router.get("/models/{model_id}/stats", response_model=LoraUsageStats)
async def get_model_stats(
    model_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get usage statistics for a LoRA model."""
    lora_model = db.query(LoraModel).filter(
        LoraModel.id == model_id,
        LoraModel.user_id == current_user.id
    ).first()
    
    if not lora_model:
        raise HTTPException(status_code=404, detail="LoRA model not found")
    
    # Get stats
    total_gens = db.query(LoraGeneratedSample).filter(
        LoraGeneratedSample.lora_model_id == model_id
    ).count()
    
    total_cost = db.query(func.sum(LoraUsageLog.cost_usd)).filter(
        LoraUsageLog.lora_model_id == model_id
    ).scalar() or 0
    
    avg_consistency = db.query(func.avg(LoraGeneratedSample.consistency_score)).filter(
        LoraGeneratedSample.lora_model_id == model_id,
        LoraGeneratedSample.consistency_score != None
    ).scalar() or 0
    
    avg_rating = db.query(func.avg(LoraGeneratedSample.user_rating)).filter(
        LoraGeneratedSample.lora_model_id == model_id,
        LoraGeneratedSample.user_rating != None
    ).scalar()
    
    # This month's generations
    from datetime import datetime, timedelta
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_gens = db.query(LoraGeneratedSample).filter(
        LoraGeneratedSample.lora_model_id == model_id,
        LoraGeneratedSample.created_at >= month_start
    ).count()
    
    return LoraUsageStats(
        total_generations=total_gens,
        total_cost_usd=round(total_cost, 2),
        average_consistency_score=round(avg_consistency, 1),
        average_user_rating=round(avg_rating, 1) if avg_rating else None,
        generations_this_month=month_gens,
        most_used_prompts=[]  # Would need more complex query
    )


@router.get("/stats", response_model=UserLoraStats)
async def get_user_lora_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's overall LoRA statistics."""
    total_models = db.query(LoraModel).filter(
        LoraModel.user_id == current_user.id
    ).count()
    
    active_models = db.query(LoraModel).filter(
        LoraModel.user_id == current_user.id,
        LoraModel.is_active == True
    ).count()
    
    training_cost = db.query(func.sum(LoraModel.training_cost_usd)).filter(
        LoraModel.user_id == current_user.id
    ).scalar() or 0
    
    gen_cost = db.query(func.sum(LoraUsageLog.cost_usd)).filter(
        LoraUsageLog.user_id == current_user.id,
        LoraUsageLog.usage_type == "generation"
    ).scalar() or 0
    
    total_gens = db.query(LoraGeneratedSample).join(LoraModel).filter(
        LoraModel.user_id == current_user.id
    ).count()
    
    avg_consistency = db.query(func.avg(LoraModel.consistency_score)).filter(
        LoraModel.user_id == current_user.id,
        LoraModel.consistency_score != None
    ).scalar() or 0
    
    return UserLoraStats(
        total_models=total_models,
        active_models=active_models,
        total_training_cost=round(training_cost, 2),
        total_generation_cost=round(gen_cost, 2),
        total_generations=total_gens,
        average_consistency=round(avg_consistency, 1)
    )


# ==================== Helper Functions ====================

def _model_to_response(lora_model: LoraModel, db: Session) -> LoraModelResponse:
    """Convert model to response with image count."""
    image_count = db.query(LoraReferenceImage).filter(
        LoraReferenceImage.lora_model_id == lora_model.id
    ).count()
    
    return LoraModelResponse(
        id=lora_model.id,
        brand_id=lora_model.brand_id,
        name=lora_model.name,
        trigger_word=lora_model.trigger_word,
        version=lora_model.version,
        base_model=lora_model.base_model,
        status=TrainingStatusEnum(lora_model.status.value),
        progress_percent=lora_model.progress_percent,
        consistency_score=lora_model.consistency_score,
        test_images_generated=lora_model.test_images_generated,
        training_cost_usd=lora_model.training_cost_usd,
        training_duration_seconds=lora_model.training_duration_seconds,
        is_active=lora_model.is_active,
        is_public=lora_model.is_public,
        training_steps=lora_model.training_steps,
        learning_rate=lora_model.learning_rate,
        lora_rank=lora_model.lora_rank,
        resolution=lora_model.resolution,
        replicate_model_name=lora_model.replicate_model_name,
        lora_weights_url=lora_model.lora_weights_url,
        created_at=lora_model.created_at,
        training_started_at=lora_model.training_started_at,
        training_completed_at=lora_model.training_completed_at,
        reference_image_count=image_count
    )


def _model_to_detail_response(lora_model: LoraModel, db: Session) -> LoraModelDetailResponse:
    """Convert model to detailed response."""
    base = _model_to_response(lora_model, db)
    
    images = db.query(LoraReferenceImage).filter(
        LoraReferenceImage.lora_model_id == lora_model.id
    ).all()
    
    samples = db.query(LoraGeneratedSample).filter(
        LoraGeneratedSample.lora_model_id == lora_model.id
    ).order_by(LoraGeneratedSample.created_at.desc()).limit(10).all()
    
    return LoraModelDetailResponse(
        **base.model_dump(),
        reference_images=[ReferenceImageResponse.model_validate(img) for img in images],
        recent_samples=[GeneratedSampleResponse.model_validate(s) for s in samples],
        error_message=lora_model.error_message
    )

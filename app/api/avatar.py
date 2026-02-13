"""
Avatar Generation API Routes

Supports two avatar creation paths:
1. Upload existing images → LoRA training
2. Generate from description → Create consistent images → LoRA training

This enables brands WITHOUT existing spokesperson photos to create AI avatars.
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime
import logging
import uuid
import os

from app.core.database import get_db
from app.core.config import get_settings
from app.auth.dependencies import get_current_user, get_current_verified_user
from app.models.user import User
from app.models import Brand
from app.billing.service import BillingService

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/avatar", tags=["avatar"])


# ==================== Pydantic Schemas ====================

class AvatarDescriptionConfig(BaseModel):
    """Configuration for generating avatar from description"""
    brand_id: int
    avatar_name: str = Field(..., min_length=1, max_length=100)
    
    # Avatar appearance
    gender: str = Field(..., description="male, female, non-binary")
    age_range: str = Field(..., description="20s, 30s, 40s, 50s, etc.")
    ethnicity: Optional[str] = None
    
    # Style & look
    style: str = Field(default="professional", description="professional, casual, creative, corporate, friendly")
    hair_description: Optional[str] = None
    clothing_style: Optional[str] = None
    
    # Custom details
    custom_description: Optional[str] = Field(None, max_length=500, description="Additional appearance details")
    
    # Generation settings
    num_concepts: int = Field(default=4, ge=2, le=8, description="Number of concept images to generate")


class AvatarConceptResponse(BaseModel):
    """Single avatar concept image"""
    index: int
    image_url: str
    seed: int
    prompt_used: str


class GenerateConceptsResponse(BaseModel):
    """Response for concept generation"""
    status: str
    concepts: List[AvatarConceptResponse]
    config_used: Dict[str, Any]
    generation_id: str


class ConfirmAvatarRequest(BaseModel):
    """Request to confirm selected avatar and start training"""
    brand_id: int
    selected_concept_index: int
    generation_id: str
    avatar_name: str


class GenerateTrainingImagesRequest(BaseModel):
    """Request to generate training images from selected concept"""
    brand_id: int
    generation_id: str
    selected_concept_index: int
    hero_image_url: str
    num_variations: int = Field(default=15, ge=10, le=25)


class TrainingImagesResponse(BaseModel):
    """Response with generated training images"""
    status: str
    images: List[Dict[str, Any]]
    total_count: int
    ready_for_training: bool


class CreateFromGeneratedRequest(BaseModel):
    """Request to create LoRA model from generated images"""
    brand_id: int
    avatar_name: str
    hero_image_url: str
    training_image_urls: List[str]
    trigger_word: Optional[str] = None


class AvatarStatusResponse(BaseModel):
    """Avatar creation status"""
    avatar_id: Optional[int]
    status: str
    progress_percent: int = 0
    hero_image_url: Optional[str]
    error_message: Optional[str]


# ==================== Utility Functions ====================

def get_user_api_keys(user: User) -> tuple[str, str]:
    """Get API keys - user's or system fallback"""
    openai_key = getattr(user, 'openai_api_key', None) or settings.openai_api_key
    replicate_key = getattr(user, 'replicate_api_token', None) or settings.replicate_api_token
    return openai_key, replicate_key


def build_avatar_prompt(config: AvatarDescriptionConfig, variation_type: str = "hero") -> str:
    """Build detailed prompt for avatar generation"""
    
    # Base prompt components
    gender_map = {
        "male": "man",
        "female": "woman", 
        "non-binary": "person"
    }
    subject = gender_map.get(config.gender.lower(), "person")
    
    style_prompts = {
        "professional": "professional, polished, confident, business-appropriate",
        "casual": "relaxed, approachable, friendly, natural",
        "creative": "artistic, unique, expressive, modern",
        "corporate": "executive, sophisticated, authoritative, refined",
        "friendly": "warm, welcoming, genuine smile, trustworthy"
    }
    style_desc = style_prompts.get(config.style, style_prompts["professional"])
    
    # Build base prompt
    prompt_parts = [
        f"portrait of a {subject}",
        f"in their {config.age_range}",
        style_desc,
    ]
    
    if config.ethnicity:
        prompt_parts.append(config.ethnicity)
    
    if config.hair_description:
        prompt_parts.append(config.hair_description)
    
    if config.clothing_style:
        prompt_parts.append(f"wearing {config.clothing_style}")
    
    if config.custom_description:
        prompt_parts.append(config.custom_description)
    
    # Add variation-specific details
    variation_additions = {
        "hero": "front-facing, studio lighting, neutral background, high quality portrait",
        "headshot": "professional headshot, clean background, soft lighting",
        "casual": "casual setting, natural lighting, relaxed pose",
        "outdoor": "outdoor portrait, natural background, golden hour lighting",
        "profile": "profile view, artistic lighting, elegant pose",
        "three_quarter": "three-quarter view, professional lighting, confident expression",
        "smile": "genuine warm smile, friendly expression, approachable",
        "serious": "serious confident expression, professional demeanor",
    }
    
    prompt_parts.append(variation_additions.get(variation_type, variation_additions["hero"]))
    
    # Quality tags
    prompt_parts.extend([
        "8k resolution",
        "photorealistic",
        "detailed skin texture",
        "perfect lighting",
        "sharp focus"
    ])
    
    return ", ".join(prompt_parts)


# ==================== API Endpoints ====================

@router.post("/generate-concepts", response_model=GenerateConceptsResponse)
async def generate_avatar_concepts(
    config: AvatarDescriptionConfig,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Step 1: Generate initial avatar concept images from description.
    User will select their preferred concept for training.
    """
    # Verify brand ownership
    brand = db.query(Brand).filter(
        Brand.id == config.brand_id,
        Brand.user_id == current_user.id
    ).first()
    
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    # Check usage limits
    billing = BillingService(db)
    limit_check = billing.check_generation_limit(current_user.id)
    if not limit_check.get("allowed", False):
        raise HTTPException(
            status_code=403,
            detail=f"Generation limit reached. {limit_check.get('message', 'Upgrade to continue.')}"
        )
    
    # Get API keys
    openai_key, replicate_key = get_user_api_keys(current_user)
    
    if not replicate_key:
        raise HTTPException(
            status_code=400,
            detail="No Replicate API key configured. Please add your key in settings."
        )
    
    try:
        import replicate
        os.environ["REPLICATE_API_TOKEN"] = replicate_key
        
        # Generate unique ID for this generation session
        generation_id = f"gen_{uuid.uuid4().hex[:12]}"
        
        concepts = []
        base_prompt = build_avatar_prompt(config, "hero")
        
        # Generate multiple concepts with different seeds
        for i in range(config.num_concepts):
            seed = 1000 + i * 1234  # Deterministic but varied seeds
            
            try:
                output = replicate.run(
                    "black-forest-labs/flux-schnell",
                    input={
                        "prompt": base_prompt,
                        "num_outputs": 1,
                        "aspect_ratio": "1:1",
                        "output_format": "webp",
                        "output_quality": 90,
                        "seed": seed
                    }
                )
                
                if output and len(output) > 0:
                    concepts.append(AvatarConceptResponse(
                        index=i,
                        image_url=str(output[0]),
                        seed=seed,
                        prompt_used=base_prompt
                    ))
                    
            except Exception as e:
                logger.error(f"Concept generation {i} failed: {e}")
                continue
        
        if not concepts:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate any avatar concepts. Please try again."
            )
        
        # Track generation usage
        billing.record_generation(current_user.id, len(concepts))
        
        return GenerateConceptsResponse(
            status="success",
            concepts=concepts,
            config_used={
                "gender": config.gender,
                "age_range": config.age_range,
                "style": config.style,
                "ethnicity": config.ethnicity
            },
            generation_id=generation_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Avatar concept generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@router.post("/generate-training-images", response_model=TrainingImagesResponse)
async def generate_training_images(
    request: GenerateTrainingImagesRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Step 2: Generate varied training images based on selected concept.
    Uses InstantID/IP-Adapter for face consistency.
    """
    # Verify brand
    brand = db.query(Brand).filter(
        Brand.id == request.brand_id,
        Brand.user_id == current_user.id
    ).first()
    
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    # Get API keys
    _, replicate_key = get_user_api_keys(current_user)
    
    if not replicate_key:
        raise HTTPException(status_code=400, detail="No Replicate API key configured")
    
    try:
        import replicate
        os.environ["REPLICATE_API_TOKEN"] = replicate_key
        
        # Variation prompts for training diversity
        variation_prompts = [
            # Different angles
            "front-facing portrait, studio lighting, neutral background",
            "slight left turn, three-quarter view, soft lighting",
            "slight right turn, professional lighting, clean background",
            "profile view, artistic lighting, elegant pose",
            
            # Different expressions
            "warm genuine smile, friendly expression, approachable look",
            "confident serious expression, professional demeanor",
            "relaxed natural expression, candid feel",
            "thoughtful expression, contemplative mood",
            
            # Different lighting
            "golden hour lighting, warm tones, outdoor feel",
            "soft diffused lighting, ethereal quality",
            "dramatic side lighting, artistic portrait",
            "bright natural window light, airy feel",
            
            # Different contexts
            "professional headshot, business attire, office background blur",
            "casual portrait, relaxed setting, natural environment",
            "editorial style, modern aesthetic, minimalist background",
            "lifestyle portrait, authentic moment, natural setting",
            
            # Close-ups
            "close-up face portrait, detailed features, sharp focus",
            "medium shot portrait, upper body, confident pose",
        ]
        
        generated_images = []
        
        # Use InstantID for face-consistent generation
        # This preserves the face from the hero image while varying other aspects
        for i in range(min(request.num_variations, len(variation_prompts))):
            try:
                # InstantID model for face consistency
                output = replicate.run(
                    "zsxkib/instant-id:2fb75683b95ef79c92aa67a86cfde13ebf3c05ca6cd6a5a8a2e51e7c01ecd9d9",
                    input={
                        "image": request.hero_image_url,
                        "prompt": f"portrait, {variation_prompts[i]}, photorealistic, high quality",
                        "negative_prompt": "blurry, low quality, distorted face, deformed",
                        "ip_adapter_scale": 0.8,  # Higher = more face preservation
                        "controlnet_conditioning_scale": 0.8,
                        "num_inference_steps": 30,
                        "guidance_scale": 5.0,
                    }
                )
                
                if output:
                    generated_images.append({
                        "index": i,
                        "image_url": str(output),
                        "variation_type": variation_prompts[i][:50],
                        "included": True
                    })
                    
            except Exception as e:
                logger.warning(f"Training image {i} generation failed: {e}")
                # Try fallback with img2img if InstantID fails
                try:
                    output = replicate.run(
                        "stability-ai/sdxl:c221b2b8ef527988fb59bf24a8b97c4561f1c671f73bd389f866bfb27c061316",
                        input={
                            "prompt": f"portrait, {variation_prompts[i]}, photorealistic, consistent face",
                            "image": request.hero_image_url,
                            "prompt_strength": 0.3,  # Low = more image preservation
                            "num_outputs": 1
                        }
                    )
                    if output and len(output) > 0:
                        generated_images.append({
                            "index": i,
                            "image_url": str(output[0]),
                            "variation_type": variation_prompts[i][:50],
                            "included": True
                        })
                except:
                    continue
        
        # Need at least 10 images for good LoRA training
        ready_for_training = len(generated_images) >= 10
        
        return TrainingImagesResponse(
            status="success" if ready_for_training else "partial",
            images=generated_images,
            total_count=len(generated_images),
            ready_for_training=ready_for_training
        )
        
    except Exception as e:
        logger.error(f"Training image generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@router.post("/create-from-generated")
async def create_avatar_from_generated(
    request: CreateFromGeneratedRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Step 3: Create LoRA model from generated training images.
    Initiates the training pipeline.
    """
    # Verify brand
    brand = db.query(Brand).filter(
        Brand.id == request.brand_id,
        Brand.user_id == current_user.id
    ).first()
    
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    # Check LoRA model limits
    billing = BillingService(db)
    limit_check = billing.check_lora_limit(current_user.id)
    if not limit_check.get("allowed", False):
        raise HTTPException(
            status_code=403,
            detail=f"Avatar limit reached. {limit_check.get('message', 'Upgrade to create more avatars.')}"
        )
    
    if len(request.training_image_urls) < 10:
        raise HTTPException(
            status_code=400,
            detail=f"Need at least 10 training images. Got {len(request.training_image_urls)}."
        )
    
    try:
        # Check for LoRA models table
        from app.lora.models import LoraModel, TrainingStatus
        from app.lora.training_service import get_lora_training_service
        
        # Generate trigger word
        trigger_word = request.trigger_word or f"AVATAR{brand.id}_{uuid.uuid4().hex[:6].upper()}"
        
        # Create LoRA model record
        lora_model = LoraModel(
            brand_id=request.brand_id,
            user_id=current_user.id,
            name=request.avatar_name,
            trigger_word=trigger_word,
            status=TrainingStatus.PENDING,
            reference_image_url=request.hero_image_url,
            training_steps=1000,
            lora_rank=16,
            learning_rate=0.0001
        )
        db.add(lora_model)
        db.commit()
        db.refresh(lora_model)
        
        # Get training service
        _, replicate_key = get_user_api_keys(current_user)
        training_service = get_lora_training_service(db, replicate_key)
        
        # Add training images
        for url in request.training_image_urls:
            await training_service.add_reference_image(lora_model, url)
        
        # Start training in background
        background_tasks.add_task(
            training_service.start_training,
            lora_model
        )
        
        return {
            "status": "training_started",
            "avatar_id": lora_model.id,
            "trigger_word": trigger_word,
            "message": "Avatar training has been queued. This typically takes 15-25 minutes.",
            "estimated_time_minutes": 20
        }
        
    except ImportError:
        # LoRA module not available, create simplified avatar record
        logger.warning("LoRA module not available, creating basic avatar")
        
        # Update brand with avatar info
        brand.reference_image_url = request.hero_image_url
        brand.persona_name = request.avatar_name
        db.commit()
        
        return {
            "status": "avatar_created",
            "avatar_id": brand.id,
            "message": "Avatar created successfully (LoRA training not available)",
            "hero_image_url": request.hero_image_url
        }
        
    except Exception as e:
        logger.error(f"Avatar creation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Avatar creation failed: {str(e)}")


@router.post("/upload-images")
async def upload_avatar_images(
    brand_id: int,
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Alternative path: Upload existing images for LoRA training.
    For brands that already have spokesperson photos.
    """
    # Verify brand
    brand = db.query(Brand).filter(
        Brand.id == brand_id,
        Brand.user_id == current_user.id
    ).first()
    
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    if len(files) < 5:
        raise HTTPException(
            status_code=400,
            detail="Please upload at least 5 images for training"
        )
    
    if len(files) > 25:
        raise HTTPException(
            status_code=400,
            detail="Maximum 25 images allowed per avatar"
        )
    
    # Validate file types
    allowed_types = {"image/jpeg", "image/png", "image/webp"}
    for file in files:
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {file.filename}. Allowed: JPEG, PNG, WebP"
            )
    
    # Process and upload images
    uploaded_urls = []
    
    try:
        # In production, upload to S3 or similar
        # For now, return placeholder indicating upload would happen
        for i, file in enumerate(files):
            # Read file content (would upload to cloud storage)
            content = await file.read()
            
            # Placeholder URL (replace with actual upload logic)
            uploaded_urls.append({
                "filename": file.filename,
                "size": len(content),
                "status": "uploaded",
                "index": i
            })
        
        return {
            "status": "success",
            "images_uploaded": len(uploaded_urls),
            "files": uploaded_urls,
            "next_step": "Call POST /avatar/create-from-uploaded to start training"
        }
        
    except Exception as e:
        logger.error(f"Image upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/status/{avatar_id}", response_model=AvatarStatusResponse)
async def get_avatar_status(
    avatar_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get avatar training status"""
    try:
        from app.lora.models import LoraModel
        
        lora_model = db.query(LoraModel).filter(
            LoraModel.id == avatar_id,
            LoraModel.user_id == current_user.id
        ).first()
        
        if not lora_model:
            raise HTTPException(status_code=404, detail="Avatar not found")
        
        return AvatarStatusResponse(
            avatar_id=lora_model.id,
            status=lora_model.status.value,
            progress_percent=lora_model.progress_percent or 0,
            hero_image_url=lora_model.reference_image_url,
            error_message=lora_model.error_message
        )
        
    except ImportError:
        raise HTTPException(status_code=404, detail="Avatar not found")


@router.get("/list")
async def list_user_avatars(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all avatars for current user"""
    try:
        from app.lora.models import LoraModel
        
        avatars = db.query(LoraModel).filter(
            LoraModel.user_id == current_user.id
        ).order_by(LoraModel.created_at.desc()).all()
        
        return {
            "avatars": [
                {
                    "id": a.id,
                    "name": a.name,
                    "brand_id": a.brand_id,
                    "status": a.status.value,
                    "trigger_word": a.trigger_word,
                    "hero_image_url": a.reference_image_url,
                    "created_at": a.created_at.isoformat() if a.created_at else None
                }
                for a in avatars
            ],
            "total": len(avatars)
        }
        
    except ImportError:
        return {"avatars": [], "total": 0}


@router.delete("/{avatar_id}")
async def delete_avatar(
    avatar_id: int,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Delete an avatar"""
    try:
        from app.lora.models import LoraModel
        
        lora_model = db.query(LoraModel).filter(
            LoraModel.id == avatar_id,
            LoraModel.user_id == current_user.id
        ).first()
        
        if not lora_model:
            raise HTTPException(status_code=404, detail="Avatar not found")
        
        db.delete(lora_model)
        db.commit()
        
        return {"status": "deleted", "avatar_id": avatar_id}
        
    except ImportError:
        raise HTTPException(status_code=404, detail="Avatar not found")

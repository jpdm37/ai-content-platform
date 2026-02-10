"""
Avatar Generation API Endpoints

Provides endpoints for:
1. Generating avatar concepts from requirements
2. Selecting a concept and generating training images
3. Creating LoRA model from generated images
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_user
from app.avatar.service import get_avatar_service, AvatarStyle
from app.lora.service import get_lora_training_service
from app.lora.models import LoraModel, TrainingStatus

router = APIRouter(prefix="/avatar", tags=["Avatar Generation"])


# ============== Request/Response Schemas ==============

class AvatarRequirements(BaseModel):
    """Requirements for generating an avatar"""
    gender: str = Field(..., description="male, female, or non-binary")
    age_range: str = Field(..., description="e.g., '25-30', '35-40'")
    style: str = Field(default="professional", description="Avatar style preset")
    ethnicity: Optional[str] = Field(None, description="Optional ethnicity/appearance")
    hair_color: Optional[str] = Field(None, description="e.g., brown, blonde, black")
    hair_style: Optional[str] = Field(None, description="e.g., short, long, curly")
    distinguishing_features: Optional[str] = Field(None, description="e.g., beard, glasses")
    custom_description: Optional[str] = Field(None, description="Additional details")


class GenerateConceptsRequest(AvatarRequirements):
    """Request to generate avatar concepts"""
    brand_id: int
    avatar_name: str
    num_concepts: int = Field(default=4, ge=2, le=8)


class ConceptImage(BaseModel):
    """A generated concept image"""
    image_url: str
    seed: int
    index: int


class GenerateConceptsResponse(BaseModel):
    """Response with generated concepts"""
    success: bool
    concepts: List[ConceptImage] = []
    prompt_used: Optional[str] = None
    requirements: Optional[dict] = None
    estimated_cost: float = 0
    error: Optional[str] = None


class SelectConceptRequest(BaseModel):
    """Request to select a concept and generate training images"""
    brand_id: int
    avatar_name: str
    selected_concept_url: str
    selected_seed: int
    original_prompt: str
    requirements: dict
    num_training_images: int = Field(default=12, ge=5, le=20)


class TrainingImage(BaseModel):
    """A generated training image"""
    image_url: str
    prompt: str
    method: str
    index: int
    seed: Optional[int] = None


class GenerateTrainingImagesResponse(BaseModel):
    """Response with training images"""
    success: bool
    training_images: List[TrainingImage] = []
    total_images: int = 0
    estimated_cost: float = 0
    ready_for_training: bool = False
    error: Optional[str] = None


class CreateAvatarFromImagesRequest(BaseModel):
    """Request to create LoRA model from generated images"""
    brand_id: int
    avatar_name: str
    training_image_urls: List[str]
    trigger_word: str = Field(default="AVATAR")
    training_steps: int = Field(default=1000, ge=500, le=2000)


class AvatarModelResponse(BaseModel):
    """Response after creating avatar model"""
    success: bool
    model_id: Optional[int] = None
    status: Optional[str] = None
    message: str
    estimated_training_time_minutes: int = 20
    estimated_cost: float = 0


# ============== Endpoints ==============

@router.post("/generate-concepts", response_model=GenerateConceptsResponse)
async def generate_avatar_concepts(
    request: GenerateConceptsRequest,
    current_user = Depends(get_current_user)
):
    """
    Generate avatar concept images based on requirements.
    
    This is step 1 of avatar creation. Returns 4 unique avatar options
    for the user to choose from.
    """
    service = get_avatar_service()
    
    result = await service.generate_avatar_concepts(
        gender=request.gender,
        age_range=request.age_range,
        style=request.style,
        ethnicity=request.ethnicity,
        hair_color=request.hair_color,
        hair_style=request.hair_style,
        distinguishing_features=request.distinguishing_features,
        custom_description=request.custom_description,
        num_concepts=request.num_concepts
    )
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Generation failed"))
    
    return GenerateConceptsResponse(
        success=True,
        concepts=[ConceptImage(**c) for c in result["concepts"]],
        prompt_used=result["prompt_used"],
        requirements=result["requirements"],
        estimated_cost=result["estimated_cost"]
    )


@router.post("/generate-training-images", response_model=GenerateTrainingImagesResponse)
async def generate_training_images(
    request: SelectConceptRequest,
    current_user = Depends(get_current_user)
):
    """
    Generate training images based on selected concept.
    
    This is step 2 of avatar creation. Takes the selected concept
    and generates multiple consistent variations for LoRA training.
    """
    service = get_avatar_service()
    
    result = await service.generate_training_images(
        reference_image_url=request.selected_concept_url,
        reference_seed=request.selected_seed,
        original_prompt=request.original_prompt,
        num_images=request.num_training_images,
        include_variations=True
    )
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Generation failed"))
    
    return GenerateTrainingImagesResponse(
        success=True,
        training_images=[TrainingImage(**img) for img in result["training_images"]],
        total_images=result["total_images"],
        estimated_cost=result["estimated_cost"],
        ready_for_training=result["ready_for_training"]
    )


@router.post("/create-from-generated", response_model=AvatarModelResponse)
async def create_avatar_from_generated_images(
    request: CreateAvatarFromImagesRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Create a LoRA model from generated training images.
    
    This is step 3 of avatar creation. Takes the generated training
    images and creates a LoRA training job.
    """
    if len(request.training_image_urls) < 5:
        raise HTTPException(
            status_code=400, 
            detail=f"Need at least 5 training images, got {len(request.training_image_urls)}"
        )
    
    try:
        # Create LoRA model record
        lora_model = LoraModel(
            user_id=current_user.id,
            brand_id=request.brand_id,
            name=request.avatar_name,
            trigger_word=request.trigger_word.upper().replace(" ", "_"),
            training_steps=request.training_steps,
            status=TrainingStatus.PENDING,
            is_generated_avatar=True  # Flag that this was AI-generated
        )
        db.add(lora_model)
        db.commit()
        db.refresh(lora_model)
        
        # Add training images
        lora_service = get_lora_training_service(db)
        await lora_service.bulk_add_images(lora_model, request.training_image_urls)
        
        # Validate readiness
        validation = await lora_service.validate_training_readiness(lora_model)
        
        if not validation["is_ready"]:
            return AvatarModelResponse(
                success=False,
                model_id=lora_model.id,
                status="validation_failed",
                message=f"Not ready: {', '.join(validation['issues'])}",
                estimated_training_time_minutes=0,
                estimated_cost=0
            )
        
        # Start training in background
        background_tasks.add_task(
            lora_service.start_training,
            lora_model
        )
        
        return AvatarModelResponse(
            success=True,
            model_id=lora_model.id,
            status="training_started",
            message="Avatar training started! This typically takes 15-30 minutes.",
            estimated_training_time_minutes=validation["estimated_time_minutes"],
            estimated_cost=validation["estimated_cost_usd"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/styles")
async def get_avatar_styles():
    """
    Get available avatar style presets.
    """
    return {
        "styles": [
            {"id": "professional", "name": "Professional", "description": "Business attire, corporate setting"},
            {"id": "influencer", "name": "Influencer", "description": "Stylish casual, lifestyle photography"},
            {"id": "corporate", "name": "Corporate", "description": "Formal executive presence"},
            {"id": "creative", "name": "Creative", "description": "Artistic, unique fashion"},
            {"id": "lifestyle", "name": "Lifestyle", "description": "Casual, authentic, natural"},
            {"id": "tech", "name": "Tech", "description": "Smart casual, modern minimalist"},
            {"id": "fitness", "name": "Fitness", "description": "Athletic, healthy, energetic"},
            {"id": "fashion", "name": "Fashion", "description": "High fashion, editorial style"}
        ]
    }


@router.get("/options")
async def get_avatar_options():
    """
    Get all available options for avatar generation form.
    """
    return {
        "genders": [
            {"id": "male", "label": "Male"},
            {"id": "female", "label": "Female"},
            {"id": "non-binary", "label": "Non-binary"}
        ],
        "age_ranges": [
            {"id": "18-24", "label": "18-24"},
            {"id": "25-30", "label": "25-30"},
            {"id": "31-40", "label": "31-40"},
            {"id": "41-50", "label": "41-50"},
            {"id": "51-60", "label": "51-60"},
            {"id": "60+", "label": "60+"}
        ],
        "ethnicities": [
            {"id": "", "label": "Any/Not specified"},
            {"id": "caucasian", "label": "Caucasian"},
            {"id": "african", "label": "African"},
            {"id": "asian", "label": "Asian"},
            {"id": "hispanic", "label": "Hispanic/Latino"},
            {"id": "middle eastern", "label": "Middle Eastern"},
            {"id": "south asian", "label": "South Asian"},
            {"id": "mixed", "label": "Mixed/Multi-ethnic"}
        ],
        "hair_colors": [
            {"id": "", "label": "Any"},
            {"id": "black", "label": "Black"},
            {"id": "brown", "label": "Brown"},
            {"id": "blonde", "label": "Blonde"},
            {"id": "red", "label": "Red"},
            {"id": "gray", "label": "Gray"},
            {"id": "white", "label": "White"}
        ],
        "hair_styles": [
            {"id": "", "label": "Any"},
            {"id": "short", "label": "Short"},
            {"id": "medium length", "label": "Medium"},
            {"id": "long", "label": "Long"},
            {"id": "curly", "label": "Curly"},
            {"id": "wavy", "label": "Wavy"},
            {"id": "straight", "label": "Straight"},
            {"id": "bald", "label": "Bald"}
        ]
    }

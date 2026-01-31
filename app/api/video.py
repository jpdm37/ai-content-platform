"""
Video Generation API Routes

Endpoints for creating talking head videos with AI avatars.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.auth.dependencies import get_current_user, get_current_verified_user
from app.billing.service import BillingService

from app.video.models import (
    GeneratedVideo, VideoTemplate, VoiceClone,
    VideoStatus, VoiceProvider, VideoAspectRatio,
    PRESET_VOICES, EXPRESSION_PRESETS
)
from app.video.schemas import (
    VideoGenerateRequest, VideoGenerateFromTemplateRequest,
    VideoResponse, VideoDetailResponse, VideoProgressResponse, VideoListResponse,
    VideoTemplateCreate, VideoTemplateResponse,
    VoiceCloneCreate, VoiceCloneResponse, VoiceListResponse, VoicePreset,
    VideoCostEstimate, EstimateCostRequest, BatchVideoRequest, BatchVideoResponse,
    VoiceProviderEnum, AspectRatioEnum, ExpressionEnum
)
from app.video.service import VideoGenerationService

router = APIRouter(prefix="/video", tags=["video-generation"])


# ==================== Video Generation ====================

@router.post("/generate", response_model=VideoResponse)
async def generate_video(
    request: VideoGenerateRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Generate a talking head video"""
    # Check subscription limits
    billing = BillingService(db)
    limit_check = billing.check_limit(current_user, "generations")
    if not limit_check["allowed"]:
        raise HTTPException(
            status_code=403,
            detail="Generation limit reached. Upgrade your plan for more."
        )
    
    # Validate avatar source
    if not request.lora_model_id and not request.avatar_image_url and not request.avatar_prompt:
        raise HTTPException(
            status_code=400,
            detail="Please provide a LoRA model, avatar image URL, or avatar prompt"
        )
    
    service = VideoGenerationService(db)
    
    try:
        video = await service.generate_video(
            user_id=current_user.id,
            script=request.script,
            voice_provider=VoiceProvider(request.voice_provider.value),
            voice_id=request.voice_id,
            voice_clone_id=request.voice_clone_id,
            voice_settings=request.voice_settings.model_dump() if request.voice_settings else None,
            lora_model_id=request.lora_model_id,
            avatar_image_url=request.avatar_image_url,
            avatar_prompt=request.avatar_prompt,
            aspect_ratio=VideoAspectRatio(request.aspect_ratio.value),
            expression=request.expression.value,
            head_movement=request.head_movement.value,
            eye_contact=request.eye_contact,
            background_color=request.background_color,
            background_image_url=request.background_image_url,
            title=request.title,
            brand_id=request.brand_id
        )
        
        # Record usage
        billing.record_usage(current_user, "video_generation", metadata={"video_id": video.id})
        
        return VideoResponse.model_validate(video)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/template", response_model=VideoResponse)
async def generate_from_template(
    request: VideoGenerateFromTemplateRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Generate video using a template"""
    # Get template
    template = db.query(VideoTemplate).filter(
        VideoTemplate.id == request.template_id,
        VideoTemplate.is_active == True
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Check if user can use template
    if template.user_id and template.user_id != current_user.id and not template.is_public:
        raise HTTPException(status_code=403, detail="Access denied to this template")
    
    # Process script with variables
    script = request.script
    if request.variables and template.script_template:
        script = template.script_template
        for key, value in request.variables.items():
            script = script.replace(f"{{{{{key}}}}}", value)
    
    service = VideoGenerationService(db)
    
    try:
        video = await service.generate_video(
            user_id=current_user.id,
            script=script,
            voice_provider=template.voice_provider,
            voice_id=template.voice_id,
            voice_settings=template.voice_settings,
            lora_model_id=request.lora_model_id,
            avatar_image_url=request.avatar_image_url,
            aspect_ratio=template.aspect_ratio,
            expression=template.expression,
            head_movement=template.head_movement,
            background_color=template.background_color,
            background_image_url=template.background_image_url,
            brand_id=request.brand_id
        )
        
        return VideoResponse.model_validate(video)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/batch", response_model=BatchVideoResponse)
async def batch_generate_videos(
    request: BatchVideoRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Generate multiple videos with different scripts"""
    # Check limits
    billing = BillingService(db)
    limit_check = billing.check_limit(current_user, "generations")
    if limit_check["remaining"] < len(request.scripts):
        raise HTTPException(
            status_code=403,
            detail=f"Not enough generations remaining ({limit_check['remaining']} < {len(request.scripts)})"
        )
    
    service = VideoGenerationService(db)
    video_ids = []
    total_cost = 0
    
    for script in request.scripts:
        try:
            video = await service.generate_video(
                user_id=current_user.id,
                script=script,
                voice_provider=VoiceProvider(request.voice_provider.value),
                voice_id=request.voice_id,
                lora_model_id=request.lora_model_id,
                avatar_image_url=request.avatar_image_url,
                aspect_ratio=VideoAspectRatio(request.aspect_ratio.value),
                brand_id=request.brand_id
            )
            video_ids.append(video.id)
            total_cost += video.total_cost_usd
            
            billing.record_usage(current_user, "video_generation")
        except Exception as e:
            # Log but continue with other videos
            pass
    
    return BatchVideoResponse(
        queued=len(video_ids),
        video_ids=video_ids,
        estimated_total_cost=total_cost
    )


# ==================== Video Management ====================

@router.get("/videos", response_model=VideoListResponse)
async def list_videos(
    brand_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List user's generated videos"""
    service = VideoGenerationService(db)
    
    status = None
    if status_filter:
        try:
            status = VideoStatus(status_filter)
        except ValueError:
            pass
    
    videos, total = service.list_videos(
        user_id=current_user.id,
        brand_id=brand_id,
        status=status,
        skip=skip,
        limit=limit
    )
    
    return VideoListResponse(
        videos=[VideoResponse.model_validate(v) for v in videos],
        total=total,
        page=skip // limit + 1,
        per_page=limit
    )


@router.get("/videos/{video_id}", response_model=VideoDetailResponse)
async def get_video(
    video_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get video details"""
    service = VideoGenerationService(db)
    video = service.get_video(video_id, current_user.id)
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    return VideoDetailResponse.model_validate(video)


@router.get("/videos/{video_id}/progress", response_model=VideoProgressResponse)
async def get_video_progress(
    video_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get video generation progress"""
    service = VideoGenerationService(db)
    progress = service.get_video_progress(video_id, current_user.id)
    
    if not progress:
        raise HTTPException(status_code=404, detail="Video not found")
    
    return VideoProgressResponse(**progress)


@router.post("/videos/{video_id}/cancel")
async def cancel_video(
    video_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel video generation"""
    service = VideoGenerationService(db)
    success = await service.cancel_video(video_id, current_user.id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Cannot cancel video")
    
    return {"success": True}


@router.delete("/videos/{video_id}")
async def delete_video(
    video_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a video"""
    service = VideoGenerationService(db)
    success = service.delete_video(video_id, current_user.id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Video not found")
    
    return {"success": True}


# ==================== Cost Estimation ====================

@router.post("/estimate-cost", response_model=VideoCostEstimate)
async def estimate_video_cost(
    request: EstimateCostRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Estimate cost for video generation"""
    service = VideoGenerationService(db)
    estimate = service.estimate_cost(request.script, request.generate_avatar)
    return VideoCostEstimate(**estimate)


# ==================== Voices ====================

@router.get("/voices", response_model=List[VoiceListResponse])
async def list_voices(
    current_user: User = Depends(get_current_user)
):
    """List available TTS voices"""
    result = []
    
    for provider, voices in PRESET_VOICES.items():
        result.append(VoiceListResponse(
            provider=VoiceProviderEnum(provider),
            voices=[
                VoicePreset(
                    id=v["id"],
                    name=v["name"],
                    gender=v.get("gender"),
                    accent=v.get("accent"),
                    style=v.get("style"),
                    provider=VoiceProviderEnum(provider)
                )
                for v in voices
            ]
        ))
    
    return result


@router.get("/voices/clones", response_model=List[VoiceCloneResponse])
async def list_voice_clones(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List user's cloned voices"""
    clones = db.query(VoiceClone).filter(
        VoiceClone.user_id == current_user.id,
        VoiceClone.is_active == True
    ).order_by(VoiceClone.created_at.desc()).all()
    
    return [VoiceCloneResponse.model_validate(c) for c in clones]


@router.post("/voices/clone", response_model=VoiceCloneResponse)
async def create_voice_clone(
    request: VoiceCloneCreate,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Create a custom voice clone (requires audio samples)"""
    # This would integrate with ElevenLabs voice cloning API
    # For now, create a placeholder
    
    clone = VoiceClone(
        user_id=current_user.id,
        name=request.name,
        description=request.description,
        provider=VoiceProvider.ELEVENLABS,
        sample_audio_urls=request.sample_audio_urls,
        gender=request.gender,
        accent=request.accent,
        is_ready=False  # Will be updated when cloning completes
    )
    
    db.add(clone)
    db.commit()
    db.refresh(clone)
    
    # TODO: Start async voice cloning process
    
    return VoiceCloneResponse.model_validate(clone)


@router.delete("/voices/clones/{clone_id}")
async def delete_voice_clone(
    clone_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a voice clone"""
    clone = db.query(VoiceClone).filter(
        VoiceClone.id == clone_id,
        VoiceClone.user_id == current_user.id
    ).first()
    
    if not clone:
        raise HTTPException(status_code=404, detail="Voice clone not found")
    
    db.delete(clone)
    db.commit()
    
    return {"success": True}


# ==================== Templates ====================

@router.get("/templates", response_model=List[VideoTemplateResponse])
async def list_templates(
    category: Optional[str] = None,
    include_public: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List video templates"""
    query = db.query(VideoTemplate).filter(VideoTemplate.is_active == True)
    
    if include_public:
        query = query.filter(
            (VideoTemplate.user_id == current_user.id) | (VideoTemplate.is_public == True)
        )
    else:
        query = query.filter(VideoTemplate.user_id == current_user.id)
    
    if category:
        query = query.filter(VideoTemplate.category == category)
    
    templates = query.order_by(VideoTemplate.created_at.desc()).all()
    
    return [VideoTemplateResponse.model_validate(t) for t in templates]


@router.post("/templates", response_model=VideoTemplateResponse)
async def create_template(
    request: VideoTemplateCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a video template"""
    template = VideoTemplate(
        user_id=current_user.id,
        name=request.name,
        description=request.description,
        category=request.category,
        voice_provider=VoiceProvider(request.voice_provider.value),
        voice_id=request.voice_id,
        voice_settings=request.voice_settings.model_dump() if request.voice_settings else None,
        aspect_ratio=VideoAspectRatio(request.aspect_ratio.value),
        resolution=request.resolution,
        expression=request.expression.value,
        head_movement=request.head_movement.value,
        background_color=request.background_color,
        background_image_url=request.background_image_url,
        script_template=request.script_template,
        is_public=request.is_public
    )
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    return VideoTemplateResponse.model_validate(template)


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a template"""
    template = db.query(VideoTemplate).filter(
        VideoTemplate.id == template_id,
        VideoTemplate.user_id == current_user.id
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    db.delete(template)
    db.commit()
    
    return {"success": True}


# ==================== Presets Info ====================

@router.get("/expressions")
async def list_expressions():
    """List available expressions"""
    return [
        {"id": key, **value}
        for key, value in EXPRESSION_PRESETS.items()
    ]


@router.get("/aspect-ratios")
async def list_aspect_ratios():
    """List available aspect ratios"""
    return [
        {"id": ar.value, "name": ar.name, "use_case": use_case}
        for ar, use_case in [
            (VideoAspectRatio.PORTRAIT, "TikTok, Reels, Shorts"),
            (VideoAspectRatio.LANDSCAPE, "YouTube, LinkedIn"),
            (VideoAspectRatio.SQUARE, "Instagram, Facebook"),
            (VideoAspectRatio.VERTICAL, "Instagram Feed"),
        ]
    ]

"""
AI Content Studio API Routes

Unified content generation from a single brief.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.models.user import User
from app.auth.dependencies import get_current_user, get_current_verified_user
from app.billing.service import BillingService

from app.studio.models import StudioProject, StudioAsset, StudioTemplate, ContentType
from app.studio.schemas import (
    CreateProjectRequest, CreateFromTemplateRequest,
    ProjectResponse, ProjectDetailResponse, ProjectListResponse, ProjectProgressResponse,
    AssetResponse, UpdateAssetRequest,
    CreateTemplateRequest, TemplateResponse,
    QuickGenerateRequest, QuickGenerateResponse,
    ContentTypeEnum, ProjectStatusEnum
)
from app.studio.service import ContentStudioService

router = APIRouter(prefix="/studio", tags=["content-studio"])


# ==================== Projects ====================

@router.post("/projects", response_model=ProjectResponse)
@limiter.limit("5/minute")  # Studio projects are resource-intensive
async def create_project(
    request_obj: Request,
    response: Response,
    request: CreateProjectRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Create a new Content Studio project.
    
    This will generate multiple content assets from a single brief:
    - Caption variations
    - Hashtag suggestions
    - Image options
    - Video (optional)
    - Platform-optimized versions
    """
    # Check billing limits
    billing = BillingService(db)
    limit_check = billing.check_limit(current_user, "generations")
    if not limit_check["allowed"]:
        raise HTTPException(
            status_code=403,
            detail="Generation limit reached. Upgrade your plan for more."
        )
    
    service = ContentStudioService(db)
    
    try:
        project = await service.create_project(
            user_id=current_user.id,
            brief=request.brief,
            name=request.name,
            target_platforms=[p.value for p in request.target_platforms],
            content_types=[c.value for c in request.content_types],
            brand_id=request.brand_id,
            tone=request.tone.value,
            num_variations=request.num_variations,
            include_video=request.include_video,
            lora_model_id=request.lora_model_id,
            video_duration=request.video_duration
        )
        
        # Record usage
        billing.record_usage(current_user, "studio_project", metadata={"project_id": project.id})
        
        return ProjectResponse.model_validate(project)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/from-template", response_model=ProjectResponse)
async def create_from_template(
    request: CreateFromTemplateRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Create a project from a template."""
    template = db.query(StudioTemplate).filter(
        StudioTemplate.id == request.template_id,
        StudioTemplate.is_active == True
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Check access
    if template.user_id and template.user_id != current_user.id and not template.is_public:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Process brief with variables
    brief = request.brief
    if request.variables and template.brief_template:
        brief = template.brief_template
        for key, value in request.variables.items():
            brief = brief.replace(f"{{{{{key}}}}}", value)
    
    service = ContentStudioService(db)
    
    project = await service.create_project(
        user_id=current_user.id,
        brief=brief,
        target_platforms=template.target_platforms,
        content_types=template.content_types,
        brand_id=request.brand_id,
        tone=template.tone,
        num_variations=template.num_variations,
        include_video=template.include_video
    )
    
    # Update template usage
    template.times_used += 1
    db.commit()
    
    return ProjectResponse.model_validate(project)


@router.get("/projects", response_model=ProjectListResponse)
async def list_projects(
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List user's studio projects."""
    service = ContentStudioService(db)
    
    status = None
    if status_filter:
        try:
            status = ProjectStatusEnum(status_filter)
        except ValueError:
            pass
    
    projects, total = service.list_projects(
        user_id=current_user.id,
        status=status,
        skip=skip,
        limit=limit
    )
    
    return ProjectListResponse(
        projects=[ProjectResponse.model_validate(p) for p in projects],
        total=total,
        page=skip // limit + 1,
        per_page=limit
    )


@router.get("/projects/{project_id}", response_model=ProjectDetailResponse)
async def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get project details with all assets."""
    service = ContentStudioService(db)
    project = service.get_project(project_id, current_user.id)
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get assets
    assets = service.get_project_assets(project_id, current_user.id)
    
    response = ProjectDetailResponse.model_validate(project)
    response.assets = [AssetResponse.model_validate(a) for a in assets]
    
    return response


@router.get("/projects/{project_id}/progress", response_model=ProjectProgressResponse)
async def get_project_progress(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get project generation progress."""
    service = ContentStudioService(db)
    project = service.get_project(project_id, current_user.id)
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return ProjectProgressResponse(
        id=project.id,
        status=ProjectStatusEnum(project.status.value),
        progress_percent=project.progress_percent,
        current_step=project.current_step,
        captions_generated=project.captions_generated,
        images_generated=project.images_generated,
        videos_generated=project.videos_generated,
        error_message=project.error_message
    )


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a project and all its assets."""
    service = ContentStudioService(db)
    success = service.delete_project(project_id, current_user.id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return {"success": True}


# ==================== Assets ====================

@router.get("/projects/{project_id}/assets", response_model=List[AssetResponse])
async def get_project_assets(
    project_id: int,
    content_type: Optional[str] = None,
    platform: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get assets for a project, optionally filtered."""
    service = ContentStudioService(db)
    
    ct = None
    if content_type:
        try:
            ct = ContentType(content_type)
        except ValueError:
            pass
    
    assets = service.get_project_assets(
        project_id=project_id,
        user_id=current_user.id,
        content_type=ct,
        platform=platform
    )
    
    return [AssetResponse.model_validate(a) for a in assets]


@router.patch("/assets/{asset_id}", response_model=AssetResponse)
async def update_asset(
    asset_id: int,
    request: UpdateAssetRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update asset (favorite, select, rate)."""
    service = ContentStudioService(db)
    
    update_data = request.model_dump(exclude_unset=True)
    asset = service.update_asset(asset_id, current_user.id, **update_data)
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    return AssetResponse.model_validate(asset)


@router.post("/assets/{asset_id}/select")
async def select_asset(
    asset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark asset as selected for use."""
    service = ContentStudioService(db)
    asset = service.update_asset(asset_id, current_user.id, is_selected=True)
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    return {"success": True, "asset_id": asset_id}


@router.post("/assets/{asset_id}/favorite")
async def toggle_favorite(
    asset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Toggle favorite status."""
    asset = db.query(StudioAsset).join(StudioProject).filter(
        StudioAsset.id == asset_id,
        StudioProject.user_id == current_user.id
    ).first()
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    asset.is_favorite = not asset.is_favorite
    db.commit()
    
    return {"success": True, "is_favorite": asset.is_favorite}


# ==================== Quick Generate ====================

@router.post("/quick-generate", response_model=QuickGenerateResponse)
async def quick_generate(
    request: QuickGenerateRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Quick generation of a single content type without creating a full project.
    Useful for one-off generations.
    """
    from openai import AsyncOpenAI
    from app.core.config import get_settings
    
    settings = get_settings()
    openai = AsyncOpenAI(api_key=settings.openai_api_key)
    
    prompts = {
        ContentTypeEnum.CAPTION: f"Write {request.num_results} unique {request.tone.value} social media captions for {request.platform.value}. Topic: {request.brief}. Number each 1-{request.num_results}.",
        ContentTypeEnum.HASHTAGS: f"Generate {request.num_results * 5} relevant hashtags for {request.platform.value}. Topic: {request.brief}. One per line, include # symbol.",
        ContentTypeEnum.HOOK: f"Write {request.num_results} attention-grabbing opening hooks. Topic: {request.brief}. Number each 1-{request.num_results}.",
        ContentTypeEnum.CTA: f"Write {request.num_results} compelling call-to-action phrases. Topic: {request.brief}. Number each 1-{request.num_results}.",
    }
    
    prompt = prompts.get(request.content_type)
    if not prompt:
        raise HTTPException(status_code=400, detail=f"Quick generate not supported for {request.content_type}")
    
    try:
        response = await openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.8
        )
        
        content = response.choices[0].message.content
        
        # Parse results
        import re
        if request.content_type == ContentTypeEnum.HASHTAGS:
            results = [h.strip() for h in content.split('\n') if h.strip().startswith('#')]
        else:
            parts = re.split(r'\n\d+[\.\)]\s*', content)
            results = [p.strip() for p in parts if p.strip()]
        
        return QuickGenerateResponse(
            content_type=request.content_type,
            results=results[:request.num_results * (5 if request.content_type == ContentTypeEnum.HASHTAGS else 1)],
            platform=request.platform.value,
            cost_usd=0.005
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Templates ====================

@router.get("/templates", response_model=List[TemplateResponse])
async def list_templates(
    category: Optional[str] = None,
    include_public: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List available templates."""
    query = db.query(StudioTemplate).filter(StudioTemplate.is_active == True)
    
    if include_public:
        query = query.filter(
            (StudioTemplate.user_id == current_user.id) | (StudioTemplate.is_public == True)
        )
    else:
        query = query.filter(StudioTemplate.user_id == current_user.id)
    
    if category:
        query = query.filter(StudioTemplate.category == category)
    
    templates = query.order_by(StudioTemplate.times_used.desc()).all()
    
    return [TemplateResponse.model_validate(t) for t in templates]


@router.post("/templates", response_model=TemplateResponse)
async def create_template(
    request: CreateTemplateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new template."""
    template = StudioTemplate(
        user_id=current_user.id,
        name=request.name,
        description=request.description,
        category=request.category,
        brief_template=request.brief_template,
        target_platforms=[p.value for p in request.target_platforms],
        content_types=[c.value for c in request.content_types],
        tone=request.tone.value,
        num_variations=request.num_variations,
        include_video=request.include_video,
        is_public=request.is_public
    )
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    return TemplateResponse.model_validate(template)


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a template."""
    template = db.query(StudioTemplate).filter(
        StudioTemplate.id == template_id,
        StudioTemplate.user_id == current_user.id
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    db.delete(template)
    db.commit()
    
    return {"success": True}


# ==================== Presets ====================

@router.get("/tones")
async def list_tones():
    """List available content tones."""
    from app.studio.models import TONE_DESCRIPTIONS
    return [
        {"id": key, "description": value}
        for key, value in TONE_DESCRIPTIONS.items()
    ]


@router.get("/platforms")
async def list_platforms():
    """List supported platforms with specs."""
    from app.studio.models import PLATFORM_SPECS
    return [
        {"id": key, **value}
        for key, value in PLATFORM_SPECS.items()
    ]

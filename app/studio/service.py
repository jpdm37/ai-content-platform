"""
AI Content Studio Service

Orchestrates multi-modal content generation from a single brief.
Generates: captions, images, videos, hashtags, and platform-optimized versions.
"""
import logging
import asyncio
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from openai import AsyncOpenAI

from app.core.config import get_settings
from app.studio.models import (
    StudioProject, StudioAsset, StudioTemplate,
    StudioProjectStatus, ContentType,
    STUDIO_PROMPTS, PLATFORM_SPECS, TONE_DESCRIPTIONS
)
from app.models.models import Brand
from app.lora.models import LoraModel
from app.services.generator import ContentGeneratorService
from app.video.service import VideoGenerationService

logger = logging.getLogger(__name__)
settings = get_settings()


class ContentStudioService:
    """
    AI Content Studio - unified content generation workflow.
    
    Flow:
    1. User provides brief, selects platforms and content types
    2. System generates multiple caption variations
    3. System generates image options
    4. System generates video (if requested)
    5. System creates platform-optimized versions
    6. User selects favorites and schedules
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.openai = AsyncOpenAI(api_key=settings.openai_api_key)
        self.content_generator = ContentGeneratorService(
            db, 
            settings.openai_api_key, 
            settings.replicate_api_token
        )
    
    # ==================== Project Management ====================
    
    async def create_project(
        self,
        user_id: int,
        brief: str,
        target_platforms: List[str],
        content_types: List[str],
        brand_id: Optional[int] = None,
        tone: str = "professional",
        num_variations: int = 3,
        include_video: bool = False,
        lora_model_id: Optional[int] = None,
        video_duration: str = "30s",
        name: Optional[str] = None
    ) -> StudioProject:
        """Create a new studio project and start generation."""
        
        project = StudioProject(
            user_id=user_id,
            brand_id=brand_id,
            name=name or f"Project {datetime.utcnow().strftime('%Y%m%d_%H%M')}",
            brief=brief,
            target_platforms=target_platforms,
            content_types=content_types,
            tone=tone,
            num_variations=num_variations,
            include_video=include_video,
            lora_model_id=lora_model_id,
            video_duration=video_duration,
            status=StudioProjectStatus.GENERATING,
            current_step="Initializing"
        )
        
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        
        # Start async generation
        asyncio.create_task(self._generate_project_content(project.id))
        
        return project
    
    async def _generate_project_content(self, project_id: int):
        """Main generation orchestrator."""
        project = self.db.query(StudioProject).filter(StudioProject.id == project_id).first()
        if not project:
            return
        
        try:
            total_cost = 0.0
            
            # Get brand info if available
            brand_voice = ""
            if project.brand_id:
                brand = self.db.query(Brand).filter(Brand.id == project.brand_id).first()
                if brand:
                    brand_voice = f"{brand.name}: {brand.description or ''}"
            
            # Step 1: Generate captions
            if "caption" in project.content_types:
                project.current_step = "Generating captions"
                project.progress_percent = 10
                self.db.commit()
                
                cost = await self._generate_captions(project, brand_voice)
                total_cost += cost
            
            # Step 2: Generate hooks
            if "hook" in project.content_types:
                project.current_step = "Generating hooks"
                project.progress_percent = 25
                self.db.commit()
                
                cost = await self._generate_hooks(project, brand_voice)
                total_cost += cost
            
            # Step 3: Generate hashtags
            if "hashtags" in project.content_types:
                project.current_step = "Generating hashtags"
                project.progress_percent = 35
                self.db.commit()
                
                cost = await self._generate_hashtags(project)
                total_cost += cost
            
            # Step 4: Generate CTAs
            if "cta" in project.content_types:
                project.current_step = "Generating CTAs"
                project.progress_percent = 45
                self.db.commit()
                
                cost = await self._generate_ctas(project)
                total_cost += cost
            
            # Step 5: Generate images
            if "image" in project.content_types:
                project.current_step = "Generating images"
                project.progress_percent = 55
                self.db.commit()
                
                cost = await self._generate_images(project, brand_voice)
                total_cost += cost
            
            # Step 6: Generate video (if requested)
            if project.include_video and "video" in project.content_types:
                project.current_step = "Generating video"
                project.progress_percent = 75
                self.db.commit()
                
                cost = await self._generate_video(project, brand_voice)
                total_cost += cost
            
            # Step 7: Create platform-optimized versions
            project.current_step = "Optimizing for platforms"
            project.progress_percent = 90
            self.db.commit()
            
            await self._create_platform_versions(project)
            
            # Complete
            project.status = StudioProjectStatus.COMPLETED
            project.progress_percent = 100
            project.current_step = "Complete"
            project.completed_at = datetime.utcnow()
            project.total_cost_usd = total_cost
            self.db.commit()
            
            logger.info(f"Studio project {project_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Studio project {project_id} failed: {e}")
            project.status = StudioProjectStatus.FAILED
            project.error_message = str(e)
            self.db.commit()
    
    # ==================== Content Generation ====================
    
    async def _generate_captions(self, project: StudioProject, brand_voice: str) -> float:
        """Generate multiple caption variations."""
        cost = 0.0
        tone_desc = TONE_DESCRIPTIONS.get(project.tone, project.tone)
        
        # Use gpt-4o-mini for captions - 20x cheaper, quality is sufficient
        model = "gpt-4o-mini"
        
        for platform in project.target_platforms:
            platform_spec = PLATFORM_SPECS.get(platform, PLATFORM_SPECS["instagram"])
            
            # Optimized prompt - shorter but effective
            prompt = f"""Generate {project.num_variations} unique {platform} captions.

Topic: {project.brief}
Tone: {tone_desc}
Max: {platform_spec['max_chars']} chars
{f'Brand: {brand_voice}' if brand_voice else ''}

Each caption needs: hook, value, CTA. Number them 1-{project.num_variations}."""

            try:
                response = await self.openai.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=1000,  # Reduced from 2000
                    temperature=0.8
                )
                
                content = response.choices[0].message.content
                # gpt-4o-mini costs ~$0.0006 per 1K tokens vs $0.01 for gpt-4o
                cost += 0.0006
                
                # Parse variations
                variations = self._parse_numbered_list(content)
                
                for i, caption in enumerate(variations[:project.num_variations], 1):
                    asset = StudioAsset(
                        project_id=project.id,
                        content_type=ContentType.CAPTION,
                        text_content=caption.strip(),
                        platform=platform,
                        variation_number=i,
                        ai_model_used=model,
                        prompt_used=prompt,
                        cost_usd=cost / len(variations)
                    )
                    self.db.add(asset)
                    project.captions_generated += 1
                
                self.db.commit()
                
            except Exception as e:
                logger.error(f"Caption generation failed for {platform}: {e}")
        
        return cost
    
    async def _generate_hooks(self, project: StudioProject, brand_voice: str) -> float:
        """Generate attention-grabbing hooks."""
        prompt = f"""Generate 5 attention-grabbing opening hooks for social media content.

Topic: {project.brief}
Brand Voice: {brand_voice or 'Not specified'}

These hooks should:
- Stop the scroll immediately
- Create curiosity or emotion
- Be under 10 words each
- Work across platforms

Return only the hooks, numbered 1-5:"""

        try:
            response = await self.openai.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.9
            )
            
            content = response.choices[0].message.content
            hooks = self._parse_numbered_list(content)
            
            for i, hook in enumerate(hooks[:5], 1):
                asset = StudioAsset(
                    project_id=project.id,
                    content_type=ContentType.HOOK,
                    text_content=hook.strip(),
                    variation_number=i,
                    ai_model_used="gpt-4o",
                    cost_usd=0.002
                )
                self.db.add(asset)
            
            self.db.commit()
            return 0.01
            
        except Exception as e:
            logger.error(f"Hook generation failed: {e}")
            return 0.0
    
    async def _generate_hashtags(self, project: StudioProject) -> float:
        """Generate platform-specific hashtags."""
        
        for platform in project.target_platforms:
            platform_spec = PLATFORM_SPECS.get(platform, PLATFORM_SPECS["instagram"])
            
            prompt = f"""Generate {platform_spec['hashtag_limit']} highly relevant hashtags for {platform}.

Content topic: {project.brief}

Requirements:
- Mix of popular (high reach) and niche (targeted) hashtags
- All hashtags must be relevant to the content
- Format: #hashtag (one per line)
- No explanations, just hashtags"""

            try:
                response = await self.openai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=300,
                    temperature=0.7
                )
                
                content = response.choices[0].message.content
                hashtags = [h.strip() for h in content.split('\n') if h.strip().startswith('#')]
                
                asset = StudioAsset(
                    project_id=project.id,
                    content_type=ContentType.HASHTAGS,
                    text_content='\n'.join(hashtags[:platform_spec['hashtag_limit']]),
                    platform=platform,
                    ai_model_used="gpt-4o-mini",
                    cost_usd=0.001
                )
                self.db.add(asset)
                
            except Exception as e:
                logger.error(f"Hashtag generation failed for {platform}: {e}")
        
        self.db.commit()
        return 0.005
    
    async def _generate_ctas(self, project: StudioProject) -> float:
        """Generate call-to-action phrases."""
        prompt = f"""Generate 5 compelling call-to-action phrases for this content:

Topic: {project.brief}

Requirements:
- Action-oriented language
- Create urgency or value
- Short and punchy (under 10 words)
- Variety of styles (question, command, invitation)

Return only the CTAs, numbered 1-5:"""

        try:
            response = await self.openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.8
            )
            
            content = response.choices[0].message.content
            ctas = self._parse_numbered_list(content)
            
            for i, cta in enumerate(ctas[:5], 1):
                asset = StudioAsset(
                    project_id=project.id,
                    content_type=ContentType.CTA,
                    text_content=cta.strip(),
                    variation_number=i,
                    ai_model_used="gpt-4o-mini",
                    cost_usd=0.001
                )
                self.db.add(asset)
            
            self.db.commit()
            return 0.005
            
        except Exception as e:
            logger.error(f"CTA generation failed: {e}")
            return 0.0
    
    async def _generate_images(self, project: StudioProject, brand_voice: str) -> float:
        """Generate image options using DALL-E or Flux."""
        cost = 0.0
        
        # First, generate an optimized image prompt
        prompt_request = f"""Create a detailed image generation prompt for this content:

Topic: {project.brief}
Brand: {brand_voice or 'Modern, professional'}

The image should:
- Be visually striking and scroll-stopping
- Work well on social media (clean, not too busy)
- Convey the message clearly
- Be professional and high-quality

Return only the image generation prompt (no explanations):"""

        try:
            response = await self.openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt_request}],
                max_tokens=300,
                temperature=0.7
            )
            
            image_prompt = response.choices[0].message.content.strip()
            
            # Generate images (using content generator)
            for i in range(min(project.num_variations, 3)):
                try:
                    # Add variation to prompt
                    varied_prompt = f"{image_prompt}, variation {i+1}, unique composition"
                    
                    result = await self.content_generator.generate_image(
                        prompt=varied_prompt,
                        style="professional"
                    )
                    
                    if result.get("image_url"):
                        asset = StudioAsset(
                            project_id=project.id,
                            content_type=ContentType.IMAGE,
                            media_url=result["image_url"],
                            variation_number=i + 1,
                            ai_model_used=result.get("model", "flux"),
                            prompt_used=varied_prompt,
                            cost_usd=0.02
                        )
                        self.db.add(asset)
                        project.images_generated += 1
                        cost += 0.02
                        
                except Exception as e:
                    logger.error(f"Image {i+1} generation failed: {e}")
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Image prompt generation failed: {e}")
        
        return cost
    
    async def _generate_video(self, project: StudioProject, brand_voice: str) -> float:
        """Generate a talking head video."""
        
        # First, generate video script
        duration_map = {"15s": 15, "30s": 30, "60s": 60, "90s": 90}
        duration_seconds = duration_map.get(project.video_duration, 30)
        word_count = duration_seconds * 2.5  # ~150 words per minute
        
        script_prompt = f"""Write a {project.video_duration} video script ({int(word_count)} words max).

Topic: {project.brief}
Brand Voice: {brand_voice or 'Professional and engaging'}

Structure:
- Hook (first 3 seconds) - grab attention immediately
- Main content - deliver value
- Call-to-action - tell viewers what to do next

The script should be conversational, as if speaking directly to the viewer.
Return only the script (no stage directions or notes):"""

        try:
            response = await self.openai.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": script_prompt}],
                max_tokens=500,
                temperature=0.7
            )
            
            script = response.choices[0].message.content.strip()
            
            # Generate video using video service
            video_service = VideoGenerationService(self.db)
            
            video = await video_service.generate_video(
                user_id=project.user_id,
                script=script,
                lora_model_id=project.lora_model_id,
                title=f"Studio: {project.name}",
                brand_id=project.brand_id
            )
            
            # Create asset reference
            asset = StudioAsset(
                project_id=project.id,
                content_type=ContentType.VIDEO,
                text_content=script,
                media_url=video.video_url,  # Will be populated when video completes
                ai_model_used="sadtalker",
                prompt_used=script_prompt,
                generation_params={"video_id": video.id},
                cost_usd=video.total_cost_usd
            )
            self.db.add(asset)
            project.videos_generated += 1
            self.db.commit()
            
            return video.total_cost_usd
            
        except Exception as e:
            logger.error(f"Video generation failed: {e}")
            return 0.0
    
    async def _create_platform_versions(self, project: StudioProject):
        """Create platform-optimized versions of captions."""
        
        # Get all captions
        captions = self.db.query(StudioAsset).filter(
            StudioAsset.project_id == project.id,
            StudioAsset.content_type == ContentType.CAPTION
        ).all()
        
        for caption in captions:
            if not caption.text_content:
                continue
            
            platform_spec = PLATFORM_SPECS.get(caption.platform, {})
            
            # Check if caption needs shortening
            if len(caption.text_content) > platform_spec.get('max_chars', 2200):
                # Shorten caption
                try:
                    response = await self.openai.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{
                            "role": "user",
                            "content": f"Shorten this caption to under {platform_spec['max_chars']} characters while keeping the key message and CTA:\n\n{caption.text_content}"
                        }],
                        max_tokens=500
                    )
                    
                    caption.platform_optimized = {
                        "shortened": response.choices[0].message.content.strip(),
                        "original_length": len(caption.text_content),
                        "new_length": len(response.choices[0].message.content.strip())
                    }
                    
                except Exception as e:
                    logger.error(f"Caption shortening failed: {e}")
        
        self.db.commit()
    
    # ==================== Helper Methods ====================
    
    def _parse_numbered_list(self, text: str) -> List[str]:
        """Parse a numbered list from AI response."""
        import re
        
        # Try to split by numbered patterns (1., 2., etc.)
        parts = re.split(r'\n\d+[\.\)]\s*', text)
        
        # Filter out empty parts
        items = [p.strip() for p in parts if p.strip()]
        
        # If that didn't work well, try splitting by double newlines
        if len(items) <= 1:
            items = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        # Last resort: split by single newlines
        if len(items) <= 1:
            items = [p.strip() for p in text.split('\n') if p.strip() and len(p.strip()) > 20]
        
        return items
    
    # ==================== Project Retrieval ====================
    
    def get_project(self, project_id: int, user_id: int) -> Optional[StudioProject]:
        """Get project with assets."""
        return self.db.query(StudioProject).filter(
            StudioProject.id == project_id,
            StudioProject.user_id == user_id
        ).first()
    
    def list_projects(
        self,
        user_id: int,
        status: Optional[StudioProjectStatus] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[StudioProject], int]:
        """List user's projects."""
        query = self.db.query(StudioProject).filter(
            StudioProject.user_id == user_id
        )
        
        if status:
            query = query.filter(StudioProject.status == status)
        
        total = query.count()
        projects = query.order_by(StudioProject.created_at.desc()).offset(skip).limit(limit).all()
        
        return projects, total
    
    def get_project_assets(
        self,
        project_id: int,
        user_id: int,
        content_type: Optional[ContentType] = None,
        platform: Optional[str] = None
    ) -> List[StudioAsset]:
        """Get assets for a project."""
        project = self.get_project(project_id, user_id)
        if not project:
            return []
        
        query = self.db.query(StudioAsset).filter(StudioAsset.project_id == project_id)
        
        if content_type:
            query = query.filter(StudioAsset.content_type == content_type)
        if platform:
            query = query.filter(StudioAsset.platform == platform)
        
        return query.all()
    
    def update_asset(self, asset_id: int, user_id: int, **kwargs) -> Optional[StudioAsset]:
        """Update asset (favorite, rating, etc.)"""
        asset = self.db.query(StudioAsset).join(StudioProject).filter(
            StudioAsset.id == asset_id,
            StudioProject.user_id == user_id
        ).first()
        
        if not asset:
            return None
        
        for key, value in kwargs.items():
            if hasattr(asset, key):
                setattr(asset, key, value)
        
        self.db.commit()
        self.db.refresh(asset)
        return asset
    
    def delete_project(self, project_id: int, user_id: int) -> bool:
        """Delete a project and all its assets."""
        project = self.get_project(project_id, user_id)
        if not project:
            return False
        
        self.db.delete(project)
        self.db.commit()
        return True


def get_studio_service(db: Session) -> ContentStudioService:
    return ContentStudioService(db)

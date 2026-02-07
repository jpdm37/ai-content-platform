"""
Content Generation Service
Handles AI image and text generation using OpenAI and Replicate
"""
import logging
from typing import Optional, List
from datetime import datetime
import replicate
from openai import OpenAI
from sqlalchemy.orm import Session

from app.models import (
    Brand, Category, Trend, GeneratedContent, 
    ContentType, ContentStatus
)
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ContentGeneratorService:
    """Service for generating AI content"""
    
    def __init__(self, db: Session, openai_api_key: str = None, replicate_api_token: str = None):
        self.db = db
        self.openai_api_key = openai_api_key
        self.replicate_api_token = replicate_api_token
        self.openai_client = OpenAI(api_key=openai_api_key) if openai_api_key else None
    
    async def generate_avatar_image(
        self,
        brand: Brand,
        user_id: int,
        custom_prompt: Optional[str] = None
    ) -> GeneratedContent:
        """Generate an AI avatar image for a brand"""
        prompt = custom_prompt or self._build_avatar_prompt(brand)
        
        content = GeneratedContent(
            user_id=user_id,
            brand_id=brand.id,
            content_type=ContentType.IMAGE,
            status=ContentStatus.GENERATING,
            prompt_used=prompt
        )
        self.db.add(content)
        self.db.commit()
        
        try:
            image_url = await self._generate_image(prompt)
            brand.reference_image_url = image_url
            content.result_url = image_url
            content.status = ContentStatus.COMPLETED
            content.completed_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(content)
            return content
        except Exception as e:
            logger.error(f"Error generating avatar: {e}")
            content.status = ContentStatus.FAILED
            content.error_message = str(e)
            self.db.commit()
            raise
    
    async def generate_content(
        self,
        brand: Brand,
        user_id: int,
        content_type: ContentType,
        category: Optional[Category] = None,
        trend: Optional[Trend] = None,
        custom_prompt: Optional[str] = None,
        include_caption: bool = True
    ) -> GeneratedContent:
        """Generate content (image/text) for a brand"""
        content = GeneratedContent(
            user_id=user_id,
            brand_id=brand.id,
            category_id=category.id if category else None,
            trend_id=trend.id if trend else None,
            content_type=content_type,
            status=ContentStatus.GENERATING
        )
        self.db.add(content)
        self.db.commit()
        
        try:
            if content_type == ContentType.IMAGE:
                prompt = custom_prompt or self._build_image_prompt(brand, category, trend)
                content.prompt_used = prompt
                image_url = await self._generate_image(prompt)
                content.result_url = image_url
                
                if include_caption and self.openai_client:
                    caption, hashtags = await self._generate_caption(brand, category, trend, prompt)
                    content.caption = caption
                    content.hashtags = hashtags
                    
            elif content_type == ContentType.TEXT:
                prompt = custom_prompt or self._build_caption_prompt(brand, category, trend)
                content.prompt_used = prompt
                
                if self.openai_client:
                    caption, hashtags = await self._generate_caption(brand, category, trend)
                    content.caption = caption
                    content.hashtags = hashtags
                else:
                    raise ValueError("OpenAI API key required for text generation")
            
            content.status = ContentStatus.COMPLETED
            content.completed_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(content)
            return content
            
        except Exception as e:
            logger.error(f"Error generating content: {e}")
            content.status = ContentStatus.FAILED
            content.error_message = str(e)
            self.db.commit()
            raise
    
    def _build_avatar_prompt(self, brand: Brand) -> str:
        """Build a prompt for avatar generation"""
        parts = ["Professional portrait photo of"]
        
        if brand.persona_gender:
            parts.append(f"a {brand.persona_gender}")
        else:
            parts.append("a person")
            
        if brand.persona_age:
            parts.append(f"in their {brand.persona_age}")
        
        if brand.persona_style:
            parts.append(f", {brand.persona_style}")
        else:
            parts.append(", modern and stylish appearance")
        
        if brand.persona_traits:
            traits = ", ".join(brand.persona_traits[:3])
            parts.append(f", looking {traits}")
        
        parts.append(". High quality, professional photography, studio lighting, social media influencer style.")
        
        return " ".join(parts)
    
    def _build_image_prompt(
        self,
        brand: Brand,
        category: Optional[Category],
        trend: Optional[Trend]
    ) -> str:
        """Build a prompt for content image generation"""
        parts = []
        
        if brand.persona_style:
            parts.append(f"Photo featuring a {brand.persona_style} influencer")
        else:
            parts.append("Photo featuring a stylish social media influencer")
        
        if category:
            if category.image_prompt_template:
                parts.append(category.image_prompt_template)
            else:
                parts.append(f"in a {category.name.lower()} setting")
        
        if trend:
            parts.append(f"related to {trend.title}")
        
        if brand.brand_keywords:
            keywords = ", ".join(brand.brand_keywords[:3])
            parts.append(f"featuring elements of {keywords}")
        
        parts.append("Professional photography, Instagram-worthy, high quality, trending aesthetic, perfect for social media.")
        
        return " ".join(parts)
    
    def _build_caption_prompt(
        self,
        brand: Brand,
        category: Optional[Category],
        trend: Optional[Trend]
    ) -> str:
        """Build a prompt for caption generation"""
        return f"""
        Brand: {brand.name}
        Persona voice: {brand.persona_voice or 'friendly and engaging'}
        Category: {category.name if category else 'general'}
        Trend: {trend.title if trend else 'general content'}
        """
    
    async def _generate_image(self, prompt: str, priority: str = "balanced") -> str:
        """Generate an image using Replicate with cost-optimized model selection."""
        if not self.replicate_api_token:
            raise ValueError("Replicate API token not configured")
        
        try:
            import os
            original_token = os.environ.get("REPLICATE_API_TOKEN")
            os.environ["REPLICATE_API_TOKEN"] = self.replicate_api_token
            
            # Use SDXL-Lightning for speed and cost (33% cheaper, 7x faster)
            # Only use full SDXL for LoRA models
            if priority == "quality":
                model = settings.replicate_image_model  # Full SDXL or Flux
                params = {
                    "prompt": prompt,
                    "width": settings.default_image_width,
                    "height": settings.default_image_height,
                    "num_outputs": 1,
                    "guidance_scale": 7.5,
                    "num_inference_steps": 30,
                }
            else:
                # SDXL-Lightning: 4-step generation
                model = "bytedance/sdxl-lightning-4step:5599ed30703defd1d160a25a63321b4dec97101d98b4674bcc56e41f62f35637"
                params = {
                    "prompt": prompt,
                    "width": settings.default_image_width,
                    "height": settings.default_image_height,
                    "num_outputs": 1,
                    "num_inference_steps": 4,  # Lightning uses only 4 steps
                    "scheduler": "K_EULER",
                }
            
            output = replicate.run(model, input=params)
            
            # Restore original token
            if original_token:
                os.environ["REPLICATE_API_TOKEN"] = original_token
            elif "REPLICATE_API_TOKEN" in os.environ:
                del os.environ["REPLICATE_API_TOKEN"]
            
            if output and len(output) > 0:
                return output[0]
            else:
                raise ValueError("No image generated")
                
        except Exception as e:
            logger.error(f"Replicate error: {e}")
            raise
    
    async def _generate_caption(
        self,
        brand: Brand,
        category: Optional[Category] = None,
        trend: Optional[Trend] = None,
        image_prompt: Optional[str] = None
    ) -> tuple[str, List[str]]:
        """Generate a caption and hashtags using OpenAI"""
        
        if not self.openai_client:
            raise ValueError("OpenAI API key not configured")
        
        # Use cost-optimized model selection
        # gpt-4o-mini is 20x cheaper than gpt-4o and sufficient for captions
        model = "gpt-4o-mini"
        
        system_prompt = """You are a social media content creator. Generate engaging captions 
        for Instagram/TikTok posts. The caption should be:
        - Engaging and on-brand
        - Include a call to action
        - Be appropriate for the category/trend
        - Match the brand's voice and personality
        
        Also generate 5-10 relevant hashtags.
        
        Respond in JSON format:
        {
            "caption": "Your caption here",
            "hashtags": ["hashtag1", "hashtag2", ...]
        }"""
        
        user_prompt = f"""
Brand: {brand.name}
Brand Description: {brand.description or 'N/A'}
Persona Name: {brand.persona_name or 'N/A'}
Persona Voice: {brand.persona_voice or 'friendly and engaging'}
Category: {category.name if category else 'general'}
Trend Topic: {trend.title if trend else 'general content'}
Image Description: {image_prompt or 'lifestyle photo'}
Brand Keywords: {', '.join(brand.brand_keywords) if brand.brand_keywords else 'N/A'}

Generate an engaging social media caption and hashtags."""
        
        try:
            response = self.openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.8,
                max_tokens=500  # Captions don't need many tokens
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            
            return result.get("caption", ""), result.get("hashtags", [])
            
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            raise


async def get_content_generator(db: Session) -> ContentGeneratorService:
    """Factory function for ContentGeneratorService"""
    return ContentGeneratorService(
        db, 
        settings.openai_api_key, 
        settings.replicate_api_token
    )


# Alias for compatibility
ContentGenerator = ContentGeneratorService

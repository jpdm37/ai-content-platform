"""
Brand Voice AI Service

Analyzes example content to learn a brand's unique writing style
and generates content that matches that voice.
"""
import logging
import json
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from openai import AsyncOpenAI

from app.core.config import get_settings
from app.brandvoice.models import (
    BrandVoice, VoiceExample, VoiceGeneration,
    VOICE_ANALYSIS_PROMPT, VOICE_PROMPT_TEMPLATE
)
from app.models.models import Brand

logger = logging.getLogger(__name__)
settings = get_settings()


class BrandVoiceService:
    """
    Service for training and using brand voice profiles.
    
    Flow:
    1. User adds example content (10-20 pieces)
    2. System analyzes examples to extract style characteristics
    3. System generates a voice prompt for content generation
    4. User generates content using the trained voice
    5. User provides feedback to improve the voice
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.openai = AsyncOpenAI(api_key=settings.openai_api_key)
    
    # ==================== Voice Profile Management ====================
    
    def get_or_create_voice(self, brand_id: int) -> BrandVoice:
        """Get existing voice profile or create a new one."""
        voice = self.db.query(BrandVoice).filter(BrandVoice.brand_id == brand_id).first()
        
        if not voice:
            voice = BrandVoice(brand_id=brand_id)
            self.db.add(voice)
            self.db.commit()
            self.db.refresh(voice)
        
        return voice
    
    def get_voice(self, brand_id: int) -> Optional[BrandVoice]:
        """Get voice profile for a brand."""
        return self.db.query(BrandVoice).filter(BrandVoice.brand_id == brand_id).first()
    
    # ==================== Training Examples ====================
    
    def add_example(
        self,
        brand_id: int,
        content: str,
        content_type: Optional[str] = None,
        platform: Optional[str] = None
    ) -> VoiceExample:
        """Add a training example for voice analysis."""
        voice = self.get_or_create_voice(brand_id)
        
        # Basic content analysis
        analysis = self._analyze_single_example(content)
        
        example = VoiceExample(
            brand_voice_id=voice.id,
            content=content,
            content_type=content_type,
            platform=platform,
            analysis=analysis
        )
        
        self.db.add(example)
        voice.example_count += 1
        
        # Mark voice as needing retraining
        if voice.is_trained:
            voice.training_status = "pending"
        
        self.db.commit()
        self.db.refresh(example)
        
        return example
    
    def add_examples_bulk(
        self,
        brand_id: int,
        examples: List[Dict[str, Any]]
    ) -> List[VoiceExample]:
        """Add multiple training examples at once."""
        added = []
        for ex in examples:
            example = self.add_example(
                brand_id=brand_id,
                content=ex["content"],
                content_type=ex.get("content_type"),
                platform=ex.get("platform")
            )
            added.append(example)
        return added
    
    def get_examples(self, brand_id: int) -> List[VoiceExample]:
        """Get all training examples for a brand."""
        voice = self.get_voice(brand_id)
        if not voice:
            return []
        return self.db.query(VoiceExample).filter(
            VoiceExample.brand_voice_id == voice.id,
            VoiceExample.is_high_quality == True
        ).all()
    
    def remove_example(self, example_id: int, brand_id: int) -> bool:
        """Remove a training example."""
        voice = self.get_voice(brand_id)
        if not voice:
            return False
        
        example = self.db.query(VoiceExample).filter(
            VoiceExample.id == example_id,
            VoiceExample.brand_voice_id == voice.id
        ).first()
        
        if not example:
            return False
        
        self.db.delete(example)
        voice.example_count = max(0, voice.example_count - 1)
        voice.training_status = "pending"
        self.db.commit()
        
        return True
    
    def _analyze_single_example(self, content: str) -> Dict[str, Any]:
        """Analyze a single piece of content."""
        import re
        
        words = content.split()
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return {
            "word_count": len(words),
            "char_count": len(content),
            "sentence_count": len(sentences),
            "avg_sentence_length": len(words) / max(len(sentences), 1),
            "emoji_count": len(re.findall(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]', content)),
            "hashtag_count": len(re.findall(r'#\w+', content)),
            "question_count": content.count('?'),
            "exclamation_count": content.count('!'),
            "has_cta": any(cta in content.lower() for cta in ['click', 'learn more', 'sign up', 'subscribe', 'follow', 'share', 'comment', 'check out']),
            "starts_with_question": content.strip().endswith('?') if sentences else False,
        }
    
    # ==================== Voice Training ====================
    
    async def train_voice(self, brand_id: int) -> BrandVoice:
        """
        Train the brand voice by analyzing all examples.
        
        This:
        1. Collects all training examples
        2. Uses GPT-4 to analyze patterns
        3. Extracts style characteristics
        4. Generates a voice prompt for future use
        """
        voice = self.get_or_create_voice(brand_id)
        examples = self.get_examples(brand_id)
        
        if len(examples) < 5:
            raise ValueError(f"Need at least 5 examples to train voice (have {len(examples)})")
        
        voice.training_status = "training"
        self.db.commit()
        
        try:
            # Get brand info
            brand = self.db.query(Brand).filter(Brand.id == brand_id).first()
            brand_name = brand.name if brand else "Brand"
            
            # Prepare examples for analysis
            example_texts = "\n\n---\n\n".join([
                f"Example {i+1} ({ex.platform or 'general'}):\n{ex.content}"
                for i, ex in enumerate(examples[:20])  # Max 20 examples
            ])
            
            # Analyze with GPT-4
            analysis_prompt = VOICE_ANALYSIS_PROMPT.format(examples=example_texts)
            
            response = await self.openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing writing styles. Return valid JSON only."},
                    {"role": "user", "content": analysis_prompt}
                ],
                max_tokens=2000,
                temperature=0.3
            )
            
            # Parse characteristics
            content = response.choices[0].message.content
            # Clean up potential markdown formatting
            content = content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            characteristics = json.loads(content)
            voice.characteristics = characteristics
            
            # Generate voice prompt
            voice_prompt = self._generate_voice_prompt(brand_name, characteristics)
            voice.voice_prompt = voice_prompt
            
            # Update status
            voice.is_trained = True
            voice.training_status = "completed"
            voice.trained_at = datetime.utcnow()
            
            # Store example texts for reference
            voice.training_examples = [ex.content for ex in examples[:20]]
            
            self.db.commit()
            self.db.refresh(voice)
            
            logger.info(f"Brand voice trained successfully for brand {brand_id}")
            return voice
            
        except Exception as e:
            logger.error(f"Voice training failed for brand {brand_id}: {e}")
            voice.training_status = "failed"
            self.db.commit()
            raise
    
    def _generate_voice_prompt(self, brand_name: str, characteristics: Dict) -> str:
        """Generate the system prompt for content generation."""
        
        patterns = characteristics.get("unique_elements", [])
        if characteristics.get("opening_patterns"):
            patterns.append(f"Opening: {characteristics['opening_patterns']}")
        if characteristics.get("closing_patterns"):
            patterns.append(f"Closing: {characteristics['closing_patterns']}")
        
        prompt = VOICE_PROMPT_TEMPLATE.format(
            brand_name=brand_name,
            tone=characteristics.get("overall_tone", "professional"),
            formality=characteristics.get("formality_level", "semi-formal"),
            sentence_style=characteristics.get("sentence_structure", "varied"),
            vocabulary=characteristics.get("vocabulary_complexity", "intermediate"),
            emoji_usage=characteristics.get("emoji_usage", "minimal"),
            patterns="\n".join(f"- {p}" for p in patterns) if patterns else "- Natural, authentic voice",
            phrases=", ".join(characteristics.get("common_phrases", [])) or "Use natural language",
            avoid=", ".join(characteristics.get("avoid_patterns", [])) or "Nothing specific",
            strength="{strength}"  # Placeholder to be filled at generation time
        )
        
        return prompt
    
    # ==================== Content Generation ====================
    
    async def generate_content(
        self,
        brand_id: int,
        prompt: str,
        content_type: str = "social_post",
        platform: Optional[str] = None,
        voice_strength: float = 0.8,
        max_length: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate content using the trained brand voice.
        
        Args:
            brand_id: Brand to use voice from
            prompt: What to generate (topic/brief)
            content_type: Type of content (social_post, blog, email, etc.)
            platform: Target platform (twitter, instagram, etc.)
            voice_strength: How strongly to apply voice (0-1)
            max_length: Maximum character length
        
        Returns:
            Dict with generated content and metadata
        """
        voice = self.get_voice(brand_id)
        
        if not voice or not voice.is_trained:
            raise ValueError("Brand voice not trained. Add examples and train first.")
        
        # Build the generation prompt
        voice_prompt = voice.voice_prompt.format(strength=int(voice_strength * 100))
        
        platform_context = ""
        if platform:
            from app.studio.models import PLATFORM_SPECS
            specs = PLATFORM_SPECS.get(platform, {})
            if specs:
                platform_context = f"\nPlatform: {platform} (max {specs.get('max_chars', 2200)} chars)"
        
        length_context = ""
        if max_length:
            length_context = f"\nMaximum length: {max_length} characters"
        
        full_prompt = f"""{voice_prompt}

Content Type: {content_type}{platform_context}{length_context}

Generate content for: {prompt}

Remember to match the brand voice characteristics. The content should feel authentic to this brand."""

        try:
            response = await self.openai.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": full_prompt}],
                max_tokens=1500,
                temperature=0.7 + (0.2 * (1 - voice_strength))  # More creative with lower strength
            )
            
            generated_content = response.choices[0].message.content.strip()
            
            # Track generation
            generation = VoiceGeneration(
                brand_voice_id=voice.id,
                user_id=voice.brand.user_id,
                prompt=prompt,
                generated_content=generated_content,
                voice_strength=voice_strength
            )
            self.db.add(generation)
            
            # Update usage
            voice.times_used += 1
            voice.last_used_at = datetime.utcnow()
            self.db.commit()
            
            return {
                "content": generated_content,
                "voice_strength": voice_strength,
                "content_type": content_type,
                "platform": platform,
                "generation_id": generation.id,
                "characteristics_applied": list(voice.characteristics.keys()) if voice.characteristics else []
            }
            
        except Exception as e:
            logger.error(f"Voice generation failed: {e}")
            raise
    
    async def generate_variations(
        self,
        brand_id: int,
        prompt: str,
        num_variations: int = 3,
        platform: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Generate multiple content variations using brand voice."""
        variations = []
        
        for i in range(num_variations):
            try:
                result = await self.generate_content(
                    brand_id=brand_id,
                    prompt=f"{prompt} (variation {i+1}, make it unique)",
                    platform=platform,
                    voice_strength=0.8
                )
                variations.append(result)
            except Exception as e:
                logger.error(f"Variation {i+1} generation failed: {e}")
        
        return variations
    
    # ==================== Feedback & Improvement ====================
    
    def record_feedback(
        self,
        generation_id: int,
        user_id: int,
        rating: int,
        voice_match_score: Optional[int] = None,
        notes: Optional[str] = None
    ) -> VoiceGeneration:
        """Record user feedback on generated content."""
        generation = self.db.query(VoiceGeneration).filter(
            VoiceGeneration.id == generation_id,
            VoiceGeneration.user_id == user_id
        ).first()
        
        if not generation:
            raise ValueError("Generation not found")
        
        generation.user_rating = rating
        generation.voice_match_score = voice_match_score
        generation.feedback_notes = notes
        
        # Update voice satisfaction average
        voice = generation.brand_voice
        all_ratings = self.db.query(VoiceGeneration).filter(
            VoiceGeneration.brand_voice_id == voice.id,
            VoiceGeneration.user_rating.isnot(None)
        ).all()
        
        if all_ratings:
            voice.user_satisfaction_avg = sum(g.user_rating for g in all_ratings) / len(all_ratings)
        
        self.db.commit()
        self.db.refresh(generation)
        
        return generation
    
    # ==================== Voice Stats ====================
    
    def get_voice_stats(self, brand_id: int) -> Dict[str, Any]:
        """Get statistics about a brand voice."""
        voice = self.get_voice(brand_id)
        
        if not voice:
            return {"trained": False, "example_count": 0}
        
        generations = self.db.query(VoiceGeneration).filter(
            VoiceGeneration.brand_voice_id == voice.id
        ).all()
        
        rated_generations = [g for g in generations if g.user_rating]
        
        return {
            "trained": voice.is_trained,
            "training_status": voice.training_status,
            "example_count": voice.example_count,
            "times_used": voice.times_used,
            "last_used_at": voice.last_used_at.isoformat() if voice.last_used_at else None,
            "trained_at": voice.trained_at.isoformat() if voice.trained_at else None,
            "avg_satisfaction": voice.user_satisfaction_avg,
            "total_generations": len(generations),
            "rated_generations": len(rated_generations),
            "characteristics": voice.characteristics
        }


def get_brand_voice_service(db: Session) -> BrandVoiceService:
    return BrandVoiceService(db)

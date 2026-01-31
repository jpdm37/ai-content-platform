"""
AI Assistant Chat Service

Context-aware AI assistant for content creation help.
Features:
- Content improvement suggestions
- Rewriting and variations
- Translation
- Hashtag suggestions
- Platform optimization
- Brand voice guidance
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from openai import AsyncOpenAI

from app.core.config import get_settings
from app.models.models import Brand, GeneratedContent
from app.brandvoice.models import BrandVoice

logger = logging.getLogger(__name__)
settings = get_settings()


class AIAssistantService:
    """
    AI Assistant for interactive content creation help.
    """
    
    SYSTEM_PROMPT = """You are a helpful AI assistant specialized in social media content creation.
You help users:
- Write and improve captions and posts
- Generate hashtags
- Optimize content for different platforms
- Translate content
- Rewrite in different tones
- Provide content strategy advice

Be concise, helpful, and creative. When appropriate, provide multiple options.
If the user has a brand context, keep suggestions aligned with their brand voice."""

    def __init__(self, db: Session):
        self.db = db
        self.openai = AsyncOpenAI(api_key=settings.openai_api_key)
    
    async def chat(
        self,
        user_id: int,
        message: str,
        conversation_history: Optional[List[Dict]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a chat message and return AI response.
        
        Args:
            user_id: User ID
            message: User's message
            conversation_history: Previous messages in conversation
            context: Optional context (current content, brand, etc.)
        
        Returns:
            Dict with response and any suggested actions
        """
        # Build context-aware system prompt
        system_prompt = self._build_system_prompt(user_id, context)
        
        # Build messages
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history
        if conversation_history:
            for msg in conversation_history[-10:]:  # Last 10 messages
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        try:
            response = await self.openai.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=1500,
                temperature=0.7
            )
            
            assistant_message = response.choices[0].message.content
            
            # Detect suggested actions
            actions = self._detect_actions(message, assistant_message)
            
            return {
                "response": assistant_message,
                "actions": actions,
                "tokens_used": response.usage.total_tokens if response.usage else 0
            }
            
        except Exception as e:
            logger.error(f"Assistant chat error: {e}")
            return {
                "response": "I'm sorry, I encountered an error. Please try again.",
                "error": str(e)
            }
    
    def _build_system_prompt(self, user_id: int, context: Optional[Dict] = None) -> str:
        """Build context-aware system prompt."""
        prompt = self.SYSTEM_PROMPT
        
        # Add brand context if available
        if context and context.get("brand_id"):
            brand = self.db.query(Brand).filter(
                Brand.id == context["brand_id"],
                Brand.user_id == user_id
            ).first()
            
            if brand:
                prompt += f"\n\nUser's Brand: {brand.name}"
                if brand.description:
                    prompt += f"\nBrand Description: {brand.description}"
                
                # Check for trained voice
                voice = self.db.query(BrandVoice).filter(
                    BrandVoice.brand_id == brand.id,
                    BrandVoice.is_trained == True
                ).first()
                
                if voice and voice.characteristics:
                    prompt += f"\nBrand Voice Characteristics: {voice.characteristics.get('overall_tone', 'professional')}"
        
        # Add current content context
        if context and context.get("current_content"):
            prompt += f"\n\nUser is currently working on this content:\n{context['current_content'][:500]}"
        
        # Add platform context
        if context and context.get("platform"):
            prompt += f"\n\nTarget Platform: {context['platform']}"
        
        return prompt
    
    def _detect_actions(self, user_message: str, response: str) -> List[Dict[str, Any]]:
        """Detect suggested actions from conversation."""
        actions = []
        
        lower_msg = user_message.lower()
        
        # Detect hashtag suggestions
        if "hashtag" in lower_msg:
            actions.append({
                "type": "copy_hashtags",
                "label": "Copy hashtags"
            })
        
        # Detect content that could be saved
        if any(word in lower_msg for word in ["write", "create", "generate", "rewrite"]):
            actions.append({
                "type": "save_as_draft",
                "label": "Save as draft"
            })
        
        # Detect translation
        if "translate" in lower_msg:
            actions.append({
                "type": "use_translation",
                "label": "Use translation"
            })
        
        return actions
    
    # ==================== Quick Actions ====================
    
    async def improve_content(self, content: str, improvement_type: str = "general") -> str:
        """Quickly improve content."""
        prompts = {
            "general": f"Improve this content to be more engaging:\n\n{content}",
            "shorter": f"Make this content shorter while keeping the key message:\n\n{content}",
            "longer": f"Expand this content with more detail:\n\n{content}",
            "engaging": f"Make this content more engaging and scroll-stopping:\n\n{content}",
            "professional": f"Make this content more professional:\n\n{content}",
            "casual": f"Make this content more casual and friendly:\n\n{content}",
        }
        
        prompt = prompts.get(improvement_type, prompts["general"])
        
        response = await self.openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.7
        )
        
        return response.choices[0].message.content
    
    async def generate_hashtags(self, content: str, platform: str = "instagram", count: int = 10) -> List[str]:
        """Generate hashtags for content."""
        response = await self.openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": f"Generate {count} relevant hashtags for {platform}. Mix popular and niche. Content:\n\n{content}\n\nReturn only hashtags, one per line."
            }],
            max_tokens=300,
            temperature=0.7
        )
        
        text = response.choices[0].message.content
        hashtags = [h.strip() for h in text.split('\n') if h.strip().startswith('#')]
        return hashtags[:count]
    
    async def translate_content(self, content: str, target_language: str) -> str:
        """Translate content to target language."""
        response = await self.openai.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": f"Translate this social media content to {target_language}. Keep the tone and style:\n\n{content}"
            }],
            max_tokens=1000,
            temperature=0.3
        )
        
        return response.choices[0].message.content
    
    async def generate_variations(self, content: str, count: int = 3) -> List[str]:
        """Generate content variations."""
        response = await self.openai.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": f"Create {count} unique variations of this content. Each should have a different angle or style but convey the same message:\n\n{content}\n\nNumber each variation."
            }],
            max_tokens=1500,
            temperature=0.8
        )
        
        text = response.choices[0].message.content
        import re
        variations = re.split(r'\n\d+[\.\)]\s*', text)
        return [v.strip() for v in variations if v.strip()][:count]
    
    async def optimize_for_platform(self, content: str, platform: str) -> Dict[str, Any]:
        """Optimize content for specific platform."""
        platform_limits = {
            "twitter": 280,
            "instagram": 2200,
            "linkedin": 3000,
            "tiktok": 2200,
            "facebook": 63206
        }
        
        char_limit = platform_limits.get(platform, 2200)
        
        response = await self.openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": f"""Optimize this content for {platform} (max {char_limit} chars).
Consider {platform}'s best practices for engagement.

Original content:
{content}

Provide the optimized version only."""
            }],
            max_tokens=1000,
            temperature=0.6
        )
        
        optimized = response.choices[0].message.content.strip()
        
        return {
            "original": content,
            "optimized": optimized,
            "platform": platform,
            "original_length": len(content),
            "optimized_length": len(optimized),
            "within_limit": len(optimized) <= char_limit
        }
    
    async def suggest_cta(self, content: str, goal: str = "engagement") -> List[str]:
        """Suggest call-to-action options."""
        response = await self.openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": f"""Suggest 5 call-to-action phrases for this content.
Goal: {goal}
Content: {content}

Return only the CTAs, one per line."""
            }],
            max_tokens=300,
            temperature=0.8
        )
        
        text = response.choices[0].message.content
        ctas = [line.strip().strip('-').strip() for line in text.split('\n') if line.strip()]
        return ctas[:5]


def get_assistant_service(db: Session) -> AIAssistantService:
    return AIAssistantService(db)

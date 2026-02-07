"""
Onboarding Service
==================

Guides new users through initial setup to achieve "aha moment" quickly.

Flow:
1. Welcome & goal selection
2. Create first brand (simplified)
3. Generate first content automatically
4. Prompt social connection
5. Schedule first post (optional)

Tracks onboarding progress and sends appropriate nudges.
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.core.config import get_settings
from app.models.user import User
from app.models.models import Brand, GeneratedContent, Category

logger = logging.getLogger(__name__)
settings = get_settings()


# ==================== Onboarding Steps ====================

ONBOARDING_STEPS = [
    {
        "id": "welcome",
        "name": "Welcome",
        "description": "Get started with the platform",
        "required": True,
        "order": 1
    },
    {
        "id": "select_goal",
        "name": "Select Your Goal",
        "description": "Tell us what you want to achieve",
        "required": True,
        "order": 2
    },
    {
        "id": "create_brand",
        "name": "Create Your Brand",
        "description": "Set up your first brand or persona",
        "required": True,
        "order": 3
    },
    {
        "id": "first_content",
        "name": "Generate Content",
        "description": "Create your first AI-powered content",
        "required": True,
        "order": 4
    },
    {
        "id": "connect_social",
        "name": "Connect Social",
        "description": "Link your social media accounts",
        "required": False,
        "order": 5
    },
    {
        "id": "schedule_post",
        "name": "Schedule Post",
        "description": "Schedule your first post",
        "required": False,
        "order": 6
    },
    {
        "id": "complete",
        "name": "All Done!",
        "description": "You're ready to create amazing content",
        "required": True,
        "order": 7
    }
]

# User goals for personalization
USER_GOALS = [
    {
        "id": "personal_brand",
        "name": "Build My Personal Brand",
        "description": "Grow your online presence and audience",
        "icon": "user",
        "suggested_categories": ["lifestyle", "motivation", "personal"]
    },
    {
        "id": "business_marketing",
        "name": "Market My Business",
        "description": "Promote products or services",
        "icon": "briefcase",
        "suggested_categories": ["business", "product", "promotion"]
    },
    {
        "id": "content_creator",
        "name": "Create Content Faster",
        "description": "Speed up your content workflow",
        "icon": "zap",
        "suggested_categories": ["entertainment", "education", "lifestyle"]
    },
    {
        "id": "agency",
        "name": "Manage Client Accounts",
        "description": "Handle multiple brands efficiently",
        "icon": "users",
        "suggested_categories": ["business", "lifestyle", "promotion"]
    },
    {
        "id": "side_hustle",
        "name": "Start a Side Hustle",
        "description": "Build an online income stream",
        "icon": "dollar-sign",
        "suggested_categories": ["business", "lifestyle", "motivation"]
    }
]

# Quick-start brand templates
BRAND_TEMPLATES = [
    {
        "id": "personal_influencer",
        "name": "Personal Influencer",
        "description": "Share your life, thoughts, and expertise",
        "persona_voice": "authentic, relatable, and inspiring",
        "persona_style": "casual yet professional",
        "brand_keywords": ["lifestyle", "inspiration", "authentic"],
        "goals": ["personal_brand", "content_creator"]
    },
    {
        "id": "business_professional",
        "name": "Business Professional",
        "description": "Establish thought leadership in your industry",
        "persona_voice": "knowledgeable, helpful, and professional",
        "persona_style": "polished and authoritative",
        "brand_keywords": ["expertise", "industry", "professional"],
        "goals": ["business_marketing", "personal_brand"]
    },
    {
        "id": "ecommerce_brand",
        "name": "E-commerce Brand",
        "description": "Showcase products and drive sales",
        "persona_voice": "friendly, enthusiastic, and helpful",
        "persona_style": "vibrant and product-focused",
        "brand_keywords": ["products", "deals", "lifestyle"],
        "goals": ["business_marketing", "side_hustle"]
    },
    {
        "id": "creative_artist",
        "name": "Creative Artist",
        "description": "Share your creative work and process",
        "persona_voice": "creative, expressive, and authentic",
        "persona_style": "artistic and unique",
        "brand_keywords": ["art", "creativity", "process"],
        "goals": ["content_creator", "personal_brand"]
    },
    {
        "id": "fitness_wellness",
        "name": "Fitness & Wellness",
        "description": "Inspire healthy living and fitness",
        "persona_voice": "motivating, supportive, and energetic",
        "persona_style": "active and health-focused",
        "brand_keywords": ["fitness", "health", "motivation"],
        "goals": ["personal_brand", "side_hustle"]
    },
    {
        "id": "food_lifestyle",
        "name": "Food & Lifestyle",
        "description": "Share recipes, food content, and lifestyle",
        "persona_voice": "warm, inviting, and passionate about food",
        "persona_style": "cozy and appetizing",
        "brand_keywords": ["food", "recipes", "lifestyle"],
        "goals": ["content_creator", "personal_brand"]
    }
]


class OnboardingService:
    """Service for managing user onboarding flow."""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ==================== Progress Tracking ====================
    
    def get_onboarding_status(self, user: User) -> Dict[str, Any]:
        """Get user's current onboarding status and progress."""
        
        # Get or initialize onboarding data
        onboarding_data = user.onboarding_data or {}
        
        completed_steps = onboarding_data.get("completed_steps", [])
        current_step = onboarding_data.get("current_step", "welcome")
        selected_goal = onboarding_data.get("selected_goal")
        
        # Calculate progress
        required_steps = [s for s in ONBOARDING_STEPS if s["required"]]
        completed_required = [s for s in completed_steps if s in [rs["id"] for rs in required_steps]]
        progress_percent = (len(completed_required) / len(required_steps)) * 100
        
        # Check if onboarding is complete
        is_complete = onboarding_data.get("completed", False)
        if not is_complete:
            # Auto-check completion based on user activity
            is_complete = self._check_auto_completion(user)
            if is_complete:
                self._mark_complete(user)
        
        return {
            "is_complete": is_complete,
            "current_step": current_step,
            "completed_steps": completed_steps,
            "progress_percent": round(progress_percent),
            "selected_goal": selected_goal,
            "steps": ONBOARDING_STEPS,
            "started_at": onboarding_data.get("started_at"),
            "completed_at": onboarding_data.get("completed_at")
        }
    
    def _check_auto_completion(self, user: User) -> bool:
        """Check if user has completed key actions regardless of wizard."""
        
        # Has at least one brand
        has_brand = self.db.query(Brand).filter(
            Brand.user_id == user.id
        ).first() is not None
        
        # Has generated content
        has_content = self.db.query(GeneratedContent).filter(
            GeneratedContent.user_id == user.id
        ).first() is not None
        
        return has_brand and has_content
    
    def update_step(
        self,
        user: User,
        step_id: str,
        completed: bool = True,
        data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Update onboarding step status."""
        
        onboarding_data = user.onboarding_data or {
            "started_at": datetime.utcnow().isoformat(),
            "completed_steps": [],
            "current_step": "welcome"
        }
        
        if completed and step_id not in onboarding_data.get("completed_steps", []):
            onboarding_data.setdefault("completed_steps", []).append(step_id)
        
        # Store any additional data
        if data:
            onboarding_data.setdefault("step_data", {})[step_id] = data
        
        # Move to next step
        current_index = next(
            (i for i, s in enumerate(ONBOARDING_STEPS) if s["id"] == step_id),
            0
        )
        if current_index < len(ONBOARDING_STEPS) - 1:
            onboarding_data["current_step"] = ONBOARDING_STEPS[current_index + 1]["id"]
        
        # Check if all required steps complete
        required_ids = [s["id"] for s in ONBOARDING_STEPS if s["required"]]
        if all(rid in onboarding_data.get("completed_steps", []) for rid in required_ids):
            onboarding_data["completed"] = True
            onboarding_data["completed_at"] = datetime.utcnow().isoformat()
        
        user.onboarding_data = onboarding_data
        self.db.commit()
        
        return self.get_onboarding_status(user)
    
    def _mark_complete(self, user: User):
        """Mark onboarding as complete."""
        onboarding_data = user.onboarding_data or {}
        onboarding_data["completed"] = True
        onboarding_data["completed_at"] = datetime.utcnow().isoformat()
        user.onboarding_data = onboarding_data
        self.db.commit()
    
    def skip_onboarding(self, user: User) -> Dict[str, Any]:
        """Allow user to skip onboarding."""
        onboarding_data = user.onboarding_data or {}
        onboarding_data["skipped"] = True
        onboarding_data["skipped_at"] = datetime.utcnow().isoformat()
        onboarding_data["completed"] = True
        user.onboarding_data = onboarding_data
        self.db.commit()
        
        return self.get_onboarding_status(user)
    
    # ==================== Goal Selection ====================
    
    def get_goals(self) -> List[Dict[str, Any]]:
        """Get available user goals."""
        return USER_GOALS
    
    def set_goal(self, user: User, goal_id: str) -> Dict[str, Any]:
        """Set user's primary goal."""
        
        goal = next((g for g in USER_GOALS if g["id"] == goal_id), None)
        if not goal:
            raise ValueError(f"Invalid goal: {goal_id}")
        
        onboarding_data = user.onboarding_data or {}
        onboarding_data["selected_goal"] = goal_id
        onboarding_data["goal_selected_at"] = datetime.utcnow().isoformat()
        user.onboarding_data = onboarding_data
        self.db.commit()
        
        # Mark step complete and return status
        return self.update_step(user, "select_goal", completed=True, data={"goal": goal_id})
    
    # ==================== Brand Creation ====================
    
    def get_brand_templates(self, goal_id: str = None) -> List[Dict[str, Any]]:
        """Get brand templates, optionally filtered by goal."""
        
        if goal_id:
            return [t for t in BRAND_TEMPLATES if goal_id in t.get("goals", [])]
        return BRAND_TEMPLATES
    
    async def create_brand_from_template(
        self,
        user: User,
        template_id: str,
        brand_name: str,
        customizations: Dict[str, Any] = None
    ) -> Brand:
        """Create a brand from a template with optional customizations."""
        
        template = next((t for t in BRAND_TEMPLATES if t["id"] == template_id), None)
        if not template:
            raise ValueError(f"Invalid template: {template_id}")
        
        # Merge template with customizations
        brand_data = {
            "name": brand_name,
            "description": customizations.get("description", template["description"]),
            "persona_name": customizations.get("persona_name", brand_name),
            "persona_voice": customizations.get("persona_voice", template["persona_voice"]),
            "persona_style": customizations.get("persona_style", template["persona_style"]),
            "brand_keywords": customizations.get("brand_keywords", template["brand_keywords"]),
        }
        
        # Add optional fields
        if customizations:
            if customizations.get("persona_gender"):
                brand_data["persona_gender"] = customizations["persona_gender"]
            if customizations.get("persona_age"):
                brand_data["persona_age"] = customizations["persona_age"]
            if customizations.get("target_audience"):
                brand_data["target_audience"] = customizations["target_audience"]
        
        brand = Brand(user_id=user.id, **brand_data)
        self.db.add(brand)
        self.db.commit()
        self.db.refresh(brand)
        
        # Update onboarding
        self.update_step(user, "create_brand", completed=True, data={
            "brand_id": brand.id,
            "template_id": template_id
        })
        
        return brand
    
    async def create_quick_brand(
        self,
        user: User,
        brand_name: str,
        brand_type: str = "personal"
    ) -> Brand:
        """Create a brand with minimal input for fastest onboarding."""
        
        # Map simple types to templates
        type_to_template = {
            "personal": "personal_influencer",
            "business": "business_professional",
            "ecommerce": "ecommerce_brand",
            "creative": "creative_artist",
            "fitness": "fitness_wellness",
            "food": "food_lifestyle"
        }
        
        template_id = type_to_template.get(brand_type, "personal_influencer")
        return await self.create_brand_from_template(user, template_id, brand_name)
    
    # ==================== First Content Generation ====================
    
    async def generate_first_content(
        self,
        user: User,
        brand: Brand,
        content_type: str = "caption"
    ) -> GeneratedContent:
        """Generate first piece of content for the user."""
        
        from app.services.generator import ContentGeneratorService
        from app.models.models import ContentType
        
        # Get a trending topic or use a generic prompt
        prompt = self._get_starter_prompt(brand)
        
        generator = ContentGeneratorService(
            self.db,
            settings.openai_api_key,
            settings.replicate_api_token
        )
        
        if content_type == "image":
            content = await generator.generate_content(
                brand=brand,
                user_id=user.id,
                content_type=ContentType.IMAGE,
                custom_prompt=prompt,
                include_caption=True
            )
        else:
            content = await generator.generate_content(
                brand=brand,
                user_id=user.id,
                content_type=ContentType.TEXT,
                custom_prompt=prompt
            )
        
        # Update onboarding
        self.update_step(user, "first_content", completed=True, data={
            "content_id": content.id,
            "content_type": content_type
        })
        
        return content
    
    def _get_starter_prompt(self, brand: Brand) -> str:
        """Get a good starter prompt based on brand."""
        
        prompts = [
            f"Create an engaging introduction post for {brand.name}",
            f"Write a post about why I started {brand.name}",
            f"Create a motivational post that reflects the {brand.persona_voice} voice",
            f"Write a post sharing a tip related to {', '.join(brand.brand_keywords or ['my expertise'])}",
        ]
        
        import random
        return random.choice(prompts)
    
    # ==================== Demo/Sample Data ====================
    
    async def create_demo_brand(self, user: User) -> Brand:
        """Create a demo brand with sample content for new users."""
        
        demo_brand = Brand(
            user_id=user.id,
            name="Demo Brand",
            description="This is a sample brand to show you how the platform works. Feel free to edit or delete it!",
            persona_name="Alex Demo",
            persona_voice="friendly, helpful, and enthusiastic",
            persona_style="modern and approachable",
            persona_gender="neutral",
            persona_age="25-34",
            brand_keywords=["demo", "example", "tutorial"],
            target_audience="People learning to use this platform",
            is_demo=True
        )
        
        self.db.add(demo_brand)
        self.db.commit()
        self.db.refresh(demo_brand)
        
        return demo_brand
    
    # ==================== Onboarding Analytics ====================
    
    def get_onboarding_analytics(self) -> Dict[str, Any]:
        """Get platform-wide onboarding analytics (admin)."""
        
        total_users = self.db.query(User).count()
        
        # Users who started onboarding
        started = self.db.query(User).filter(
            User.onboarding_data.isnot(None)
        ).count()
        
        # Users who completed onboarding
        # This is a simplified query - in production you'd use JSON queries
        completed = self.db.query(User).filter(
            User.onboarding_data.isnot(None)
        ).all()
        completed_count = sum(
            1 for u in completed 
            if u.onboarding_data and u.onboarding_data.get("completed")
        )
        
        # Users who skipped
        skipped_count = sum(
            1 for u in completed 
            if u.onboarding_data and u.onboarding_data.get("skipped")
        )
        
        return {
            "total_users": total_users,
            "started_onboarding": started,
            "completed_onboarding": completed_count,
            "skipped_onboarding": skipped_count,
            "completion_rate": round((completed_count / max(started, 1)) * 100, 1),
            "skip_rate": round((skipped_count / max(started, 1)) * 100, 1)
        }


def get_onboarding_service(db: Session) -> OnboardingService:
    return OnboardingService(db)

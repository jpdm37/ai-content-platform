"""
Avatar Generation Service

Creates consistent AI avatars from brand requirements.
Uses a multi-stage approach:
1. Generate initial avatar concepts based on description
2. User selects preferred look
3. Generate multiple training images of selected avatar
4. Train LoRA for consistent reproduction

Key Models Used:
- Flux for high-quality generation
- PhotoMaker/IP-Adapter for face consistency (when available)
- Face embedding for similarity matching
"""
import logging
import os
import uuid
import random
from typing import Optional, List, Dict, Any
from datetime import datetime
import replicate
from sqlalchemy.orm import Session

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AvatarStyle:
    """Predefined avatar styles for consistency"""
    PROFESSIONAL = "professional"
    INFLUENCER = "influencer"
    CORPORATE = "corporate"
    CREATIVE = "creative"
    LIFESTYLE = "lifestyle"
    TECH = "tech"
    FITNESS = "fitness"
    FASHION = "fashion"


class AvatarGenerationService:
    """
    Service for generating consistent AI avatars from scratch.
    
    Workflow:
    1. User provides avatar requirements (age, gender, style, etc.)
    2. Generate 4 concept variations for user to choose from
    3. User picks their favorite
    4. Generate 10-15 training images of that same face
    5. Create LoRA training job with generated images
    6. Avatar is ready for consistent content generation
    """
    
    # High-quality models for generation
    FLUX_SCHNELL = "black-forest-labs/flux-schnell"
    FLUX_DEV = "black-forest-labs/flux-dev"
    
    # Face consistency model (PhotoMaker style)
    # This model takes a reference face and generates new images keeping face consistent
    PHOTOMAKER = "tencentarc/photomaker:ddfc2b08d209f9fa8c1edd8e2f7fee71c4e4ce72d4e7c3d8c4097eb2f01fbe1c"
    
    # Alternative: IP-Adapter for face consistency
    IP_ADAPTER = "lucataco/ip-adapter-faceid:7c1cd4e3a7f3e1f5f7b5f6d6e5f4e3d2c1b0a9"
    
    # Cost estimates
    COST_PER_CONCEPT = 0.003  # ~$0.003 per image with Flux Schnell
    COST_PER_TRAINING_IMAGE = 0.02  # Higher quality for training
    
    def __init__(self, replicate_api_token: Optional[str] = None):
        self.replicate_token = replicate_api_token or settings.replicate_api_token
        if self.replicate_token:
            os.environ["REPLICATE_API_TOKEN"] = self.replicate_token
    
    def build_avatar_prompt(
        self,
        gender: str,
        age_range: str,
        ethnicity: Optional[str] = None,
        style: str = AvatarStyle.PROFESSIONAL,
        hair_color: Optional[str] = None,
        hair_style: Optional[str] = None,
        distinguishing_features: Optional[str] = None,
        custom_description: Optional[str] = None
    ) -> str:
        """
        Build a detailed prompt for avatar generation.
        The prompt is designed to create a realistic, professional-looking person.
        """
        # Base prompt for high-quality portrait
        parts = [
            "ultra realistic photograph",
            "professional headshot portrait",
            f"{age_range} year old {gender}",
        ]
        
        # Ethnicity/appearance
        if ethnicity:
            parts.append(ethnicity)
        
        # Hair
        if hair_color:
            parts.append(f"{hair_color} hair")
        if hair_style:
            parts.append(f"{hair_style} hairstyle")
        
        # Style-specific additions
        style_prompts = {
            AvatarStyle.PROFESSIONAL: "wearing business attire, confident expression, corporate setting, clean background",
            AvatarStyle.INFLUENCER: "stylish casual outfit, warm friendly smile, modern aesthetic, lifestyle photography",
            AvatarStyle.CORPORATE: "formal business suit, authoritative yet approachable, executive presence, studio lighting",
            AvatarStyle.CREATIVE: "artistic style, unique fashion, creative expression, interesting background",
            AvatarStyle.LIFESTYLE: "casual relaxed style, natural setting, authentic genuine expression, warm tones",
            AvatarStyle.TECH: "smart casual, modern minimalist style, innovative look, clean aesthetic",
            AvatarStyle.FITNESS: "athletic wear, healthy energetic look, confident pose, dynamic lighting",
            AvatarStyle.FASHION: "high fashion styling, editorial look, striking features, designer aesthetic"
        }
        
        parts.append(style_prompts.get(style, style_prompts[AvatarStyle.PROFESSIONAL]))
        
        # Distinguishing features
        if distinguishing_features:
            parts.append(distinguishing_features)
        
        # Custom additions
        if custom_description:
            parts.append(custom_description)
        
        # Quality tags
        parts.extend([
            "highly detailed face",
            "sharp focus on eyes",
            "natural skin texture",
            "professional photography",
            "8k resolution",
            "soft studio lighting"
        ])
        
        return ", ".join(parts)
    
    def build_negative_prompt(self) -> str:
        """Standard negative prompt for avatar generation"""
        return ", ".join([
            "cartoon", "anime", "illustration", "painting", "drawing",
            "blurry", "out of focus", "low quality", "pixelated",
            "deformed", "distorted", "disfigured", "bad anatomy",
            "extra limbs", "missing limbs", "floating limbs",
            "disconnected limbs", "mutation", "mutated",
            "ugly", "disgusting", "bad proportions",
            "duplicate", "morbid", "mutilated",
            "watermark", "text", "logo", "signature"
        ])
    
    async def generate_avatar_concepts(
        self,
        gender: str,
        age_range: str,
        style: str = AvatarStyle.PROFESSIONAL,
        ethnicity: Optional[str] = None,
        hair_color: Optional[str] = None,
        hair_style: Optional[str] = None,
        distinguishing_features: Optional[str] = None,
        custom_description: Optional[str] = None,
        num_concepts: int = 4
    ) -> Dict[str, Any]:
        """
        Generate initial avatar concepts for user to choose from.
        Each concept will be a unique individual matching the requirements.
        
        Returns:
            Dict with concept images and metadata
        """
        prompt = self.build_avatar_prompt(
            gender=gender,
            age_range=age_range,
            ethnicity=ethnicity,
            style=style,
            hair_color=hair_color,
            hair_style=hair_style,
            distinguishing_features=distinguishing_features,
            custom_description=custom_description
        )
        
        negative_prompt = self.build_negative_prompt()
        
        concepts = []
        seeds = []
        
        try:
            # Generate concepts with different seeds for variety
            for i in range(num_concepts):
                seed = random.randint(1, 2147483647)
                seeds.append(seed)
                
                output = replicate.run(
                    self.FLUX_SCHNELL,
                    input={
                        "prompt": prompt,
                        "num_outputs": 1,
                        "aspect_ratio": "1:1",
                        "output_format": "webp",
                        "output_quality": 90,
                        "seed": seed
                    }
                )
                
                if output and len(output) > 0:
                    concepts.append({
                        "image_url": output[0],
                        "seed": seed,
                        "index": i
                    })
            
            return {
                "success": True,
                "concepts": concepts,
                "prompt_used": prompt,
                "requirements": {
                    "gender": gender,
                    "age_range": age_range,
                    "style": style,
                    "ethnicity": ethnicity,
                    "hair_color": hair_color,
                    "hair_style": hair_style
                },
                "estimated_cost": len(concepts) * self.COST_PER_CONCEPT
            }
            
        except Exception as e:
            logger.error(f"Avatar concept generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "concepts": []
            }
    
    async def generate_training_images(
        self,
        reference_image_url: str,
        reference_seed: int,
        original_prompt: str,
        num_images: int = 12,
        include_variations: bool = True
    ) -> Dict[str, Any]:
        """
        Generate multiple training images based on a selected avatar concept.
        Uses the same seed and similar prompts to maintain face consistency.
        
        For best LoRA training, we need:
        - Same face in different poses/angles
        - Variety in lighting and backgrounds
        - Consistent identity throughout
        """
        training_images = []
        
        # Variation prompts - same person, different contexts
        variation_prompts = [
            # Headshots from different angles
            "professional headshot, front facing, direct eye contact, neutral expression",
            "professional portrait, slight smile, warm expression, studio lighting",
            "headshot, looking slightly left, natural expression, soft lighting",
            "portrait, looking slightly right, confident expression, professional",
            
            # Different expressions
            "portrait with genuine smile, friendly approachable expression",
            "thoughtful expression, professional demeanor, clean background",
            "confident expression, direct gaze, executive presence",
            
            # Different lighting/settings
            "natural lighting portrait, outdoor setting, soft background blur",
            "studio portrait, dramatic lighting, dark background",
            "bright airy portrait, white background, clean professional",
            
            # Slight variations in framing
            "close-up portrait, detailed face, sharp focus",
            "medium shot portrait, shoulders visible, professional attire"
        ]
        
        base_prompt_parts = original_prompt.split(", ")
        # Extract key identity features (first few descriptors)
        identity_features = ", ".join(base_prompt_parts[:5])
        
        try:
            # Method 1: Try PhotoMaker for face-consistent generation
            try:
                training_images = await self._generate_with_photomaker(
                    reference_image_url,
                    identity_features,
                    variation_prompts[:num_images]
                )
            except Exception as e:
                logger.warning(f"PhotoMaker not available, using seed-based method: {e}")
                training_images = []
            
            # Method 2: Fallback to seed-based generation with slight variations
            if not training_images or len(training_images) < num_images:
                seed_based_images = await self._generate_with_seed_consistency(
                    original_prompt,
                    reference_seed,
                    variation_prompts,
                    num_images - len(training_images)
                )
                training_images.extend(seed_based_images)
            
            return {
                "success": True,
                "training_images": training_images,
                "total_images": len(training_images),
                "estimated_cost": len(training_images) * self.COST_PER_TRAINING_IMAGE,
                "ready_for_training": len(training_images) >= 5
            }
            
        except Exception as e:
            logger.error(f"Training image generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "training_images": training_images
            }
    
    async def _generate_with_photomaker(
        self,
        reference_url: str,
        identity_prompt: str,
        variation_prompts: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Use PhotoMaker or similar model to generate face-consistent variations.
        This maintains the exact face while changing pose, lighting, etc.
        """
        images = []
        
        for i, variation in enumerate(variation_prompts):
            try:
                full_prompt = f"{identity_prompt}, {variation}"
                
                output = replicate.run(
                    self.PHOTOMAKER,
                    input={
                        "input_image": reference_url,
                        "prompt": full_prompt,
                        "style_name": "Photographic",
                        "num_outputs": 1,
                        "guidance_scale": 5,
                        "style_strength_ratio": 20,
                        "num_steps": 50
                    }
                )
                
                if output and len(output) > 0:
                    images.append({
                        "image_url": output[0],
                        "prompt": full_prompt,
                        "method": "photomaker",
                        "index": i
                    })
                    
            except Exception as e:
                logger.warning(f"PhotoMaker generation {i} failed: {e}")
                continue
        
        return images
    
    async def _generate_with_seed_consistency(
        self,
        base_prompt: str,
        reference_seed: int,
        variation_prompts: List[str],
        num_images: int
    ) -> List[Dict[str, Any]]:
        """
        Generate consistent images using seed-based approach.
        Uses the same seed with slight prompt variations.
        
        Note: This is less reliable than PhotoMaker but works as fallback.
        """
        images = []
        
        # Use seeds close to reference for consistency
        for i in range(min(num_images, len(variation_prompts))):
            try:
                # Slight seed variation to get different poses while keeping face similar
                seed = reference_seed + (i * 7)  # Small increments
                
                # Combine base identity with variation
                variation = variation_prompts[i]
                
                # Extract identity parts from base prompt
                base_parts = base_prompt.split(", ")
                identity = ", ".join(base_parts[:6])  # Keep core identity
                
                full_prompt = f"{identity}, {variation}, same person, consistent face"
                
                output = replicate.run(
                    self.FLUX_DEV,  # Use higher quality model for training images
                    input={
                        "prompt": full_prompt,
                        "num_outputs": 1,
                        "aspect_ratio": "1:1",
                        "output_format": "webp",
                        "output_quality": 95,
                        "guidance": 3.5,
                        "num_inference_steps": 28,
                        "seed": seed
                    }
                )
                
                if output and len(output) > 0:
                    images.append({
                        "image_url": output[0],
                        "prompt": full_prompt,
                        "seed": seed,
                        "method": "seed_based",
                        "index": i
                    })
                    
            except Exception as e:
                logger.warning(f"Seed-based generation {i} failed: {e}")
                continue
        
        return images
    
    async def create_avatar_from_scratch(
        self,
        brand_id: int,
        avatar_name: str,
        gender: str,
        age_range: str,
        style: str = AvatarStyle.PROFESSIONAL,
        ethnicity: Optional[str] = None,
        hair_color: Optional[str] = None,
        hair_style: Optional[str] = None,
        distinguishing_features: Optional[str] = None,
        custom_description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Complete workflow to create an avatar from scratch.
        
        Steps:
        1. Generate concepts
        2. (User selects one - handled by frontend)
        3. Generate training images
        4. Create LoRA model
        5. Start training
        
        This method handles step 1. Steps 2-5 are separate API calls.
        """
        # Generate initial concepts
        result = await self.generate_avatar_concepts(
            gender=gender,
            age_range=age_range,
            style=style,
            ethnicity=ethnicity,
            hair_color=hair_color,
            hair_style=hair_style,
            distinguishing_features=distinguishing_features,
            custom_description=custom_description,
            num_concepts=4
        )
        
        if not result["success"]:
            return result
        
        return {
            "success": True,
            "stage": "concept_selection",
            "concepts": result["concepts"],
            "next_step": "Select a concept and call /avatar/generate-training-images",
            "brand_id": brand_id,
            "avatar_name": avatar_name,
            "requirements": result["requirements"],
            "prompt_template": result["prompt_used"]
        }


# Singleton instance
avatar_service = AvatarGenerationService()


def get_avatar_service(replicate_token: Optional[str] = None) -> AvatarGenerationService:
    """Factory function to get avatar service instance"""
    if replicate_token:
        return AvatarGenerationService(replicate_token)
    return avatar_service

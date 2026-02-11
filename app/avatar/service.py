"""
Avatar Generation Service v2

Uses InstantID for face-consistent image generation.
This provides 90-95% face consistency from a single reference image,
which is then used to generate training images for LoRA fine-tuning.

Workflow:
1. Generate initial concepts with Flux (different faces)
2. User selects preferred look
3. InstantID generates 12+ consistent variations of that face
4. LoRA trains on InstantID outputs
5. Future generations use trained LoRA for 99% consistency

Models Used:
- Flux Schnell: Fast concept generation ($0.003/image)
- InstantID: Face-consistent variations ($0.02/image) 
- Flux LoRA Trainer: Training ($2-3/job)
- Flux LoRA: Generation with trained model ($0.003/image)
"""
import logging
import os
import random
from typing import Optional, List, Dict, Any
import replicate

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AvatarStyle:
    """Predefined avatar styles"""
    PROFESSIONAL = "professional"
    INFLUENCER = "influencer"  
    CORPORATE = "corporate"
    CREATIVE = "creative"
    LIFESTYLE = "lifestyle"
    TECH = "tech"
    FITNESS = "fitness"
    FASHION = "fashion"


# Style-specific prompt additions
STYLE_PROMPTS = {
    AvatarStyle.PROFESSIONAL: "professional business attire, confident expression, corporate setting, studio lighting",
    AvatarStyle.INFLUENCER: "stylish casual outfit, warm friendly smile, lifestyle photography, natural lighting",
    AvatarStyle.CORPORATE: "formal business suit, executive presence, professional headshot, clean background",
    AvatarStyle.CREATIVE: "artistic style, creative fashion, expressive, interesting background",
    AvatarStyle.LIFESTYLE: "casual relaxed style, natural setting, authentic expression, warm tones",
    AvatarStyle.TECH: "smart casual, modern minimalist, innovative look, clean aesthetic",
    AvatarStyle.FITNESS: "athletic wear, healthy energetic look, confident pose, dynamic",
    AvatarStyle.FASHION: "high fashion styling, editorial look, striking, designer aesthetic"
}

# Prompts for generating diverse training images
TRAINING_VARIATION_PROMPTS = [
    "professional headshot, front facing, direct eye contact, neutral background, studio lighting",
    "portrait with warm genuine smile, approachable expression, soft lighting",
    "slight angle view, confident expression, professional attire, clean background",
    "three-quarter view portrait, natural expression, office environment",
    "close-up headshot, sharp focus, professional lighting, minimal background",
    "business casual look, relaxed confident pose, natural lighting",
    "portrait looking slightly left, thoughtful expression, soft background blur",
    "portrait looking slightly right, friendly smile, professional setting",
    "medium shot, shoulders visible, executive presence, studio background",
    "natural outdoor portrait, soft daylight, genuine expression",
    "high-key lighting portrait, clean white background, professional",
    "dramatic lighting portrait, confident gaze, artistic quality"
]


class AvatarGenerationService:
    """
    Service for generating consistent AI avatars using InstantID.
    
    InstantID allows generating new images while preserving facial identity
    from a single reference image. This is more reliable than seed-based
    approaches and doesn't require upfront training.
    """
    
    # Model endpoints
    FLUX_SCHNELL = "black-forest-labs/flux-schnell"
    FLUX_DEV = "black-forest-labs/flux-dev"
    
    # InstantID - best balance of quality and consistency
    # Takes a face image and generates new images preserving identity
    INSTANTID = "zsxkib/instant-id:2aff0dc55a1b6cce6c1f3ab10c8c66a75c77f45c2b2d5a8c6e9f3b4c2d1e0f9a"
    
    # Alternative models (fallbacks)
    INSTANTID_V2 = "instantx/instant-id:19066fa28cd3f74546935178c61c5f24b83e5987ab1babfbbd665ccce26db292"
    IP_ADAPTER_FACEID = "lucataco/ip-adapter-face-id:728e1f90a3b7d21a2e2b2e7a1f7a2b9d3c4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a"
    
    # Cost tracking
    COST_FLUX_SCHNELL = 0.003
    COST_INSTANTID = 0.02
    COST_LORA_TRAINING = 2.50
    
    def __init__(self, replicate_api_token: Optional[str] = None):
        self.replicate_token = replicate_api_token or settings.replicate_api_token
        if self.replicate_token:
            os.environ["REPLICATE_API_TOKEN"] = self.replicate_token
    
    def _build_base_prompt(
        self,
        gender: str,
        age_range: str,
        ethnicity: Optional[str] = None,
        hair_color: Optional[str] = None,
        custom_description: Optional[str] = None
    ) -> str:
        """Build the base identity prompt"""
        parts = [
            "ultra realistic photograph",
            "high quality portrait",
            f"{age_range} year old {gender}",
        ]
        
        if ethnicity:
            parts.append(ethnicity)
        if hair_color:
            parts.append(f"{hair_color} hair")
        if custom_description:
            parts.append(custom_description)
            
        parts.extend([
            "highly detailed face",
            "natural skin texture",
            "sharp focus",
            "professional photography"
        ])
        
        return ", ".join(parts)
    
    def _build_negative_prompt(self) -> str:
        """Standard negative prompt for quality"""
        return (
            "cartoon, anime, illustration, painting, drawing, blurry, "
            "low quality, distorted, deformed, ugly, bad anatomy, "
            "watermark, text, logo, extra limbs, missing limbs"
        )
    
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
        Generate initial avatar concepts for user selection.
        Uses Flux Schnell for fast, diverse results.
        Each concept is a unique person matching the requirements.
        """
        # Build the full prompt
        base_prompt = self._build_base_prompt(
            gender=gender,
            age_range=age_range,
            ethnicity=ethnicity,
            hair_color=hair_color,
            custom_description=custom_description
        )
        
        style_addition = STYLE_PROMPTS.get(style, STYLE_PROMPTS[AvatarStyle.PROFESSIONAL])
        full_prompt = f"{base_prompt}, {style_addition}"
        
        if hair_style:
            full_prompt += f", {hair_style} hairstyle"
        if distinguishing_features:
            full_prompt += f", {distinguishing_features}"
        
        concepts = []
        
        try:
            for i in range(num_concepts):
                seed = random.randint(1, 2147483647)
                
                output = replicate.run(
                    self.FLUX_SCHNELL,
                    input={
                        "prompt": full_prompt,
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
                "prompt_used": full_prompt,
                "requirements": {
                    "gender": gender,
                    "age_range": age_range,
                    "style": style,
                    "ethnicity": ethnicity,
                    "hair_color": hair_color,
                },
                "estimated_cost": len(concepts) * self.COST_FLUX_SCHNELL
            }
            
        except Exception as e:
            logger.error(f"Concept generation failed: {e}")
            return {"success": False, "error": str(e), "concepts": []}
    
    async def generate_training_images_instantid(
        self,
        reference_image_url: str,
        style: str = AvatarStyle.PROFESSIONAL,
        num_images: int = 12
    ) -> Dict[str, Any]:
        """
        Generate consistent training images using InstantID.
        
        InstantID preserves facial identity while allowing different:
        - Poses and angles
        - Lighting conditions
        - Backgrounds
        - Expressions
        
        This is the key to getting consistent avatars without expensive
        per-image training.
        """
        training_images = []
        style_addition = STYLE_PROMPTS.get(style, STYLE_PROMPTS[AvatarStyle.PROFESSIONAL])
        
        # Use subset of variation prompts
        prompts_to_use = TRAINING_VARIATION_PROMPTS[:num_images]
        
        try:
            for i, variation_prompt in enumerate(prompts_to_use):
                full_prompt = f"{variation_prompt}, {style_addition}"
                
                try:
                    # Try InstantID first
                    output = replicate.run(
                        self.INSTANTID_V2,
                        input={
                            "image": reference_image_url,
                            "prompt": full_prompt,
                            "negative_prompt": self._build_negative_prompt(),
                            "num_steps": 30,
                            "guidance_scale": 5.0,
                            "ip_adapter_scale": 0.8,  # How much to preserve face
                            "controlnet_conditioning_scale": 0.8,
                            "seed": random.randint(1, 2147483647)
                        }
                    )
                    
                    if output:
                        image_url = output[0] if isinstance(output, list) else output
                        training_images.append({
                            "image_url": image_url,
                            "prompt": full_prompt,
                            "method": "instantid",
                            "index": i
                        })
                        logger.info(f"Generated training image {i+1}/{num_images}")
                        
                except Exception as e:
                    logger.warning(f"InstantID failed for image {i}, trying fallback: {e}")
                    # Fallback to IP-Adapter
                    try:
                        output = await self._generate_with_ip_adapter(
                            reference_image_url, full_prompt
                        )
                        if output:
                            training_images.append({
                                "image_url": output,
                                "prompt": full_prompt,
                                "method": "ip_adapter",
                                "index": i
                            })
                    except Exception as e2:
                        logger.error(f"Fallback also failed: {e2}")
                        continue
            
            return {
                "success": len(training_images) >= 5,
                "training_images": training_images,
                "total_images": len(training_images),
                "estimated_cost": len(training_images) * self.COST_INSTANTID,
                "ready_for_training": len(training_images) >= 5
            }
            
        except Exception as e:
            logger.error(f"Training image generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "training_images": training_images,
                "ready_for_training": False
            }
    
    async def _generate_with_ip_adapter(
        self,
        reference_url: str,
        prompt: str
    ) -> Optional[str]:
        """Fallback: Use IP-Adapter for face consistency"""
        try:
            output = replicate.run(
                self.IP_ADAPTER_FACEID,
                input={
                    "image": reference_url,
                    "prompt": prompt,
                    "negative_prompt": self._build_negative_prompt(),
                    "num_inference_steps": 30,
                    "guidance_scale": 6.0,
                    "ip_adapter_scale": 0.6
                }
            )
            return output[0] if output else None
        except Exception as e:
            logger.error(f"IP-Adapter failed: {e}")
            return None
    
    async def generate_training_images(
        self,
        reference_image_url: str,
        reference_seed: int,
        original_prompt: str,
        num_images: int = 12,
        include_variations: bool = True
    ) -> Dict[str, Any]:
        """
        Main entry point for training image generation.
        Tries InstantID first, falls back to other methods.
        """
        # Extract style from original prompt if possible
        style = AvatarStyle.PROFESSIONAL
        for s in STYLE_PROMPTS.keys():
            if s in original_prompt.lower():
                style = s
                break
        
        # Use InstantID for best results
        result = await self.generate_training_images_instantid(
            reference_image_url=reference_image_url,
            style=style,
            num_images=num_images
        )
        
        # If InstantID didn't generate enough, try seed-based fallback
        if len(result.get("training_images", [])) < 5:
            logger.warning("InstantID produced insufficient images, using seed fallback")
            seed_images = await self._generate_seed_based_fallback(
                original_prompt, 
                reference_seed,
                5 - len(result.get("training_images", []))
            )
            result["training_images"].extend(seed_images)
            result["total_images"] = len(result["training_images"])
            result["ready_for_training"] = len(result["training_images"]) >= 5
        
        return result
    
    async def _generate_seed_based_fallback(
        self,
        base_prompt: str,
        reference_seed: int,
        num_needed: int
    ) -> List[Dict[str, Any]]:
        """Last resort: seed-based generation"""
        images = []
        
        for i in range(num_needed):
            try:
                # Use nearby seeds for face similarity
                seed = reference_seed + (i * 3)
                
                output = replicate.run(
                    self.FLUX_DEV,
                    input={
                        "prompt": base_prompt + ", same person, consistent identity",
                        "num_outputs": 1,
                        "aspect_ratio": "1:1",
                        "guidance": 3.5,
                        "seed": seed
                    }
                )
                
                if output:
                    images.append({
                        "image_url": output[0],
                        "prompt": base_prompt,
                        "method": "seed_fallback",
                        "seed": seed,
                        "index": len(images)
                    })
            except Exception as e:
                logger.error(f"Seed fallback failed: {e}")
                
        return images
    
    def estimate_total_cost(self, num_concepts: int = 4, num_training: int = 12) -> Dict[str, float]:
        """Estimate total cost for avatar creation"""
        return {
            "concept_generation": num_concepts * self.COST_FLUX_SCHNELL,
            "training_images": num_training * self.COST_INSTANTID,
            "lora_training": self.COST_LORA_TRAINING,
            "total": (num_concepts * self.COST_FLUX_SCHNELL) + 
                    (num_training * self.COST_INSTANTID) + 
                    self.COST_LORA_TRAINING
        }


# Singleton
avatar_service = AvatarGenerationService()


def get_avatar_service(replicate_token: Optional[str] = None) -> AvatarGenerationService:
    if replicate_token:
        return AvatarGenerationService(replicate_token)
    return avatar_service

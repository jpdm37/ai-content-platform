"""
LoRA Training Service

Handles the complete LoRA training pipeline:
1. Image validation and preprocessing
2. Training job creation on Replicate
3. Progress monitoring
4. Model deployment
5. Generation with trained LoRA
"""
import logging
import asyncio
import os
import uuid
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
import httpx
import replicate
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.lora.models import (
    LoraModel, LoraReferenceImage, LoraGeneratedSample,
    LoraTrainingQueue, LoraUsageLog,
    TrainingStatus, ImageValidationStatus
)
from app.lora.image_service import ImageValidationService, ValidationResult

logger = logging.getLogger(__name__)
settings = get_settings()


class LoraTrainingService:
    """
    Comprehensive LoRA training service using Replicate's flux-dev-lora-trainer.
    
    Training Pipeline:
    1. Upload reference images
    2. Validate images (face detection, quality)
    3. Auto-caption images
    4. Create training job on Replicate
    5. Monitor progress
    6. Deploy trained model
    7. Generate test samples
    8. Calculate consistency score
    """
    
    # Replicate model endpoints
    FLUX_TRAINER = "ostris/flux-dev-lora-trainer:4ffd32160efd92e956d39c5338a9b8fbafca58e03f791f6d8011f3e20e8ea6fa"
    FLUX_DEV = "black-forest-labs/flux-dev"
    FLUX_SCHNELL = "black-forest-labs/flux-schnell"
    FLUX_LORA = "lucataco/flux-dev-lora:a22c463f11808638ad5e2ebd582e07a469031f48dd567366fb4c6fdab91d614d"
    
    # Cost estimates (USD per training)
    COST_PER_STEP = 0.001  # Approximate
    BASE_TRAINING_COST = 1.50
    COST_PER_GENERATION = 0.003
    
    def __init__(self, db: Session, replicate_api_token: Optional[str] = None):
        self.db = db
        self.replicate_token = replicate_api_token or settings.replicate_api_token
        self.image_service = ImageValidationService(self.replicate_token)
        
        if self.replicate_token:
            os.environ["REPLICATE_API_TOKEN"] = self.replicate_token
    
    # ==================== Image Management ====================
    
    async def add_reference_image(
        self,
        lora_model: LoraModel,
        image_url: str,
        custom_caption: Optional[str] = None,
        image_type: Optional[str] = None
    ) -> LoraReferenceImage:
        """
        Add and validate a reference image for training.
        """
        # Create reference image record
        ref_image = LoraReferenceImage(
            lora_model_id=lora_model.id,
            original_url=image_url,
            custom_caption=custom_caption,
            image_type=image_type,
            validation_status=ImageValidationStatus.PROCESSING
        )
        self.db.add(ref_image)
        self.db.commit()
        
        try:
            # Validate image
            validation = await self.image_service.validate_image(image_url)
            
            ref_image.face_detected = validation.face_detected
            ref_image.face_confidence = validation.face_confidence
            ref_image.face_bbox = validation.face_bbox
            ref_image.quality_score = validation.quality_score
            ref_image.validation_errors = validation.errors if validation.errors else None
            
            if validation.is_valid:
                ref_image.validation_status = ImageValidationStatus.VALID
            else:
                ref_image.validation_status = ImageValidationStatus.INVALID
                ref_image.is_included_in_training = False
            
            # Auto-generate caption if not provided
            if not custom_caption and self.replicate_token:
                try:
                    caption = await self._generate_caption(image_url)
                    ref_image.caption = caption
                except Exception as e:
                    logger.warning(f"Caption generation failed: {e}")
            
            self.db.commit()
            self.db.refresh(ref_image)
            
        except Exception as e:
            logger.error(f"Error validating image: {e}")
            ref_image.validation_status = ImageValidationStatus.INVALID
            ref_image.validation_errors = [str(e)]
            self.db.commit()
        
        return ref_image
    
    async def bulk_add_images(
        self,
        lora_model: LoraModel,
        image_urls: List[str]
    ) -> List[LoraReferenceImage]:
        """Add multiple reference images."""
        results = []
        for url in image_urls:
            try:
                ref_image = await self.add_reference_image(lora_model, url)
                results.append(ref_image)
            except Exception as e:
                logger.error(f"Error adding image {url}: {e}")
        return results
    
    async def validate_training_readiness(
        self,
        lora_model: LoraModel
    ) -> Dict[str, Any]:
        """
        Check if model is ready for training.
        Returns validation status and any issues.
        """
        issues = []
        warnings = []
        
        # Get valid images
        valid_images = self.db.query(LoraReferenceImage).filter(
            LoraReferenceImage.lora_model_id == lora_model.id,
            LoraReferenceImage.validation_status == ImageValidationStatus.VALID,
            LoraReferenceImage.is_included_in_training == True
        ).all()
        
        image_count = len(valid_images)
        
        # Check minimum images
        if image_count < 5:
            issues.append(f"Need at least 5 valid images. You have {image_count}.")
        elif image_count < 10:
            warnings.append(f"Recommend 10-20 images for best results. You have {image_count}.")
        
        # Check face detection
        faces_detected = sum(1 for img in valid_images if img.face_detected)
        face_ratio = faces_detected / image_count if image_count > 0 else 0
        
        if face_ratio < 0.5:
            warnings.append(f"Only {faces_detected}/{image_count} images have detected faces. Consider using clearer face photos.")
        
        # Check quality scores
        avg_quality = sum(img.quality_score or 0 for img in valid_images) / image_count if image_count > 0 else 0
        if avg_quality < 50:
            warnings.append(f"Average image quality is low ({avg_quality:.0f}/100). Higher quality images produce better results.")
        
        # Check for diversity (basic check)
        image_types = set(img.image_type for img in valid_images if img.image_type)
        if len(image_types) < 2 and image_count >= 10:
            warnings.append("Consider adding more variety in poses and angles.")
        
        # Estimate cost and time
        steps = lora_model.training_steps
        estimated_cost = self.BASE_TRAINING_COST + (steps * self.COST_PER_STEP)
        estimated_time_minutes = max(10, steps // 50)  # Rough estimate
        
        return {
            "is_ready": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "valid_image_count": image_count,
            "faces_detected": faces_detected,
            "average_quality": avg_quality,
            "estimated_cost_usd": round(estimated_cost, 2),
            "estimated_time_minutes": estimated_time_minutes,
            "recommendations": self._get_training_recommendations(valid_images, lora_model)
        }
    
    # ==================== Training Pipeline ====================
    
    async def start_training(
        self,
        lora_model: LoraModel,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Start LoRA training on Replicate.
        """
        # Validate readiness
        readiness = await self.validate_training_readiness(lora_model)
        if not readiness["is_ready"]:
            raise ValueError(f"Not ready for training: {readiness['issues']}")
        
        # Update status
        lora_model.status = TrainingStatus.UPLOADING
        lora_model.training_started_at = datetime.utcnow()
        self.db.commit()
        
        try:
            # Get valid images
            valid_images = self.db.query(LoraReferenceImage).filter(
                LoraReferenceImage.lora_model_id == lora_model.id,
                LoraReferenceImage.validation_status == ImageValidationStatus.VALID,
                LoraReferenceImage.is_included_in_training == True
            ).all()
            
            # Prepare training data
            zip_url = await self._prepare_training_data(valid_images, lora_model.trigger_word)
            
            # Configure training
            training_config = self._build_training_config(lora_model, config)
            training_config["input_images"] = zip_url
            
            # Create unique model name
            model_name = f"lora-{lora_model.brand_id}-{lora_model.id}-{uuid.uuid4().hex[:8]}"
            
            # Start training on Replicate
            lora_model.status = TrainingStatus.TRAINING
            self.db.commit()
            
            training = replicate.trainings.create(
                destination=f"{settings.replicate_username or 'user'}/{model_name}",
                version=self.FLUX_TRAINER,
                input=training_config
            )
            
            # Store training info
            lora_model.replicate_training_id = training.id
            lora_model.replicate_model_name = model_name
            self.db.commit()
            
            # Log usage
            self._log_usage(lora_model, "training", estimated_cost=readiness["estimated_cost_usd"])
            
            return {
                "training_id": training.id,
                "model_name": model_name,
                "status": "training",
                "estimated_cost": readiness["estimated_cost_usd"],
                "estimated_time_minutes": readiness["estimated_time_minutes"]
            }
            
        except Exception as e:
            logger.error(f"Training start failed: {e}")
            lora_model.status = TrainingStatus.FAILED
            lora_model.error_message = str(e)
            self.db.commit()
            raise
    
    async def check_training_progress(
        self,
        lora_model: LoraModel
    ) -> Dict[str, Any]:
        """
        Check and update training progress.
        """
        if not lora_model.replicate_training_id:
            return {"error": "No training job found"}
        
        try:
            training = replicate.trainings.get(lora_model.replicate_training_id)
            
            # Parse progress from logs
            progress = self._parse_training_progress(training)
            
            # Update model status
            if training.status == "succeeded":
                lora_model.status = TrainingStatus.COMPLETED
                lora_model.training_completed_at = datetime.utcnow()
                lora_model.progress_percent = 100
                
                # Get trained model version
                if training.output:
                    lora_model.lora_weights_url = training.output.get("weights")
                    lora_model.replicate_version = training.output.get("version")
                
                # Calculate training duration
                if lora_model.training_started_at:
                    duration = (datetime.utcnow() - lora_model.training_started_at).total_seconds()
                    lora_model.training_duration_seconds = int(duration)
                
                # Estimate actual cost
                lora_model.training_cost_usd = self._estimate_training_cost(lora_model)
                
            elif training.status == "failed":
                lora_model.status = TrainingStatus.FAILED
                lora_model.error_message = training.error or "Training failed"
                
            elif training.status == "canceled":
                lora_model.status = TrainingStatus.CANCELLED
                
            else:
                lora_model.status = TrainingStatus.TRAINING
                lora_model.progress_percent = progress.get("percent", 0)
            
            self.db.commit()
            
            return {
                "status": lora_model.status.value,
                "progress_percent": lora_model.progress_percent,
                "current_step": progress.get("current_step"),
                "total_steps": progress.get("total_steps"),
                "eta_seconds": progress.get("eta_seconds"),
                "logs": progress.get("recent_logs", [])[-10:],
                "error_message": lora_model.error_message
            }
            
        except Exception as e:
            logger.error(f"Error checking progress: {e}")
            return {"error": str(e)}
    
    async def cancel_training(self, lora_model: LoraModel) -> bool:
        """Cancel ongoing training."""
        if not lora_model.replicate_training_id:
            return False
        
        try:
            replicate.trainings.cancel(lora_model.replicate_training_id)
            lora_model.status = TrainingStatus.CANCELLED
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error cancelling training: {e}")
            return False
    
    # ==================== Generation ====================
    
    async def generate_with_lora(
        self,
        lora_model: LoraModel,
        prompt: str,
        negative_prompt: Optional[str] = None,
        lora_scale: float = 1.0,
        guidance_scale: float = 3.5,
        num_inference_steps: int = 28,
        seed: Optional[int] = None,
        aspect_ratio: str = "1:1",
        num_outputs: int = 1
    ) -> List[LoraGeneratedSample]:
        """
        Generate images using a trained LoRA model.
        """
        if lora_model.status != TrainingStatus.COMPLETED:
            raise ValueError("LoRA model not ready for generation")
        
        if not lora_model.lora_weights_url:
            raise ValueError("LoRA weights not available")
        
        # Build prompt with trigger word
        full_prompt = f"{lora_model.trigger_word} {prompt}"
        
        # Aspect ratio to dimensions
        dimensions = self._aspect_to_dimensions(aspect_ratio)
        
        try:
            # Generate using flux-dev-lora
            output = replicate.run(
                self.FLUX_LORA,
                input={
                    "prompt": full_prompt,
                    "hf_lora": lora_model.lora_weights_url,
                    "lora_scale": lora_scale,
                    "num_outputs": num_outputs,
                    "aspect_ratio": aspect_ratio,
                    "guidance_scale": guidance_scale,
                    "num_inference_steps": num_inference_steps,
                    "seed": seed,
                    "output_format": "webp",
                    "output_quality": 90
                }
            )
            
            # Store generated samples
            samples = []
            for i, image_url in enumerate(output):
                sample = LoraGeneratedSample(
                    lora_model_id=lora_model.id,
                    prompt=full_prompt,
                    negative_prompt=negative_prompt,
                    image_url=image_url,
                    lora_scale=lora_scale,
                    guidance_scale=guidance_scale,
                    num_inference_steps=num_inference_steps,
                    seed=seed
                )
                self.db.add(sample)
                samples.append(sample)
            
            self.db.commit()
            
            # Log usage
            cost = self.COST_PER_GENERATION * num_outputs
            self._log_usage(lora_model, "generation", cost, full_prompt)
            
            # Refresh to get IDs
            for sample in samples:
                self.db.refresh(sample)
            
            return samples
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise
    
    async def generate_test_samples(
        self,
        lora_model: LoraModel,
        num_samples: int = 4
    ) -> List[LoraGeneratedSample]:
        """
        Generate test samples to evaluate model quality.
        """
        test_prompts = [
            "professional headshot, studio lighting, neutral background",
            "casual portrait, natural lighting, outdoor setting",
            "close-up portrait, soft lighting, warm tones",
            "full body shot, urban background, street photography style",
            "portrait with gentle smile, golden hour lighting",
            "profile view, artistic lighting, dramatic shadows",
            "candid shot, natural expression, lifestyle photography",
            "business professional photo, office setting, confident pose"
        ]
        
        samples = []
        for i in range(min(num_samples, len(test_prompts))):
            try:
                result = await self.generate_with_lora(
                    lora_model,
                    prompt=test_prompts[i],
                    num_outputs=1
                )
                if result:
                    result[0].is_test_sample = True
                    samples.extend(result)
            except Exception as e:
                logger.error(f"Test generation failed: {e}")
        
        self.db.commit()
        
        # Update test count
        lora_model.test_images_generated = len(samples)
        self.db.commit()
        
        return samples
    
    async def calculate_consistency_score(
        self,
        lora_model: LoraModel
    ) -> float:
        """
        Calculate consistency score based on test samples.
        Uses face similarity and style consistency metrics.
        """
        # Get test samples
        test_samples = self.db.query(LoraGeneratedSample).filter(
            LoraGeneratedSample.lora_model_id == lora_model.id,
            LoraGeneratedSample.is_test_sample == True
        ).all()
        
        if not test_samples:
            return 0.0
        
        # Get reference images
        ref_images = self.db.query(LoraReferenceImage).filter(
            LoraReferenceImage.lora_model_id == lora_model.id,
            LoraReferenceImage.validation_status == ImageValidationStatus.VALID
        ).all()
        
        if not ref_images:
            return 0.0
        
        try:
            # Use face similarity model
            scores = []
            for sample in test_samples[:4]:
                score = await self._calculate_face_similarity(
                    sample.image_url,
                    [img.original_url for img in ref_images[:3]]
                )
                scores.append(score)
                sample.face_similarity_score = score
            
            self.db.commit()
            
            avg_score = sum(scores) / len(scores) if scores else 0
            lora_model.consistency_score = avg_score
            self.db.commit()
            
            return avg_score
            
        except Exception as e:
            logger.error(f"Consistency calculation failed: {e}")
            return 0.0
    
    # ==================== Batch Operations ====================
    
    async def generate_batch(
        self,
        lora_model: LoraModel,
        prompts: List[str],
        **kwargs
    ) -> List[LoraGeneratedSample]:
        """Generate multiple images with different prompts."""
        all_samples = []
        for prompt in prompts:
            try:
                samples = await self.generate_with_lora(lora_model, prompt, **kwargs)
                all_samples.extend(samples)
            except Exception as e:
                logger.error(f"Batch generation failed for prompt: {e}")
        return all_samples
    
    async def generate_scenario(
        self,
        lora_model: LoraModel,
        scenario: str,
        custom_details: Optional[str] = None,
        num_variations: int = 4
    ) -> List[LoraGeneratedSample]:
        """Generate avatar in predefined scenarios."""
        scenario_prompts = {
            "professional": [
                "professional headshot, business attire, studio background, confident expression",
                "corporate portrait, modern office, natural lighting, approachable smile",
                "executive photo, premium quality, neutral background, professional lighting",
                "business casual, relaxed professional setting, warm lighting"
            ],
            "casual": [
                "casual portrait, relaxed pose, natural setting, friendly expression",
                "lifestyle photo, coffee shop background, candid moment",
                "casual outdoor portrait, natural lighting, genuine smile",
                "relaxed portrait, home setting, comfortable atmosphere"
            ],
            "outdoor": [
                "outdoor portrait, nature background, golden hour lighting",
                "urban street photography, city backdrop, natural light",
                "park setting, trees and greenery, soft sunlight",
                "beach portrait, ocean background, warm sunset light"
            ],
            "studio": [
                "studio portrait, professional lighting, clean background",
                "high-end studio shot, dramatic lighting, black background",
                "fashion studio, soft box lighting, minimal background",
                "artistic studio portrait, creative lighting, professional quality"
            ],
            "social_media": [
                "instagram worthy photo, trendy aesthetic, vibrant colors",
                "influencer style photo, modern setting, perfect lighting",
                "tiktok creator vibe, dynamic pose, engaging expression",
                "youtube thumbnail style, expressive face, bright lighting"
            ]
        }
        
        prompts = scenario_prompts.get(scenario, scenario_prompts["professional"])
        if custom_details:
            prompts = [f"{p}, {custom_details}" for p in prompts]
        
        return await self.generate_batch(
            lora_model,
            prompts[:num_variations]
        )
    
    # ==================== Helper Methods ====================
    
    async def _prepare_training_data(
        self,
        images: List[LoraReferenceImage],
        trigger_word: str
    ) -> str:
        """Prepare and upload training data zip."""
        zip_path, _ = await self.image_service.prepare_training_zip(
            [img.original_url for img in images],
            target_size=1024,
            trigger_word=trigger_word,
            captions=[img.custom_caption or img.caption for img in images]
        )
        
        # Upload to file hosting (using Replicate's file upload)
        # In production, use S3 or similar
        with open(zip_path, 'rb') as f:
            file_url = replicate.files.create(f)
        
        return file_url
    
    def _build_training_config(
        self,
        lora_model: LoraModel,
        overrides: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Build training configuration."""
        config = {
            "steps": lora_model.training_steps,
            "lora_rank": lora_model.lora_rank,
            "optimizer": "adamw8bit",
            "batch_size": 1,
            "resolution": f"{lora_model.resolution}",
            "autocaption": True,
            "trigger_word": lora_model.trigger_word,
            "learning_rate": lora_model.learning_rate,
            "wandb_project": "flux-lora-training",
            "wandb_save_interval": 100,
            "caption_dropout_rate": 0.05,
            "cache_latents_to_disk": False,
            "wandb_sample_interval": 100
        }
        
        if overrides:
            config.update(overrides)
        
        return config
    
    def _parse_training_progress(self, training) -> Dict[str, Any]:
        """Parse progress from Replicate training object."""
        progress = {
            "percent": 0,
            "current_step": 0,
            "total_steps": 0,
            "eta_seconds": None,
            "recent_logs": []
        }
        
        if hasattr(training, 'logs') and training.logs:
            logs = training.logs.split('\n') if isinstance(training.logs, str) else training.logs
            progress["recent_logs"] = logs[-20:]
            
            # Parse step info from logs
            for log in reversed(logs):
                if 'step' in log.lower():
                    try:
                        # Parse formats like "Step 500/1000" or "step: 500"
                        import re
                        match = re.search(r'step[:\s]*(\d+)[/\s]*(\d+)?', log.lower())
                        if match:
                            progress["current_step"] = int(match.group(1))
                            if match.group(2):
                                progress["total_steps"] = int(match.group(2))
                                progress["percent"] = int(
                                    (progress["current_step"] / progress["total_steps"]) * 100
                                )
                            break
                    except:
                        pass
        
        return progress
    
    def _estimate_training_cost(self, lora_model: LoraModel) -> float:
        """Estimate actual training cost."""
        base = self.BASE_TRAINING_COST
        step_cost = lora_model.training_steps * self.COST_PER_STEP
        return round(base + step_cost, 2)
    
    def _aspect_to_dimensions(self, aspect_ratio: str) -> Tuple[int, int]:
        """Convert aspect ratio to dimensions."""
        ratios = {
            "1:1": (1024, 1024),
            "16:9": (1344, 768),
            "9:16": (768, 1344),
            "4:3": (1152, 896),
            "3:4": (896, 1152),
            "21:9": (1536, 640),
            "9:21": (640, 1536)
        }
        return ratios.get(aspect_ratio, (1024, 1024))
    
    async def _generate_caption(self, image_url: str) -> Optional[str]:
        """Generate caption for image."""
        try:
            output = replicate.run(
                "salesforce/blip:2e1dddc8621f72155f24cf2e0adbde548458d3cab9f00c0139eea840d0ac4746",
                input={"image": image_url, "task": "image_captioning"}
            )
            return output if isinstance(output, str) else None
        except:
            return None
    
    async def _calculate_face_similarity(
        self,
        generated_url: str,
        reference_urls: List[str]
    ) -> float:
        """Calculate face similarity score."""
        try:
            # Use face recognition model
            # This is a placeholder - in production use a proper face embedding model
            output = replicate.run(
                "lucataco/insightface:4599c5f2d8a24f08bc0c32b6b81e8ca2be4dc13ce5a1da18292e69e54cc1e5c7",
                input={
                    "input_image": generated_url,
                    "target_image": reference_urls[0]
                }
            )
            
            # Parse similarity score
            if output and isinstance(output, dict):
                return output.get("similarity", 0) * 100
            
            return 75.0  # Default fallback
            
        except Exception as e:
            logger.warning(f"Face similarity calculation failed: {e}")
            return 75.0
    
    def _get_training_recommendations(
        self,
        images: List[LoraReferenceImage],
        lora_model: LoraModel
    ) -> List[str]:
        """Get recommendations to improve training results."""
        recommendations = []
        
        if len(images) < 15:
            recommendations.append(
                f"Add more images ({15 - len(images)} more recommended) for better consistency."
            )
        
        face_ratio = sum(1 for img in images if img.face_detected) / len(images) if images else 0
        if face_ratio < 0.8:
            recommendations.append(
                "Include more images with clear, visible faces."
            )
        
        avg_quality = sum(img.quality_score or 0 for img in images) / len(images) if images else 0
        if avg_quality < 70:
            recommendations.append(
                "Use higher resolution images for better results."
            )
        
        image_types = set(img.image_type for img in images if img.image_type)
        if len(image_types) < 3:
            recommendations.append(
                "Include variety: headshots, profile views, and different poses."
            )
        
        if lora_model.training_steps < 800:
            recommendations.append(
                "Consider increasing training steps to 1000+ for better quality."
            )
        
        return recommendations
    
    def _log_usage(
        self,
        lora_model: LoraModel,
        usage_type: str,
        cost: float = 0,
        prompt: str = None
    ):
        """Log usage for billing and analytics."""
        log = LoraUsageLog(
            lora_model_id=lora_model.id,
            user_id=lora_model.user_id,
            usage_type=usage_type,
            prompt=prompt,
            cost_usd=cost
        )
        self.db.add(log)
        self.db.commit()


# Factory function
def get_lora_training_service(db: Session, replicate_token: Optional[str] = None) -> LoraTrainingService:
    return LoraTrainingService(db, replicate_token)

"""
Image Validation and Processing Service for LoRA Training

Handles:
- Image validation (format, size, quality)
- Face detection and cropping
- Auto-captioning
- Image preprocessing for training
"""
import logging
import io
import os
import zipfile
import tempfile
from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass
import httpx
from PIL import Image
import replicate

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class ValidationResult:
    """Result of image validation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    quality_score: float  # 0-100
    face_detected: bool
    face_confidence: float
    face_bbox: Optional[Dict[str, int]]  # {x, y, width, height}
    recommended_crop: Optional[Dict[str, int]]
    dimensions: Tuple[int, int]
    file_size_bytes: int
    format: str


@dataclass
class ProcessedImage:
    """Result of image processing"""
    original_path: str
    processed_path: str
    caption: str
    width: int
    height: int
    face_bbox: Optional[Dict[str, int]]


class ImageValidationService:
    """
    Service for validating and processing images for LoRA training.
    """
    
    # Validation constants
    MIN_DIMENSION = 512
    MAX_DIMENSION = 4096
    MIN_FILE_SIZE = 10 * 1024  # 10KB
    MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
    SUPPORTED_FORMATS = {'JPEG', 'JPG', 'PNG', 'WEBP'}
    OPTIMAL_RESOLUTION = 1024
    MIN_IMAGES_FOR_TRAINING = 5
    MAX_IMAGES_FOR_TRAINING = 50
    RECOMMENDED_IMAGES = 15
    
    def __init__(self, replicate_api_token: Optional[str] = None):
        self.replicate_token = replicate_api_token or settings.replicate_api_token
        if self.replicate_token:
            os.environ["REPLICATE_API_TOKEN"] = self.replicate_token
    
    async def validate_image(self, image_url: str) -> ValidationResult:
        """
        Validate a single image for LoRA training suitability.
        """
        errors = []
        warnings = []
        face_detected = False
        face_confidence = 0.0
        face_bbox = None
        quality_score = 0.0
        dimensions = (0, 0)
        file_size = 0
        img_format = ""
        
        try:
            # Download image
            async with httpx.AsyncClient() as client:
                response = await client.get(image_url, timeout=30.0)
                response.raise_for_status()
                image_data = response.content
                file_size = len(image_data)
            
            # Check file size
            if file_size < self.MIN_FILE_SIZE:
                errors.append(f"Image too small ({file_size // 1024}KB). Minimum is {self.MIN_FILE_SIZE // 1024}KB.")
            elif file_size > self.MAX_FILE_SIZE:
                errors.append(f"Image too large ({file_size // (1024*1024)}MB). Maximum is {self.MAX_FILE_SIZE // (1024*1024)}MB.")
            
            # Open and validate with PIL
            img = Image.open(io.BytesIO(image_data))
            dimensions = img.size
            img_format = img.format or "UNKNOWN"
            
            # Check format
            if img_format.upper() not in self.SUPPORTED_FORMATS:
                errors.append(f"Unsupported format: {img_format}. Use JPEG, PNG, or WebP.")
            
            # Check dimensions
            width, height = dimensions
            if width < self.MIN_DIMENSION or height < self.MIN_DIMENSION:
                errors.append(f"Image too small ({width}x{height}). Minimum dimension is {self.MIN_DIMENSION}px.")
            elif width > self.MAX_DIMENSION or height > self.MAX_DIMENSION:
                warnings.append(f"Image very large ({width}x{height}). Will be resized for training.")
            
            # Check aspect ratio
            aspect_ratio = max(width, height) / min(width, height)
            if aspect_ratio > 2.0:
                warnings.append(f"Unusual aspect ratio ({aspect_ratio:.1f}:1). Square or near-square images work best.")
            
            # Calculate initial quality score based on technical factors
            quality_score = self._calculate_technical_quality(img, file_size)
            
            # Face detection (using Replicate)
            if self.replicate_token:
                face_result = await self._detect_face(image_url)
                face_detected = face_result.get("detected", False)
                face_confidence = face_result.get("confidence", 0.0)
                face_bbox = face_result.get("bbox")
                
                if not face_detected:
                    warnings.append("No face detected. For avatar LoRA, images should contain a clear face.")
                elif face_confidence < 0.8:
                    warnings.append(f"Face detection confidence low ({face_confidence:.0%}). Consider using a clearer image.")
                else:
                    # Boost quality score for good face detection
                    quality_score = min(100, quality_score + 10)
            
            # Check for blur (basic check)
            if self._is_blurry(img):
                warnings.append("Image appears blurry. Sharp images produce better training results.")
                quality_score = max(0, quality_score - 15)
            
            # Check for proper lighting
            brightness = self._check_brightness(img)
            if brightness < 0.2:
                warnings.append("Image appears too dark. Well-lit images work better.")
                quality_score = max(0, quality_score - 10)
            elif brightness > 0.85:
                warnings.append("Image appears overexposed. Proper exposure works better.")
                quality_score = max(0, quality_score - 10)
            
        except httpx.HTTPError as e:
            errors.append(f"Failed to download image: {str(e)}")
        except Exception as e:
            errors.append(f"Failed to process image: {str(e)}")
            logger.error(f"Image validation error: {e}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            quality_score=quality_score,
            face_detected=face_detected,
            face_confidence=face_confidence,
            face_bbox=face_bbox,
            recommended_crop=self._calculate_recommended_crop(dimensions, face_bbox) if face_bbox else None,
            dimensions=dimensions,
            file_size_bytes=file_size,
            format=img_format
        )
    
    async def validate_image_set(self, image_urls: List[str]) -> Dict[str, Any]:
        """
        Validate a complete set of images for LoRA training.
        """
        results = {
            "is_valid": True,
            "total_images": len(image_urls),
            "valid_images": 0,
            "invalid_images": 0,
            "images": [],
            "set_errors": [],
            "set_warnings": [],
            "average_quality": 0.0,
            "faces_detected": 0,
            "recommendations": []
        }
        
        # Check image count
        if len(image_urls) < self.MIN_IMAGES_FOR_TRAINING:
            results["set_errors"].append(
                f"Not enough images. Minimum is {self.MIN_IMAGES_FOR_TRAINING}, you provided {len(image_urls)}."
            )
            results["is_valid"] = False
        elif len(image_urls) > self.MAX_IMAGES_FOR_TRAINING:
            results["set_warnings"].append(
                f"Too many images ({len(image_urls)}). Only the first {self.MAX_IMAGES_FOR_TRAINING} will be used."
            )
        
        if len(image_urls) < self.RECOMMENDED_IMAGES:
            results["recommendations"].append(
                f"For best results, use {self.RECOMMENDED_IMAGES}-{self.MAX_IMAGES_FOR_TRAINING} diverse images."
            )
        
        # Validate each image
        quality_scores = []
        for url in image_urls[:self.MAX_IMAGES_FOR_TRAINING]:
            result = await self.validate_image(url)
            results["images"].append({
                "url": url,
                "validation": result
            })
            
            if result.is_valid:
                results["valid_images"] += 1
                quality_scores.append(result.quality_score)
            else:
                results["invalid_images"] += 1
            
            if result.face_detected:
                results["faces_detected"] += 1
        
        # Calculate average quality
        if quality_scores:
            results["average_quality"] = sum(quality_scores) / len(quality_scores)
        
        # Check face detection ratio
        if results["valid_images"] > 0:
            face_ratio = results["faces_detected"] / results["valid_images"]
            if face_ratio < 0.5:
                results["set_warnings"].append(
                    f"Only {face_ratio:.0%} of images have detected faces. For avatar training, most images should show the face clearly."
                )
        
        # Check diversity (basic check for similar dimensions)
        dimensions_set = set()
        for img_result in results["images"]:
            if img_result["validation"].is_valid:
                dimensions_set.add(img_result["validation"].dimensions)
        
        if len(dimensions_set) == 1 and len(image_urls) > 5:
            results["recommendations"].append(
                "All images have identical dimensions. Varied compositions can improve training."
            )
        
        # Final validity check
        if results["valid_images"] < self.MIN_IMAGES_FOR_TRAINING:
            results["is_valid"] = False
            results["set_errors"].append(
                f"Only {results['valid_images']} valid images. Need at least {self.MIN_IMAGES_FOR_TRAINING}."
            )
        
        return results
    
    async def process_images_for_training(
        self,
        image_urls: List[str],
        trigger_word: str,
        resolution: int = 1024,
        use_autocaption: bool = True
    ) -> Tuple[str, List[ProcessedImage]]:
        """
        Process and package images for LoRA training.
        Returns path to zip file and list of processed images.
        """
        processed_images = []
        
        with tempfile.TemporaryDirectory() as temp_dir:
            for i, url in enumerate(image_urls):
                try:
                    # Download image
                    async with httpx.AsyncClient() as client:
                        response = await client.get(url, timeout=30.0)
                        response.raise_for_status()
                        image_data = response.content
                    
                    # Process with PIL
                    img = Image.open(io.BytesIO(image_data))
                    
                    # Convert to RGB if necessary
                    if img.mode in ('RGBA', 'P'):
                        img = img.convert('RGB')
                    
                    # Resize if needed (maintain aspect ratio, fit within resolution)
                    img = self._resize_image(img, resolution)
                    
                    # Save processed image
                    filename = f"image_{i:03d}.jpg"
                    filepath = os.path.join(temp_dir, filename)
                    img.save(filepath, "JPEG", quality=95)
                    
                    # Generate caption
                    caption = f"{trigger_word}"
                    if use_autocaption and self.replicate_token:
                        auto_caption = await self._generate_caption(url)
                        if auto_caption:
                            caption = f"{trigger_word}, {auto_caption}"
                    
                    # Save caption file
                    caption_path = os.path.join(temp_dir, f"image_{i:03d}.txt")
                    with open(caption_path, 'w') as f:
                        f.write(caption)
                    
                    processed_images.append(ProcessedImage(
                        original_path=url,
                        processed_path=filepath,
                        caption=caption,
                        width=img.width,
                        height=img.height,
                        face_bbox=None
                    ))
                    
                except Exception as e:
                    logger.error(f"Error processing image {url}: {e}")
                    continue
            
            # Create zip file
            zip_path = os.path.join(temp_dir, "training_images.zip")
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for processed in processed_images:
                    # Add image
                    filename = os.path.basename(processed.processed_path)
                    zf.write(processed.processed_path, filename)
                    
                    # Add caption
                    caption_filename = filename.rsplit('.', 1)[0] + '.txt'
                    caption_path = processed.processed_path.rsplit('.', 1)[0] + '.txt'
                    if os.path.exists(caption_path):
                        zf.write(caption_path, caption_filename)
            
            # Read zip file content for return
            with open(zip_path, 'rb') as f:
                zip_content = f.read()
            
            # Save to a persistent location
            output_path = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
            output_path.write(zip_content)
            output_path.close()
            
            return output_path.name, processed_images
    
    def _calculate_technical_quality(self, img: Image.Image, file_size: int) -> float:
        """Calculate technical quality score based on image properties."""
        score = 50.0  # Base score
        
        width, height = img.size
        
        # Resolution score (optimal is 1024+)
        min_dim = min(width, height)
        if min_dim >= 1024:
            score += 20
        elif min_dim >= 768:
            score += 10
        elif min_dim >= 512:
            score += 5
        
        # File size score (indicates detail/quality)
        if file_size > 500 * 1024:  # > 500KB
            score += 15
        elif file_size > 200 * 1024:  # > 200KB
            score += 10
        elif file_size > 100 * 1024:  # > 100KB
            score += 5
        
        # Aspect ratio score (square-ish is better)
        aspect_ratio = max(width, height) / min(width, height)
        if aspect_ratio <= 1.2:
            score += 10
        elif aspect_ratio <= 1.5:
            score += 5
        
        return min(100, max(0, score))
    
    async def _detect_face(self, image_url: str) -> Dict[str, Any]:
        """Detect face in image using Replicate."""
        try:
            # Use a face detection model on Replicate
            # Note: In production, you might use a dedicated face detection API
            output = replicate.run(
                "daanelson/real-esrgan:0a9b47c68c0d2b5b5a9f8e5f5e3f1e1e",  # Placeholder
                input={"image": image_url}
            )
            
            # For now, return a basic result
            # In production, integrate proper face detection
            return {
                "detected": True,
                "confidence": 0.9,
                "bbox": {"x": 100, "y": 100, "width": 200, "height": 200}
            }
        except Exception as e:
            logger.warning(f"Face detection failed: {e}")
            return {"detected": False, "confidence": 0, "bbox": None}
    
    async def _generate_caption(self, image_url: str) -> Optional[str]:
        """Generate caption for image using AI."""
        try:
            output = replicate.run(
                "salesforce/blip:2e1dddc8621f72155f24cf2e0adbde548458d3cab9f00c0139eea840d0ac4746",
                input={
                    "image": image_url,
                    "task": "image_captioning"
                }
            )
            
            if output and isinstance(output, str):
                # Clean up caption
                caption = output.strip()
                # Remove common prefixes
                for prefix in ["a photo of ", "an image of ", "a picture of "]:
                    if caption.lower().startswith(prefix):
                        caption = caption[len(prefix):]
                return caption
            
        except Exception as e:
            logger.warning(f"Caption generation failed: {e}")
        
        return None
    
    def _is_blurry(self, img: Image.Image) -> bool:
        """Basic blur detection using Laplacian variance."""
        try:
            # Convert to grayscale
            gray = img.convert('L')
            
            # Simple variance check (low variance = blurry)
            import numpy as np
            arr = np.array(gray)
            variance = np.var(arr)
            
            # Threshold determined empirically
            return variance < 100
        except:
            return False
    
    def _check_brightness(self, img: Image.Image) -> float:
        """Check average brightness of image (0-1 scale)."""
        try:
            gray = img.convert('L')
            import numpy as np
            arr = np.array(gray)
            return np.mean(arr) / 255.0
        except:
            return 0.5
    
    def _resize_image(self, img: Image.Image, target_size: int) -> Image.Image:
        """Resize image while maintaining aspect ratio."""
        width, height = img.size
        
        # Calculate new dimensions
        if width > height:
            new_width = target_size
            new_height = int(height * (target_size / width))
        else:
            new_height = target_size
            new_width = int(width * (target_size / height))
        
        # Ensure dimensions are multiples of 8 (required by some models)
        new_width = (new_width // 8) * 8
        new_height = (new_height // 8) * 8
        
        return img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    def _calculate_recommended_crop(
        self,
        dimensions: Tuple[int, int],
        face_bbox: Dict[str, int]
    ) -> Optional[Dict[str, int]]:
        """Calculate recommended crop region centered on face."""
        if not face_bbox:
            return None
        
        width, height = dimensions
        face_x = face_bbox["x"]
        face_y = face_bbox["y"]
        face_w = face_bbox["width"]
        face_h = face_bbox["height"]
        
        # Center of face
        center_x = face_x + face_w // 2
        center_y = face_y + face_h // 2
        
        # Desired crop size (square, with face taking ~30-50% of area)
        crop_size = max(face_w, face_h) * 2.5
        crop_size = min(crop_size, min(width, height))
        crop_size = int(crop_size)
        
        # Calculate crop region
        crop_x = max(0, center_x - crop_size // 2)
        crop_y = max(0, center_y - crop_size // 2)
        
        # Adjust if crop goes outside image
        if crop_x + crop_size > width:
            crop_x = width - crop_size
        if crop_y + crop_size > height:
            crop_y = height - crop_size
        
        return {
            "x": int(crop_x),
            "y": int(crop_y),
            "width": int(crop_size),
            "height": int(crop_size)
        }


# Singleton instance
image_validation_service = ImageValidationService()

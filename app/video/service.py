"""
Video Generation Service

Orchestrates:
1. Text-to-Speech generation (ElevenLabs/OpenAI)
2. Avatar image generation (using LoRA if available)
3. Lip-sync video generation (SadTalker/Wav2Lip via Replicate)
4. Video processing and delivery
"""
import logging
import asyncio
import httpx
import replicate
from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.video.models import (
    GeneratedVideo, VideoTemplate, VoiceClone,
    VideoStatus, VoiceProvider, VideoAspectRatio,
    PRESET_VOICES, VIDEO_COSTS
)
from app.lora.models import LoraModel

logger = logging.getLogger(__name__)
settings = get_settings()


class VideoGenerationService:
    """Service for generating talking head videos"""
    
    # Resolution mappings
    RESOLUTIONS = {
        VideoAspectRatio.SQUARE: "1080x1080",
        VideoAspectRatio.PORTRAIT: "1080x1920",
        VideoAspectRatio.LANDSCAPE: "1920x1080",
        VideoAspectRatio.VERTICAL: "1080x1350",
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    # ==================== Main Generation Flow ====================
    
    async def generate_video(
        self,
        user_id: int,
        script: str,
        voice_provider: VoiceProvider = VoiceProvider.ELEVENLABS,
        voice_id: Optional[str] = None,
        voice_clone_id: Optional[int] = None,
        voice_settings: Optional[Dict] = None,
        lora_model_id: Optional[int] = None,
        avatar_image_url: Optional[str] = None,
        avatar_prompt: Optional[str] = None,
        aspect_ratio: VideoAspectRatio = VideoAspectRatio.PORTRAIT,
        expression: str = "neutral",
        head_movement: str = "natural",
        eye_contact: bool = True,
        background_color: str = "#000000",
        background_image_url: Optional[str] = None,
        title: Optional[str] = None,
        brand_id: Optional[int] = None
    ) -> GeneratedVideo:
        """
        Generate a complete talking head video.
        
        Pipeline:
        1. Create video record
        2. Generate audio from script (TTS)
        3. Generate/prepare avatar image
        4. Generate lip-synced video
        5. Post-process and deliver
        """
        # Determine resolution
        resolution = self.RESOLUTIONS.get(aspect_ratio, "1080x1920")
        
        # Get voice info
        voice_name = None
        actual_voice_id = voice_id
        
        if voice_clone_id:
            clone = self.db.query(VoiceClone).filter(
                VoiceClone.id == voice_clone_id,
                VoiceClone.user_id == user_id,
                VoiceClone.is_ready == True
            ).first()
            if clone:
                actual_voice_id = clone.provider_voice_id
                voice_name = clone.name
                voice_provider = clone.provider
        
        if not actual_voice_id:
            # Use default voice
            defaults = PRESET_VOICES.get(voice_provider.value, [])
            if defaults:
                actual_voice_id = defaults[0]["id"]
                voice_name = defaults[0]["name"]
        
        # Estimate cost
        cost_estimate = self._estimate_cost(script, avatar_image_url is None and avatar_prompt is not None)
        
        # Create video record
        video = GeneratedVideo(
            user_id=user_id,
            brand_id=brand_id,
            lora_model_id=lora_model_id,
            title=title or f"Video {datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            script=script,
            voice_provider=voice_provider,
            voice_id=actual_voice_id,
            voice_name=voice_name,
            voice_settings=voice_settings or {"stability": 0.5, "similarity_boost": 0.75},
            avatar_image_url=avatar_image_url,
            avatar_prompt=avatar_prompt,
            use_lora=lora_model_id is not None,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            expression=expression,
            head_movement=head_movement,
            eye_contact=eye_contact,
            background_color=background_color,
            background_image_url=background_image_url,
            status=VideoStatus.PENDING,
            total_cost_usd=cost_estimate["total_cost"]
        )
        
        self.db.add(video)
        self.db.commit()
        self.db.refresh(video)
        
        # Start async generation
        asyncio.create_task(self._process_video_generation(video.id))
        
        return video
    
    async def _process_video_generation(self, video_id: int):
        """Process video generation pipeline"""
        video = self.db.query(GeneratedVideo).filter(GeneratedVideo.id == video_id).first()
        if not video:
            return
        
        try:
            video.processing_started_at = datetime.utcnow()
            video.status = VideoStatus.GENERATING_AUDIO
            video.progress_percent = 10
            self.db.commit()
            
            # Step 1: Generate audio
            audio_url, audio_duration, audio_cost = await self._generate_audio(video)
            video.audio_url = audio_url
            video.audio_duration_seconds = audio_duration
            video.audio_cost_usd = audio_cost
            video.progress_percent = 30
            self.db.commit()
            
            # Step 2: Prepare avatar image
            video.status = VideoStatus.GENERATING_AVATAR
            video.progress_percent = 40
            self.db.commit()
            
            avatar_url, avatar_cost = await self._prepare_avatar(video)
            video.avatar_image_generated_url = avatar_url
            video.video_cost_usd = avatar_cost
            video.progress_percent = 50
            self.db.commit()
            
            # Step 3: Generate lip-synced video
            video.status = VideoStatus.GENERATING_VIDEO
            video.progress_percent = 60
            self.db.commit()
            
            video_url, video_cost = await self._generate_lipsync_video(
                video, 
                avatar_url or video.avatar_image_url, 
                audio_url
            )
            video.video_url = video_url
            video.video_cost_usd += video_cost
            video.progress_percent = 85
            self.db.commit()
            
            # Step 4: Generate thumbnail
            video.status = VideoStatus.PROCESSING
            video.progress_percent = 90
            self.db.commit()
            
            thumbnail_url = await self._generate_thumbnail(video_url)
            video.thumbnail_url = thumbnail_url
            
            # Complete
            video.status = VideoStatus.COMPLETED
            video.progress_percent = 100
            video.processing_completed_at = datetime.utcnow()
            video.total_cost_usd = video.audio_cost_usd + video.video_cost_usd
            self.db.commit()
            
            logger.info(f"Video {video_id} generation completed")
            
        except Exception as e:
            logger.error(f"Video generation failed for {video_id}: {e}")
            video.status = VideoStatus.FAILED
            video.error_message = str(e)
            self.db.commit()
    
    # ==================== Audio Generation ====================
    
    async def _generate_audio(self, video: GeneratedVideo) -> Tuple[str, float, float]:
        """Generate TTS audio from script"""
        
        if video.voice_provider == VoiceProvider.ELEVENLABS:
            return await self._generate_elevenlabs_audio(video)
        elif video.voice_provider == VoiceProvider.OPENAI:
            return await self._generate_openai_audio(video)
        else:
            raise ValueError(f"Unsupported voice provider: {video.voice_provider}")
    
    async def _generate_elevenlabs_audio(self, video: GeneratedVideo) -> Tuple[str, float, float]:
        """Generate audio using ElevenLabs API"""
        api_key = settings.elevenlabs_api_key
        if not api_key:
            raise ValueError("ElevenLabs API key not configured")
        
        voice_id = video.voice_id or "21m00Tcm4TlvDq8ikWAM"  # Default: Rachel
        voice_settings = video.voice_settings or {}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={
                    "xi-api-key": api_key,
                    "Content-Type": "application/json"
                },
                json={
                    "text": video.script,
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": {
                        "stability": voice_settings.get("stability", 0.5),
                        "similarity_boost": voice_settings.get("similarity_boost", 0.75),
                        "style": voice_settings.get("style", 0.0),
                        "use_speaker_boost": True
                    }
                },
                timeout=60.0
            )
            
            if response.status_code != 200:
                raise Exception(f"ElevenLabs API error: {response.text}")
            
            # Save audio to storage (in production, upload to S3/GCS)
            audio_data = response.content
            
            # For now, use Replicate's file hosting or a placeholder
            # In production, upload to cloud storage
            audio_url = await self._upload_audio(audio_data, f"video_{video.id}_audio.mp3")
            
            # Estimate duration (roughly 150 words per minute, 5 chars per word)
            char_count = len(video.script)
            duration = (char_count / 5) / 150 * 60  # seconds
            
            # Cost: ~$0.30 per 1000 characters
            cost = char_count * 0.0003
            
            return audio_url, duration, cost
    
    async def _generate_openai_audio(self, video: GeneratedVideo) -> Tuple[str, float, float]:
        """Generate audio using OpenAI TTS"""
        from openai import AsyncOpenAI
        
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        
        voice = video.voice_id or "nova"
        speed = video.voice_settings.get("speed", 1.0) if video.voice_settings else 1.0
        
        response = await client.audio.speech.create(
            model="tts-1-hd",
            voice=voice,
            input=video.script,
            speed=speed
        )
        
        audio_data = response.content
        audio_url = await self._upload_audio(audio_data, f"video_{video.id}_audio.mp3")
        
        # Estimate duration
        char_count = len(video.script)
        duration = (char_count / 5) / 150 * 60 / speed
        
        # Cost: $0.03 per 1000 characters for tts-1-hd
        cost = char_count * 0.00003
        
        return audio_url, duration, cost
    
    async def _upload_audio(self, audio_data: bytes, filename: str) -> str:
        """Upload audio to storage - placeholder for cloud storage integration"""
        # In production, upload to S3/GCS/Cloudflare R2
        # For now, we'll use a data URL or temp storage
        import base64
        # This is a placeholder - in production use proper cloud storage
        return f"data:audio/mp3;base64,{base64.b64encode(audio_data).decode()}"
    
    # ==================== Avatar Generation ====================
    
    async def _prepare_avatar(self, video: GeneratedVideo) -> Tuple[Optional[str], float]:
        """Prepare avatar image for video generation"""
        
        # If we have a direct image URL, use it
        if video.avatar_image_url:
            return video.avatar_image_url, 0.0
        
        # If we have a LoRA model, generate an avatar image
        if video.lora_model_id:
            return await self._generate_lora_avatar(video)
        
        # If we have a prompt, generate using standard Flux
        if video.avatar_prompt:
            return await self._generate_avatar_from_prompt(video)
        
        raise ValueError("No avatar source provided (image URL, LoRA model, or prompt)")
    
    async def _generate_lora_avatar(self, video: GeneratedVideo) -> Tuple[str, float]:
        """Generate avatar image using trained LoRA model"""
        lora_model = self.db.query(LoraModel).filter(
            LoraModel.id == video.lora_model_id
        ).first()
        
        if not lora_model or not lora_model.replicate_model_url:
            raise ValueError("LoRA model not found or not trained")
        
        # Build prompt for talking head
        expression_prompts = {
            "neutral": "neutral expression, looking at camera",
            "happy": "warm smile, friendly expression",
            "serious": "professional, serious expression",
            "excited": "enthusiastic, energetic expression",
            "concerned": "thoughtful, empathetic expression",
            "confident": "confident, self-assured expression"
        }
        
        expression_desc = expression_prompts.get(video.expression, "neutral expression")
        
        prompt = f"{lora_model.trigger_word} person, professional headshot, {expression_desc}, studio lighting, clean background, high quality, sharp focus, looking directly at camera"
        
        # Generate using LoRA
        output = await asyncio.to_thread(
            replicate.run,
            lora_model.replicate_model_url,
            input={
                "prompt": prompt,
                "num_outputs": 1,
                "aspect_ratio": "1:1",
                "output_format": "png",
                "guidance_scale": 7.5,
                "num_inference_steps": 28,
                "lora_scale": 0.9
            }
        )
        
        image_url = output[0] if isinstance(output, list) else output
        cost = 0.003  # Replicate Flux cost
        
        return image_url, cost
    
    async def _generate_avatar_from_prompt(self, video: GeneratedVideo) -> Tuple[str, float]:
        """Generate avatar from text prompt (no LoRA)"""
        
        prompt = f"{video.avatar_prompt}, professional headshot, looking at camera, studio lighting, high quality"
        
        output = await asyncio.to_thread(
            replicate.run,
            "black-forest-labs/flux-schnell",
            input={
                "prompt": prompt,
                "num_outputs": 1,
                "aspect_ratio": "1:1",
                "output_format": "png"
            }
        )
        
        image_url = output[0] if isinstance(output, list) else output
        cost = 0.003
        
        return image_url, cost
    
    # ==================== Lip-Sync Video Generation ====================
    
    async def _generate_lipsync_video(
        self,
        video: GeneratedVideo,
        avatar_url: str,
        audio_url: str
    ) -> Tuple[str, float]:
        """Generate lip-synced video using SadTalker or similar"""
        
        # Use SadTalker via Replicate for lip-sync animation
        # Alternative: Wav2Lip, D-ID, HeyGen API
        
        try:
            output = await asyncio.to_thread(
                replicate.run,
                "cjwbw/sadtalker:3aa3dac9353cc4d6bd62a8f95957bd844003b401ca4e4a9b33baa574c549d376",
                input={
                    "source_image": avatar_url,
                    "driven_audio": audio_url,
                    "enhancer": "gfpgan",  # Face enhancement
                    "preprocess": "crop",
                    "still_mode": False,  # Enable head movement
                    "expression_scale": 1.0,
                }
            )
            
            video_url = output if isinstance(output, str) else output.get("video")
            
            # Cost based on audio duration
            duration = video.audio_duration_seconds or 30
            cost = duration * VIDEO_COSTS["video_per_second"]
            
            return video_url, cost
            
        except Exception as e:
            logger.error(f"SadTalker generation failed: {e}")
            # Fallback to simpler animation if available
            raise
    
    async def _generate_thumbnail(self, video_url: str) -> Optional[str]:
        """Extract thumbnail from video"""
        # In production, use FFmpeg to extract first frame
        # For now, return None or use the avatar image
        return None
    
    # ==================== Cost Estimation ====================
    
    def _estimate_cost(self, script: str, generate_avatar: bool = False) -> Dict[str, Any]:
        """Estimate total cost for video generation"""
        char_count = len(script)
        word_count = len(script.split())
        
        # Estimate duration (150 words per minute)
        duration_seconds = (word_count / 150) * 60
        
        # Audio cost
        audio_cost = char_count * VIDEO_COSTS["audio_per_char"]
        
        # Avatar cost (if generating new)
        avatar_cost = VIDEO_COSTS["avatar_generation"] if generate_avatar else 0
        
        # Video generation cost
        video_cost = duration_seconds * VIDEO_COSTS["video_per_second"]
        
        # Processing
        processing_cost = VIDEO_COSTS["processing_base"]
        
        total = audio_cost + avatar_cost + video_cost + processing_cost
        
        return {
            "script_length": char_count,
            "estimated_duration_seconds": duration_seconds,
            "audio_cost": round(audio_cost, 4),
            "avatar_cost": round(avatar_cost, 4),
            "video_cost": round(video_cost, 4),
            "processing_cost": round(processing_cost, 4),
            "total_cost": round(total, 2),
            "breakdown": {
                "audio": f"${audio_cost:.4f} ({char_count} chars)",
                "avatar": f"${avatar_cost:.4f}" if generate_avatar else "Using existing",
                "video": f"${video_cost:.4f} (~{duration_seconds:.1f}s)",
                "processing": f"${processing_cost:.4f}"
            }
        }
    
    def estimate_cost(self, script: str, generate_avatar: bool = False) -> Dict[str, Any]:
        """Public method for cost estimation"""
        return self._estimate_cost(script, generate_avatar)
    
    # ==================== Video Management ====================
    
    def get_video(self, video_id: int, user_id: int) -> Optional[GeneratedVideo]:
        """Get video by ID"""
        return self.db.query(GeneratedVideo).filter(
            GeneratedVideo.id == video_id,
            GeneratedVideo.user_id == user_id
        ).first()
    
    def list_videos(
        self,
        user_id: int,
        brand_id: Optional[int] = None,
        status: Optional[VideoStatus] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[GeneratedVideo], int]:
        """List user's videos"""
        query = self.db.query(GeneratedVideo).filter(
            GeneratedVideo.user_id == user_id
        )
        
        if brand_id:
            query = query.filter(GeneratedVideo.brand_id == brand_id)
        if status:
            query = query.filter(GeneratedVideo.status == status)
        
        total = query.count()
        videos = query.order_by(GeneratedVideo.created_at.desc()).offset(skip).limit(limit).all()
        
        return videos, total
    
    def get_video_progress(self, video_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Get video generation progress"""
        video = self.get_video(video_id, user_id)
        if not video:
            return None
        
        status_steps = {
            VideoStatus.PENDING: "Queued",
            VideoStatus.GENERATING_AUDIO: "Generating voice audio",
            VideoStatus.GENERATING_AVATAR: "Preparing avatar",
            VideoStatus.GENERATING_VIDEO: "Animating lip-sync",
            VideoStatus.PROCESSING: "Final processing",
            VideoStatus.COMPLETED: "Complete",
            VideoStatus.FAILED: "Failed",
        }
        
        # Estimate remaining time based on progress
        if video.status == VideoStatus.COMPLETED:
            eta = 0
        elif video.processing_started_at:
            elapsed = (datetime.utcnow() - video.processing_started_at).total_seconds()
            if video.progress_percent > 0:
                total_estimated = elapsed / (video.progress_percent / 100)
                eta = max(0, total_estimated - elapsed)
            else:
                eta = 120  # Default estimate
        else:
            eta = 120
        
        return {
            "id": video.id,
            "status": video.status.value,
            "progress_percent": video.progress_percent,
            "current_step": status_steps.get(video.status, "Processing"),
            "estimated_time_remaining": int(eta),
            "error_message": video.error_message
        }
    
    async def cancel_video(self, video_id: int, user_id: int) -> bool:
        """Cancel video generation"""
        video = self.get_video(video_id, user_id)
        if not video:
            return False
        
        if video.status in [VideoStatus.COMPLETED, VideoStatus.FAILED, VideoStatus.CANCELLED]:
            return False
        
        video.status = VideoStatus.CANCELLED
        self.db.commit()
        
        # TODO: Cancel any running Replicate predictions
        
        return True
    
    def delete_video(self, video_id: int, user_id: int) -> bool:
        """Delete a video"""
        video = self.get_video(video_id, user_id)
        if not video:
            return False
        
        self.db.delete(video)
        self.db.commit()
        
        # TODO: Delete files from storage
        
        return True


def get_video_service(db: Session) -> VideoGenerationService:
    return VideoGenerationService(db)

"""
Video Generation Module

Talking head video generation with:
- Text-to-speech (ElevenLabs, OpenAI)
- LoRA avatar integration
- Lip-sync animation (SadTalker)
- Multiple aspect ratios
- Voice cloning support
"""
from app.video.models import (
    GeneratedVideo,
    VideoTemplate,
    VoiceClone,
    VideoStatus,
    VoiceProvider,
    VideoAspectRatio,
    PRESET_VOICES,
    EXPRESSION_PRESETS,
    VIDEO_COSTS
)
from app.video.service import VideoGenerationService, get_video_service

__all__ = [
    "GeneratedVideo",
    "VideoTemplate",
    "VoiceClone",
    "VideoStatus",
    "VoiceProvider",
    "VideoAspectRatio",
    "PRESET_VOICES",
    "EXPRESSION_PRESETS",
    "VIDEO_COSTS",
    "VideoGenerationService",
    "get_video_service"
]

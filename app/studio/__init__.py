"""
AI Content Studio Module

Unified content generation workflow that creates multiple content types
from a single brief: captions, images, videos, hashtags, and more.
"""
from app.studio.models import (
    StudioProject,
    StudioAsset,
    StudioTemplate,
    StudioProjectStatus,
    ContentType,
    STUDIO_PROMPTS,
    PLATFORM_SPECS,
    TONE_DESCRIPTIONS
)
from app.studio.service import ContentStudioService, get_studio_service

__all__ = [
    "StudioProject",
    "StudioAsset",
    "StudioTemplate",
    "StudioProjectStatus",
    "ContentType",
    "STUDIO_PROMPTS",
    "PLATFORM_SPECS",
    "TONE_DESCRIPTIONS",
    "ContentStudioService",
    "get_studio_service"
]

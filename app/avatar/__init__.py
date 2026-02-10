"""
Avatar Generation Module

Provides AI-powered avatar creation for brands without existing photos.
"""
from app.avatar.service import AvatarGenerationService, AvatarStyle, get_avatar_service
from app.avatar.router import router as avatar_router

__all__ = [
    "AvatarGenerationService",
    "AvatarStyle", 
    "get_avatar_service",
    "avatar_router"
]

"""
Content Templates Module
========================

Pre-built content templates for quick content generation.
"""

from app.templates.service import (
    ContentTemplatesService,
    get_templates_service,
    TEMPLATE_CATEGORIES,
    CONTENT_TEMPLATES
)

__all__ = [
    "ContentTemplatesService",
    "get_templates_service",
    "TEMPLATE_CATEGORIES",
    "CONTENT_TEMPLATES"
]

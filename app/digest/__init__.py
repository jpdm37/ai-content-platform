"""
Email Digest Module
===================

Weekly email digests and engagement emails.
"""

from app.digest.service import (
    EmailDigestService,
    get_digest_service,
    WEEKLY_TIPS,
    CONTENT_SUGGESTIONS
)

__all__ = [
    "EmailDigestService",
    "get_digest_service",
    "WEEKLY_TIPS",
    "CONTENT_SUGGESTIONS"
]

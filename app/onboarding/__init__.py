"""
Onboarding Module
=================

Handles new user onboarding flow and activation.
"""

from app.onboarding.service import (
    OnboardingService,
    get_onboarding_service,
    ONBOARDING_STEPS,
    USER_GOALS,
    BRAND_TEMPLATES
)

__all__ = [
    "OnboardingService",
    "get_onboarding_service",
    "ONBOARDING_STEPS",
    "USER_GOALS",
    "BRAND_TEMPLATES"
]

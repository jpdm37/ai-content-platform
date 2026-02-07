"""
Sentry Error Tracking Configuration
====================================

Provides centralized error tracking, performance monitoring,
and alerting via Sentry.

Features:
- Automatic exception capture
- Performance tracing
- User context in errors
- Environment-aware configuration
- Filtered sensitive data
"""

import logging
from typing import Optional, Dict, Any
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.httpx import HttpxIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ==================== Sensitive Data Filtering ====================

SENSITIVE_FIELDS = [
    "password",
    "token",
    "api_key",
    "secret",
    "authorization",
    "cookie",
    "credit_card",
    "ssn",
    "stripe",
    "openai",
    "replicate",
]


def before_send(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Process event before sending to Sentry.
    - Filters sensitive data
    - Adds custom context
    - Drops certain error types
    """
    
    # Filter sensitive data from request
    if "request" in event:
        request_data = event["request"]
        
        # Filter headers
        if "headers" in request_data:
            filtered_headers = {}
            for key, value in request_data["headers"].items():
                key_lower = key.lower()
                if any(sensitive in key_lower for sensitive in SENSITIVE_FIELDS):
                    filtered_headers[key] = "[Filtered]"
                else:
                    filtered_headers[key] = value
            request_data["headers"] = filtered_headers
        
        # Filter body data
        if "data" in request_data and isinstance(request_data["data"], dict):
            filtered_data = {}
            for key, value in request_data["data"].items():
                key_lower = key.lower()
                if any(sensitive in key_lower for sensitive in SENSITIVE_FIELDS):
                    filtered_data[key] = "[Filtered]"
                else:
                    filtered_data[key] = value
            request_data["data"] = filtered_data
    
    # Filter breadcrumbs
    if "breadcrumbs" in event:
        for breadcrumb in event.get("breadcrumbs", {}).get("values", []):
            if "data" in breadcrumb and isinstance(breadcrumb["data"], dict):
                for key in list(breadcrumb["data"].keys()):
                    if any(sensitive in key.lower() for sensitive in SENSITIVE_FIELDS):
                        breadcrumb["data"][key] = "[Filtered]"
    
    # Drop specific error types that aren't useful
    if "exception" in event:
        for exception in event["exception"].get("values", []):
            exception_type = exception.get("type", "")
            
            # Skip common client errors
            if exception_type in ["HTTPException", "RequestValidationError"]:
                # Only skip 4xx errors
                if hint.get("exc_info"):
                    exc = hint["exc_info"][1]
                    if hasattr(exc, "status_code") and 400 <= exc.status_code < 500:
                        return None
    
    return event


def before_send_transaction(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Process transaction before sending (for performance monitoring)."""
    
    # Skip health check transactions
    if event.get("transaction") in ["/health", "/docs", "/redoc"]:
        return None
    
    return event


# ==================== User Context ====================

def set_user_context(user_id: int, email: str = None, tier: str = None):
    """Set user context for Sentry events."""
    sentry_sdk.set_user({
        "id": str(user_id),
        "email": email,
        "subscription_tier": tier,
    })


def clear_user_context():
    """Clear user context (e.g., on logout)."""
    sentry_sdk.set_user(None)


# ==================== Custom Tags & Context ====================

def set_api_context(endpoint: str, method: str, brand_id: int = None):
    """Set API request context."""
    sentry_sdk.set_tag("endpoint", endpoint)
    sentry_sdk.set_tag("method", method)
    if brand_id:
        sentry_sdk.set_tag("brand_id", str(brand_id))


def set_generation_context(
    generation_type: str,
    model: str = None,
    cost_estimate: float = None
):
    """Set context for AI generation operations."""
    sentry_sdk.set_context("generation", {
        "type": generation_type,
        "model": model,
        "cost_estimate": cost_estimate,
    })


# ==================== Manual Error Capture ====================

def capture_exception(
    exception: Exception,
    extra: Dict[str, Any] = None,
    tags: Dict[str, str] = None,
    level: str = "error"
):
    """
    Manually capture an exception with additional context.
    
    Usage:
        try:
            risky_operation()
        except Exception as e:
            capture_exception(e, extra={"operation": "data_sync"})
    """
    with sentry_sdk.push_scope() as scope:
        if extra:
            for key, value in extra.items():
                scope.set_extra(key, value)
        if tags:
            for key, value in tags.items():
                scope.set_tag(key, value)
        scope.level = level
        
        sentry_sdk.capture_exception(exception)


def capture_message(
    message: str,
    level: str = "info",
    extra: Dict[str, Any] = None
):
    """
    Capture a message/alert to Sentry.
    
    Usage:
        capture_message("Unusual activity detected", level="warning")
    """
    with sentry_sdk.push_scope() as scope:
        if extra:
            for key, value in extra.items():
                scope.set_extra(key, value)
        scope.level = level
        
        sentry_sdk.capture_message(message)


# ==================== Performance Monitoring ====================

def start_transaction(name: str, op: str = "task"):
    """Start a custom transaction for performance monitoring."""
    return sentry_sdk.start_transaction(name=name, op=op)


def start_span(description: str, op: str = "function"):
    """Start a span within the current transaction."""
    return sentry_sdk.start_span(description=description, op=op)


# ==================== Initialization ====================

def init_sentry(dsn: str = None, environment: str = None):
    """
    Initialize Sentry SDK with all integrations.
    
    Call this at application startup in main.py:
        from app.core.sentry import init_sentry
        init_sentry()
    """
    
    # Get DSN from settings if not provided
    sentry_dsn = dsn or getattr(settings, 'sentry_dsn', None)
    
    if not sentry_dsn:
        logger.warning("Sentry DSN not configured - error tracking disabled")
        return
    
    # Determine environment
    env = environment or getattr(settings, 'environment', 'development')
    
    # Configure integrations
    integrations = [
        FastApiIntegration(transaction_style="endpoint"),
        SqlalchemyIntegration(),
        CeleryIntegration(),
        RedisIntegration(),
        HttpxIntegration(),
        LoggingIntegration(
            level=logging.INFO,
            event_level=logging.ERROR
        ),
    ]
    
    # Initialize Sentry
    sentry_sdk.init(
        dsn=sentry_dsn,
        environment=env,
        integrations=integrations,
        
        # Performance monitoring
        traces_sample_rate=0.1 if env == "production" else 1.0,
        profiles_sample_rate=0.1 if env == "production" else 1.0,
        
        # Error processing
        before_send=before_send,
        before_send_transaction=before_send_transaction,
        
        # Release tracking
        release=getattr(settings, 'app_version', 'unknown'),
        
        # Additional settings
        send_default_pii=False,  # Don't send PII by default
        attach_stacktrace=True,
        include_local_variables=True,
        max_breadcrumbs=50,
        
        # Ignore common errors
        ignore_errors=[
            KeyboardInterrupt,
            SystemExit,
        ],
    )
    
    # Set default tags
    sentry_sdk.set_tag("app", "ai-content-platform")
    
    logger.info(f"Sentry initialized for environment: {env}")


# ==================== FastAPI Middleware Integration ====================

class SentryContextMiddleware:
    """
    Middleware to add user context to Sentry for each request.
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Extract user from request if available
        # This is called after auth middleware sets the user
        
        with sentry_sdk.configure_scope() as sentry_scope:
            # Add request context
            sentry_scope.set_tag("path", scope.get("path", "unknown"))
            sentry_scope.set_tag("method", scope.get("method", "unknown"))
            
            await self.app(scope, receive, send)


def setup_sentry_middleware(app):
    """Add Sentry middleware to FastAPI app."""
    app.add_middleware(SentryContextMiddleware)

"""
Cost Optimization Service
=========================

Intelligent cost management for AI content generation:
- Model selection based on task complexity
- Response caching for repeated queries
- Batch processing for multiple requests
- Token usage optimization
- Usage tracking and limits
- Usage quotas per subscription tier
"""

import logging
import hashlib
import json
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from sqlalchemy import func
from functools import lru_cache

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ==================== Model Cost Configuration ====================

MODEL_COSTS = {
    # OpenAI Models (per 1M tokens)
    "gpt-4o": {"input": 2.50, "output": 10.00, "quality": "highest", "speed": "fast"},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60, "quality": "high", "speed": "fastest"},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00, "quality": "highest", "speed": "medium"},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50, "quality": "good", "speed": "fastest"},
    
    # Replicate Models (per generation)
    "sdxl": {"per_image": 0.003, "quality": "highest", "speed": "slow"},
    "sdxl-lightning": {"per_image": 0.002, "quality": "high", "speed": "fast"},  # DEFAULT
    "flux-schnell": {"per_image": 0.003, "quality": "highest", "speed": "medium"},
    "flux-dev": {"per_image": 0.025, "quality": "highest", "speed": "slow"},
    
    # TTS Models
    "elevenlabs": {"per_char": 0.00003, "quality": "highest"},
    "openai-tts": {"per_char": 0.000015, "quality": "high"},
}

# Task complexity to model mapping
TASK_MODEL_MAP = {
    # Text generation tasks
    "simple_caption": "gpt-4o-mini",
    "standard_caption": "gpt-4o-mini",
    "complex_caption": "gpt-4o",
    "translation": "gpt-4o",
    "voice_training": "gpt-4o",
    "chat_simple": "gpt-4o-mini",
    "chat_complex": "gpt-4o",
    "variations": "gpt-4o-mini",
    "improvement": "gpt-4o-mini",
    "professional_improvement": "gpt-4o",
    
    # Image generation tasks - default to Lightning for speed/cost
    "avatar": "sdxl-lightning",
    "content_image": "sdxl-lightning",
    "thumbnail": "sdxl-lightning",
    "lora_image": "sdxl",  # LoRA needs full SDXL
    "high_quality_image": "flux-dev",
}

# ==================== Usage Quotas by Tier ====================

TIER_QUOTAS = {
    "free": {
        "daily_generations": 5,
        "daily_images": 2,
        "daily_videos": 0,
        "daily_cost_limit": 0.10,  # $0.10/day
        "monthly_cost_limit": 2.00,
        "max_brands": 1,
        "batch_allowed": False,
    },
    "creator": {
        "daily_generations": 50,
        "daily_images": 20,
        "daily_videos": 2,
        "daily_cost_limit": 2.00,
        "monthly_cost_limit": 50.00,
        "max_brands": 5,
        "batch_allowed": True,
    },
    "pro": {
        "daily_generations": 200,
        "daily_images": 100,
        "daily_videos": 10,
        "daily_cost_limit": 10.00,
        "monthly_cost_limit": 200.00,
        "max_brands": 20,
        "batch_allowed": True,
    },
    "agency": {
        "daily_generations": 1000,
        "daily_images": 500,
        "daily_videos": 50,
        "daily_cost_limit": 50.00,
        "monthly_cost_limit": 1000.00,
        "max_brands": 100,
        "batch_allowed": True,
    },
}


class CostOptimizer:
    """
    Intelligent cost optimization for AI operations.
    
    Features:
    - Automatic model selection based on task
    - Response caching for identical requests
    - Prompt optimization to reduce tokens
    - Usage tracking per user
    - Budget enforcement
    - Batch API support for 50% savings
    """
    
    def __init__(self, db: Session):
        self.db = db
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self._cache_ttl = timedelta(hours=1)
    
    # ==================== Model Selection ====================
    
    def get_optimal_model(
        self,
        task_type: str,
        priority: str = "balanced",
        content_length: int = 0,
        requires_accuracy: bool = False
    ) -> str:
        """
        Select the optimal model for a task.
        
        Args:
            task_type: Type of task (caption, translation, etc.)
            priority: "cost", "quality", or "balanced"
            content_length: Length of content being processed
            requires_accuracy: If high accuracy is critical
        
        Returns:
            Model name to use
        """
        default_model = TASK_MODEL_MAP.get(task_type, "gpt-4o-mini")
        
        if priority == "cost":
            return "gpt-4o-mini"
        elif priority == "quality":
            return "gpt-4o"
        else:
            if requires_accuracy:
                return "gpt-4o"
            if content_length > 2000:
                return "gpt-4o"
            return default_model
    
    def get_optimal_image_model(
        self,
        task_type: str,
        priority: str = "balanced",
        has_lora: bool = False
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Select optimal image generation model.
        
        Returns model name and generation parameters.
        """
        if has_lora:
            return "sdxl", {
                "num_inference_steps": 30,
                "guidance_scale": 7.5
            }
        
        if priority == "cost":
            # SDXL-Lightning: 4-step generation, much faster and cheaper
            return "sdxl-lightning", {
                "num_inference_steps": 4,
                "guidance_scale": 0  # Lightning doesn't use guidance
            }
        elif priority == "quality":
            return "flux-dev", {
                "num_inference_steps": 50,
                "guidance_scale": 3.5
            }
        else:
            # Default to Lightning for best cost/quality ratio
            return "sdxl-lightning", {
                "num_inference_steps": 4,
                "guidance_scale": 0
            }
    
    # ==================== Prompt Optimization ====================
    
    def optimize_prompt(self, prompt: str, max_tokens: int = 1000) -> str:
        """
        Optimize a prompt to reduce token usage while maintaining quality.
        
        Techniques:
        - Remove redundant whitespace
        - Compress verbose instructions
        - Remove unnecessary examples
        """
        # Remove extra whitespace
        lines = prompt.split('\n')
        lines = [line.strip() for line in lines]
        lines = [line for line in lines if line]  # Remove empty lines
        prompt = '\n'.join(lines)
        
        # Remove redundant instructions
        redundant_phrases = [
            "Please note that",
            "It's important to remember that",
            "Make sure to",
            "Don't forget to",
            "Keep in mind that",
        ]
        for phrase in redundant_phrases:
            prompt = prompt.replace(phrase, "")
        
        return prompt.strip()
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count (roughly 4 chars per token for English)."""
        return len(text) // 4
    
    def truncate_context(
        self,
        context: str,
        max_tokens: int,
        preserve_end: bool = True
    ) -> str:
        """Truncate context to fit token limit while preserving important parts."""
        estimated_tokens = self.estimate_tokens(context)
        
        if estimated_tokens <= max_tokens:
            return context
        
        # Calculate how much to keep
        keep_ratio = max_tokens / estimated_tokens
        keep_chars = int(len(context) * keep_ratio * 0.9)  # 10% buffer
        
        if preserve_end:
            # Keep the end (most recent context)
            return "..." + context[-keep_chars:]
        else:
            # Keep the beginning
            return context[:keep_chars] + "..."
    
    # ==================== Response Caching ====================
    
    def get_cache_key(self, prompt: str, model: str, **params) -> str:
        """Generate a cache key for a request."""
        data = {
            "prompt": prompt,
            "model": model,
            **params
        }
        return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()
    
    def get_cached_response(self, cache_key: str) -> Optional[Any]:
        """Get a cached response if available and not expired."""
        if cache_key in self._cache:
            response, timestamp = self._cache[cache_key]
            if datetime.utcnow() - timestamp < self._cache_ttl:
                logger.info(f"Cache hit for key: {cache_key[:8]}...")
                return response
            else:
                # Expired
                del self._cache[cache_key]
        return None
    
    def cache_response(self, cache_key: str, response: Any):
        """Cache a response."""
        self._cache[cache_key] = (response, datetime.utcnow())
        
        # Limit cache size
        if len(self._cache) > 1000:
            # Remove oldest entries
            sorted_keys = sorted(
                self._cache.keys(),
                key=lambda k: self._cache[k][1]
            )
            for key in sorted_keys[:100]:
                del self._cache[key]
    
    # ==================== Batch Processing ====================
    
    def batch_similar_requests(
        self,
        requests: List[Dict[str, Any]],
        max_batch_size: int = 5
    ) -> List[List[Dict[str, Any]]]:
        """
        Group similar requests for batch processing.
        
        Similar requests can be processed in a single API call,
        reducing overhead and costs.
        """
        # Group by model and task type
        groups: Dict[str, List[Dict]] = {}
        
        for req in requests:
            key = f"{req.get('model', 'default')}:{req.get('task_type', 'default')}"
            if key not in groups:
                groups[key] = []
            groups[key].append(req)
        
        # Split into batches
        batches = []
        for group in groups.values():
            for i in range(0, len(group), max_batch_size):
                batches.append(group[i:i + max_batch_size])
        
        return batches
    
    def create_batch_prompt(self, prompts: List[str]) -> str:
        """Combine multiple prompts into a single batch prompt."""
        combined = "Complete each of the following tasks. Number your responses.\n\n"
        
        for i, prompt in enumerate(prompts, 1):
            combined += f"Task {i}:\n{prompt}\n\n"
        
        combined += "Provide numbered responses for each task."
        return combined
    
    # ==================== Cost Estimation ====================
    
    def estimate_cost(
        self,
        task_type: str,
        input_tokens: int = 0,
        output_tokens: int = 500,
        num_images: int = 0,
        audio_chars: int = 0
    ) -> Dict[str, float]:
        """
        Estimate the cost of a generation task.
        
        Returns detailed cost breakdown.
        """
        model = self.get_optimal_model(task_type)
        costs = MODEL_COSTS.get(model, MODEL_COSTS["gpt-4o-mini"])
        
        breakdown = {
            "text_input": 0,
            "text_output": 0,
            "images": 0,
            "audio": 0,
            "total": 0
        }
        
        # Text costs
        if input_tokens > 0:
            breakdown["text_input"] = (input_tokens / 1_000_000) * costs.get("input", 0)
        if output_tokens > 0:
            breakdown["text_output"] = (output_tokens / 1_000_000) * costs.get("output", 0)
        
        # Image costs
        if num_images > 0:
            image_model = self.get_optimal_image_model(task_type)
            image_costs = MODEL_COSTS.get(image_model, {})
            breakdown["images"] = num_images * image_costs.get("per_image", 0.003)
        
        # Audio costs (TTS)
        if audio_chars > 0:
            breakdown["audio"] = audio_chars * MODEL_COSTS["elevenlabs"]["per_char"]
        
        breakdown["total"] = sum([
            breakdown["text_input"],
            breakdown["text_output"],
            breakdown["images"],
            breakdown["audio"]
        ])
        
        return breakdown
    
    def estimate_project_cost(
        self,
        platforms: List[str],
        content_types: List[str],
        num_variations: int = 3,
        include_video: bool = False,
        video_duration: int = 30
    ) -> Dict[str, Any]:
        """
        Estimate total cost for a studio project.
        """
        costs = {
            "captions": 0,
            "hashtags": 0,
            "hooks": 0,
            "ctas": 0,
            "images": 0,
            "video": 0,
            "total": 0,
            "details": []
        }
        
        num_platforms = len(platforms)
        
        # Text generation costs (per platform * variations)
        if "caption" in content_types:
            # ~500 tokens output per caption set
            caption_cost = self.estimate_cost(
                "standard_caption",
                input_tokens=200,
                output_tokens=500 * num_variations
            )
            costs["captions"] = caption_cost["total"] * num_platforms
            costs["details"].append(f"Captions: {num_platforms} platforms x {num_variations} variations")
        
        if "hashtags" in content_types:
            hashtag_cost = self.estimate_cost(
                "simple_caption",
                input_tokens=100,
                output_tokens=200
            )
            costs["hashtags"] = hashtag_cost["total"] * num_platforms
        
        if "hook" in content_types:
            hook_cost = self.estimate_cost(
                "simple_caption",
                input_tokens=150,
                output_tokens=300 * num_variations
            )
            costs["hooks"] = hook_cost["total"]
        
        if "cta" in content_types:
            cta_cost = self.estimate_cost(
                "simple_caption",
                input_tokens=100,
                output_tokens=200
            )
            costs["ctas"] = cta_cost["total"]
        
        # Image costs
        if "image" in content_types:
            costs["images"] = num_variations * 0.003  # SDXL Lightning
            costs["details"].append(f"Images: {num_variations} variations")
        
        # Video costs
        if include_video:
            # Script generation + TTS + video generation
            script_tokens = video_duration * 3  # ~3 words per second
            tts_chars = script_tokens * 5  # ~5 chars per word
            
            script_cost = self.estimate_cost(
                "standard_caption",
                input_tokens=100,
                output_tokens=script_tokens
            )
            tts_cost = tts_chars * MODEL_COSTS["elevenlabs"]["per_char"]
            video_gen_cost = 0.05  # SadTalker approximate
            
            costs["video"] = script_cost["total"] + tts_cost + video_gen_cost
            costs["details"].append(f"Video: {video_duration}s with TTS")
        
        costs["total"] = sum([
            costs["captions"],
            costs["hashtags"],
            costs["hooks"],
            costs["ctas"],
            costs["images"],
            costs["video"]
        ])
        
        return costs


# ==================== Cost-Optimized Generation Helpers ====================

def get_cheap_model_for_task(task: str) -> str:
    """Quick helper to get the cheapest model for a task."""
    cheap_tasks = ["hashtags", "simple_caption", "improvement", "variations"]
    if any(t in task.lower() for t in cheap_tasks):
        return "gpt-4o-mini"
    return "gpt-4o-mini"  # Default to cheap model


def should_use_cache(task_type: str) -> bool:
    """Determine if a task type should use caching."""
    # Don't cache personalized content
    no_cache = ["brand_voice", "translation", "chat"]
    return not any(t in task_type for t in no_cache)


def optimize_generation_params(
    task_type: str,
    priority: str = "balanced"
) -> Dict[str, Any]:
    """Get optimized parameters for a generation task."""
    
    # Base parameters
    params = {
        "temperature": 0.7,
        "max_tokens": 1000,
        "model": "gpt-4o-mini"
    }
    
    # Task-specific optimizations
    if "caption" in task_type:
        params["max_tokens"] = 500  # Captions don't need many tokens
        params["temperature"] = 0.8  # Slightly more creative
    
    elif "hashtag" in task_type:
        params["max_tokens"] = 200  # Hashtags are short
        params["temperature"] = 0.7
    
    elif "translation" in task_type:
        params["model"] = "gpt-4o"  # Need accuracy
        params["temperature"] = 0.3  # Less creative, more accurate
        params["max_tokens"] = 1500
    
    elif "voice_training" in task_type:
        params["model"] = "gpt-4o"  # Complex analysis
        params["temperature"] = 0.3
        params["max_tokens"] = 2000
    
    elif "variation" in task_type:
        params["temperature"] = 0.9  # More creative for variations
        params["max_tokens"] = 800
    
    # Priority overrides
    if priority == "cost":
        params["model"] = "gpt-4o-mini"
        params["max_tokens"] = min(params["max_tokens"], 800)
    
    elif priority == "quality":
        params["model"] = "gpt-4o"
    
    return params


# ==================== Usage Tracking ====================

class UsageTracker:
    """Track API usage per user for cost monitoring and quota enforcement."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_tier(self, user_id: int) -> str:
        """Get user's subscription tier."""
        from app.billing.models import Subscription
        
        subscription = self.db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status == "active"
        ).first()
        
        return subscription.tier if subscription else "free"
    
    def get_tier_quotas(self, tier: str) -> Dict[str, Any]:
        """Get quota limits for a tier."""
        return TIER_QUOTAS.get(tier, TIER_QUOTAS["free"])
    
    def get_usage_today(self, user_id: int) -> Dict[str, Any]:
        """Get user's usage for today."""
        from app.models.models import GeneratedContent
        from app.video.models import GeneratedVideo
        
        today = date.today()
        start_of_day = datetime.combine(today, datetime.min.time())
        
        # Count generations today
        generations_count = self.db.query(GeneratedContent).filter(
            GeneratedContent.user_id == user_id,
            GeneratedContent.created_at >= start_of_day
        ).count()
        
        # Count images today
        images_count = self.db.query(GeneratedContent).filter(
            GeneratedContent.user_id == user_id,
            GeneratedContent.created_at >= start_of_day,
            GeneratedContent.content_type == "image"
        ).count()
        
        # Count videos today
        videos_count = self.db.query(GeneratedVideo).filter(
            GeneratedVideo.user_id == user_id,
            GeneratedVideo.created_at >= start_of_day
        ).count()
        
        # Calculate cost (approximate)
        estimated_cost = (generations_count * 0.001) + (images_count * 0.002) + (videos_count * 0.05)
        
        return {
            "date": today.isoformat(),
            "generations": generations_count,
            "images": images_count,
            "videos": videos_count,
            "estimated_cost": estimated_cost
        }
    
    def get_usage_month(self, user_id: int) -> Dict[str, Any]:
        """Get user's usage for current month."""
        from app.models.models import GeneratedContent
        from app.video.models import GeneratedVideo
        
        today = date.today()
        start_of_month = today.replace(day=1)
        start_datetime = datetime.combine(start_of_month, datetime.min.time())
        
        generations_count = self.db.query(GeneratedContent).filter(
            GeneratedContent.user_id == user_id,
            GeneratedContent.created_at >= start_datetime
        ).count()
        
        images_count = self.db.query(GeneratedContent).filter(
            GeneratedContent.user_id == user_id,
            GeneratedContent.created_at >= start_datetime,
            GeneratedContent.content_type == "image"
        ).count()
        
        videos_count = self.db.query(GeneratedVideo).filter(
            GeneratedVideo.user_id == user_id,
            GeneratedVideo.created_at >= start_datetime
        ).count()
        
        estimated_cost = (generations_count * 0.001) + (images_count * 0.002) + (videos_count * 0.05)
        
        return {
            "month": today.strftime("%Y-%m"),
            "generations": generations_count,
            "images": images_count,
            "videos": videos_count,
            "estimated_cost": estimated_cost
        }
    
    def check_quota(
        self,
        user_id: int,
        generation_type: str = "text",
        count: int = 1
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Check if user has quota for a generation.
        
        Returns:
            (allowed, message, quota_info)
        """
        tier = self.get_user_tier(user_id)
        quotas = self.get_tier_quotas(tier)
        usage_today = self.get_usage_today(user_id)
        usage_month = self.get_usage_month(user_id)
        
        quota_info = {
            "tier": tier,
            "usage_today": usage_today,
            "usage_month": usage_month,
            "limits": quotas
        }
        
        # Check daily limits
        if generation_type == "text" or generation_type == "caption":
            if usage_today["generations"] + count > quotas["daily_generations"]:
                remaining = max(0, quotas["daily_generations"] - usage_today["generations"])
                return False, f"Daily generation limit reached ({quotas['daily_generations']}). {remaining} remaining.", quota_info
        
        elif generation_type == "image":
            if usage_today["images"] + count > quotas["daily_images"]:
                remaining = max(0, quotas["daily_images"] - usage_today["images"])
                return False, f"Daily image limit reached ({quotas['daily_images']}). {remaining} remaining.", quota_info
        
        elif generation_type == "video":
            if usage_today["videos"] + count > quotas["daily_videos"]:
                remaining = max(0, quotas["daily_videos"] - usage_today["videos"])
                return False, f"Daily video limit reached ({quotas['daily_videos']}). {remaining} remaining.", quota_info
        
        # Check cost limits
        if usage_today["estimated_cost"] >= quotas["daily_cost_limit"]:
            return False, f"Daily cost limit reached (${quotas['daily_cost_limit']})", quota_info
        
        if usage_month["estimated_cost"] >= quotas["monthly_cost_limit"]:
            return False, f"Monthly cost limit reached (${quotas['monthly_cost_limit']})", quota_info
        
        return True, "OK", quota_info
    
    def track_usage(
        self,
        user_id: int,
        generation_type: str,
        count: int = 1,
        cost_usd: float = 0,
        model_used: str = None,
        tokens_used: int = 0
    ):
        """Track a usage event. This is called after successful generation."""
        # For now, usage is tracked through the existing content tables
        # This method can be extended to write to a dedicated usage_logs table
        logger.info(
            f"Usage tracked: user={user_id}, type={generation_type}, "
            f"count={count}, cost=${cost_usd:.4f}, model={model_used}"
        )


# ==================== Batch Processing ====================

class BatchProcessor:
    """
    Handle batch API requests for 50% cost savings.
    
    OpenAI Batch API:
    - 50% discount on all requests
    - 24-hour completion window
    - Best for non-time-sensitive content
    """
    
    def __init__(self, db: Session):
        self.db = db
        self._pending_batches: Dict[str, List[Dict]] = {}
    
    def can_use_batch(self, user_id: int) -> bool:
        """Check if user's tier allows batch processing."""
        tracker = UsageTracker(self.db)
        tier = tracker.get_user_tier(user_id)
        quotas = TIER_QUOTAS.get(tier, TIER_QUOTAS["free"])
        return quotas.get("batch_allowed", False)
    
    def add_to_batch(
        self,
        user_id: int,
        request_type: str,
        prompt: str,
        model: str = "gpt-4o-mini",
        params: Dict = None
    ) -> str:
        """
        Add a request to the pending batch.
        
        Returns request_id for tracking.
        """
        import uuid
        
        request_id = str(uuid.uuid4())
        batch_key = f"{user_id}:{request_type}"
        
        if batch_key not in self._pending_batches:
            self._pending_batches[batch_key] = []
        
        self._pending_batches[batch_key].append({
            "request_id": request_id,
            "prompt": prompt,
            "model": model,
            "params": params or {},
            "added_at": datetime.utcnow().isoformat()
        })
        
        return request_id
    
    def get_batch_size(self, user_id: int, request_type: str) -> int:
        """Get number of pending requests in batch."""
        batch_key = f"{user_id}:{request_type}"
        return len(self._pending_batches.get(batch_key, []))
    
    def should_submit_batch(self, user_id: int, request_type: str, threshold: int = 10) -> bool:
        """Check if batch should be submitted (enough requests accumulated)."""
        return self.get_batch_size(user_id, request_type) >= threshold
    
    async def submit_batch(self, user_id: int, request_type: str) -> Dict[str, Any]:
        """
        Submit accumulated batch to OpenAI Batch API.
        
        Note: This is a simplified implementation. Full implementation would:
        1. Create JSONL file with requests
        2. Upload to OpenAI
        3. Create batch job
        4. Poll for completion
        5. Process results
        """
        batch_key = f"{user_id}:{request_type}"
        requests = self._pending_batches.get(batch_key, [])
        
        if not requests:
            return {"status": "empty", "message": "No pending requests"}
        
        # For now, return batch info (actual submission would use OpenAI Batch API)
        batch_info = {
            "status": "pending",
            "batch_key": batch_key,
            "request_count": len(requests),
            "estimated_cost": len(requests) * 0.0003,  # 50% of normal cost
            "estimated_savings": len(requests) * 0.0003,
            "requests": requests
        }
        
        # Clear pending batch
        self._pending_batches[batch_key] = []
        
        logger.info(f"Batch submitted: {batch_key} with {len(requests)} requests")
        
        return batch_info
    
    def create_batch_request_file(self, requests: List[Dict]) -> str:
        """
        Create JSONL file content for OpenAI Batch API.
        
        Format required by OpenAI:
        {"custom_id": "req-1", "method": "POST", "url": "/v1/chat/completions", "body": {...}}
        """
        lines = []
        for i, req in enumerate(requests):
            batch_request = {
                "custom_id": req.get("request_id", f"req-{i}"),
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": req.get("model", "gpt-4o-mini"),
                    "messages": [{"role": "user", "content": req["prompt"]}],
                    "max_tokens": req.get("params", {}).get("max_tokens", 1000)
                }
            }
            lines.append(json.dumps(batch_request))
        
        return "\n".join(lines)


# ==================== Factory Functions ====================

def get_cost_optimizer(db: Session) -> CostOptimizer:
    return CostOptimizer(db)


def get_usage_tracker(db: Session) -> UsageTracker:
    return UsageTracker(db)


def get_batch_processor(db: Session) -> BatchProcessor:
    return BatchProcessor(db)

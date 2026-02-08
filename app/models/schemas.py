"""
Pydantic Schemas for API Request/Response validation
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum
import json


# ========== Helper for JSON string parsing ==========

def parse_json_list(v: Any) -> Optional[List[str]]:
    """Parse a JSON string or list into a Python list"""
    if v is None:
        return None
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        try:
            parsed = json.loads(v)
            if isinstance(parsed, list):
                return parsed
            return []
        except (json.JSONDecodeError, TypeError):
            return []
    return []


# Enums
class ContentTypeEnum(str, Enum):
    IMAGE = "image"
    TEXT = "text"
    VIDEO = "video"


class ContentStatusEnum(str, Enum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


# ========== Brand Schemas ==========

class BrandBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class BrandCreate(BrandBase):
    persona_name: Optional[str] = None
    persona_age: Optional[str] = None
    persona_gender: Optional[str] = None
    persona_style: Optional[str] = Field(
        None, 
        description="Visual style description for the AI avatar"
    )
    persona_voice: Optional[str] = Field(
        None,
        description="Writing tone and voice for captions"
    )
    persona_traits: Optional[List[str]] = None
    brand_colors: Optional[List[str]] = None
    brand_keywords: Optional[List[str]] = None
    category_ids: Optional[List[int]] = None


class BrandUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    persona_name: Optional[str] = None
    persona_age: Optional[str] = None
    persona_gender: Optional[str] = None
    persona_style: Optional[str] = None
    persona_voice: Optional[str] = None
    persona_traits: Optional[List[str]] = None
    reference_image_url: Optional[str] = None
    brand_colors: Optional[List[str]] = None
    brand_keywords: Optional[List[str]] = None
    category_ids: Optional[List[int]] = None


class BrandResponse(BrandBase):
    id: int
    persona_name: Optional[str] = None
    persona_age: Optional[str] = None
    persona_gender: Optional[str] = None
    persona_style: Optional[str] = None
    persona_voice: Optional[str] = None
    persona_traits: Optional[List[str]] = None
    reference_image_url: Optional[str] = None
    brand_colors: Optional[List[str]] = None
    brand_keywords: Optional[List[str]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator('persona_traits', 'brand_colors', 'brand_keywords', mode='before')
    @classmethod
    def parse_json_fields(cls, v):
        return parse_json_list(v)

    class Config:
        from_attributes = True


# ========== Category Schemas ==========

class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class CategoryCreate(CategoryBase):
    keywords: Optional[List[str]] = None
    image_prompt_template: Optional[str] = None
    caption_prompt_template: Optional[str] = None


class CategoryResponse(CategoryBase):
    id: int
    keywords: Optional[List[str]] = None
    image_prompt_template: Optional[str] = None
    caption_prompt_template: Optional[str] = None
    created_at: Optional[datetime] = None

    @field_validator('keywords', mode='before')
    @classmethod
    def parse_keywords(cls, v):
        return parse_json_list(v)

    class Config:
        from_attributes = True


# ========== Trend Schemas ==========

class TrendBase(BaseModel):
    title: str
    description: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None


class TrendCreate(TrendBase):
    category_id: int
    popularity_score: Optional[int] = 0
    related_keywords: Optional[List[str]] = None


class TrendResponse(TrendBase):
    id: int
    category_id: Optional[int] = None
    popularity_score: Optional[int] = 0
    related_keywords: Optional[List[str]] = None
    scraped_at: Optional[datetime] = None

    @field_validator('related_keywords', mode='before')
    @classmethod
    def parse_related_keywords(cls, v):
        return parse_json_list(v)

    class Config:
        from_attributes = True


# ========== Content Generation Schemas ==========

class GenerateContentRequest(BaseModel):
    brand_id: int
    category_id: Optional[int] = None
    trend_id: Optional[int] = None
    content_type: ContentTypeEnum
    custom_prompt: Optional[str] = Field(
        None,
        description="Optional custom prompt to override defaults"
    )
    include_caption: bool = Field(
        True,
        description="Whether to generate a caption for the image"
    )


class GenerateAvatarRequest(BaseModel):
    brand_id: int
    custom_prompt: Optional[str] = None


class GeneratedContentResponse(BaseModel):
    id: int
    brand_id: Optional[int] = None
    category_id: Optional[int] = None
    trend_id: Optional[int] = None
    content_type: Optional[ContentTypeEnum] = None
    status: Optional[ContentStatusEnum] = None
    prompt_used: Optional[str] = None
    result_url: Optional[str] = None
    caption: Optional[str] = None
    hashtags: Optional[List[str]] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @field_validator('hashtags', mode='before')
    @classmethod
    def parse_hashtags(cls, v):
        return parse_json_list(v)

    class Config:
        from_attributes = True


# ========== Scraping Schemas ==========

class ScrapeRequest(BaseModel):
    category_id: Optional[int] = None
    sources: Optional[List[str]] = Field(
        default=["google_trends", "rss"],
        description="Sources to scrape: google_trends, rss, news_api"
    )


class ScrapeResponse(BaseModel):
    message: str
    trends_found: int
    category_id: Optional[int]


# ========== General Schemas ==========

class HealthResponse(BaseModel):
    status: str
    version: str
    database: str


class PaginatedResponse(BaseModel):
    items: List
    total: int
    page: int
    per_page: int
    pages: int

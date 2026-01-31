"""
Pydantic Schemas for API Request/Response validation
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


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
    persona_name: Optional[str]
    persona_age: Optional[str]
    persona_gender: Optional[str]
    persona_style: Optional[str]
    persona_voice: Optional[str]
    persona_traits: Optional[List[str]]
    reference_image_url: Optional[str]
    brand_colors: Optional[List[str]]
    brand_keywords: Optional[List[str]]
    created_at: datetime
    updated_at: datetime

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
    keywords: Optional[List[str]]
    image_prompt_template: Optional[str]
    caption_prompt_template: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ========== Trend Schemas ==========

class TrendBase(BaseModel):
    title: str
    description: Optional[str] = None
    source: str
    source_url: Optional[str] = None


class TrendCreate(TrendBase):
    category_id: int
    popularity_score: Optional[int] = 0
    related_keywords: Optional[List[str]] = None


class TrendResponse(TrendBase):
    id: int
    category_id: int
    popularity_score: int
    related_keywords: Optional[List[str]]
    scraped_at: datetime

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
    brand_id: int
    category_id: Optional[int]
    trend_id: Optional[int]
    content_type: ContentTypeEnum
    status: ContentStatusEnum
    prompt_used: Optional[str]
    result_url: Optional[str]
    caption: Optional[str]
    hashtags: Optional[List[str]]
    error_message: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

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

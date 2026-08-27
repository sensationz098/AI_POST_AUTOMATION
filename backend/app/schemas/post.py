from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class PostCreate(BaseModel):
    brand_id: int
    title: Optional[str] = "AI Generated Social Post"
    caption: str
    hashtags: List[str] = Field(default_factory=list)
    cta: Optional[str] = None
    seo_keywords: List[str] = Field(default_factory=list)
    image_prompt: Optional[str] = None
    image_url: Optional[str] = None
    media_type: Optional[str] = Field(default=None, description="'image' or 'video'")
    thumbnail_url: Optional[str] = None
    thumbnail_type: Optional[str] = Field(default="NONE", description="'NONE', 'FRAME', or 'CUSTOM'")
    thumbnail_offset_ms: Optional[int] = None
    platforms: List[str] = Field(default_factory=lambda: ["facebook", "instagram"])
    status: Optional[str] = "DRAFT"
    scheduled_at: Optional[datetime] = None

class PostUpdate(BaseModel):
    title: Optional[str] = None
    caption: Optional[str] = None
    hashtags: Optional[List[str]] = None
    cta: Optional[str] = None
    seo_keywords: Optional[List[str]] = None
    image_url: Optional[str] = None
    media_type: Optional[str] = None
    thumbnail_url: Optional[str] = None
    thumbnail_type: Optional[str] = None
    thumbnail_offset_ms: Optional[int] = None
    platforms: Optional[List[str]] = None
    status: Optional[str] = None
    scheduled_at: Optional[datetime] = None

class SchedulePostRequest(BaseModel):
    scheduled_at: datetime

class PostResponse(BaseModel):
    id: int
    brand_id: int
    user_id: int
    title: Optional[str]
    caption: str
    hashtags: List[str]
    cta: Optional[str]
    seo_keywords: List[str]
    image_prompt: Optional[str]
    image_url: Optional[str]
    media_type: Optional[str] = None
    thumbnail_url: Optional[str] = None
    thumbnail_type: Optional[str] = "NONE"
    thumbnail_offset_ms: Optional[int] = None
    platforms: List[str]
    status: str
    scheduled_at: Optional[datetime]
    published_at: Optional[datetime]
    retry_count: int
    max_retries: int
    last_error: Optional[str]
    fb_post_id: Optional[str]
    ig_media_id: Optional[str]
    created_at: datetime
    updated_at: datetime


    class Config:
        from_attributes = True


class TargetDeleteDetail(BaseModel):
    platform: str
    account_id: Optional[str] = None
    account_name: Optional[str] = None
    external_post_id: str
    success: bool
    error: Optional[str] = None


class PostDeleteResponse(BaseModel):
    success: bool
    message: str
    post_id: int
    deleted_external_targets: int = 0
    failed_external_targets: int = 0
    details: List[TargetDeleteDetail] = Field(default_factory=list)


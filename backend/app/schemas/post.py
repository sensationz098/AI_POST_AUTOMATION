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
    platforms: List[str] = Field(default_factory=lambda: ["facebook", "instagram"])
    target_account_ids: Optional[List[int]] = Field(default=None, description="Selected SocialAccount database IDs")
    social_account_ids: Optional[List[int]] = Field(default=None, description="Selected SocialAccount database IDs")
    status: Optional[str] = "DRAFT"
    scheduled_at: Optional[datetime] = None

class PostUpdate(BaseModel):
    title: Optional[str] = None
    caption: Optional[str] = None
    hashtags: Optional[List[str]] = None
    cta: Optional[str] = None
    seo_keywords: Optional[List[str]] = None
    image_url: Optional[str] = None
    platforms: Optional[List[str]] = None
    target_account_ids: Optional[List[int]] = None
    social_account_ids: Optional[List[int]] = None
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
    platforms: List[str]
    status: str
    scheduled_at: Optional[datetime]
    published_at: Optional[datetime]
    retry_count: int
    max_retries: int
    last_error: Optional[str]
    fb_post_id: Optional[str]
    ig_media_id: Optional[str]
    batch_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

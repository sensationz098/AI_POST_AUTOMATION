from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime


class StoryCreate(BaseModel):
    brand_id: int
    title: Optional[str] = None
    caption: Optional[str] = None
    media_url: str = Field(..., description="Public HTTPS URL of image or video")
    media_type: str = Field(default="image", description="'image' or 'video'")
    thumbnail_url: Optional[str] = None
    target_account_ids: List[int] = Field(default_factory=list, description="Authoritative SocialAccount database IDs")
    platforms: List[str] = Field(default_factory=list, description="Derived/reported platforms")
    status: Optional[str] = "DRAFT"
    scheduled_at: Optional[datetime] = None


class StoryUpdate(BaseModel):
    title: Optional[str] = None
    caption: Optional[str] = None
    media_url: Optional[str] = None
    media_type: Optional[str] = None
    thumbnail_url: Optional[str] = None
    target_account_ids: Optional[List[int]] = None
    platforms: Optional[List[str]] = None
    status: Optional[str] = None
    scheduled_at: Optional[datetime] = None


class StoryScheduleRequest(BaseModel):
    scheduled_at: datetime


class StoryResponse(BaseModel):
    id: int
    brand_id: int
    user_id: int
    title: Optional[str] = None
    caption: Optional[str] = None
    media_url: str
    media_type: str
    thumbnail_url: Optional[str] = None
    target_account_ids: List[int] = Field(default_factory=list)
    platforms: List[str] = Field(default_factory=list)
    status: str
    scheduled_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    last_error: Optional[str] = None
    fb_story_id: Optional[str] = None
    ig_container_id: Optional[str] = None
    ig_story_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StoryValidationResult(BaseModel):
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    account_checks: List[Dict[str, Any]] = Field(default_factory=list)

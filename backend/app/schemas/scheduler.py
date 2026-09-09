from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime


class SchedulerTargetAccount(BaseModel):
    id: int
    account_id: str
    account_name: str
    platform: str
    username: Optional[str] = None
    logo_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SchedulerItemResponse(BaseModel):
    id: int
    item_type: str = Field(..., description="'post' or 'story'")
    brand_id: int
    user_id: int
    title: Optional[str] = None
    caption: Optional[str] = None
    media_url: Optional[str] = None
    media_type: Optional[str] = None
    thumbnail_url: Optional[str] = None
    platforms: List[str] = Field(default_factory=list)
    target_account_ids: List[int] = Field(default_factory=list)
    target_accounts: List[SchedulerTargetAccount] = Field(default_factory=list)
    status: str
    scheduled_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    last_error: Optional[str] = None
    fb_id: Optional[str] = None
    ig_id: Optional[str] = None
    fb_url: Optional[str] = None
    ig_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class SocialAccountConnectRequest(BaseModel):
    brand_id: Optional[int] = None
    platform: str = Field(..., description="'facebook' or 'instagram'")
    account_id: str = Field(..., description="Facebook Page ID or Instagram Business Account ID")
    account_name: str = Field(..., description="Facebook Page Name or Instagram Username")
    access_token: str = Field(..., description="Page Access Token or User Access Token")
    token_type: Optional[str] = "page_access_token"
    expires_at: Optional[datetime] = None
    logo_url: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None

class SocialAccountResponse(BaseModel):
    id: int
    user_id: int
    brand_id: Optional[int] = None
    platform: str
    account_id: str
    account_name: str
    token_type: Optional[str] = None
    expires_at: Optional[datetime] = None
    status: str  # "CONNECTED", "TOKEN_EXPIRED", "REVOKED"
    logo_url: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class MultiPublishRequest(BaseModel):
    post_id: int
    social_account_ids: List[int] = Field(..., description="List of SocialAccount IDs to publish to")
    media_type: Optional[str] = Field(default=None, description="Optional override for media_type: 'image' or 'video'")
    idempotency_key: Optional[str] = None


class PublishingJobResponse(BaseModel):
    id: int
    batch_id: int
    social_account_id: int
    platform: str
    account_name: Optional[str] = None
    status: str
    external_post_id: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    attempts: int
    published_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PublishingBatchResponse(BaseModel):
    id: int
    post_id: int
    user_id: int
    idempotency_key: Optional[str] = None
    status: str
    total_targets: int
    successful_targets: int
    failed_targets: int
    created_at: datetime
    completed_at: Optional[datetime] = None
    jobs: List[PublishingJobResponse] = []

    class Config:
        from_attributes = True

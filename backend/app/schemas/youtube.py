from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class YouTubeOAuthStartResponse(BaseModel):
    authorization_url: str
    state: str
    client_id_configured: bool

class YouTubeChannelInfo(BaseModel):
    id: int
    account_id: str = Field(..., description="YouTube Channel ID (e.g. UC...)")
    account_name: str = Field(..., description="YouTube Channel Title")
    logo_url: Optional[str] = None
    custom_url: Optional[str] = None
    uploads_playlist_id: Optional[str] = None
    subscriber_count: Optional[str] = None
    video_count: Optional[str] = None
    view_count: Optional[str] = None
    status: str = "CONNECTED"
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class YouTubeConnectResponse(BaseModel):
    success: bool
    message: str
    channel: Optional[YouTubeChannelInfo] = None

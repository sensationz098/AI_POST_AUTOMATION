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

class YouTubeUploadInitiateRequest(BaseModel):
    social_account_id: int = Field(..., description="ID of connected YouTube SocialAccount")
    title: str = Field(..., min_length=1, max_length=100, description="Video title")
    description: Optional[str] = Field(default="", max_length=5000, description="Video description")
    privacy_status: Optional[str] = Field(default="private", description="privacy: private, unlisted, public")
    filename: Optional[str] = Field(default="video.mp4", description="Original filename")
    mime_type: Optional[str] = Field(default="video/mp4", description="MIME type, e.g. video/mp4")
    file_size_bytes: int = Field(..., gt=0, description="Total video file size in bytes")

class YouTubeUploadInitiateResponse(BaseModel):
    upload_id: str = Field(..., description="Unique upload session identifier")
    channel_id: str = Field(..., description="YouTube Channel ID")
    channel_title: str = Field(..., description="YouTube Channel Title")
    title: str
    file_size_bytes: int
    mime_type: str
    status: str = "INITIATED"
    message: str = "Resumable upload session initiated successfully."

class YouTubeUploadChunkResponse(BaseModel):
    upload_id: str
    status: str = Field(..., description="RESUME_INCOMPLETE or COMPLETED")
    http_status: int
    range_header: Optional[str] = None
    last_byte_received: Optional[int] = None
    next_byte_offset: Optional[int] = None
    total_bytes: int
    is_complete: bool
    video_id: Optional[str] = None
    video_url: Optional[str] = None

class YouTubeUploadStatusResponse(BaseModel):
    upload_id: str
    channel_id: str
    title: str
    file_size_bytes: int
    mime_type: str
    status: str
    http_status: int
    range_header: Optional[str] = None
    last_byte_received: Optional[int] = None
    next_byte_offset: Optional[int] = None
    is_complete: bool
    video_id: Optional[str] = None
    video_url: Optional[str] = None


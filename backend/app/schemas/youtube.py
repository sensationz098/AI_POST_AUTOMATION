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
    tags: Optional[List[str]] = Field(default=None, description="Video tags/keywords")
    category_id: Optional[str] = Field(default=None, description="YouTube Category ID")
    privacy_status: Optional[str] = Field(default="private", description="privacy: private, unlisted, public")
    made_for_kids: Optional[bool] = Field(default=False, description="COPPA Made for kids declaration")
    filename: Optional[str] = Field(default="video.mp4", description="Original filename")
    mime_type: Optional[str] = Field(default="video/mp4", description="MIME type, e.g. video/mp4")
    file_size_bytes: int = Field(..., gt=0, description="Total video file size in bytes")
    client_mutation_id: Optional[str] = Field(default=None, max_length=100, description="Client idempotency mutation key")
    thumbnail_url: Optional[str] = Field(default=None, description="Custom thumbnail image URL")
    publish_at: Optional[datetime] = Field(default=None, description="Scheduled publication timestamp (ISO 8601 UTC)")

class YouTubeUploadInitiateResponse(BaseModel):
    upload_id: str = Field(..., description="Unique upload session identifier")
    client_mutation_id: Optional[str] = None
    channel_id: str = Field(..., description="YouTube Channel ID")
    channel_title: str = Field(..., description="YouTube Channel Title")
    title: str
    file_size_bytes: int
    chunk_size_bytes: int = Field(default=8 * 1024 * 1024, description="Target chunk size in bytes (8 MB)")
    mime_type: str
    privacy_status: str = "private"
    status: str = "INITIATED"
    thumbnail_url: Optional[str] = None
    thumbnail_status: Optional[str] = None
    next_byte_offset: int = 0
    message: str = "Resumable upload session initiated successfully."

class YouTubeUploadChunkResponse(BaseModel):
    upload_id: str
    status: str = Field(..., description="RESUME_INCOMPLETE, COMPLETED, PROCESSING, READY, or FAILED")
    http_status: int
    range_header: Optional[str] = None
    last_byte_received: Optional[int] = None
    next_byte_offset: Optional[int] = None
    total_bytes: int
    bytes_uploaded: int = 0
    progress_percentage: float = 0.0
    is_complete: bool
    video_id: Optional[str] = None
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    thumbnail_status: Optional[str] = None
    thumbnail_error: Optional[str] = None

class YouTubeUploadStatusResponse(BaseModel):
    upload_id: str
    channel_id: str
    title: str
    file_size_bytes: int
    bytes_uploaded: int = 0
    progress_percentage: float = 0.0
    mime_type: str
    status: str
    http_status: int
    range_header: Optional[str] = None
    last_byte_received: Optional[int] = None
    next_byte_offset: Optional[int] = None
    is_complete: bool
    processing_status: Optional[str] = None
    processing_failure_reason: Optional[str] = None
    video_id: Optional[str] = None
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    thumbnail_status: Optional[str] = None
    thumbnail_error: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class YouTubeUploadDetailResponse(BaseModel):
    id: int
    upload_id: str
    user_id: int
    social_account_id: int
    channel_id: str
    video_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    privacy_status: str
    original_filename: Optional[str] = None
    mime_type: str
    file_size_bytes: int
    bytes_uploaded: int
    progress_percentage: float
    upload_status: str
    processing_status: Optional[str] = None
    processing_failure_reason: Optional[str] = None
    thumbnail_url: Optional[str] = None
    thumbnail_status: Optional[str] = None
    thumbnail_error: Optional[str] = None
    error_message: Optional[str] = None
    video_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class YouTubeThumbnailUploadResponse(BaseModel):
    thumbnail_url: str
    filename: str
    file_size_bytes: int

class YouTubeThumbnailRetryResponse(BaseModel):
    success: bool
    upload_id: str
    thumbnail_status: str
    thumbnail_error: Optional[str] = None
    message: str

class YouTubeUploadCancelResponse(BaseModel):
    success: bool
    upload_id: str
    status: str = "CANCELLED"
    message: str

class YouTubeUploadListResponse(BaseModel):
    items: List[YouTubeUploadDetailResponse]
    total: int

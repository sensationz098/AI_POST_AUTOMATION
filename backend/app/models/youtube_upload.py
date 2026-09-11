from sqlalchemy import Column, Integer, BigInteger, Float, String, Text, DateTime, ForeignKey, JSON, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from enum import Enum
from app.core.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class YouTubeUploadStatus(str, Enum):
    INITIATED = "INITIATED"
    UPLOADING = "UPLOADING"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class YouTubeUpload(Base):
    __tablename__ = "youtube_uploads"
    __table_args__ = (
        Index("idx_yt_uploads_user", "user_id"),
        Index("idx_yt_uploads_account", "social_account_id"),
        Index("idx_yt_uploads_status", "upload_status"),
        UniqueConstraint("user_id", "client_mutation_id", name="uq_youtube_uploads_user_mutation"),
    )

    id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(String(100), unique=True, nullable=False, index=True)  # Public opaque identifier e.g. ytu_...
    client_mutation_id = Column(String(100), nullable=True, index=True)  # Idempotency key from client

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    social_account_id = Column(Integer, ForeignKey("social_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    channel_id = Column(String(255), nullable=False)
    video_id = Column(String(100), nullable=True, index=True)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True, default="")
    privacy_status = Column(String(50), default="private")  # "private", "unlisted", "public"

    original_filename = Column(String(255), nullable=True)
    mime_type = Column(String(100), default="video/mp4")
    file_size_bytes = Column(BigInteger, nullable=False)
    bytes_uploaded = Column(BigInteger, default=0)
    progress_percentage = Column(Float, default=0.0)

    upload_status = Column(String(50), default=YouTubeUploadStatus.INITIATED.value, index=True)
    processing_status = Column(String(50), nullable=True)  # "processing", "succeeded", "failed", "terminated"
    processing_failure_reason = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    encrypted_session_url = Column(Text, nullable=True)  # Encrypted Google capability session URL
    video_url = Column(Text, nullable=True)
    thumbnail_url = Column(Text, nullable=True)
    thumbnail_status = Column(String(50), nullable=True)  # "PENDING", "APPLIED", "FAILED"
    thumbnail_error = Column(Text, nullable=True)
    metadata_json = Column(JSON, default=dict)

    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    completed_at = Column(DateTime, nullable=True)

    owner = relationship("User")
    social_account = relationship("SocialAccount")

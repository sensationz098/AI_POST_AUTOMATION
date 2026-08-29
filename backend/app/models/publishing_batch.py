from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from app.core.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class BatchStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"

class JobStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    RETRYING = "RETRYING"

class PublishingBatch(Base):
    __tablename__ = "publishing_batches"
    __table_args__ = (
        Index("idx_batches_user_status", "user_id", "status"),
        Index("idx_batches_post", "post_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    idempotency_key = Column(String(255), unique=True, index=True, nullable=True)
    status = Column(String(50), default=BatchStatus.QUEUED.value, index=True)
    
    total_targets = Column(Integer, default=0)
    successful_targets = Column(Integer, default=0)
    failed_targets = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=utc_now)
    completed_at = Column(DateTime, nullable=True)

    post = relationship("Post")
    user = relationship("User")
    jobs = relationship("PublishingJob", back_populates="batch", cascade="all, delete-orphan")

class PublishingJob(Base):
    __tablename__ = "publishing_jobs"
    __table_args__ = (
        UniqueConstraint("batch_id", "social_account_id", name="uq_publishing_job_batch_social_account"),
        Index("idx_jobs_batch_status", "batch_id", "status"),
        Index("idx_jobs_account_status", "social_account_id", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("publishing_batches.id"), nullable=False)
    social_account_id = Column(Integer, ForeignKey("social_accounts.id"), nullable=False)
    
    platform = Column(String(50), nullable=False)  # "facebook" or "instagram"
    status = Column(String(50), default=JobStatus.QUEUED.value, index=True)
    
    external_post_id = Column(String(255), nullable=True)  # FB post ID or IG media ID
    ig_container_id = Column(String(255), nullable=True)  # Persisted IG container ID
    
    error_code = Column(String(100), nullable=True)  # "TOKEN_EXPIRED", "PERMISSION_ERROR", "RATE_LIMIT", etc.
    error_message = Column(Text, nullable=True)  # Clean human-readable message
    
    meta_status_code = Column(Integer, nullable=True)  # Raw HTTP status code (e.g. 403)
    meta_error_code = Column(Integer, nullable=True)  # Raw Meta error code (e.g. 4)
    meta_error_subcode = Column(Integer, nullable=True)  # Raw Meta error subcode (e.g. 2207051)
    meta_error_message = Column(Text, nullable=True)  # Raw Meta API error string
    
    attempts = Column(Integer, default=0)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    batch = relationship("PublishingBatch", back_populates="jobs")
    social_account = relationship("SocialAccount")

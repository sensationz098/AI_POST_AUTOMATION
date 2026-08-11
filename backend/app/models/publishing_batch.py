from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base

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

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    idempotency_key = Column(String(255), unique=True, index=True, nullable=True)
    status = Column(String(50), default=BatchStatus.QUEUED.value, index=True)
    
    total_targets = Column(Integer, default=0)
    successful_targets = Column(Integer, default=0)
    failed_targets = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    post = relationship("Post")
    user = relationship("User")
    jobs = relationship("PublishingJob", back_populates="batch", cascade="all, delete-orphan")

class PublishingJob(Base):
    __tablename__ = "publishing_jobs"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("publishing_batches.id"), nullable=False)
    social_account_id = Column(Integer, ForeignKey("social_accounts.id"), nullable=False)
    
    platform = Column(String(50), nullable=False)  # "facebook" or "instagram"
    status = Column(String(50), default=JobStatus.QUEUED.value, index=True)
    
    external_post_id = Column(String(255), nullable=True)  # FB post ID or IG media ID
    error_code = Column(String(100), nullable=True)  # "TOKEN_EXPIRED", "PERMISSION_ERROR", "RATE_LIMIT", etc.
    error_message = Column(Text, nullable=True)  # Clean human-readable message
    
    attempts = Column(Integer, default=0)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    batch = relationship("PublishingBatch", back_populates="jobs")
    social_account = relationship("SocialAccount")

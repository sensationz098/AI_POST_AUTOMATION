from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, UniqueConstraint, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base

class CommentProcessingStatus(str, enum.Enum):
    RECEIVED = "RECEIVED"
    PENDING = "PENDING"
    PROCESSED = "PROCESSED"
    IGNORED = "IGNORED"
    FAILED = "FAILED"
    DELETED = "DELETED"

class SocialComment(Base):
    __tablename__ = "social_comments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    social_account_id = Column(Integer, ForeignKey("social_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    platform = Column(String(50), nullable=False, index=True)  # 'facebook' or 'instagram'
    external_comment_id = Column(String(255), nullable=False, index=True)
    external_post_id = Column(String(255), nullable=True, index=True)
    parent_comment_id = Column(String(255), nullable=True)
    comment_text = Column(Text, nullable=True)
    commenter_id = Column(String(255), nullable=True)
    commenter_name = Column(String(255), nullable=True)
    event_timestamp = Column(DateTime(timezone=True), nullable=True)
    webhook_object = Column(String(50), nullable=False)  # 'page' or 'instagram'
    processing_status = Column(String(50), nullable=False, default="RECEIVED", index=True)
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    meta_ad_id = Column(Integer, ForeignKey("meta_ads.id", ondelete="SET NULL"), nullable=True, index=True)

    user = relationship("User", backref="social_comments")
    social_account = relationship("SocialAccount", back_populates="comments")
    meta_ad = relationship("MetaAd", back_populates="comments")
    replies = relationship(
        "SocialCommentReply",
        back_populates="comment",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    __table_args__ = (
        UniqueConstraint("platform", "external_comment_id", name="uq_social_comment_platform_ext_id"),
    )

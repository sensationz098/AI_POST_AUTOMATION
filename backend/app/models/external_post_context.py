from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class ExternalPostContext(Base):
    """
    Cached lightweight post metadata fetched from Meta Graph API for posts not created natively in app.
    Prevents repeated N+1 Meta API calls for comments on the same external post.
    """
    __tablename__ = "external_post_contexts"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), nullable=False, index=True)  # 'facebook' or 'instagram'
    social_account_id = Column(Integer, ForeignKey("social_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    external_post_id = Column(String(255), nullable=False, index=True)

    caption = Column(Text, nullable=True)
    media_type = Column(String(50), nullable=True)  # 'IMAGE', 'VIDEO', 'CAROUSEL_ALBUM', 'TEXT'
    media_url = Column(Text, nullable=True)
    thumbnail_url = Column(Text, nullable=True)
    permalink = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=True)

    status = Column(String(50), nullable=False, default="ACTIVE")  # 'ACTIVE' or 'UNAVAILABLE'
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    social_account = relationship("SocialAccount", back_populates="external_post_contexts")

    __table_args__ = (
        UniqueConstraint("social_account_id", "platform", "external_post_id", name="uq_ext_post_account_platform_ext_id"),
    )

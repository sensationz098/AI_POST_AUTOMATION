from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from app.core.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class StoryStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SCHEDULED = "SCHEDULED"
    PUBLISHING = "PUBLISHING"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"


class Story(Base):
    __tablename__ = "stories"
    __table_args__ = (
        Index("idx_stories_user_status", "user_id", "status"),
        Index("idx_stories_brand_status", "brand_id", "status"),
        Index("idx_stories_scheduled", "scheduled_at", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=True)
    caption = Column(Text, nullable=True)  # Optional text / internal note
    media_url = Column(Text, nullable=False)  # Public HTTPS URL
    media_type = Column(String(50), nullable=False, default="image")  # "image" or "video"
    thumbnail_url = Column(Text, nullable=True)

    target_account_ids = Column(JSON, default=list)  # Database IDs of targeted SocialAccount records
    platforms = Column(JSON, default=list)  # Derived/reported ["facebook", "instagram"]
    status = Column(String(50), default=StoryStatus.DRAFT.value, index=True)

    scheduled_at = Column(DateTime, nullable=True, index=True)
    published_at = Column(DateTime, nullable=True)

    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    last_error = Column(Text, nullable=True)

    fb_story_id = Column(String(255), nullable=True)
    ig_container_id = Column(String(255), nullable=True)
    ig_story_id = Column(String(255), nullable=True)

    brand_id = Column(Integer, ForeignKey("brand_profiles.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    brand = relationship("BrandProfile")
    author = relationship("User")

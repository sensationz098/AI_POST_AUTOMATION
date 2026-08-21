from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Enum, Index
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from app.core.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class PostStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    SCHEDULED = "SCHEDULED"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"

class Post(Base):
    __tablename__ = "posts"
    __table_args__ = (
        Index("idx_posts_user_status", "user_id", "status"),
        Index("idx_posts_brand_status", "brand_id", "status"),
        Index("idx_posts_scheduled", "scheduled_at", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=True)
    caption = Column(Text, nullable=False)
    hashtags = Column(JSON, default=list)  # ["#AI", "#Marketing"]
    cta = Column(String(255), nullable=True)
    seo_keywords = Column(JSON, default=list)
    image_prompt = Column(Text, nullable=True)
    image_url = Column(Text, nullable=True)
    media_type = Column(String(50), nullable=True)  # "image" or "video"
    
    platforms = Column(JSON, default=list)  # ["facebook", "instagram"]
    status = Column(String(50), default=PostStatus.DRAFT.value, index=True)
    
    scheduled_at = Column(DateTime, nullable=True, index=True)
    published_at = Column(DateTime, nullable=True)
    
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    last_error = Column(Text, nullable=True)
    
    fb_post_id = Column(String(255), nullable=True)
    ig_container_id = Column(String(255), nullable=True)
    ig_media_id = Column(String(255), nullable=True)
    
    brand_id = Column(Integer, ForeignKey("brand_profiles.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    brand = relationship("BrandProfile", back_populates="posts")
    author = relationship("User", back_populates="posts")
    analytics = relationship("PostAnalytics", back_populates="post", uselist=False, cascade="all, delete-orphan")

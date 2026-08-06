from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base

class PostStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    SCHEDULED = "SCHEDULED"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"

class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=True)
    caption = Column(Text, nullable=False)
    hashtags = Column(JSON, default=list)  # ["#AI", "#Marketing"]
    cta = Column(String(255), nullable=True)
    seo_keywords = Column(JSON, default=list)
    image_prompt = Column(Text, nullable=True)
    image_url = Column(String(1000), nullable=True)
    
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
    
    brand_id = Column(Integer, ForeignKey("brand_profiles.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    brand = relationship("BrandProfile", back_populates="posts")
    author = relationship("User", back_populates="posts")
    analytics = relationship("PostAnalytics", back_populates="post", uselist=False, cascade="all, delete-orphan")

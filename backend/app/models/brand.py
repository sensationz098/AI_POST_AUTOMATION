from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class BrandProfile(Base):
    __tablename__ = "brand_profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    logo_url = Column(String(500), nullable=True)
    brand_colors = Column(JSON, default=list)  # e.g. ["#4F46E5", "#06B6D4"]
    tone_of_voice = Column(String(255), default="Professional & Engaging")
    target_audience = Column(Text, nullable=True)
    cta_style = Column(String(255), default="Direct & Urgency-driven")
    industry = Column(String(255), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    owner = relationship("User", back_populates="brands")
    posts = relationship("Post", back_populates="brand", cascade="all, delete-orphan")
    meta_account = relationship("MetaAccount", back_populates="brand", uselist=False, cascade="all, delete-orphan")

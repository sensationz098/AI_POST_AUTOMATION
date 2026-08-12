from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class MetaAccount(Base):
    __tablename__ = "meta_accounts"

    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brand_profiles.id"), nullable=False, unique=True)
    access_token = Column(Text, nullable=True)
    facebook_page_id = Column(String(255), nullable=True)
    facebook_page_name = Column(String(255), nullable=True)
    instagram_account_id = Column(String(255), nullable=True)
    instagram_username = Column(String(255), nullable=True)
    logo_url = Column(String(500), nullable=True)
    is_connected = Column(Boolean, default=False)
    last_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    brand = relationship("BrandProfile", back_populates="meta_account")

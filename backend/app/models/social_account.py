from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class SocialAccount(Base):
    __tablename__ = "social_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    brand_id = Column(Integer, ForeignKey("brand_profiles.id"), nullable=True)

    platform = Column(String(50), nullable=False)  # "facebook" or "instagram"
    account_id = Column(String(255), nullable=False)  # Facebook Page ID or IG Business Account ID
    account_name = Column(String(255), nullable=False)  # Page Name or IG Username
    
    access_token = Column(Text, nullable=False)  # Sensitive credential stored server-side only
    token_type = Column(String(100), default="page_access_token")
    expires_at = Column(DateTime, nullable=True)
    
    status = Column(String(50), default="CONNECTED")  # "CONNECTED", "TOKEN_EXPIRED", "REVOKED"
    logo_url = Column(String(500), nullable=True)
    metadata_json = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User")
    brand = relationship("BrandProfile")

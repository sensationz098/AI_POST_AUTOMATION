from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class MetaAd(Base):
    __tablename__ = "meta_ads"
    __table_args__ = (
        UniqueConstraint("user_id", "meta_ad_id", name="uq_user_meta_ad"),
        Index("idx_meta_ads_user", "user_id"),
        Index("idx_meta_ads_ad_account", "meta_ad_account_id"),
        Index("idx_meta_ads_meta_ad_id", "meta_ad_id"),
        Index("idx_meta_ads_fb_post", "facebook_post_id"),
        Index("idx_meta_ads_ig_media", "instagram_media_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    meta_ad_account_id = Column(String(255), nullable=False, index=True)  # e.g. "act_123456789"
    ad_account_db_id = Column(Integer, ForeignKey("meta_ad_accounts.id", ondelete="CASCADE"), nullable=True, index=True)

    meta_ad_id = Column(String(255), nullable=False)  # Meta ad ID (e.g. "12020582928371")
    name = Column(String(255), nullable=True)
    campaign_id = Column(String(255), nullable=True)
    campaign_name = Column(String(255), nullable=True)
    adset_id = Column(String(255), nullable=True)
    adset_name = Column(String(255), nullable=True)

    effective_status = Column(String(50), default="ACTIVE", nullable=True)  # e.g. "ACTIVE", "PAUSED", "ARCHIVED"
    configured_status = Column(String(50), nullable=True)
    creative_id = Column(String(255), nullable=True)

    # Engagement / Content Object Mapping fields
    facebook_page_id = Column(String(255), nullable=True)
    facebook_post_id = Column(String(255), nullable=True)  # Facebook Page Post ID (e.g. "page_id_post_id")
    instagram_account_id = Column(String(255), nullable=True)
    instagram_media_id = Column(String(255), nullable=True)  # Instagram Media ID
    engagement_object_type = Column(String(50), nullable=True)  # "FACEBOOK_POST", "INSTAGRAM_MEDIA", "BOTH", "UNKNOWN"
    engagement_object_id = Column(String(255), nullable=True)  # Primary resolved ID
    mapping_status = Column(String(50), default="NOT_AVAILABLE", nullable=False)  # MAPPED, PARTIALLY_MAPPED, NOT_AVAILABLE, UNSUPPORTED, ERROR

    metadata_json = Column(JSON, default=dict)

    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    user = relationship("User", back_populates="meta_ads")
    ad_account = relationship("MetaAdAccount", back_populates="ads")
    comments = relationship("SocialComment", back_populates="meta_ad", cascade="all, delete-orphan", passive_deletes=True)

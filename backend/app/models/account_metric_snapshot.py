from sqlalchemy import Column, Integer, BigInteger, Float, Date, DateTime, ForeignKey, JSON, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class AccountMetricSnapshot(Base):
    """
    Stores historical daily metric snapshots for connected social accounts
    (Instagram Business, Facebook Pages, YouTube Channels).
    Supports idempotent daily upserts via unique (social_account_id, snapshot_date).
    """
    __tablename__ = "account_metric_snapshots"
    __table_args__ = (
        UniqueConstraint("social_account_id", "snapshot_date", name="uq_social_account_snapshot_date"),
        Index("idx_account_snapshots_account_date", "social_account_id", "snapshot_date"),
        Index("idx_account_snapshots_date", "snapshot_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    social_account_id = Column(Integer, ForeignKey("social_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    snapshot_date = Column(Date, nullable=False, index=True)

    followers_count = Column(Integer, nullable=True)     # Instagram followers / Facebook page followers or fans / YouTube subscribers
    following_count = Column(Integer, nullable=True)     # Instagram follows_count
    media_count = Column(Integer, nullable=True)         # Instagram media_count / Facebook post count / YouTube video_count
    views_count = Column(BigInteger, nullable=True)      # YouTube lifetime views
    reach = Column(Integer, nullable=True)               # Total reach (nullable for platform-specific availability)
    impressions = Column(Integer, nullable=True)         # Total impressions (nullable for platform-specific availability)
    engagement_rate = Column(Float, nullable=True)       # Estimated or derived engagement rate

    metadata_json = Column(JSON, default=dict)           # Platform details (fan_count, subscriber_count, etc.)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    social_account = relationship("SocialAccount", back_populates="metric_snapshots")

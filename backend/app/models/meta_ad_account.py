from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class MetaAdAccount(Base):
    __tablename__ = "meta_ad_accounts"
    __table_args__ = (
        UniqueConstraint("user_id", "meta_ad_account_id", name="uq_user_meta_ad_account"),
        Index("idx_meta_ad_accounts_user", "user_id"),
        Index("idx_meta_ad_accounts_account_id", "meta_ad_account_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    meta_ad_account_id = Column(String(255), nullable=False)  # Stored as String (e.g. "act_123456789")
    name = Column(String(255), nullable=True)
    account_status = Column(Integer, nullable=True)  # Meta Graph API integer status code (1=ACTIVE, 2=DISABLED, etc.)
    currency = Column(String(10), nullable=True)  # e.g. "USD"
    timezone_name = Column(String(100), nullable=True)  # e.g. "America/Los_Angeles"

    metadata_json = Column(JSON, default=dict)

    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    user = relationship("User", back_populates="meta_ad_accounts")

    @property
    def status_label(self) -> str:
        """Human-readable account status derived from Meta Graph API status codes."""
        status_map = {
            1: "ACTIVE",
            2: "DISABLED",
            3: "UNSETTLED",
            7: "PENDING_RISK_REVIEW",
            8: "IN_GRACE_PERIOD",
            9: "PENDING_CLOSURE",
            100: "CLOSED"
        }
        return status_map.get(self.account_status, "UNKNOWN")

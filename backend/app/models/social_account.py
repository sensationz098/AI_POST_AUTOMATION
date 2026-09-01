from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class SocialAccount(Base):
    __tablename__ = "social_accounts"
    __table_args__ = (
        UniqueConstraint("user_id", "platform", "account_id", name="uq_user_social_account"),
        Index("idx_accounts_user_platform", "user_id", "platform"),
        Index("idx_accounts_status", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    brand_id = Column(Integer, ForeignKey("brand_profiles.id"), nullable=True, index=True)

    platform = Column(String(50), nullable=False)  # "facebook" or "instagram"
    account_id = Column(String(255), nullable=False)  # Facebook Page ID or IG Business Account ID
    account_name = Column(String(255), nullable=False)  # Page Name or IG Username
    
    access_token = Column(Text, nullable=False)  # Sensitive credential stored server-side only
    token_type = Column(String(100), default="page_access_token")
    expires_at = Column(DateTime, nullable=True)
    
    status = Column(String(50), default="CONNECTED")  # "CONNECTED", "TOKEN_EXPIRED", "REVOKED"
    logo_url = Column(Text, nullable=True)
    metadata_json = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    owner = relationship("User")
    brand = relationship("BrandProfile")
    comments = relationship(
        "SocialComment",
        back_populates="social_account",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    publishing_jobs = relationship(
        "PublishingJob",
        back_populates="social_account",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    @property
    def requires_reconnection_for_comment_automation(self) -> bool:
        """
        Evaluate if an existing connected account requires OAuth reconnection to obtain comment automation scopes.
        Existing accounts connected prior to scope expansion do not have comment_automation_ready=True in metadata_json.
        """
        meta = self.metadata_json or {}
        if meta.get("comment_automation_ready") is True:
            return False
        return True


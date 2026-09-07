from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.core.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class AutomationStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"

class TriggerType(str, enum.Enum):
    ANY_COMMENT = "ANY_COMMENT"
    KEYWORD = "KEYWORD"

class PostTargetType(str, enum.Enum):
    SPECIFIC_POST = "SPECIFIC_POST"
    ANY_POST = "ANY_POST"
    NEXT_POST = "NEXT_POST"

class Automation(Base):
    __tablename__ = "automations"
    __table_args__ = (
        Index("idx_automations_user_status", "user_id", "status"),
        Index("idx_automations_account_post", "social_account_id", "external_post_id", "status"),
        Index("idx_automations_platform_status", "platform", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    social_account_id = Column(Integer, ForeignKey("social_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    
    name = Column(String(255), nullable=False)
    platform = Column(String(50), nullable=False, index=True)  # 'facebook' or 'instagram'
    status = Column(String(50), nullable=False, default=AutomationStatus.DRAFT.value, index=True)
    
    # Target post configuration
    post_target_type = Column(String(50), nullable=False, default=PostTargetType.SPECIFIC_POST.value)
    external_post_id = Column(String(255), nullable=True, index=True)
    internal_post_id = Column(Integer, ForeignKey("posts.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Trigger configuration
    trigger_type = Column(String(50), nullable=False, default=TriggerType.ANY_COMMENT.value)
    trigger_config = Column(JSON, nullable=False, default=dict)  # {"keywords": ["price", "cost"]}
    
    # Action configuration (extensible for future action nodes)
    action_config = Column(JSON, nullable=False, default=dict)
    # {
    #   "public_reply": {"enabled": True, "variations": ["Thanks! Check your DM 👋"]},
    #   "private_message": {"enabled": True, "message": "Hey! Here are the details..."}
    # }
    
    metadata_json = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    user = relationship("User", backref="automations")
    social_account = relationship("SocialAccount", backref="automations")
    post = relationship("Post", backref="automations")
    executions = relationship(
        "AutomationExecution",
        back_populates="automation",
        cascade="all, delete-orphan"
    )


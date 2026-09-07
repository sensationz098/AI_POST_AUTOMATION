from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from app.core.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class ExecutionStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PARTIAL_FAILURE = "PARTIAL_FAILURE"

class ActionExecutionStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"

class AutomationExecution(Base):
    __tablename__ = "automation_executions"
    __table_args__ = (
        UniqueConstraint("automation_id", "external_comment_id", name="uq_automation_execution_comment"),
        Index("idx_auto_exec_user_status", "user_id", "status"),
        Index("idx_auto_exec_created_at", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    automation_id = Column(Integer, ForeignKey("automations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    social_account_id = Column(Integer, ForeignKey("social_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    comment_id = Column(Integer, ForeignKey("social_comments.id", ondelete="SET NULL"), nullable=True, index=True)
    
    external_comment_id = Column(String(255), nullable=False, index=True)
    external_post_id = Column(String(255), nullable=True, index=True)
    platform = Column(String(50), nullable=False, index=True)  # 'facebook' or 'instagram'
    
    # Contact / Triggering user identifier
    contact_identifier = Column(String(255), nullable=True)  # commenter PSID / IGSID / user ID
    contact_name = Column(String(255), nullable=True)
    
    # Overall execution status
    status = Column(String(50), nullable=False, default=ExecutionStatus.PENDING.value, index=True)
    
    # Trigger matching details
    trigger_result = Column(JSON, nullable=True)  # {"matched": True, "trigger_type": "KEYWORD", "matched_keyword": "price", "comment_text": "..."}
    
    # Public reply action execution details
    public_reply_status = Column(String(50), nullable=False, default=ActionExecutionStatus.PENDING.value)
    public_reply_result = Column(JSON, nullable=True)  # {"message": "...", "external_reply_id": "...", "error": None}
    
    # Private message action execution details
    private_message_status = Column(String(50), nullable=False, default=ActionExecutionStatus.PENDING.value)
    private_message_result = Column(JSON, nullable=True)  # {"message": "...", "external_message_id": "...", "error": None}
    
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    automation = relationship("Automation", back_populates="executions")
    user = relationship("User")
    social_account = relationship("SocialAccount")
    comment = relationship("SocialComment")

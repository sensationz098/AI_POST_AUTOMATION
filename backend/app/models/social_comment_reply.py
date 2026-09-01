from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.core.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class SocialCommentReply(Base):
    __tablename__ = "social_comment_replies"

    id = Column(Integer, primary_key=True, index=True)
    comment_id = Column(Integer, ForeignKey("social_comments.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    platform = Column(String(50), nullable=False, index=True)  # 'facebook' or 'instagram'
    message = Column(Text, nullable=False)
    external_reply_id = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default="SUCCESS", index=True)  # 'SUCCESS' or 'FAILED'
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    comment = relationship("SocialComment", back_populates="replies")
    user = relationship("User")

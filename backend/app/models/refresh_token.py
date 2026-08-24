from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class RefreshToken(Base):
    """
    SQLAlchemy model for server-side tracking of refresh token sessions.
    Stores hashed tokens only to ensure plaintext refresh tokens are never persisted.
    """
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(255), unique=True, index=True, nullable=False)
    family_id = Column(String(255), index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    replaced_by = Column(String(255), nullable=True)
    user_agent = Column(String(500), nullable=True)
    ip_address = Column(String(100), nullable=True)

    user = relationship("User", backref="refresh_tokens")

from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    """Repository handling persistence operations for refresh token sessions."""

    def create(
        self,
        db: Session,
        user_id: int,
        token_hash: str,
        family_id: str,
        expires_at: datetime,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> RefreshToken:
        session_record = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            family_id=family_id,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address
        )
        db.add(session_record)
        db.commit()
        db.refresh(session_record)
        return session_record

    def get_by_hash(self, db: Session, token_hash: str) -> Optional[RefreshToken]:
        return db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()

    def get_active_sessions_for_user(self, db: Session, user_id: int) -> List[RefreshToken]:
        now = datetime.now(timezone.utc)
        return (
            db.query(RefreshToken)
            .filter(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > now
            )
            .all()
        )

    def revoke(self, db: Session, record: RefreshToken, replaced_by: Optional[str] = None) -> RefreshToken:
        record.revoked_at = datetime.now(timezone.utc)
        if replaced_by:
            record.replaced_by = replaced_by
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    def revoke_family(self, db: Session, family_id: str) -> int:
        """Revokes all refresh tokens in a given family (used during reuse detection)."""
        now = datetime.now(timezone.utc)
        rows_updated = (
            db.query(RefreshToken)
            .filter(
                RefreshToken.family_id == family_id,
                RefreshToken.revoked_at.is_(None)
            )
            .update({RefreshToken.revoked_at: now}, synchronize_session=False)
        )
        db.commit()
        return rows_updated

    def revoke_all_for_user(self, db: Session, user_id: int) -> int:
        """Revokes all active refresh tokens for a user."""
        now = datetime.now(timezone.utc)
        rows_updated = (
            db.query(RefreshToken)
            .filter(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None)
            )
            .update({RefreshToken.revoked_at: now}, synchronize_session=False)
        )
        db.commit()
        return rows_updated


refresh_token_repo = RefreshTokenRepository()

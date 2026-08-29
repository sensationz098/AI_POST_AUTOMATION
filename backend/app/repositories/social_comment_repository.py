from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.social_comment import SocialComment, CommentProcessingStatus

class SocialCommentRepository:
    def create_or_get_existing(
        self,
        db: Session,
        user_id: int,
        social_account_id: int,
        platform: str,
        external_comment_id: str,
        external_post_id: Optional[str] = None,
        parent_comment_id: Optional[str] = None,
        comment_text: Optional[str] = None,
        commenter_id: Optional[str] = None,
        commenter_name: Optional[str] = None,
        event_timestamp: Optional[datetime] = None,
        webhook_object: str = "page",
        processing_status: str = "RECEIVED",
        metadata_json: Optional[Dict[str, Any]] = None
    ) -> SocialComment:
        """
        Idempotent creation of SocialComment record.
        If a comment with the same (platform, external_comment_id) already exists, returns the existing record.
        """
        existing = db.query(SocialComment).filter(
            SocialComment.platform == platform,
            SocialComment.external_comment_id == external_comment_id
        ).first()

        if existing:
            return existing

        now = datetime.now(timezone.utc)
        new_comment = SocialComment(
            user_id=user_id,
            social_account_id=social_account_id,
            platform=platform,
            external_comment_id=external_comment_id,
            external_post_id=external_post_id,
            parent_comment_id=parent_comment_id,
            comment_text=comment_text,
            commenter_id=commenter_id,
            commenter_name=commenter_name,
            event_timestamp=event_timestamp or now,
            webhook_object=webhook_object,
            processing_status=processing_status,
            metadata_json=metadata_json or {},
            created_at=now,
            updated_at=now
        )

        try:
            db.add(new_comment)
            db.commit()
            db.refresh(new_comment)
            return new_comment
        except IntegrityError:
            db.rollback()
            return db.query(SocialComment).filter(
                SocialComment.platform == platform,
                SocialComment.external_comment_id == external_comment_id
            ).first()

    def get_by_user_id(
        self,
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 50,
        platform: Optional[str] = None
    ) -> List[SocialComment]:
        """Fetch comments belonging to a specific user with pagination."""
        query = db.query(SocialComment).filter(SocialComment.user_id == user_id)
        if platform:
            query = query.filter(SocialComment.platform == platform)
        return query.order_by(SocialComment.created_at.desc()).offset(skip).limit(limit).all()

social_comment_repo = SocialCommentRepository()

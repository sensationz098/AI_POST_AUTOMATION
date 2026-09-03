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
        metadata_json: Optional[Dict[str, Any]] = None,
        meta_ad_id: Optional[int] = None
    ) -> SocialComment:
        """
        Idempotent creation of SocialComment record.
        If a comment with the same (platform, external_comment_id) already exists, returns the existing record.
        Links to meta_ad_id if provided.
        """
        existing = db.query(SocialComment).filter(
            SocialComment.platform == platform,
            SocialComment.external_comment_id == external_comment_id
        ).first()

        if existing:
            is_updated = False
            if meta_ad_id is not None and existing.meta_ad_id is None:
                existing.meta_ad_id = meta_ad_id
                is_updated = True
            if commenter_name and not existing.commenter_name:
                existing.commenter_name = commenter_name
                is_updated = True
            if commenter_id and not existing.commenter_id:
                existing.commenter_id = commenter_id
                is_updated = True
            if is_updated:
                existing.updated_at = datetime.now(timezone.utc)
                db.commit()
                db.refresh(existing)
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
            meta_ad_id=meta_ad_id,
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
            ext = db.query(SocialComment).filter(
                SocialComment.platform == platform,
                SocialComment.external_comment_id == external_comment_id
            ).first()
            if ext:
                is_updated = False
                if meta_ad_id is not None and ext.meta_ad_id is None:
                    ext.meta_ad_id = meta_ad_id
                    is_updated = True
                if commenter_name and not ext.commenter_name:
                    ext.commenter_name = commenter_name
                    is_updated = True
                if commenter_id and not ext.commenter_id:
                    ext.commenter_id = commenter_id
                    is_updated = True
                if is_updated:
                    ext.updated_at = datetime.now(timezone.utc)
                    db.commit()
                    db.refresh(ext)
            return ext

    def get_by_user_id(
        self,
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 50,
        platform: Optional[str] = None,
        social_account_id: Optional[int] = None,
        meta_ad_id: Optional[int] = None,
        external_post_id: Optional[str] = None,
        is_ad: Optional[bool] = None
    ) -> List[SocialComment]:
        """Fetch comments belonging to a specific user with pagination, excluding owner reply echoes."""
        from app.models.social_comment_reply import SocialCommentReply
        from sqlalchemy.orm import joinedload

        reply_subquery = db.query(SocialCommentReply.external_reply_id).filter(
            SocialCommentReply.user_id == user_id,
            SocialCommentReply.external_reply_id.isnot(None)
        )
        if platform:
            reply_subquery = reply_subquery.filter(SocialCommentReply.platform == platform)

        query = db.query(SocialComment).options(
            joinedload(SocialComment.social_account),
            joinedload(SocialComment.meta_ad)
        ).filter(
            SocialComment.user_id == user_id,
            SocialComment.is_deleted.isnot(True),
            ~SocialComment.external_comment_id.in_(reply_subquery)
        )
        if platform:
            query = query.filter(SocialComment.platform == platform)
        if social_account_id:
            query = query.filter(SocialComment.social_account_id == social_account_id)
        if meta_ad_id is not None:
            query = query.filter(SocialComment.meta_ad_id == meta_ad_id)
        if external_post_id:
            query = query.filter(SocialComment.external_post_id == external_post_id)
        if is_ad is True:
            query = query.filter(SocialComment.meta_ad_id.isnot(None))
        elif is_ad is False:
            query = query.filter(SocialComment.meta_ad_id.is_(None))

        return query.order_by(SocialComment.created_at.desc()).offset(skip).limit(limit).all()

    def count_by_user_id(
        self,
        db: Session,
        user_id: int,
        platform: Optional[str] = None,
        social_account_id: Optional[int] = None,
        meta_ad_id: Optional[int] = None,
        external_post_id: Optional[str] = None,
        is_ad: Optional[bool] = None
    ) -> int:
        """Count comments belonging to a specific user, excluding owner reply echoes."""
        from app.models.social_comment_reply import SocialCommentReply

        reply_subquery = db.query(SocialCommentReply.external_reply_id).filter(
            SocialCommentReply.user_id == user_id,
            SocialCommentReply.external_reply_id.isnot(None)
        )
        if platform:
            reply_subquery = reply_subquery.filter(SocialCommentReply.platform == platform)

        query = db.query(SocialComment).filter(
            SocialComment.user_id == user_id,
            SocialComment.is_deleted.isnot(True),
            ~SocialComment.external_comment_id.in_(reply_subquery)
        )
        if platform:
            query = query.filter(SocialComment.platform == platform)
        if social_account_id:
            query = query.filter(SocialComment.social_account_id == social_account_id)
        if meta_ad_id is not None:
            query = query.filter(SocialComment.meta_ad_id == meta_ad_id)
        if external_post_id:
            query = query.filter(SocialComment.external_post_id == external_post_id)
        if is_ad is True:
            query = query.filter(SocialComment.meta_ad_id.isnot(None))
        elif is_ad is False:
            query = query.filter(SocialComment.meta_ad_id.is_(None))

        return query.count()

    def get_by_id_and_user_id(
        self,
        db: Session,
        comment_id: int,
        user_id: int
    ) -> Optional[SocialComment]:
        """Strict user ownership retrieval of a comment."""
        return db.query(SocialComment).filter(
            SocialComment.id == comment_id,
            SocialComment.user_id == user_id
        ).first()

    def mark_as_deleted(
        self,
        db: Session,
        comment_id: int,
        user_id: int
    ) -> Optional[SocialComment]:
        """Mark a social comment as deleted after successful Meta Graph API deletion."""
        comment = self.get_by_id_and_user_id(db, comment_id=comment_id, user_id=user_id)
        if not comment:
            return None
        now = datetime.now(timezone.utc)
        comment.is_deleted = True
        comment.deleted_at = now
        comment.processing_status = "DELETED"
        comment.updated_at = now
        db.commit()
        db.refresh(comment)
        return comment

    def create_reply_audit(
        self,
        db: Session,
        comment_id: int,
        user_id: int,
        platform: str,
        message: str,
        external_reply_id: Optional[str] = None,
        status: str = "SUCCESS",
        error_message: Optional[str] = None
    ):
        """Record manual reply attempt for auditing and reply history tracking."""
        from app.models.social_comment_reply import SocialCommentReply
        reply_record = SocialCommentReply(
            comment_id=comment_id,
            user_id=user_id,
            platform=platform,
            message=message,
            external_reply_id=external_reply_id,
            status=status,
            error_message=error_message,
            created_at=datetime.now(timezone.utc)
        )
        db.add(reply_record)
        db.commit()
        db.refresh(reply_record)
        return reply_record

social_comment_repo = SocialCommentRepository()


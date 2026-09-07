from typing import Optional, List
from sqlalchemy.orm import Session
from app.repositories.base import BaseRepository
from app.models.automation import Automation, AutomationStatus, PostTargetType
from app.models.social_account import SocialAccount
from app.models.post import Post


class AutomationRepository(BaseRepository[Automation]):
    def __init__(self):
        super().__init__(Automation)

    def get_by_id_and_user(self, db: Session, automation_id: int, user_id: int) -> Optional[Automation]:
        """Fetch automation by ID ensuring user ownership."""
        return db.query(Automation).filter(
            Automation.id == automation_id,
            Automation.user_id == user_id
        ).first()

    def get_by_user(
        self,
        db: Session,
        user_id: int,
        status: Optional[str] = None,
        platform: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Automation]:
        """List automations for a given user with optional filtering."""
        query = db.query(Automation).filter(Automation.user_id == user_id)
        if status:
            query = query.filter(Automation.status == status)
        if platform:
            query = query.filter(Automation.platform == platform)
        return query.order_by(Automation.created_at.desc()).offset(skip).limit(limit).all()

    def get_active_by_post(
        self,
        db: Session,
        social_account_id: int,
        external_post_id: str,
        platform: Optional[str] = None
    ) -> List[Automation]:
        """Fetch active automations matching a specific post and social account."""
        query = db.query(Automation).filter(
            Automation.social_account_id == social_account_id,
            Automation.status == AutomationStatus.ACTIVE.value,
            (
                (Automation.post_target_type == PostTargetType.SPECIFIC_POST.value) &
                (Automation.external_post_id == external_post_id)
            )
        )
        if platform:
            query = query.filter(Automation.platform == platform)
        return query.all()

    def validate_ownership(
        self,
        db: Session,
        user_id: int,
        social_account_id: int,
        internal_post_id: Optional[int] = None
    ) -> bool:
        """
        Validate that the social account (and optional internal post) belong to the given user.
        Prevents cross-user relationship hijacking.
        """
        account = db.query(SocialAccount).filter(
            SocialAccount.id == social_account_id,
            SocialAccount.user_id == user_id
        ).first()
        if not account:
            return False

        if internal_post_id is not None:
            post = db.query(Post).filter(
                Post.id == internal_post_id,
                Post.user_id == user_id
            ).first()
            if not post:
                return False

        return True


automation_repository = AutomationRepository()

from typing import List, Optional, Union, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from app.repositories.base import BaseRepository
from app.models.story import Story, StoryStatus


class StoryRepository(BaseRepository[Story]):
    def __init__(self):
        super().__init__(Story)

    def create(self, db: Session, obj_in: Union[Dict[str, Any], Story]) -> Story:
        if isinstance(obj_in, Story):
            db.add(obj_in)
            db.commit()
            db.refresh(obj_in)
            return obj_in
        return super().create(db, obj_in)

    def get_by_user(self, db: Session, user_id: int, status: Optional[str] = None) -> List[Story]:
        query = db.query(Story).filter(Story.user_id == user_id)
        if status:
            query = query.filter(Story.status == status)
        return query.order_by(Story.created_at.desc()).all()

    def get_by_brand(self, db: Session, brand_id: int, status: Optional[str] = None) -> List[Story]:
        query = db.query(Story).filter(Story.brand_id == brand_id)
        if status:
            query = query.filter(Story.status == status)
        return query.order_by(Story.created_at.desc()).all()

    def get_due_scheduled_stories(self, db: Session, now: datetime) -> List[Story]:
        query = db.query(Story).filter(
            Story.status == StoryStatus.SCHEDULED.value,
            Story.scheduled_at <= now
        )
        if db.bind and db.bind.dialect.name == "postgresql":
            query = query.with_for_update(skip_locked=True)
        return query.all()

    def get_failed_retryable_stories(self, db: Session) -> List[Story]:
        return db.query(Story).filter(
            Story.status == StoryStatus.FAILED.value,
            Story.retry_count < Story.max_retries
        ).all()


story_repo = StoryRepository()

from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.repositories.base import BaseRepository
from app.models.post import Post, PostStatus

class PostRepository(BaseRepository[Post]):
    def __init__(self):
        super().__init__(Post)

    def get_by_brand(self, db: Session, brand_id: int, status: Optional[str] = None) -> List[Post]:
        query = db.query(Post).filter(Post.brand_id == brand_id)
        if status:
            query = query.filter(Post.status == status)
        return query.order_by(Post.created_at.desc()).all()

    def get_due_scheduled_posts(self, db: Session, now: datetime) -> List[Post]:
        query = db.query(Post).filter(
            Post.status == PostStatus.SCHEDULED.value,
            Post.scheduled_at <= now
        )
        if db.bind and db.bind.dialect.name == "postgresql":
            query = query.with_for_update(skip_locked=True)
        return query.all()

    def get_failed_retryable_posts(self, db: Session) -> List[Post]:
        return db.query(Post).filter(
            Post.status == PostStatus.FAILED.value,
            Post.retry_count < Post.max_retries
        ).all()

post_repo = PostRepository()

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import List, Optional
from datetime import datetime
import logging
from app.repositories.post_repository import post_repo
from app.repositories.brand_repository import brand_repo
from app.repositories.audit_repository import audit_repo
from app.repositories.analytics_repository import analytics_repo
from app.schemas.post import PostCreate, PostUpdate
from app.models.post import Post, PostStatus
from app.services.meta_service import meta_service

logger = logging.getLogger(__name__)

class PostService:
    def create_post(self, db: Session, user_id: int, post_in: PostCreate) -> Post:
        data = post_in.model_dump()
        data["user_id"] = user_id
        post = post_repo.create(db, data)
        
        audit_repo.log(
            db=db,
            user_id=user_id,
            action="POST_CREATED",
            resource_type="Post",
            resource_id=post.id,
            details={"title": post.title, "status": post.status}
        )
        return post

    def get_post(self, db: Session, post_id: int) -> Post:
        post = post_repo.get(db, post_id)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        return post

    def get_brand_posts(self, db: Session, brand_id: int, status: Optional[str] = None) -> List[Post]:
        return post_repo.get_by_brand(db, brand_id, status)

    def update_post(self, db: Session, post_id: int, user_id: int, post_in: PostUpdate) -> Post:
        post = self.get_post(db, post_id)
        updated = post_repo.update(db, post, post_in.model_dump(exclude_unset=True))
        audit_repo.log(
            db=db,
            user_id=user_id,
            action="POST_UPDATED",
            resource_type="Post",
            resource_id=post_id,
            details=post_in.model_dump(exclude_unset=True)
        )
        return updated

    def approve_post(self, db: Session, post_id: int, user_id: int) -> Post:
        post = self.get_post(db, post_id)
        post.status = PostStatus.APPROVED.value
        db.commit()
        db.refresh(post)
        audit_repo.log(
            db=db,
            user_id=user_id,
            action="POST_APPROVED",
            resource_type="Post",
            resource_id=post_id
        )
        return post

    def schedule_post(self, db: Session, post_id: int, user_id: int, scheduled_at: datetime) -> Post:
        post = self.get_post(db, post_id)
        post.scheduled_at = scheduled_at
        post.status = PostStatus.SCHEDULED.value
        db.commit()
        db.refresh(post)
        audit_repo.log(
            db=db,
            user_id=user_id,
            action="POST_SCHEDULED",
            resource_type="Post",
            resource_id=post_id,
            details={"scheduled_at": scheduled_at.isoformat()}
        )
        return post

    def execute_publish(self, db: Session, post_id: int) -> Post:
        """Execute social publishing to Facebook Pages & Instagram Business via Meta API."""
        post = self.get_post(db, post_id)
        meta_acc = brand_repo.get_meta_account(db, post.brand_id)

        access_token = meta_acc.access_token if meta_acc else "sandbox_token"
        fb_page_id = meta_acc.facebook_page_id if meta_acc else "sandbox"
        ig_user_id = meta_acc.instagram_account_id if meta_acc else "sandbox"

        formatted_caption = f"{post.caption}\n\n{' '.join(post.hashtags or [])}\n\n{post.cta or ''}".strip()
        errors = []

        # 1. Publish to Facebook
        if "facebook" in (post.platforms or ["facebook"]):
            try:
                res = meta_service.publish_to_facebook_page(
                    page_id=fb_page_id,
                    access_token=access_token,
                    message=formatted_caption,
                    image_url=post.image_url
                )
                post.fb_post_id = res.get("id")
            except Exception as e:
                errors.append(f"FB Publish Error: {str(e)}")

        # 2. Publish to Instagram
        if "instagram" in (post.platforms or ["instagram"]):
            try:
                if not post.image_url:
                    errors.append("IG Publish Error: Image URL is required for Instagram posts.")
                else:
                    res = meta_service.publish_to_instagram_business(
                        ig_user_id=ig_user_id,
                        access_token=access_token,
                        caption=formatted_caption,
                        image_url=post.image_url
                    )
                    post.ig_container_id = res.get("container_id")
                    post.ig_media_id = res.get("id")
            except Exception as e:
                errors.append(f"IG Publish Error: {str(e)}")

        if errors:
            post.retry_count += 1
            post.last_error = " | ".join(errors)
            if post.retry_count >= post.max_retries:
                post.status = PostStatus.FAILED.value
            else:
                post.status = PostStatus.FAILED.value  # Marked failed until retry task picks up
            db.commit()
            db.refresh(post)
            audit_repo.log(
                db=db,
                user_id=post.user_id,
                action="POST_PUBLISH_FAILED",
                resource_type="Post",
                resource_id=post.id,
                details={"errors": errors, "retry_count": post.retry_count}
            )
            return post

        # Successful publish
        post.status = PostStatus.PUBLISHED.value
        post.published_at = datetime.utcnow()
        post.last_error = None
        db.commit()
        db.refresh(post)

        # Initialize mock analytics record for post
        analytics_repo.create(
            db=db,
            obj_in={
                "post_id": post.id,
                "likes": 142,
                "comments": 28,
                "shares": 19,
                "saves": 35,
                "reach": 1850,
                "impressions": 2400,
                "engagement_rate": 8.4,
                "follower_growth": 12
            }
        )

        audit_repo.log(
            db=db,
            user_id=post.user_id,
            action="POST_PUBLISHED",
            resource_type="Post",
            resource_id=post.id,
            details={"fb_id": post.fb_post_id, "ig_id": post.ig_media_id}
        )
        return post

    def retry_failed_post(self, db: Session, post_id: int, user_id: int) -> Post:
        post = self.get_post(db, post_id)
        if post.status != PostStatus.FAILED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only failed posts can be retried"
            )
        post.retry_count = 0
        db.commit()
        return self.execute_publish(db, post_id)

post_service = PostService()

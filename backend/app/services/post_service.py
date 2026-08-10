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

import requests

logger = logging.getLogger(__name__)

def upload_base64_to_public_https(base64_str: str) -> Optional[str]:
    """Compress and upload custom base64 image data to public HTTPS CDN (catbox.moe) for Meta Instagram Graph API."""
    try:
        if not base64_str or not base64_str.startswith("data:image"):
            return None
        import base64, io
        from PIL import Image

        encoded_data = base64_str.split(",", 1)[1] if "," in base64_str else base64_str
        raw_bytes = base64.b64decode(encoded_data)

        # Optimize custom uploaded photo with PIL to standard 1080x1080 Instagram JPEG format
        img = Image.open(io.BytesIO(raw_bytes))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.thumbnail((1080, 1080))

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85, optimize=True)
        img_bytes = buffer.getvalue()

        # Post directly to catbox.moe free public CDN (returns direct https://files.catbox.moe/*.jpg URL)
        files = {"fileToUpload": ("custom_post_photo.jpg", img_bytes, "image/jpeg")}
        data = {"reqtype": "fileupload"}
        res = requests.post("https://catbox.moe/user/api.php", data=data, files=files, timeout=20)

        if res.status_code == 200 and res.text.startswith("https://files.catbox.moe/"):
            public_url = res.text.strip()
            logger.info(f"Custom photo uploaded to public HTTPS CDN for Instagram: {public_url}")
            return public_url
    except Exception as e:
        logger.error(f"Failed to upload base64 image to catbox CDN: {e}")
    return None

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
        from app.models.meta_account import MetaAccount
        
        post = self.get_post(db, post_id)
        meta_acc = brand_repo.get_meta_account(db, post.brand_id)

        # Fallback to any connected MetaAccount in DB if brand doesn't have explicit Meta Account
        if not meta_acc or not meta_acc.is_connected or not meta_acc.access_token:
            meta_acc = db.query(MetaAccount).filter(MetaAccount.is_connected == True).first()

        access_token = meta_acc.access_token if (meta_acc and meta_acc.access_token) else "sandbox_token"
        fb_page_id = meta_acc.facebook_page_id if (meta_acc and meta_acc.facebook_page_id) else "sandbox"
        ig_user_id = meta_acc.instagram_account_id if (meta_acc and meta_acc.instagram_account_id) else "sandbox"

        # Resolve exact public HTTPS image URL so both Facebook and Instagram post the IDENTICAL image
        public_image_url = post.image_url
        if public_image_url and (public_image_url.startswith("data:") or public_image_url.startswith("blob:")):
            uploaded_url = upload_base64_to_public_https(public_image_url)
            if uploaded_url:
                public_image_url = uploaded_url
            else:
                try:
                    import base64, uuid, os
                    header, encoded = public_image_url.split(",", 1)
                    mime_type = header.split(";")[0].split(":")[1] if ";" in header else "image/png"
                    ext = mime_type.split("/")[1] if "/" in mime_type else "png"
                    img_data = base64.b64decode(encoded)

                    os.makedirs("uploads", exist_ok=True)
                    filename = f"post_{post.id}_{uuid.uuid4().hex[:8]}.{ext}"
                    filepath = os.path.join("uploads", filename)
                    with open(filepath, "wb") as f:
                        f.write(img_data)

                    public_image_url = f"http://127.0.0.1:8000/uploads/{filename}"
                except Exception as e:
                    logger.error(f"Failed to process base64 upload: {e}")

        formatted_caption = f"{post.caption}\n\n{' '.join(post.hashtags or [])}\n\n{post.cta or ''}".strip()
        errors = []

        is_sandbox_fb = False
        is_sandbox_ig = False

        # 1. Publish to Facebook
        if "facebook" in (post.platforms or ["facebook"]):
            try:
                res = meta_service.publish_to_facebook_page(
                    page_id=fb_page_id,
                    access_token=access_token,
                    message=formatted_caption,
                    image_url=post.image_url or public_image_url
                )
                post.fb_post_id = res.get("id")
                if res.get("status") == "published_sandbox":
                    is_sandbox_fb = True
            except Exception as e:
                errors.append(f"FB Publish Error: {str(e)}")

        # 2. Publish to Instagram (Custom Photo Only — AI model image fallbacks disabled)
        if "instagram" in (post.platforms or ["instagram"]):
            try:
                ig_url = public_image_url
                if ig_url and (ig_url.startswith("data:") or ig_url.startswith("blob:")):
                    ig_url = upload_base64_to_public_https(ig_url) or ig_url

                if not ig_url or ig_url.startswith("data:") or ig_url.startswith("blob:"):
                    errors.append("IG Publish Error: A valid custom photo file or public Image URL is required for Instagram publishing.")
                else:
                    res = meta_service.publish_to_instagram_business(
                        ig_user_id=ig_user_id,
                        access_token=access_token,
                        caption=formatted_caption,
                        image_url=ig_url
                    )
                    post.ig_container_id = res.get("container_id")
                    post.ig_media_id = res.get("id")
                    if res.get("status") == "published_sandbox":
                        is_sandbox_ig = True
            except Exception as e:
                errors.append(f"IG Publish Error: {str(e)}")

        if errors:
            post.retry_count += 1
            post.last_error = " | ".join(errors)
            post.status = PostStatus.FAILED.value
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
        if is_sandbox_fb or is_sandbox_ig:
            post.last_error = "SANDBOX_MODE: Post simulated in local sandbox mode. Connect real Meta credentials (User/Page Access Token & Page ID) in 'Connect Meta Accounts' to post live to Facebook & Instagram."
        else:
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

    def check_and_publish_due_posts(self, db: Session) -> List[Post]:
        """Find any scheduled posts whose scheduled time has passed and execute publishing."""
        now = datetime.utcnow()
        due_posts = post_repo.get_due_scheduled_posts(db, now)
        published_posts = []
        for post in due_posts:
            try:
                published = self.execute_publish(db, post.id)
                published_posts.append(published)
                logger.info(f"Auto-published scheduled post ID={post.id} (Scheduled at: {post.scheduled_at})")
            except Exception as e:
                logger.error(f"Auto-publish failed for scheduled post ID={post.id}: {e}")
        return published_posts

post_service = PostService()

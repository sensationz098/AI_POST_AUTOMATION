from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import List, Optional
from datetime import datetime, timezone
import logging
from app.repositories.post_repository import post_repo
from app.repositories.brand_repository import brand_repo
from app.repositories.audit_repository import audit_repo
from app.repositories.analytics_repository import analytics_repo
from app.schemas.post import PostCreate, PostUpdate
from app.models.post import Post, PostStatus
from app.services.meta_service import meta_service

import requests

from app.services.cloudinary_service import upload_media_to_cloudinary

from app.core.logging_config import sanitize_url
from app.services.publisher_service import resolve_media_type

logger = logging.getLogger(__name__)

def upload_base64_to_public_https(base64_str: str) -> Optional[str]:
    """Upload image or video media to Cloudinary HTTPS CDN for Meta Facebook & Instagram Graph API."""
    return upload_media_to_cloudinary(base64_str)

class PostService:
    def _process_and_upload_post_media(self, data: dict) -> dict:
        """
        Inspect incoming post data dictionary for media content, resolve media_type explicitly,
        and ensure Base64 / data URIs are uploaded to Cloudinary CDN before DB persistence.
        """
        raw_url = data.get("image_url")
        req_media_type = data.get("media_type")

        # 1. Resolve media_type explicitly
        resolved_type, is_video = resolve_media_type(
            explicit_media_type=req_media_type,
            stored_media_type=None,
            media_url=raw_url
        )
        data["media_type"] = resolved_type

        if not raw_url:
            return data

        # 2. Check if raw_url is a data URL / base64 or blob URL requiring Cloudinary upload
        is_data_uri = (
            raw_url.startswith("data:") or
            raw_url.startswith("blob:") or
            (";base64," in raw_url)
        )

        if is_data_uri:
            payload_bytes = len(raw_url)
            size_mb = payload_bytes / (1024 * 1024)
            logger.info(
                f"[MEDIA_TRACE] POST_MEDIA_RECEIVED | source=data_url | "
                f"media_type={resolved_type} | payload_size_mb={size_mb:.2f}"
            )
            logger.info(f"[MEDIA_TRACE] CLOUDINARY_UPLOAD_STARTED | media_type={resolved_type}")

            cloudinary_url = upload_media_to_cloudinary(raw_url, media_type=resolved_type)

            if cloudinary_url:
                sanitized_cdn_url = sanitize_url(cloudinary_url)
                logger.info(
                    f"[MEDIA_TRACE] CLOUDINARY_UPLOAD_SUCCESS | media_type={resolved_type} | "
                    f"url={sanitized_cdn_url}"
                )
                data["image_url"] = cloudinary_url
            else:
                logger.error(
                    f"[MEDIA_TRACE] CLOUDINARY_UPLOAD_FAILED | media_type={resolved_type} | "
                    f"payload_size_mb={size_mb:.2f}"
                )
                if payload_bytes > 500000:  # > 500KB
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Failed to upload large media asset to Cloudinary. Raw Base64 payloads cannot be saved directly to database."
                    )
        elif raw_url.startswith("https://res.cloudinary.com/"):
            logger.info(f"[MEDIA_TRACE] POST_MEDIA_REUSED | source=cloudinary_url | media_type={resolved_type}")
        else:
            logger.info(f"[MEDIA_TRACE] POST_MEDIA_RECEIVED | source=external_url | media_type={resolved_type}")

        return data

    def create_post(self, db: Session, user_id: int, post_in: PostCreate) -> Post:
        from app.models.brand import BrandProfile
        data = post_in.model_dump()
        data["user_id"] = user_id

        # Pre-process media: resolve media_type and upload base64 payloads to Cloudinary CDN before DB insert
        data = self._process_and_upload_post_media(data)

        # Ensure brand exists and belongs to current user
        brand_id = data.get("brand_id", 1)
        existing_brand = db.query(BrandProfile).filter(
            BrandProfile.id == brand_id,
            BrandProfile.user_id == user_id
        ).first()
        if not existing_brand:
            user_brand = db.query(BrandProfile).filter(BrandProfile.user_id == user_id).first()
            if user_brand:
                data["brand_id"] = user_brand.id
            else:
                new_brand = BrandProfile(
                    name="Apex Innovations",
                    industry="Artificial Intelligence",
                    tone_of_voice="Professional & Energetic",
                    target_audience="Tech Enthusiasts",
                    cta_style="Value focused",
                    user_id=user_id
                )
                db.add(new_brand)
                try:
                    db.commit()
                    db.refresh(new_brand)
                    data["brand_id"] = new_brand.id
                except Exception:
                    db.rollback()

        logger.info(
            f"[MEDIA_TRACE] POST_PERSISTING | media_type={data.get('media_type')} | "
            f"media_url_len={len(data.get('image_url') or '')}"
        )
        post = post_repo.create(db, data)
        logger.info(f"[MEDIA_TRACE] POST_PERSISTED | post_id={post.id} | media_type={post.media_type}")

        audit_repo.log(
            db=db,
            user_id=user_id,
            action="POST_CREATED",
            resource_type="Post",
            resource_id=post.id,
            details={"title": post.title, "status": post.status}
        )
        return post


    def get_post(self, db: Session, post_id: int, user_id: int) -> Post:
        """Get single post with strict user ownership validation."""
        post = post_repo.get(db, post_id)
        if not post or post.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found or access denied"
            )
        return post

    def get_user_posts(self, db: Session, user_id: int, status: Optional[str] = None) -> List[Post]:
        """Retrieve all posts belonging to the authenticated user across all brands."""
        self.check_and_publish_due_posts(db, user_id)
        query = db.query(Post).filter(Post.user_id == user_id)
        if status:
            query = query.filter(Post.status == status)
        return query.order_by(Post.created_at.desc()).all()

    def get_brand_posts(self, db: Session, brand_id: int, user_id: int, status: Optional[str] = None) -> List[Post]:
        from app.models.brand import BrandProfile
        brand = db.query(BrandProfile).filter(
            BrandProfile.id == brand_id,
            BrandProfile.user_id == user_id
        ).first()
        if not brand:
            # Fallback: check if user has any brand profile or return all user posts
            user_brand = db.query(BrandProfile).filter(BrandProfile.user_id == user_id).first()
            if user_brand:
                brand_id = user_brand.id
            else:
                return self.get_user_posts(db, user_id, status)
        self.check_and_publish_due_posts(db, user_id)
        return post_repo.get_by_brand(db, brand_id, status)

    def update_post(self, db: Session, post_id: int, user_id: int, post_in: PostUpdate) -> Post:
        post = self.get_post(db, post_id, user_id)
        update_data = post_in.model_dump(exclude_unset=True)
        if "image_url" in update_data or "media_type" in update_data:
            update_data = self._process_and_upload_post_media(update_data)
        updated = post_repo.update(db, post, update_data)
        audit_repo.log(
            db=db,
            user_id=user_id,
            action="POST_UPDATED",
            resource_type="Post",
            resource_id=post_id,
            details=update_data
        )
        return updated


    def approve_post(self, db: Session, post_id: int, user_id: int) -> Post:
        post = self.get_post(db, post_id, user_id)
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
        post = self.get_post(db, post_id, user_id)
        now_utc = datetime.now(timezone.utc)
        # Ensure scheduled_at is comparable
        sched = scheduled_at.replace(tzinfo=timezone.utc) if scheduled_at.tzinfo is None else scheduled_at
        if sched <= now_utc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Scheduled publishing time must be in the future."
            )
        post.scheduled_at = sched
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

    def execute_publish(self, db: Session, post_id: int, user_id: Optional[int] = None) -> Post:
        """Execute social publishing to user's connected Meta accounts."""
        from app.models.meta_account import MetaAccount
        from app.core.security_encryption import decrypt_token
        
        post = post_repo.get(db, post_id)
        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
        if user_id and post.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        # Fetch Meta account owned ONLY by current post user
        meta_acc = brand_repo.get_meta_account(db, post.brand_id)
        if meta_acc and meta_acc.brand and meta_acc.brand.user_id != post.user_id:
            meta_acc = None

        from app.models.social_account import SocialAccount
        user_accounts = db.query(SocialAccount).filter(
            SocialAccount.user_id == post.user_id,
            SocialAccount.status == "CONNECTED"
        ).all()

        fb_acc = next((a for a in user_accounts if a.platform == "facebook" and (not post.brand_id or a.brand_id == post.brand_id)), None)
        if not fb_acc:
            fb_acc = next((a for a in user_accounts if a.platform == "facebook"), None)

        ig_acc = next((a for a in user_accounts if a.platform == "instagram" and (not post.brand_id or a.brand_id == post.brand_id)), None)
        if not ig_acc:
            ig_acc = next((a for a in user_accounts if a.platform == "instagram"), None)

        if not meta_acc and not fb_acc and not ig_acc:
            post.status = PostStatus.FAILED.value
            post.last_error = "No connected social account found. Please connect your Facebook Page or Instagram account."
            db.commit()
            return post

        fb_token = decrypt_token(fb_acc.access_token) if fb_acc else (decrypt_token(meta_acc.access_token) if meta_acc else None)
        fb_page_id = fb_acc.account_id if fb_acc else (meta_acc.facebook_page_id if meta_acc else "sandbox")

        ig_token = decrypt_token(ig_acc.access_token) if ig_acc else (decrypt_token(meta_acc.access_token) if meta_acc else None)
        ig_user_id = ig_acc.account_id if ig_acc else (meta_acc.instagram_account_id if meta_acc else "sandbox")

        # Resolve public HTTPS media URL via Cloudinary
        public_image_url = post.image_url
        if public_image_url and (public_image_url.startswith("data:") or public_image_url.startswith("blob:")):
            public_image_url = upload_base64_to_public_https(public_image_url) or public_image_url

        formatted_caption = f"{post.caption}\n\n{' '.join(post.hashtags or [])}\n\n{post.cta or ''}".strip()
        errors = []
        successful_publish = False

        from app.services.publisher_service import resolve_media_type
        resolved_media_type, is_video = resolve_media_type(
            stored_media_type=getattr(post, "media_type", None),
            media_url=post.image_url or public_image_url
        )


        is_sandbox_fb = False
        is_sandbox_ig = False

        # 1. Publish to Facebook
        if "facebook" in (post.platforms or ["facebook"]):
            if fb_acc or (meta_acc and meta_acc.facebook_page_id):
                try:
                    fb_media_url = public_image_url or post.image_url
                    if is_video and (not fb_media_url or fb_media_url.startswith("data:") or fb_media_url.startswith("blob:") or not (fb_media_url.startswith("http://") or fb_media_url.startswith("https://"))):
                        errors.append("FB Publish Error: A valid public HTTPS video URL is required for Facebook video publishing.")
                    else:
                        res = meta_service.publish_to_facebook_page(
                            page_id=fb_page_id,
                            access_token=fb_token or "sandbox_token",
                            message=formatted_caption,
                            image_url=fb_media_url,
                            is_video=is_video
                        )
                        fb_id = res.get("id")
                        if not fb_id:
                            raise Exception("Facebook API returned response without published post ID.")
                        post.fb_post_id = str(fb_id)
                        successful_publish = True
                        if res.get("status") == "published_sandbox":
                            is_sandbox_fb = True
                except Exception as e:
                    errors.append(f"FB Publish Error: {str(e)}")
            else:
                errors.append("FB Publish Notice: No connected Facebook Page account found.")

        # 2. Publish to Instagram
        if "instagram" in (post.platforms or ["instagram"]):
            if ig_acc or (meta_acc and meta_acc.instagram_account_id):
                try:
                    ig_url = public_image_url
                    if is_video and (not ig_url or ig_url.startswith("data:") or ig_url.startswith("blob:") or not (ig_url.startswith("http://") or ig_url.startswith("https://"))):
                        errors.append("IG Publish Error: A valid public HTTPS video URL is required for Instagram Reel publishing.")
                    elif not is_video and (not ig_url or ig_url.startswith("data:") or ig_url.startswith("blob:")):
                        errors.append("IG Publish Error: A valid photo file or public URL is required for Instagram publishing.")
                    else:
                        res = meta_service.publish_to_instagram_business(
                            ig_user_id=ig_user_id,
                            access_token=ig_token or "sandbox_token",
                            caption=formatted_caption,
                            image_url=ig_url,
                            is_video=is_video
                        )
                        post.ig_container_id = res.get("container_id")
                        published_ig_id = res.get("id")
                        if not published_ig_id:
                            raise Exception("Instagram API returned response without published media ID.")
                        post.ig_media_id = str(published_ig_id)
                        successful_publish = True
                        if res.get("status") == "published_sandbox":
                            is_sandbox_ig = True
                except Exception as e:
                    errors.append(f"IG Publish Error: {str(e)}")
            else:
                errors.append("IG Publish Notice: No connected Instagram Business account found.")


        if not successful_publish:
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

        # At least one targeted platform published successfully
        post.status = PostStatus.PUBLISHED.value
        post.published_at = datetime.now(timezone.utc)
        if errors:
            post.last_error = f"Published with warnings: {' | '.join(errors)}"
        elif is_sandbox_fb or is_sandbox_ig:
            post.last_error = "SANDBOX_MODE: Simulated publishing."
        else:
            post.last_error = None

        db.commit()
        db.refresh(post)

        audit_repo.log(
            db=db,
            user_id=post.user_id,
            action="POST_PUBLISHED",
            resource_type="Post",
            resource_id=post.id,
            details={"fb_id": post.fb_post_id, "ig_id": post.ig_media_id, "errors": errors}
        )
        return post

    def retry_failed_post(self, db: Session, post_id: int, user_id: int) -> Post:
        post = self.get_post(db, post_id, user_id)
        if post.status != PostStatus.FAILED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only failed posts can be retried"
            )
        post.retry_count = 0
        db.commit()
        return self.execute_publish(db, post_id, user_id)

    def check_and_publish_due_posts(self, db: Session, user_id: Optional[int] = None) -> List[Post]:
        """Find scheduled posts whose time has passed and execute publishing."""
        try:
            now = datetime.now(timezone.utc)
            due_posts = post_repo.get_due_scheduled_posts(db, now)
            if user_id:
                due_posts = [p for p in due_posts if p.user_id == user_id]
            published_posts = []
            for post in due_posts:
                try:
                    published = self.execute_publish(db, post.id, post.user_id)
                    published_posts.append(published)
                    logger.info(f"Auto-published scheduled post ID={post.id} (Scheduled at: {post.scheduled_at})")
                except Exception as e:
                    logger.error(f"Auto-publish failed for scheduled post ID={post.id}: {e}")
            return published_posts
        except Exception as e:
            logger.error(f"Failed checking due posts: {e}")
            try:
                db.rollback()
            except Exception:
                pass
            return []

post_service = PostService()

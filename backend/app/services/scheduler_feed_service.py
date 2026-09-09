import logging
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.social_account import SocialAccount
from app.schemas.scheduler import SchedulerItemResponse, SchedulerTargetAccount
from app.services.post_service import post_service
from app.services.story_service import story_service
from app.core.story_url_helper import (
    is_valid_facebook_story_url,
    is_valid_instagram_story_url,
    build_instagram_story_url,
    resolve_instagram_username_from_social_account,
    sanitize_instagram_username,
)

logger = logging.getLogger(__name__)


class SchedulerFeedService:
    """Unified scheduler feed service that aggregates Posts and Stories into a single chronological queue."""

    def get_scheduler_feed(
        self,
        db: Session,
        user_id: int,
        brand_id: Optional[int] = None,
        status: Optional[str] = None,
        item_type: Optional[str] = None
    ) -> List[SchedulerItemResponse]:
        """Fetch unified queue of posts and stories sorted chronologically."""
        # 1. Trigger due checks for stories
        try:
            story_service.check_and_publish_due_stories(db, user_id)
        except Exception as e:
            logger.warning(f"[SCHEDULER_FEED] Error during check_and_publish_due_stories: {e}")

        # 2. Fetch social accounts for user
        user_accounts = db.query(SocialAccount).filter(SocialAccount.user_id == user_id).all()
        acc_map = {acc.id: acc for acc in user_accounts}

        items: List[SchedulerItemResponse] = []

        # 3. Posts
        if not item_type or item_type.lower() == "post":
            if brand_id:
                posts = post_service.get_brand_posts(db, brand_id, user_id, status)
            else:
                posts = post_service.get_user_posts(db, user_id, status)

            for p in posts:
                p_targets = getattr(p, "target_account_ids", None) or []
                matched_accs = [
                    SchedulerTargetAccount(
                        id=acc.id,
                        account_id=acc.account_id,
                        account_name=acc.account_name,
                        platform=acc.platform,
                        username=(acc.metadata_json or {}).get("username") if isinstance(acc.metadata_json, dict) else acc.account_name,
                        logo_url=acc.logo_url
                    )
                    for aid in p_targets
                    if (acc := acc_map.get(aid)) is not None
                ]

                items.append(
                    SchedulerItemResponse(
                        id=p.id,
                        item_type="post",
                        brand_id=p.brand_id,
                        user_id=p.user_id,
                        title=p.title,
                        caption=p.caption,
                        media_url=p.image_url,
                        media_type=p.media_type or ("video" if (p.image_url and any(p.image_url.lower().endswith(ext) for ext in [".mp4", ".mov", ".webm"])) else "image"),
                        thumbnail_url=p.thumbnail_url or p.image_url,
                        platforms=p.platforms or [],
                        target_account_ids=p_targets,
                        target_accounts=matched_accs,
                        status=p.status,
                        scheduled_at=p.scheduled_at,
                        published_at=p.published_at,
                        retry_count=p.retry_count,
                        max_retries=p.max_retries,
                        last_error=p.last_error,
                        fb_id=p.fb_post_id,
                        ig_id=p.ig_media_id,
                        fb_url=p.fb_post_url,
                        ig_url=p.ig_media_url,
                        created_at=p.created_at,
                        updated_at=p.updated_at
                    )
                )

        # 4. Stories
        if not item_type or item_type.lower() == "story":
            stories = story_service.get_user_stories(db, user_id, brand_id, status)
            for s in stories:
                s_targets = s.target_account_ids or []
                matched_accs = [
                    SchedulerTargetAccount(
                        id=acc.id,
                        account_id=acc.account_id,
                        account_name=acc.account_name,
                        platform=acc.platform,
                        username=resolve_instagram_username_from_social_account(acc) if acc.platform == "instagram" else ((acc.metadata_json or {}).get("username") if isinstance(acc.metadata_json, dict) else acc.account_name),
                        logo_url=acc.logo_url
                    )
                    for aid in s_targets
                    if (acc := acc_map.get(aid)) is not None
                ]

                # Facebook Story URL: Only legitimate individual permalink is used. Never fake page-id URL.
                fb_url = None
                if s.fb_story_id and s.fb_story_url and is_valid_facebook_story_url(s.fb_story_url):
                    fb_url = s.fb_story_url

                # Instagram Story URL: Resolve legitimate username story link or valid permalink. Never bare /stories/.
                ig_url = None
                if s.ig_story_id:
                    if s.ig_story_url and is_valid_instagram_story_url(s.ig_story_url):
                        ig_url = s.ig_story_url
                    else:
                        # Attempt resolution from story.ig_username or matched IG accounts
                        ig_user = sanitize_instagram_username(s.ig_username)
                        if not ig_user:
                            for aid in s_targets:
                                acc = acc_map.get(aid)
                                if acc and acc.platform == "instagram":
                                    resolved = resolve_instagram_username_from_social_account(acc)
                                    if resolved:
                                        ig_user = resolved
                                        break
                        if ig_user:
                            ig_url = build_instagram_story_url(ig_user)

                items.append(
                    SchedulerItemResponse(
                        id=s.id,
                        item_type="story",
                        brand_id=s.brand_id,
                        user_id=s.user_id,
                        title=s.title,
                        caption=s.caption,
                        media_url=s.media_url,
                        media_type=s.media_type,
                        thumbnail_url=s.thumbnail_url or s.media_url,
                        platforms=s.platforms or [],
                        target_account_ids=s_targets,
                        target_accounts=matched_accs,
                        status=s.status,
                        scheduled_at=s.scheduled_at,
                        published_at=s.published_at,
                        retry_count=s.retry_count,
                        max_retries=s.max_retries,
                        last_error=s.last_error,
                        fb_id=s.fb_story_id,
                        ig_id=s.ig_story_id,
                        fb_url=fb_url,
                        ig_url=ig_url,
                        created_at=s.created_at,
                        updated_at=s.updated_at
                    )
                )

        # 5. Chronological sort (newest scheduled / published / created first)
        def sort_key(item: SchedulerItemResponse):
            dt = item.scheduled_at or item.published_at or item.created_at
            return dt.timestamp() if dt else 0.0

        items.sort(key=sort_key, reverse=True)
        return items


scheduler_feed_service = SchedulerFeedService()

from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.orm import Session
from app.repositories.analytics_repository import analytics_repo
from app.repositories.brand_repository import brand_repo
from app.repositories.social_account_repository import social_account_repo
from app.schemas.analytics import (
    DashboardAnalyticsResponse,
    MetricOverview,
    DailyMetricPoint,
    FacebookPageMetrics,
    InstagramAccountMetrics,
)
from app.services.meta_service import meta_service
from app.models.meta_account import MetaAccount

from app.core.security_encryption import decrypt_token
from fastapi import HTTPException, status

class AnalyticsService:
    def get_user_overview_dashboard(self, db: Session, user_id: int) -> DashboardAnalyticsResponse:
        """Fetch aggregated insights across ALL connected Facebook Pages & Instagram accounts belonging to the user."""
        all_accounts = social_account_repo.get_by_user(db, user_id)
        fake_ids = {"109823471029", "17841400928371", "17841400928372", "17841400928373", "109823471030", "sandbox"}
        real_accounts = [
            a for a in all_accounts
            if a.account_id not in fake_ids and not (a.access_token and ("sandbox" in a.access_token or "mock" in a.access_token))
        ]

        summary = analytics_repo.get_user_summary(db, user_id) if hasattr(analytics_repo, 'get_user_summary') else {
            "total_posts": 0, "published_posts": 0, "scheduled_posts": 0, "failed_posts": 0,
            "total_likes": 0, "total_comments": 0, "total_shares": 0, "total_reach": 0,
            "total_impressions": 0, "avg_engagement_rate": 0.0
        }

        accounts_list = []
        total_followers_combined = 0
        total_reach_combined = summary.get("total_reach", 0)
        total_impressions_combined = summary.get("total_impressions", 0)
        has_live_meta = False

        def _fetch_account_entry(acc):
            token = decrypt_token(acc.access_token) or acc.access_token
            try:
                if acc.platform == "facebook":
                    fb_raw = meta_service.fetch_facebook_page_metrics(page_id=acc.account_id, access_token=token)
                    followers = fb_raw.get("followers_count")
                    return {
                        "entry": {
                            "id": acc.id,
                            "account_id": acc.account_id,
                            "account_name": acc.account_name,
                            "platform": "facebook",
                            "logo_url": acc.logo_url,
                            "followers_count": followers if followers is not None else 0,
                            "fan_count": fb_raw.get("fan_count"),
                            "media_count": fb_raw.get("media_count"),
                            "media_count_source": fb_raw.get("media_count_source", "meta_total_unavailable"),
                            "category": fb_raw.get("category", "Facebook Page"),
                            "status": acc.status,
                            "link": f"https://facebook.com/{acc.account_id}"
                        },
                        "followers": followers or 0,
                        "is_live": not fb_raw.get("is_sandbox")
                    }
                elif acc.platform == "instagram":
                    ig_raw = meta_service.fetch_instagram_account_metrics(ig_user_id=acc.account_id, access_token=token)
                    followers = ig_raw.get("followers_count")
                    return {
                        "entry": {
                            "id": acc.id,
                            "account_id": acc.account_id,
                            "account_name": acc.account_name,
                            "platform": "instagram",
                            "logo_url": acc.logo_url,
                            "followers_count": followers if followers is not None else 0,
                            "media_count": ig_raw.get("media_count"),
                            "media_count_source": ig_raw.get("media_count_source", "meta_verified_exact_total"),
                            "status": acc.status,
                            "link": f"https://instagram.com/{acc.account_name.lstrip('@')}"
                        },
                        "followers": followers or 0,
                        "is_live": not ig_raw.get("is_sandbox")
                    }
            except Exception as e:
                import logging
                logging.getLogger("uvicorn.error").error(f"[ANALYTICS_ACCOUNT_ISOLATION_ERROR] platform={acc.platform} account_id={acc.account_id} error={e}")
                return {
                    "entry": {
                        "id": acc.id,
                        "account_id": acc.account_id,
                        "account_name": acc.account_name,
                        "platform": acc.platform,
                        "logo_url": acc.logo_url,
                        "followers_count": 0,
                        "media_count": None,
                        "media_count_source": "meta_total_unavailable",
                        "status": acc.status,
                        "link": f"https://facebook.com/{acc.account_id}" if acc.platform == "facebook" else f"https://instagram.com/{acc.account_name.lstrip('@')}"
                    },
                    "followers": 0,
                    "is_live": False
                }

        if real_accounts:
            with ThreadPoolExecutor(max_workers=min(len(real_accounts), 10)) as executor:
                futures = [executor.submit(_fetch_account_entry, acc) for acc in real_accounts]
                results = [f.result() for f in futures]

            for res in results:
                accounts_list.append(res["entry"])
                total_followers_combined += res["followers"]
                if res["is_live"]:
                    has_live_meta = True

        summary["total_reach"] = total_reach_combined
        summary["total_impressions"] = total_impressions_combined

        overview = MetricOverview(**summary)
        daily_trends = []

        return DashboardAnalyticsResponse(
            overview=overview,
            daily_trends=daily_trends,
            accounts_list=accounts_list,
            is_live_meta=has_live_meta
        )

    def get_brand_dashboard(self, db: Session, brand_id: int, user_id: int) -> DashboardAnalyticsResponse:
        from app.models.brand import BrandProfile
        brand = db.query(BrandProfile).filter(
            BrandProfile.id == brand_id,
            BrandProfile.user_id == user_id
        ).first()
        if not brand:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Brand profile not found or access denied"
            )

        summary = analytics_repo.get_brand_summary(db, brand_id)
        meta_acc = brand_repo.get_meta_account(db, brand_id)

        fb_metrics = None
        ig_metrics = None
        is_live = False

        if meta_acc and meta_acc.is_connected:
            token = decrypt_token(meta_acc.access_token) or meta_acc.access_token
            fb_raw = meta_service.fetch_facebook_page_metrics(
                page_id=meta_acc.facebook_page_id,
                access_token=token
            )
            ig_raw = meta_service.fetch_instagram_account_metrics(
                ig_user_id=meta_acc.instagram_account_id,
                access_token=token
            )

            fb_metrics = FacebookPageMetrics(**fb_raw)
            ig_metrics = InstagramAccountMetrics(**ig_raw)
            is_live = not (fb_raw.get("is_sandbox") and ig_raw.get("is_sandbox"))

        overview = MetricOverview(**summary)
        daily_trends = []

        return DashboardAnalyticsResponse(
            overview=overview,
            daily_trends=daily_trends,
            facebook_page=fb_metrics,
            instagram_account=ig_metrics,
            is_live_meta=is_live,
        )

    def sync_post_analytics(self, db: Session, post_id: int) -> Optional[Any]:
        """
        Synchronize performance metrics for a published Post across all its destinations
        (Instagram, Facebook, YouTube).
        - Multi-platform metrics are aggregated (summed reach is non-deduplicated).
        - Distinguishes 0 from None.
        - YouTube views are NOT mapped into impressions.
        - Calculates engagement rate: (likes + comments + shares + saves) / impressions * 100
          (fallback to reach if impressions is None; returns None if neither is available).
        """
        import logging
        from app.models.post import Post
        from app.models.publishing_batch import PublishingBatch, PublishingJob
        from app.models.youtube_upload import YouTubeUpload, YouTubeUploadStatus
        from app.services.youtube_service import youtube_service

        logger = logging.getLogger(__name__)

        post = db.query(Post).filter(Post.id == post_id).first()
        if not post or post.status != "PUBLISHED":
            return None

        # Discover published destinations scoped to this post's user and brand
        targets = []  # List of tuples: (platform, external_id, SocialAccount)

        # 1. From multi-account PublishingJobs
        batches = db.query(PublishingBatch).filter(PublishingBatch.post_id == post.id).all()
        for batch in batches:
            for job in batch.jobs:
                if job.status == "SUCCESS" and job.external_post_id and job.social_account:
                    # Enforce tenant scoping: account must belong to post owner
                    if job.social_account.user_id == post.user_id:
                        targets.append((job.platform.lower(), str(job.external_post_id), job.social_account))

        # 2. From direct Post identifiers
        if post.ig_media_id and not any(t[0] == "instagram" and t[1] == post.ig_media_id for t in targets):
            user_ig_accounts = social_account_repo.get_by_user_and_platform(db, post.user_id, "instagram")
            matched_ig = next((a for a in user_ig_accounts if a.brand_id == post.brand_id), None) or (user_ig_accounts[0] if user_ig_accounts else None)
            if matched_ig:
                targets.append(("instagram", str(post.ig_media_id), matched_ig))

        if post.fb_post_id and not any(t[0] == "facebook" and t[1] == post.fb_post_id for t in targets):
            user_fb_accounts = social_account_repo.get_by_user_and_platform(db, post.user_id, "facebook")
            matched_fb = next((a for a in user_fb_accounts if a.brand_id == post.brand_id), None) or (user_fb_accounts[0] if user_fb_accounts else None)
            if matched_fb:
                targets.append(("facebook", str(post.fb_post_id), matched_fb))

        # 3. From associated YouTube Uploads
        if post.platforms and "youtube" in post.platforms:
            yt_upload = db.query(YouTubeUpload).filter(
                YouTubeUpload.user_id == post.user_id,
                YouTubeUpload.upload_status == YouTubeUploadStatus.READY.value,
                YouTubeUpload.video_id.isnot(None)
            ).filter(
                (YouTubeUpload.title == post.title) | (YouTubeUpload.description.contains(post.caption[:30] if post.caption else ""))
            ).first()
            if yt_upload and yt_upload.social_account and not any(t[0] == "youtube" and t[1] == yt_upload.video_id for t in targets):
                targets.append(("youtube", str(yt_upload.video_id), yt_upload.social_account))

        if not targets:
            logger.info(f"[POST_ANALYTICS_SYNC] No external publication targets found for post_id={post_id}")
            return None

        platform_results = []
        for platform, ext_id, acc in targets:
            try:
                if platform == "instagram":
                    token = decrypt_token(acc.access_token) or acc.access_token
                    res = meta_service.fetch_instagram_post_metrics(ext_id, token)
                    platform_results.append(res)
                elif platform == "facebook":
                    token = decrypt_token(acc.access_token) or acc.access_token
                    res = meta_service.fetch_facebook_post_metrics(ext_id, token)
                    platform_results.append(res)
                elif platform == "youtube":
                    token = youtube_service.get_valid_access_token_for_account(db, acc)
                    res = youtube_service.fetch_video_statistics(token, ext_id)
                    platform_results.append(res)
            except Exception as e:
                logger.error(f"[POST_ANALYTICS_TARGET_ERROR] Failed fetching metrics for post_id={post_id} platform={platform} ext_id={ext_id}: {e}")

        if not platform_results:
            return None

        # Multi-Platform Aggregation:
        # If all platforms return None for a metric, aggregate is None.
        # If at least one platform provides a valid value, sum the valid values.
        aggregated = {}
        for key in ["likes", "comments", "shares", "saves", "reach", "impressions"]:
            valid_vals = [res[key] for res in platform_results if res.get(key) is not None]
            aggregated[key] = sum(valid_vals) if valid_vals else None

        # Engagement Rate calculation
        eng_vals = [aggregated[k] for k in ["likes", "comments", "shares", "saves"] if aggregated[k] is not None]
        total_engagements = sum(eng_vals) if eng_vals else 0

        denominator = None
        if aggregated["impressions"] is not None and aggregated["impressions"] > 0:
            denominator = aggregated["impressions"]
        elif aggregated["reach"] is not None and aggregated["reach"] > 0:
            denominator = aggregated["reach"]

        engagement_rate = None
        if denominator is not None and denominator > 0 and eng_vals:
            engagement_rate = round((total_engagements / denominator) * 100, 2)

        return analytics_repo.upsert_post_analytics(
            db=db,
            post_id=post.id,
            likes=aggregated["likes"],
            comments=aggregated["comments"],
            shares=aggregated["shares"],
            saves=aggregated["saves"],
            reach=aggregated["reach"],
            impressions=aggregated["impressions"],
            engagement_rate=engagement_rate
        )

    def sync_all_published_posts_analytics(self, db: Session, limit: int = 50) -> Dict[str, Any]:
        """
        Iterate through recent published posts up to `limit` and synchronize their metrics.
        Isolated per post so individual errors do not halt batch processing.
        """
        import logging
        from app.models.post import Post

        logger = logging.getLogger(__name__)

        posts = db.query(Post).filter(
            Post.status == "PUBLISHED"
        ).order_by(
            Post.published_at.desc().nullslast(),
            Post.id.desc()
        ).limit(limit).all()

        total = len(posts)
        success_count = 0
        failure_count = 0

        logger.info(f"[POST_ANALYTICS_BATCH] Starting post analytics sync for {total} published posts (limit={limit}).")

        for p in posts:
            try:
                result = self.sync_post_analytics(db, p.id)
                if result:
                    success_count += 1
                else:
                    failure_count += 1
            except Exception as e:
                db.rollback()
                failure_count += 1
                logger.error(f"[POST_ANALYTICS_BATCH_ERROR] Error syncing post_id={p.id}: {e}")

        logger.info(f"[POST_ANALYTICS_BATCH_COMPLETE] Finished. Total={total}, Success={success_count}, Failed={failure_count}")


        return {
            "total_posts": total,
            "success": success_count,
            "failed": failure_count
        }

analytics_service = AnalyticsService()


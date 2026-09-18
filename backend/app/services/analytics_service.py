from concurrent.futures import ThreadPoolExecutor
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from sqlalchemy.orm import Session
from app.repositories.analytics_repository import analytics_repo
from app.repositories.account_metric_snapshot_repository import account_metric_snapshot_repo
from app.repositories.brand_repository import brand_repo
from app.repositories.social_account_repository import social_account_repo
from app.schemas.analytics import (
    DashboardAnalyticsResponse,
    MetricOverview,
    DailyMetricPoint,
    FacebookPageMetrics,
    InstagramAccountMetrics,
    AccountSnapshotPoint,
    GrowthMetrics,
    AccountAnalyticsResponse,
    OverviewReportResponse,
    PlatformBreakdownItem,
    PlatformBreakdownResponse,
    PostPerformanceItem,
    PostPerformanceListResponse,
)
from app.services.meta_service import meta_service
from app.models.meta_account import MetaAccount
from app.models.social_account import SocialAccount
from app.models.account_metric_snapshot import AccountMetricSnapshot

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
                elif acc.platform == "youtube":
                    latest_snap = db.query(AccountMetricSnapshot).filter(
                        AccountMetricSnapshot.social_account_id == acc.id
                    ).order_by(AccountMetricSnapshot.snapshot_date.desc()).first()
                    followers = latest_snap.followers_count if latest_snap else 0
                    return {
                        "entry": {
                            "id": acc.id,
                            "account_id": acc.account_id,
                            "account_name": acc.account_name,
                            "platform": "youtube",
                            "logo_url": acc.logo_url,
                            "followers_count": followers if followers is not None else 0,
                            "media_count": latest_snap.media_count if latest_snap else None,
                            "media_count_source": "persisted_snapshot",
                            "category": "YouTube Channel",
                            "status": acc.status,
                            "link": f"https://youtube.com/channel/{acc.account_id}"
                        },
                        "followers": followers or 0,
                        "is_live": False
                    }
                else:
                    return {
                        "entry": {
                            "id": acc.id,
                            "account_id": acc.account_id,
                            "account_name": acc.account_name,
                            "platform": acc.platform,
                            "logo_url": acc.logo_url,
                            "followers_count": 0,
                            "media_count": None,
                            "media_count_source": "unavailable",
                            "category": "Social Account",
                            "status": acc.status,
                            "link": ""
                        },
                        "followers": 0,
                        "is_live": False
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
                if res and "entry" in res:
                    accounts_list.append(res["entry"])
                    total_followers_combined += res.get("followers", 0)
                    if res.get("is_live"):
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

    # ==============================================================================
    # Phase 2B.5-A3: Read-Only Aggregation & Analytics Endpoints Service Methods
    # ==============================================================================

    def _validate_scope(self, db: Session, user_id: int, brand_id: Optional[int] = None, social_account_id: Optional[int] = None):
        """Helper to enforce strict tenant/brand/account boundary checks."""
        from app.models.brand import BrandProfile
        if brand_id is not None:
            brand = db.query(BrandProfile).filter(
                BrandProfile.id == brand_id,
                BrandProfile.user_id == user_id
            ).first()
            if not brand:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Brand profile not found or access denied"
                )

        if social_account_id is not None:
            account = db.query(SocialAccount).filter(
                SocialAccount.id == social_account_id,
                SocialAccount.user_id == user_id
            ).first()
            if not account:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Social account not found or access denied"
                )
            if brand_id is not None and account.brand_id != brand_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Social account does not belong to the specified brand"
                )

    def get_account_historical_analytics(
        self,
        db: Session,
        user_id: int,
        brand_id: Optional[int] = None,
        social_account_id: Optional[int] = None,
        platform: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> AccountAnalyticsResponse:
        """
        Retrieve chronological account metric snapshots and calculate growth rates
        with strict tenant/brand isolation. 100% read-only.
        """
        self._validate_scope(db, user_id, brand_id, social_account_id)

        if social_account_id is not None:
            snapshots = account_metric_snapshot_repo.get_snapshots_for_account(
                db=db,
                social_account_id=social_account_id,
                start_date=start_date,
                end_date=end_date
            )
        elif brand_id is not None:
            snapshots = account_metric_snapshot_repo.get_snapshots_by_brand(
                db=db,
                brand_id=brand_id,
                user_id=user_id,
                platform=platform,
                start_date=start_date,
                end_date=end_date
            )
        else:
            snapshots = account_metric_snapshot_repo.get_snapshots_by_user(
                db=db,
                user_id=user_id,
                platform=platform,
                start_date=start_date,
                end_date=end_date
            )

        # Convert to response points
        points = []
        for s in snapshots:
            points.append(AccountSnapshotPoint(
                id=s.id,
                social_account_id=s.social_account_id,
                platform=s.social_account.platform if s.social_account else "unknown",
                account_name=s.social_account.account_name if s.social_account else None,
                snapshot_date=s.snapshot_date,
                followers_count=s.followers_count,
                following_count=s.following_count,
                media_count=s.media_count,
                views_count=s.views_count,
                reach=s.reach,
                impressions=s.impressions,
                engagement_rate=s.engagement_rate,
                metadata_json=s.metadata_json or {}
            ))

        # Calculate Growth Metrics
        if not snapshots:
            growth = GrowthMetrics()
        elif social_account_id is not None or len({s.social_account_id for s in snapshots}) == 1:
            first_snap = snapshots[0]
            last_snap = snapshots[-1]

            initial_followers = first_snap.followers_count
            current_followers = last_snap.followers_count
            follower_change = (
                current_followers - initial_followers
                if (initial_followers is not None and current_followers is not None)
                else None
            )

            follower_growth_rate = None
            if initial_followers is not None and current_followers is not None:
                if initial_followers > 0:
                    follower_growth_rate = round(((current_followers - initial_followers) / initial_followers) * 100, 2)
                elif initial_followers == 0 and current_followers == 0:
                    follower_growth_rate = 0.0

            initial_media = first_snap.media_count
            current_media = last_snap.media_count
            media_change = (
                current_media - initial_media
                if (initial_media is not None and current_media is not None)
                else None
            )

            initial_views = first_snap.views_count
            current_views = last_snap.views_count
            views_change = (
                current_views - initial_views
                if (initial_views is not None and current_views is not None)
                else None
            )

            growth = GrowthMetrics(
                initial_followers=initial_followers,
                current_followers=current_followers,
                follower_change=follower_change,
                follower_growth_rate=follower_growth_rate,
                initial_media_count=initial_media,
                current_media_count=current_media,
                media_count_change=media_change,
                initial_views=initial_views,
                current_views=current_views,
                views_change=views_change,
            )
        else:
            # Multi-account aggregation by earliest/latest calendar date
            distinct_dates = sorted(list({s.snapshot_date for s in snapshots}))
            earliest_date = distinct_dates[0]
            latest_date = distinct_dates[-1]

            first_snaps = [s for s in snapshots if s.snapshot_date == earliest_date]
            last_snaps = [s for s in snapshots if s.snapshot_date == latest_date]

            first_fol = [s.followers_count for s in first_snaps if s.followers_count is not None]
            last_fol = [s.followers_count for s in last_snaps if s.followers_count is not None]
            initial_followers = sum(first_fol) if first_fol else None
            current_followers = sum(last_fol) if last_fol else None

            follower_change = (
                current_followers - initial_followers
                if (initial_followers is not None and current_followers is not None)
                else None
            )

            follower_growth_rate = None
            if initial_followers is not None and current_followers is not None:
                if initial_followers > 0:
                    follower_growth_rate = round(((current_followers - initial_followers) / initial_followers) * 100, 2)
                elif initial_followers == 0 and current_followers == 0:
                    follower_growth_rate = 0.0

            first_med = [s.media_count for s in first_snaps if s.media_count is not None]
            last_med = [s.media_count for s in last_snaps if s.media_count is not None]
            initial_media = sum(first_med) if first_med else None
            current_media = sum(last_med) if last_med else None
            media_change = (
                current_media - initial_media
                if (initial_media is not None and current_media is not None)
                else None
            )

            first_vw = [s.views_count for s in first_snaps if s.views_count is not None]
            last_vw = [s.views_count for s in last_snaps if s.views_count is not None]
            initial_views = sum(first_vw) if first_vw else None
            current_views = sum(last_vw) if last_vw else None
            views_change = (
                current_views - initial_views
                if (initial_views is not None and current_views is not None)
                else None
            )

            growth = GrowthMetrics(
                initial_followers=initial_followers,
                current_followers=current_followers,
                follower_change=follower_change,
                follower_growth_rate=follower_growth_rate,
                initial_media_count=initial_media,
                current_media_count=current_media,
                media_count_change=media_change,
                initial_views=initial_views,
                current_views=current_views,
                views_change=views_change,
            )

        return AccountAnalyticsResponse(
            snapshots=points,
            growth=growth,
            total_records=len(points)
        )

    def get_overview_report(
        self,
        db: Session,
        user_id: int,
        brand_id: Optional[int] = None,
        social_account_id: Optional[int] = None,
        platform: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> OverviewReportResponse:
        """
        Aggregate overview report combining account-level total followers
        (arithmetic sum across available platform accounts; not deduplicated)
        and post-level engagement and volume metrics. 100% read-only.
        """
        self._validate_scope(db, user_id, brand_id, social_account_id)

        # 1. Post-level aggregations
        post_metrics = analytics_repo.get_aggregated_post_metrics(
            db=db,
            user_id=user_id,
            brand_id=brand_id,
            platform=platform,
            social_account_id=social_account_id,
            start_date=start_date,
            end_date=end_date
        )

        # 2. Account-level follower arithmetic sum
        acc_query = db.query(SocialAccount).filter(
            SocialAccount.user_id == user_id,
            SocialAccount.status == "CONNECTED"
        )
        if brand_id is not None:
            acc_query = acc_query.filter(SocialAccount.brand_id == brand_id)
        if social_account_id is not None:
            acc_query = acc_query.filter(SocialAccount.id == social_account_id)
        if platform is not None:
            acc_query = acc_query.filter(SocialAccount.platform == platform.lower())

        accounts = acc_query.all()

        account_followers = []
        for acc in accounts:
            snap_q = db.query(AccountMetricSnapshot).filter(AccountMetricSnapshot.social_account_id == acc.id)
            if end_date is not None:
                snap_q = snap_q.filter(AccountMetricSnapshot.snapshot_date <= end_date)
            latest_snap = snap_q.order_by(AccountMetricSnapshot.snapshot_date.desc()).first()

            if latest_snap and latest_snap.followers_count is not None:
                account_followers.append(latest_snap.followers_count)

        total_followers = sum(account_followers) if account_followers else None

        return OverviewReportResponse(
            total_followers=total_followers,
            total_posts=post_metrics["total_posts"],
            published_posts=post_metrics["published_posts"],
            scheduled_posts=post_metrics["scheduled_posts"],
            failed_posts=post_metrics["failed_posts"],
            total_likes=post_metrics["total_likes"],
            total_comments=post_metrics["total_comments"],
            total_shares=post_metrics["total_shares"],
            total_saves=post_metrics["total_saves"],
            total_reach=post_metrics["total_reach"],
            total_impressions=post_metrics["total_impressions"],
            aggregate_engagement_rate=post_metrics["aggregate_engagement_rate"],
            start_date=start_date,
            end_date=end_date
        )

    def get_platform_breakdown(
        self,
        db: Session,
        user_id: int,
        brand_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> PlatformBreakdownResponse:
        """
        Break down metrics by platform (Instagram, Facebook, YouTube) within user/brand scope. 100% read-only.
        """
        self._validate_scope(db, user_id, brand_id=brand_id)

        platforms = ["instagram", "facebook", "youtube"]
        items = []

        for plat in platforms:
            acc_query = db.query(SocialAccount).filter(
                SocialAccount.user_id == user_id,
                SocialAccount.platform == plat,
                SocialAccount.status == "CONNECTED"
            )
            if brand_id is not None:
                acc_query = acc_query.filter(SocialAccount.brand_id == brand_id)
            accounts = acc_query.all()
            connected_count = len(accounts)

            # Followers and views from latest snapshots
            fol_vals = []
            views_vals = []
            for acc in accounts:
                snap_q = db.query(AccountMetricSnapshot).filter(AccountMetricSnapshot.social_account_id == acc.id)
                if end_date is not None:
                    snap_q = snap_q.filter(AccountMetricSnapshot.snapshot_date <= end_date)
                latest_snap = snap_q.order_by(AccountMetricSnapshot.snapshot_date.desc()).first()

                if latest_snap:
                    if latest_snap.followers_count is not None:
                        fol_vals.append(latest_snap.followers_count)
                    if latest_snap.views_count is not None:
                        views_vals.append(latest_snap.views_count)

            total_followers = sum(fol_vals) if fol_vals else None
            total_views = sum(views_vals) if views_vals else None

            # Post metrics for this platform
            metrics = analytics_repo.get_aggregated_post_metrics(
                db=db,
                user_id=user_id,
                brand_id=brand_id,
                platform=plat,
                start_date=start_date,
                end_date=end_date
            )

            items.append(PlatformBreakdownItem(
                platform=plat,
                connected_accounts_count=connected_count,
                total_followers=total_followers,
                total_posts=metrics["total_posts"],
                total_likes=metrics["total_likes"],
                total_comments=metrics["total_comments"],
                total_shares=metrics["total_shares"],
                total_saves=metrics["total_saves"],
                total_reach=metrics["total_reach"],
                total_impressions=metrics["total_impressions"],
                total_views=total_views,
                aggregate_engagement_rate=metrics["aggregate_engagement_rate"]
            ))

        return PlatformBreakdownResponse(platforms=items)

    def get_posts_performance_list(
        self,
        db: Session,
        user_id: int,
        brand_id: Optional[int] = None,
        social_account_id: Optional[int] = None,
        platform: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        order_by: str = "published_at",
        order_dir: str = "desc",
        limit: int = 50,
        offset: int = 0
    ) -> PostPerformanceListResponse:
        """
        Retrieve paginated list of posts with performance metrics, deterministic NULL-safe sorting,
        and tenant/brand scoping. 100% read-only.
        """
        self._validate_scope(db, user_id, brand_id, social_account_id)

        posts, total = analytics_repo.get_posts_performance(
            db=db,
            user_id=user_id,
            brand_id=brand_id,
            platform=platform,
            social_account_id=social_account_id,
            start_date=start_date,
            end_date=end_date,
            order_by=order_by,
            order_dir=order_dir,
            limit=limit,
            offset=offset
        )

        items = []
        for p in posts:
            items.append(PostPerformanceItem(
                post_id=p.id,
                title=p.title,
                caption=p.caption,
                status=p.status,
                platforms=p.platforms or [],
                media_type=p.media_type,
                thumbnail_url=p.thumbnail_url,
                image_url=p.image_url,
                published_at=p.published_at,
                created_at=p.created_at,
                likes=p.analytics.likes if p.analytics else None,
                comments=p.analytics.comments if p.analytics else None,
                shares=p.analytics.shares if p.analytics else None,
                saves=p.analytics.saves if p.analytics else None,
                reach=p.analytics.reach if p.analytics else None,
                impressions=p.analytics.impressions if p.analytics else None,
                engagement_rate=p.analytics.engagement_rate if p.analytics else None,
                analytics_updated_at=p.analytics.updated_at if p.analytics else None,
            ))

        return PostPerformanceListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset
        )

analytics_service = AnalyticsService()


import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.social_account import SocialAccount
from app.models.brand import BrandProfile
from app.repositories.social_account_repository import social_account_repo
from app.repositories.account_metric_snapshot_repository import account_metric_snapshot_repo
from app.schemas.analytics import (
    LiveAccountMetrics,
    LiveAnalyticsMetrics,
    LiveAccountCapabilities,
    LiveAccountAnalyticsItem,
    LiveAnalyticsSummary,
    LiveAnalyticsResponse,
)
from app.services.meta_service import meta_service
from app.services.youtube_service import youtube_service
from app.services.account_snapshot_service import account_snapshot_service
from app.core.security_encryption import decrypt_token

logger = logging.getLogger(__name__)



class LiveAnalyticsService:
    """
    Hybrid Live Analytics Service:
    - Fetches REAL, current platform analytics from Meta Graph API & YouTube Data API.
    - Normalizes data into a platform-independent contract with explicit metric capabilities.
    - Preserves exact NULL vs 0 semantics (never converts missing metrics into 0).
    - Idempotently captures/updates today's historical snapshot row in AccountMetricSnapshot.
    - Strictly prevents credentials/tokens from leaking into logs or API responses.
    """

    def get_live_account_analytics(
        self,
        db: Session,
        account: SocialAccount
    ) -> LiveAccountAnalyticsItem:
        """
        Fetch current live metrics for a single connected social account,
        persist today's historical snapshot, and return a normalized item.
        """
        platform = (account.platform or "").lower()
        now_iso = datetime.now(timezone.utc).isoformat()

        account_metrics = LiveAccountMetrics()
        analytics_metrics = LiveAnalyticsMetrics()
        capabilities = LiveAccountCapabilities()
        error_msg: Optional[str] = None
        status_str = account.status or "CONNECTED"

        try:
            if platform == "instagram":
                token = decrypt_token(account.access_token) or account.access_token
                raw_ig = meta_service.fetch_instagram_account_metrics(
                    ig_user_id=account.account_id,
                    access_token=token
                )
                
                followers = raw_ig.get("followers_count")
                follows = raw_ig.get("follows_count")
                media = raw_ig.get("media_count")

                account_metrics = LiveAccountMetrics(
                    followers=followers,
                    following=follows,
                    media_count=media,
                    views_count=None
                )
                capabilities = LiveAccountCapabilities(
                    followers=followers is not None,
                    following=follows is not None,
                    media_count=media is not None,
                    views_count=False,
                    reach=False,
                    impressions=False,
                    engagement_rate=False
                )

            elif platform == "facebook":
                token = decrypt_token(account.access_token) or account.access_token
                raw_fb = meta_service.fetch_facebook_page_metrics(
                    page_id=account.account_id,
                    access_token=token
                )
                
                followers = raw_fb.get("followers_count")
                if followers is None and raw_fb.get("fan_count") is not None:
                    followers = raw_fb.get("fan_count")
                media = raw_fb.get("media_count")

                account_metrics = LiveAccountMetrics(
                    followers=followers,
                    following=None,
                    media_count=media,
                    views_count=None
                )
                capabilities = LiveAccountCapabilities(
                    followers=followers is not None,
                    following=False,
                    media_count=media is not None,
                    views_count=False,
                    reach=False,
                    impressions=False,
                    engagement_rate=False
                )

            elif platform == "youtube":
                access_token = youtube_service.get_valid_access_token_for_account(db, account)
                channel_data = youtube_service.fetch_authenticated_channel(access_token)

                sub_count = channel_data.get("subscriber_count")
                vid_count = channel_data.get("video_count")
                vw_count = channel_data.get("view_count")

                followers = int(sub_count) if sub_count is not None else None
                media = int(vid_count) if vid_count is not None else None
                views = int(vw_count) if vw_count is not None else None

                account_metrics = LiveAccountMetrics(
                    followers=followers,
                    following=None,
                    media_count=media,
                    views_count=views
                )
                capabilities = LiveAccountCapabilities(
                    followers=followers is not None,
                    following=False,
                    media_count=media is not None,
                    views_count=views is not None,
                    reach=False,
                    impressions=False,
                    engagement_rate=False
                )
            else:
                logger.warning(
                    f"[LIVE_ANALYTICS_UNSUPPORTED_PLATFORM] social_account_id={account.id} platform={platform}"
                )
                error_msg = f"Unsupported platform '{platform}'"
                status_str = "UNSUPPORTED"

            # Historical snapshot sync for today directly with the freshly fetched live metrics
            try:
                today_date = datetime.now(timezone.utc).date()
                account_metric_snapshot_repo.upsert_snapshot(
                    db=db,
                    social_account_id=account.id,
                    snapshot_date=today_date,
                    followers_count=account_metrics.followers,
                    following_count=account_metrics.following,
                    media_count=account_metrics.media_count,
                    views_count=account_metrics.views_count,
                    reach=analytics_metrics.reach,
                    impressions=analytics_metrics.impressions,
                    engagement_rate=analytics_metrics.engagement_rate
                )
            except Exception as snap_err:
                logger.warning(
                    f"[LIVE_ANALYTICS_SNAPSHOT_PERSIST_WARNING] social_account_id={account.id} platform={platform} error={snap_err}"
                )

            logger.info(
                f"[LIVE_ANALYTICS_FETCH_SUCCESS] social_account_id={account.id} platform={platform} "
                f"followers={account_metrics.followers} media={account_metrics.media_count}"
            )


        except Exception as e:
            error_msg = str(e)
            status_str = "ERROR"
            logger.error(
                f"[LIVE_ANALYTICS_FETCH_ERROR] social_account_id={account.id} platform={platform} error={str(e)}"
            )

        return LiveAccountAnalyticsItem(
            social_account_id=account.id,
            platform=platform,
            account_name=account.account_name,
            account_id=account.account_id,
            logo_url=account.logo_url,
            status=status_str,
            account=account_metrics,
            analytics=analytics_metrics,
            capabilities=capabilities,
            source="live_platform_api",
            fetched_at=now_iso,
            error_message=error_msg
        )

    def get_live_analytics(
        self,
        db: Session,
        user_id: int,
        brand_id: Optional[int] = None,
        social_account_id: Optional[int] = None,
        platform: Optional[str] = None
    ) -> LiveAnalyticsResponse:
        """
        Fetch real-time analytics for all matching connected accounts owned by the user,
        aggregate summary metrics, and return a comprehensive normalized response.
        """
        # Validate scope & permissions
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

        # Build account query
        query = db.query(SocialAccount).filter(
            SocialAccount.user_id == user_id,
            SocialAccount.status == "CONNECTED"
        )
        if brand_id is not None:
            query = query.filter(SocialAccount.brand_id == brand_id)
        if social_account_id is not None:
            query = query.filter(SocialAccount.id == social_account_id)
        if platform is not None:
            query = query.filter(SocialAccount.platform == platform.lower())

        accounts = query.all()

        # Fetch live items with failure isolation per account
        items: List[LiveAccountAnalyticsItem] = []
        for acc in accounts:
            item = self.get_live_account_analytics(db=db, account=acc)
            items.append(item)

        # Compute cross-platform summary totals (arithmetic sums)
        follower_vals = [i.account.followers for i in items if i.account.followers is not None]
        reach_vals = [i.analytics.reach for i in items if i.analytics.reach is not None]
        impression_vals = [i.analytics.impressions for i in items if i.analytics.impressions is not None]

        total_followers = sum(follower_vals) if follower_vals else None
        total_reach = sum(reach_vals) if reach_vals else None
        total_impressions = sum(impression_vals) if impression_vals else None

        summary = LiveAnalyticsSummary(
            total_followers=total_followers,
            total_reach=total_reach,
            total_impressions=total_impressions,
            aggregate_engagement_rate=None
        )

        return LiveAnalyticsResponse(
            accounts=items,
            summary=summary,
            fetched_at=datetime.now(timezone.utc).isoformat()
        )


live_analytics_service = LiveAnalyticsService()

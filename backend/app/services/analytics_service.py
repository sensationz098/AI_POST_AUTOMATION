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
from app.models.post import Post

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

        user_published_posts = db.query(Post).filter(
            Post.user_id == user_id,
            Post.status == "PUBLISHED"
        ).count()

        accounts_list = []
        total_followers_combined = 0
        total_reach_combined = summary.get("total_reach", 0)
        total_impressions_combined = summary.get("total_impressions", 0)
        has_live_meta = False

        for acc in real_accounts:
            token = decrypt_token(acc.access_token) or acc.access_token
            if acc.platform == "facebook":
                fb_raw = meta_service.fetch_facebook_page_metrics(page_id=acc.account_id, access_token=token)
                followers = fb_raw.get("followers_count", 0) or fb_raw.get("fan_count", 0)
                total_followers_combined += followers
                accounts_list.append({
                    "id": acc.id,
                    "account_id": acc.account_id,
                    "account_name": acc.account_name,
                    "platform": "facebook",
                    "logo_url": acc.logo_url,
                    "followers_count": followers,
                    "fan_count": fb_raw.get("fan_count", 0),
                    "posts_count": fb_raw.get("media_count", user_published_posts),
                    "media_count": fb_raw.get("media_count", user_published_posts),
                    "category": fb_raw.get("category", "Facebook Page"),
                    "status": acc.status,
                    "link": f"https://facebook.com/{acc.account_id}"
                })
                if not fb_raw.get("is_sandbox"):
                    has_live_meta = True

            elif acc.platform == "instagram":
                ig_raw = meta_service.fetch_instagram_account_metrics(ig_user_id=acc.account_id, access_token=token)
                followers = ig_raw.get("followers_count", 0)
                total_followers_combined += followers
                accounts_list.append({
                    "id": acc.id,
                    "account_id": acc.account_id,
                    "account_name": acc.account_name,
                    "platform": "instagram",
                    "logo_url": acc.logo_url,
                    "followers_count": followers,
                    "posts_count": ig_raw.get("media_count", user_published_posts),
                    "media_count": ig_raw.get("media_count", user_published_posts),
                    "status": acc.status,
                    "link": f"https://instagram.com/{acc.account_name.lstrip('@')}"
                })
                if not ig_raw.get("is_sandbox"):
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

analytics_service = AnalyticsService()

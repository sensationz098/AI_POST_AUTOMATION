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

analytics_service = AnalyticsService()

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.repositories.base import BaseRepository
from app.models.analytics import PostAnalytics
from app.models.post import Post

class AnalyticsRepository(BaseRepository[PostAnalytics]):
    def __init__(self):
        super().__init__(PostAnalytics)

    def get_by_post(self, db: Session, post_id: int) -> Optional[PostAnalytics]:
        return db.query(PostAnalytics).filter(PostAnalytics.post_id == post_id).first()

    def get_brand_summary(self, db: Session, brand_id: int) -> dict:
        posts = db.query(Post).filter(Post.brand_id == brand_id).all()
        total_posts = len(posts)
        published_posts = len([p for p in posts if p.status == "PUBLISHED"])
        scheduled_posts = len([p for p in posts if p.status == "SCHEDULED"])
        failed_posts = len([p for p in posts if p.status == "FAILED"])

        analytics_list = (
            db.query(PostAnalytics)
            .join(Post, PostAnalytics.post_id == Post.id)
            .filter(Post.brand_id == brand_id)
            .all()
        )

        total_likes = sum(a.likes for a in analytics_list)
        total_comments = sum(a.comments for a in analytics_list)
        total_shares = sum(a.shares for a in analytics_list)
        total_reach = sum(a.reach for a in analytics_list)
        total_impressions = sum(a.impressions for a in analytics_list)

        avg_engagement = (
            sum(a.engagement_rate for a in analytics_list) / len(analytics_list)
            if analytics_list
            else 0.0
        )

        return {
            "total_posts": total_posts,
            "published_posts": published_posts,
            "scheduled_posts": scheduled_posts,
            "failed_posts": failed_posts,
            "total_likes": total_likes,
            "total_comments": total_comments,
            "total_shares": total_shares,
            "total_reach": total_reach,
            "total_impressions": total_impressions,
            "avg_engagement_rate": round(avg_engagement, 2),
        }

    def get_user_summary(self, db: Session, user_id: int) -> dict:
        posts = db.query(Post).all()
        total_posts = len(posts)
        published_posts = len([p for p in posts if p.status == "PUBLISHED"])
        scheduled_posts = len([p for p in posts if p.status == "SCHEDULED"])
        failed_posts = len([p for p in posts if p.status == "FAILED"])

        analytics_list = db.query(PostAnalytics).all()

        total_likes = sum(a.likes for a in analytics_list)
        total_comments = sum(a.comments for a in analytics_list)
        total_shares = sum(a.shares for a in analytics_list)
        total_reach = sum(a.reach for a in analytics_list)
        total_impressions = sum(a.impressions for a in analytics_list)

        avg_engagement = (
            sum(a.engagement_rate for a in analytics_list) / len(analytics_list)
            if analytics_list
            else 0.0
        )

        return {
            "total_posts": total_posts,
            "published_posts": published_posts,
            "scheduled_posts": scheduled_posts,
            "failed_posts": failed_posts,
            "total_likes": total_likes,
            "total_comments": total_comments,
            "total_shares": total_shares,
            "total_reach": total_reach,
            "total_impressions": total_impressions,
            "avg_engagement_rate": round(avg_engagement, 2),
        }

analytics_repo = AnalyticsRepository()

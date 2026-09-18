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

    def upsert_post_analytics(
        self,
        db: Session,
        post_id: int,
        likes: Optional[int] = None,
        comments: Optional[int] = None,
        shares: Optional[int] = None,
        saves: Optional[int] = None,
        reach: Optional[int] = None,
        impressions: Optional[int] = None,
        engagement_rate: Optional[float] = None,
        follower_growth: Optional[int] = None
    ) -> PostAnalytics:
        """
        Idempotently create or update a PostAnalytics record for a given post_id.
        Distinguishes explicit 0 from None (unavailable/unsupported metrics).
        """
        from datetime import datetime, timezone
        existing = self.get_by_post(db, post_id)
        now = datetime.now(timezone.utc)

        if existing:
            existing.likes = likes
            existing.comments = comments
            existing.shares = shares
            existing.saves = saves
            existing.reach = reach
            existing.impressions = impressions
            existing.engagement_rate = engagement_rate
            if follower_growth is not None:
                existing.follower_growth = follower_growth
            existing.updated_at = now
            db.commit()
            db.refresh(existing)
            return existing

        new_analytics = PostAnalytics(
            post_id=post_id,
            likes=likes,
            comments=comments,
            shares=shares,
            saves=saves,
            reach=reach,
            impressions=impressions,
            engagement_rate=engagement_rate,
            follower_growth=follower_growth or 0,
            updated_at=now
        )
        db.add(new_analytics)
        db.commit()
        db.refresh(new_analytics)
        return new_analytics


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

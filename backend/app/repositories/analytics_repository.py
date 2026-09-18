from typing import Optional, List, Tuple
from datetime import date, datetime, time
from sqlalchemy.orm import Session
from sqlalchemy import func, String
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

        total_likes = sum(a.likes or 0 for a in analytics_list)
        total_comments = sum(a.comments or 0 for a in analytics_list)
        total_shares = sum(a.shares or 0 for a in analytics_list)
        total_reach = sum(a.reach or 0 for a in analytics_list)
        total_impressions = sum(a.impressions or 0 for a in analytics_list)

        avg_engagement = (
            sum(a.engagement_rate or 0.0 for a in analytics_list) / len(analytics_list)
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
        posts = db.query(Post).filter(Post.user_id == user_id).all()
        total_posts = len(posts)
        published_posts = len([p for p in posts if p.status == "PUBLISHED"])
        scheduled_posts = len([p for p in posts if p.status == "SCHEDULED"])
        failed_posts = len([p for p in posts if p.status == "FAILED"])

        analytics_list = (
            db.query(PostAnalytics)
            .join(Post, PostAnalytics.post_id == Post.id)
            .filter(Post.user_id == user_id)
            .all()
        )

        total_likes = sum(a.likes or 0 for a in analytics_list)
        total_comments = sum(a.comments or 0 for a in analytics_list)
        total_shares = sum(a.shares or 0 for a in analytics_list)
        total_reach = sum(a.reach or 0 for a in analytics_list)
        total_impressions = sum(a.impressions or 0 for a in analytics_list)

        avg_engagement = (
            sum(a.engagement_rate or 0.0 for a in analytics_list) / len(analytics_list)
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

    # ==============================================================================
    # Phase 2B.5-A3: Aggregation & Performance Queries
    # ==============================================================================

    def get_posts_performance(
        self,
        db: Session,
        user_id: int,
        brand_id: Optional[int] = None,
        platform: Optional[str] = None,
        social_account_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        order_by: str = "published_at",
        order_dir: str = "desc",
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Post], int]:
        """
        Query paginated post performance records with deterministic NULL-safe sorting
        and strict tenant/brand isolation.
        """
        query = db.query(Post).outerjoin(PostAnalytics, Post.id == PostAnalytics.post_id).filter(
            Post.user_id == user_id
        )

        if brand_id is not None:
            query = query.filter(Post.brand_id == brand_id)

        if platform is not None:
            query = query.filter(Post.platforms.cast(String).contains(platform.lower()))

        if social_account_id is not None:
            from app.models.publishing_batch import PublishingBatch, PublishingJob
            job_post_ids = db.query(PublishingBatch.post_id).join(
                PublishingJob, PublishingJob.batch_id == PublishingBatch.id
            ).filter(
                PublishingJob.social_account_id == social_account_id
            ).subquery()
            query = query.filter(Post.id.in_(job_post_ids))

        if start_date is not None:
            start_dt = datetime.combine(start_date, time.min)
            query = query.filter(
                (Post.published_at >= start_dt) | ((Post.published_at.is_(None)) & (Post.created_at >= start_dt))
            )

        if end_date is not None:
            end_dt = datetime.combine(end_date, time.max)
            query = query.filter(
                (Post.published_at <= end_dt) | ((Post.published_at.is_(None)) & (Post.created_at <= end_dt))
            )

        total = query.with_entities(func.count(func.distinct(Post.id))).scalar() or 0

        # Deterministic sorting mapping
        sort_map = {
            "published_at": Post.published_at,
            "created_at": Post.created_at,
            "likes": PostAnalytics.likes,
            "comments": PostAnalytics.comments,
            "shares": PostAnalytics.shares,
            "saves": PostAnalytics.saves,
            "reach": PostAnalytics.reach,
            "impressions": PostAnalytics.impressions,
            "engagement_rate": PostAnalytics.engagement_rate,
        }

        col = sort_map.get(order_by.lower(), Post.published_at)

        if order_dir.lower() == "asc":
            order_clause = col.asc().nullslast()
            secondary = Post.published_at.asc().nullslast()
            tertiary = Post.id.asc()
        else:
            order_clause = col.desc().nullslast()
            secondary = Post.published_at.desc().nullslast()
            tertiary = Post.id.desc()

        items = query.order_by(order_clause, secondary, tertiary).limit(limit).offset(offset).all()
        return items, total

    def get_aggregated_post_metrics(
        self,
        db: Session,
        user_id: int,
        brand_id: Optional[int] = None,
        platform: Optional[str] = None,
        social_account_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> dict:
        """
        Calculates aggregate metrics and aggregate engagement rate with strict NULL semantics
        and deduplicated logical post counts.
        """
        base_posts_query = db.query(Post).filter(Post.user_id == user_id)

        if brand_id is not None:
            base_posts_query = base_posts_query.filter(Post.brand_id == brand_id)

        if platform is not None:
            base_posts_query = base_posts_query.filter(Post.platforms.cast(String).contains(platform.lower()))

        if social_account_id is not None:
            from app.models.publishing_batch import PublishingBatch, PublishingJob
            job_post_ids = db.query(PublishingBatch.post_id).join(
                PublishingJob, PublishingJob.batch_id == PublishingBatch.id
            ).filter(
                PublishingJob.social_account_id == social_account_id
            ).subquery()
            base_posts_query = base_posts_query.filter(Post.id.in_(job_post_ids))

        if start_date is not None:
            start_dt = datetime.combine(start_date, time.min)
            base_posts_query = base_posts_query.filter(
                (Post.published_at >= start_dt) | ((Post.published_at.is_(None)) & (Post.created_at >= start_dt))
            )

        if end_date is not None:
            end_dt = datetime.combine(end_date, time.max)
            base_posts_query = base_posts_query.filter(
                (Post.published_at <= end_dt) | ((Post.published_at.is_(None)) & (Post.created_at <= end_dt))
            )

        posts = base_posts_query.all()
        total_posts = len(posts)
        published_posts = len([p for p in posts if p.status == "PUBLISHED"])
        scheduled_posts = len([p for p in posts if p.status == "SCHEDULED"])
        failed_posts = len([p for p in posts if p.status == "FAILED"])

        published_post_ids = [p.id for p in posts if p.status == "PUBLISHED"]

        analytics_list = []
        if published_post_ids:
            analytics_list = db.query(PostAnalytics).filter(PostAnalytics.post_id.in_(published_post_ids)).all()

        # Strict NULL vs 0 preservation:
        # If all records have NULL for a metric, aggregate is NULL (None).
        # If at least one record has a non-NULL value, aggregate is sum of non-NULL values.
        def _aggregate_metric(field_name: str) -> Optional[int]:
            valid_vals = [getattr(a, field_name) for a in analytics_list if getattr(a, field_name) is not None]
            return sum(valid_vals) if valid_vals else None

        total_likes = _aggregate_metric("likes")
        total_comments = _aggregate_metric("comments")
        total_shares = _aggregate_metric("shares")
        total_saves = _aggregate_metric("saves")
        total_reach = _aggregate_metric("reach")
        total_impressions = _aggregate_metric("impressions")

        # Aggregate engagement rate
        eng_components = [total_likes, total_comments, total_shares, total_saves]
        non_none_eng = [v for v in eng_components if v is not None]
        numerator = sum(non_none_eng) if non_none_eng else None

        denominator = None
        if total_impressions is not None and total_impressions > 0:
            denominator = total_impressions
        elif total_reach is not None and total_reach > 0:
            denominator = total_reach

        aggregate_engagement_rate = None
        if numerator is not None and denominator is not None and denominator > 0:
            aggregate_engagement_rate = round((numerator / denominator) * 100, 2)

        return {
            "total_posts": total_posts,
            "published_posts": published_posts,
            "scheduled_posts": scheduled_posts,
            "failed_posts": failed_posts,
            "total_likes": total_likes,
            "total_comments": total_comments,
            "total_shares": total_shares,
            "total_saves": total_saves,
            "total_reach": total_reach,
            "total_impressions": total_impressions,
            "aggregate_engagement_rate": aggregate_engagement_rate,
        }

analytics_repo = AnalyticsRepository()

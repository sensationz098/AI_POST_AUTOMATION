from typing import List, Optional, Dict, Any
from datetime import date, datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.account_metric_snapshot import AccountMetricSnapshot
from app.models.social_account import SocialAccount

class AccountMetricSnapshotRepository:
    def get_by_id(self, db: Session, snapshot_id: int) -> Optional[AccountMetricSnapshot]:
        return db.query(AccountMetricSnapshot).filter(AccountMetricSnapshot.id == snapshot_id).first()

    def get_by_account_and_date(
        self,
        db: Session,
        social_account_id: int,
        snapshot_date: date
    ) -> Optional[AccountMetricSnapshot]:
        """Retrieve snapshot for a specific social account and calendar date."""
        return db.query(AccountMetricSnapshot).filter(
            AccountMetricSnapshot.social_account_id == social_account_id,
            AccountMetricSnapshot.snapshot_date == snapshot_date
        ).first()

    def upsert_snapshot(
        self,
        db: Session,
        social_account_id: int,
        snapshot_date: date,
        followers_count: Optional[int] = None,
        following_count: Optional[int] = None,
        media_count: Optional[int] = None,
        views_count: Optional[int] = None,
        reach: Optional[int] = None,
        impressions: Optional[int] = None,
        engagement_rate: Optional[float] = None,
        metadata_json: Optional[Dict[str, Any]] = None
    ) -> AccountMetricSnapshot:
        """
        Idempotently create or update a daily snapshot for a social account.
        If a record already exists for the given (social_account_id, snapshot_date),
        it updates the metrics in-place.
        """
        existing = self.get_by_account_and_date(db, social_account_id, snapshot_date)
        now = datetime.now(timezone.utc)

        if existing:
            if followers_count is not None:
                existing.followers_count = followers_count
            if following_count is not None:
                existing.following_count = following_count
            if media_count is not None:
                existing.media_count = media_count
            if views_count is not None:
                existing.views_count = views_count
            if reach is not None:
                existing.reach = reach
            if impressions is not None:
                existing.impressions = impressions
            if engagement_rate is not None:
                existing.engagement_rate = engagement_rate
            if metadata_json is not None:
                merged_meta = dict(existing.metadata_json or {})
                merged_meta.update(metadata_json)
                existing.metadata_json = merged_meta
            existing.updated_at = now
            db.commit()
            db.refresh(existing)
            return existing

        new_snapshot = AccountMetricSnapshot(
            social_account_id=social_account_id,
            snapshot_date=snapshot_date,
            followers_count=followers_count,
            following_count=following_count,
            media_count=media_count,
            views_count=views_count,
            reach=reach,
            impressions=impressions,
            engagement_rate=engagement_rate,
            metadata_json=metadata_json or {},
            created_at=now,
            updated_at=now
        )
        db.add(new_snapshot)
        db.commit()
        db.refresh(new_snapshot)
        return new_snapshot

    def get_snapshots_for_account(
        self,
        db: Session,
        social_account_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[AccountMetricSnapshot]:
        """Retrieve chronological snapshots for a single social account within an optional date range."""
        query = db.query(AccountMetricSnapshot).filter(
            AccountMetricSnapshot.social_account_id == social_account_id
        )
        if start_date:
            query = query.filter(AccountMetricSnapshot.snapshot_date >= start_date)
        if end_date:
            query = query.filter(AccountMetricSnapshot.snapshot_date <= end_date)
        return query.order_by(AccountMetricSnapshot.snapshot_date.asc()).all()

    def get_snapshots_by_user(
        self,
        db: Session,
        user_id: int,
        platform: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[AccountMetricSnapshot]:
        """
        Retrieve snapshots for all social accounts owned by a specific user (tenant isolation).
        Optionally filter by platform and date range.
        """
        query = db.query(AccountMetricSnapshot).join(
            SocialAccount,
            AccountMetricSnapshot.social_account_id == SocialAccount.id
        ).filter(SocialAccount.user_id == user_id)

        if platform:
            query = query.filter(SocialAccount.platform == platform)
        if start_date:
            query = query.filter(AccountMetricSnapshot.snapshot_date >= start_date)
        if end_date:
            query = query.filter(AccountMetricSnapshot.snapshot_date <= end_date)

        return query.order_by(
            AccountMetricSnapshot.snapshot_date.asc(),
            AccountMetricSnapshot.social_account_id.asc()
        ).all()

    def get_snapshots_by_brand(
        self,
        db: Session,
        brand_id: int,
        user_id: int,
        platform: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[AccountMetricSnapshot]:
        """
        Retrieve snapshots for all social accounts scoped to a specific brand and user.
        """
        query = db.query(AccountMetricSnapshot).join(
            SocialAccount,
            AccountMetricSnapshot.social_account_id == SocialAccount.id
        ).filter(
            SocialAccount.brand_id == brand_id,
            SocialAccount.user_id == user_id
        )

        if platform:
            query = query.filter(SocialAccount.platform == platform)
        if start_date:
            query = query.filter(AccountMetricSnapshot.snapshot_date >= start_date)
        if end_date:
            query = query.filter(AccountMetricSnapshot.snapshot_date <= end_date)

        return query.order_by(
            AccountMetricSnapshot.snapshot_date.asc(),
            AccountMetricSnapshot.social_account_id.asc()
        ).all()

account_metric_snapshot_repo = AccountMetricSnapshotRepository()

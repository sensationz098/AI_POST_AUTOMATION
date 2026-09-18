import logging
from typing import Dict, Any, Optional, List
from datetime import date, datetime, timezone
from sqlalchemy.orm import Session

from app.models.social_account import SocialAccount
from app.models.account_metric_snapshot import AccountMetricSnapshot
from app.repositories.account_metric_snapshot_repository import account_metric_snapshot_repo
from app.core.security_encryption import decrypt_token
from app.services.meta_service import meta_service
from app.services.youtube_service import youtube_service

logger = logging.getLogger(__name__)

class AccountSnapshotService:
    def capture_snapshot_for_account(
        self,
        db: Session,
        account: SocialAccount,
        snapshot_date: Optional[date] = None
    ) -> Optional[AccountMetricSnapshot]:
        """
        Capture and persist a single historical metrics snapshot for a social account.
        Reuses existing platform integrations without altering tokens or scopes.
        Errors during collection are safely handled and logged without sensitive tokens.
        """
        if snapshot_date is None:
            snapshot_date = datetime.now(timezone.utc).date()

        platform = (account.platform or "").lower()
        followers_count = None
        following_count = None
        media_count = None
        views_count = None
        reach = None
        impressions = None
        engagement_rate = None
        metadata_json: Dict[str, Any] = {}

        try:
            if platform == "facebook":
                token = decrypt_token(account.access_token) or account.access_token
                raw_fb = meta_service.fetch_facebook_page_metrics(
                    page_id=account.account_id,
                    access_token=token
                )
                followers_count = raw_fb.get("followers_count")
                if followers_count is None and raw_fb.get("fan_count") is not None:
                    followers_count = raw_fb.get("fan_count")
                media_count = raw_fb.get("media_count")
                metadata_json = {
                    "fan_count": raw_fb.get("fan_count"),
                    "category": raw_fb.get("category"),
                    "media_count_source": raw_fb.get("media_count_source", "meta_total_unavailable"),
                    "is_sandbox": raw_fb.get("is_sandbox", False)
                }

            elif platform == "instagram":
                token = decrypt_token(account.access_token) or account.access_token
                raw_ig = meta_service.fetch_instagram_account_metrics(
                    ig_user_id=account.account_id,
                    access_token=token
                )
                followers_count = raw_ig.get("followers_count")
                following_count = raw_ig.get("follows_count")
                media_count = raw_ig.get("media_count")
                metadata_json = {
                    "media_count_source": raw_ig.get("media_count_source", "meta_verified_exact_total"),
                    "is_sandbox": raw_ig.get("is_sandbox", False)
                }

            elif platform == "youtube":
                # Automatically handles token refresh if nearing expiration
                access_token = youtube_service.get_valid_access_token_for_account(db, account)
                channel_data = youtube_service.fetch_authenticated_channel(access_token)
                
                sub_count = channel_data.get("subscriber_count")
                vid_count = channel_data.get("video_count")
                vw_count = channel_data.get("view_count")

                followers_count = int(sub_count) if sub_count is not None else None
                media_count = int(vid_count) if vid_count is not None else None
                views_count = int(vw_count) if vw_count is not None else None

                metadata_json = {
                    "channel_title": channel_data.get("title"),
                    "custom_url": channel_data.get("custom_url"),
                    "uploads_playlist_id": channel_data.get("uploads_playlist_id")
                }
            else:
                logger.warning(
                    f"[ACCOUNT_SNAPSHOT] Unsupported platform '{platform}' for social_account_id={account.id}."
                )
                return None

            snapshot = account_metric_snapshot_repo.upsert_snapshot(
                db=db,
                social_account_id=account.id,
                snapshot_date=snapshot_date,
                followers_count=followers_count,
                following_count=following_count,
                media_count=media_count,
                views_count=views_count,
                reach=reach,
                impressions=impressions,
                engagement_rate=engagement_rate,
                metadata_json=metadata_json
            )

            logger.info(
                f"[ACCOUNT_SNAPSHOT_SUCCESS] Captured snapshot for account_id={account.id} "
                f"platform={platform} date={snapshot_date} followers={followers_count} media={media_count}"
            )
            return snapshot

        except Exception as e:
            # Strictly safe logging: account_id, platform, snapshot_date (no tokens)
            logger.error(
                f"[ACCOUNT_SNAPSHOT_ERROR] Failed to capture snapshot for account_id={account.id} "
                f"platform={platform} date={snapshot_date}. Error: {str(e)}"
            )
            return None

    def capture_all_active_snapshots(
        self,
        db: Session,
        snapshot_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Iterate through all active connected SocialAccounts and capture their daily snapshot.
        Ensures individual account failure does NOT abort execution for remaining accounts.
        """
        if snapshot_date is None:
            snapshot_date = datetime.now(timezone.utc).date()

        active_accounts = db.query(SocialAccount).filter(
            SocialAccount.status == "CONNECTED"
        ).all()

        total = len(active_accounts)
        success_count = 0
        failure_count = 0

        logger.info(
            f"[ACCOUNT_SNAPSHOT_BATCH] Starting snapshot collection for {total} connected accounts on date={snapshot_date}."
        )

        for acc in active_accounts:
            try:
                result = self.capture_snapshot_for_account(
                    db=db,
                    account=acc,
                    snapshot_date=snapshot_date
                )
                if result:
                    success_count += 1
                else:
                    failure_count += 1
            except Exception as e:
                failure_count += 1
                logger.error(
                    f"[ACCOUNT_SNAPSHOT_BATCH_ERROR] Unexpected error processing social_account_id={acc.id}: {str(e)}"
                )

        logger.info(
            f"[ACCOUNT_SNAPSHOT_BATCH_COMPLETE] Finished date={snapshot_date}. Total={total}, Success={success_count}, Failed={failure_count}"
        )

        return {
            "snapshot_date": str(snapshot_date),
            "total_accounts": total,
            "success": success_count,
            "failed": failure_count
        }

    def get_account_snapshots(
        self,
        db: Session,
        social_account_id: int,
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[AccountMetricSnapshot]:
        """
        Retrieve historical metric snapshots for a specific social account.
        Enforces tenant isolation by validating that the account belongs to user_id.
        """
        account = db.query(SocialAccount).filter(
            SocialAccount.id == social_account_id,
            SocialAccount.user_id == user_id
        ).first()

        if not account:
            return []

        return account_metric_snapshot_repo.get_snapshots_for_account(
            db=db,
            social_account_id=social_account_id,
            start_date=start_date,
            end_date=end_date
        )

account_snapshot_service = AccountSnapshotService()

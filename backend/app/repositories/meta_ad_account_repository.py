from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from app.models.meta_ad_account import MetaAdAccount

class MetaAdAccountRepository:
    def get_by_user(self, db: Session, user_id: int) -> List[MetaAdAccount]:
        """Retrieve all Meta Ad Accounts belonging to the authenticated user."""
        return db.query(MetaAdAccount).filter(
            MetaAdAccount.user_id == user_id
        ).order_by(MetaAdAccount.created_at.desc()).all()

    def get_by_user_and_ad_account_id(
        self,
        db: Session,
        user_id: int,
        meta_ad_account_id: str
    ) -> Optional[MetaAdAccount]:
        """Retrieve a specific Meta Ad Account by user_id and meta_ad_account_id string."""
        return db.query(MetaAdAccount).filter(
            MetaAdAccount.user_id == user_id,
            MetaAdAccount.meta_ad_account_id == str(meta_ad_account_id)
        ).first()

    def upsert(
        self,
        db: Session,
        user_id: int,
        ad_data: Dict[str, Any]
    ) -> MetaAdAccount:
        """
        Upsert a single Meta Ad Account record for a user.
        If existing (user_id, meta_ad_account_id) match: update name, status, currency, timezone, metadata.
        If new: create and persist new MetaAdAccount.
        """
        ad_account_id_str = str(ad_data.get("id", ""))
        name = ad_data.get("name")
        status = ad_data.get("account_status")
        currency = ad_data.get("currency")
        timezone_name = ad_data.get("timezone_name")

        existing = self.get_by_user_and_ad_account_id(db, user_id, ad_account_id_str)

        now = datetime.now(timezone.utc)
        if existing:
            existing.name = name or existing.name
            existing.account_status = status if status is not None else existing.account_status
            existing.currency = currency or existing.currency
            existing.timezone_name = timezone_name or existing.timezone_name
            existing.updated_at = now
            # Update extra metadata fields while preserving existing keys
            current_meta = dict(existing.metadata_json or {})
            current_meta.update({
                "last_synced_at": now.isoformat(),
                "raw_meta_status": status
            })
            existing.metadata_json = current_meta
            db.commit()
            db.refresh(existing)
            return existing
        else:
            meta_json = {
                "last_synced_at": now.isoformat(),
                "raw_meta_status": status
            }
            new_acc = MetaAdAccount(
                user_id=user_id,
                meta_ad_account_id=ad_account_id_str,
                name=name,
                account_status=status,
                currency=currency,
                timezone_name=timezone_name,
                metadata_json=meta_json,
                created_at=now,
                updated_at=now
            )
            db.add(new_acc)
            db.commit()
            db.refresh(new_acc)
            return new_acc

    def sync_ad_accounts_for_user(
        self,
        db: Session,
        user_id: int,
        ad_accounts_data: List[Dict[str, Any]]
    ) -> List[MetaAdAccount]:
        """
        Sync a list of Ad Accounts returned from Meta Graph API for the user.
        Upserts each record safely and returns the updated list.
        """
        synced_accounts = []
        for ad_data in ad_accounts_data:
            if not ad_data.get("id"):
                continue
            acc = self.upsert(db, user_id, ad_data)
            synced_accounts.append(acc)
        return synced_accounts

meta_ad_account_repo = MetaAdAccountRepository()

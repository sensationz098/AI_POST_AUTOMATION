from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.social_account import SocialAccount
from datetime import datetime, timezone

from app.core.security_encryption import encrypt_token

class SocialAccountRepository:
    def get_by_id(self, db: Session, account_id: int) -> Optional[SocialAccount]:
        return db.query(SocialAccount).filter(SocialAccount.id == account_id).first()

    def get_by_user(self, db: Session, user_id: int) -> List[SocialAccount]:
        return db.query(SocialAccount).filter(SocialAccount.user_id == user_id).all()

    def get_by_user_and_platform(self, db: Session, user_id: int, platform: str) -> List[SocialAccount]:
        return db.query(SocialAccount).filter(
            SocialAccount.user_id == user_id,
            SocialAccount.platform == platform
        ).all()

    def get_by_account_id(self, db: Session, user_id: int, platform: str, account_id: str) -> Optional[SocialAccount]:
        return db.query(SocialAccount).filter(
            SocialAccount.user_id == user_id,
            SocialAccount.platform == platform,
            SocialAccount.account_id == account_id
        ).first()

    def create_or_update(
        self,
        db: Session,
        user_id: int,
        platform: str,
        account_id: str,
        account_name: str,
        access_token: str,
        brand_id: Optional[int] = None,
        token_type: str = "page_access_token",
        expires_at: Optional[datetime] = None,
        logo_url: Optional[str] = None,
        metadata_json: Optional[dict] = None
    ) -> SocialAccount:
        encrypted_tok = encrypt_token(access_token)
        existing = self.get_by_account_id(db, user_id, platform, account_id)
        if existing:
            existing.account_name = account_name
            existing.access_token = encrypted_tok
            existing.brand_id = brand_id or existing.brand_id
            existing.token_type = token_type
            existing.expires_at = expires_at or existing.expires_at
            existing.status = "CONNECTED"
            existing.logo_url = logo_url or existing.logo_url
            if metadata_json:
                existing.metadata_json = metadata_json
            existing.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(existing)
            return existing

        new_acc = SocialAccount(
            user_id=user_id,
            brand_id=brand_id,
            platform=platform,
            account_id=account_id,
            account_name=account_name,
            access_token=encrypted_tok,
            token_type=token_type,
            expires_at=expires_at,
            status="CONNECTED",
            logo_url=logo_url,
            metadata_json=metadata_json or {}
        )
        db.add(new_acc)
        db.commit()
        db.refresh(new_acc)
        return new_acc

    def mark_status(self, db: Session, account_id: int, status: str) -> Optional[SocialAccount]:
        acc = self.get_by_id(db, account_id)
        if acc:
            acc.status = status
            acc.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(acc)
        return acc

    def delete(self, db: Session, account_id: object, user_id: int) -> bool:
        # Search by DB id primary key or by string account_id
        query = db.query(SocialAccount).filter(SocialAccount.user_id == user_id)
        
        acc = None
        # Check if account_id is a valid integer primary key within standard 32-bit int bounds
        if isinstance(account_id, int) and account_id <= 2147483647:
            acc = query.filter(SocialAccount.id == account_id).first()
            
        if not acc:
            acc = query.filter(SocialAccount.account_id == str(account_id)).first()

        if acc:
            brand_id = acc.brand_id
            platform = acc.platform
            # 1. Clean up referencing PublishingJobs to avoid IntegrityError (FK constraint)
            from app.models.publishing_batch import PublishingJob
            db.query(PublishingJob).filter(PublishingJob.social_account_id == acc.id).delete(synchronize_session=False)

            # 2. Delete social account record
            db.delete(acc)
            db.commit()

            # 3. Check if any remaining connected social accounts exist for this user/brand & update MetaAccount
            if brand_id:
                from app.models.meta_account import MetaAccount
                meta = db.query(MetaAccount).filter(MetaAccount.brand_id == brand_id).first()
                if meta:
                    if platform == "facebook":
                        meta.facebook_page_id = None
                        meta.facebook_page_name = None
                    elif platform == "instagram":
                        meta.instagram_account_id = None
                        meta.instagram_username = None

                    remaining = db.query(SocialAccount).filter(
                        SocialAccount.user_id == user_id,
                        SocialAccount.brand_id == brand_id
                    ).count()
                    if remaining == 0:
                        meta.is_connected = False
                        meta.access_token = None
                    db.commit()
            return True
        return False

    def delete_all_for_user(self, db: Session, user_id: int) -> int:
        accounts = db.query(SocialAccount).filter(SocialAccount.user_id == user_id).all()
        if not accounts:
            # Also clear any lingering MetaAccounts if social accounts are already empty
            from app.models.meta_account import MetaAccount
            from app.models.brand import BrandProfile
            user_brand_ids = [b.id for b in db.query(BrandProfile.id).filter(BrandProfile.user_id == user_id).all()]
            if user_brand_ids:
                db.query(MetaAccount).filter(MetaAccount.brand_id.in_(user_brand_ids)).update({
                    "is_connected": False,
                    "facebook_page_id": None,
                    "facebook_page_name": None,
                    "instagram_account_id": None,
                    "instagram_username": None,
                    "access_token": None
                }, synchronize_session=False)
                db.commit()
            return 0
        
        acc_ids = [a.id for a in accounts]

        # 1. Clean up referencing PublishingJobs
        from app.models.publishing_batch import PublishingJob
        db.query(PublishingJob).filter(PublishingJob.social_account_id.in_(acc_ids)).delete(synchronize_session=False)

        # 2. Delete all social accounts
        count = db.query(SocialAccount).filter(SocialAccount.user_id == user_id).delete(synchronize_session=False)
        db.commit()

        # 3. Reset MetaAccount records for user's brands
        from app.models.meta_account import MetaAccount
        from app.models.brand import BrandProfile
        user_brand_ids = [b.id for b in db.query(BrandProfile.id).filter(BrandProfile.user_id == user_id).all()]
        if user_brand_ids:
            db.query(MetaAccount).filter(MetaAccount.brand_id.in_(user_brand_ids)).update({
                "is_connected": False,
                "facebook_page_id": None,
                "facebook_page_name": None,
                "instagram_account_id": None,
                "instagram_username": None,
                "access_token": None
            }, synchronize_session=False)
            db.commit()

        return count

social_account_repo = SocialAccountRepository()


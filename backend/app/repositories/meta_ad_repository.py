from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from app.models.meta_ad import MetaAd
from app.models.meta_ad_account import MetaAdAccount

class MetaAdRepository:
    def get_by_user(self, db: Session, user_id: int) -> List[MetaAd]:
        """Retrieve all Meta Ads belonging to the authenticated user."""
        return db.query(MetaAd).filter(
            MetaAd.user_id == user_id
        ).order_by(MetaAd.created_at.desc()).all()

    def get_by_ad_account(
        self,
        db: Session,
        user_id: int,
        meta_ad_account_id: str
    ) -> List[MetaAd]:
        """
        Retrieve all Meta Ads for a specific Meta Ad Account belonging to the authenticated user.
        Normalizes account ID (supports both 'act_123456' and '123456').
        """
        raw_id = str(meta_ad_account_id)
        prefixed_id = raw_id if raw_id.startswith("act_") else f"act_{raw_id}"
        unprefixed_id = raw_id.replace("act_", "")

        return db.query(MetaAd).filter(
            MetaAd.user_id == user_id,
            MetaAd.meta_ad_account_id.in_([prefixed_id, unprefixed_id])
        ).order_by(MetaAd.created_at.desc()).all()

    def get_by_user_and_ad_id(
        self,
        db: Session,
        user_id: int,
        meta_ad_id: str
    ) -> Optional[MetaAd]:
        """Retrieve a specific Meta Ad by user_id and Meta ad_id."""
        return db.query(MetaAd).filter(
            MetaAd.user_id == user_id,
            MetaAd.meta_ad_id == str(meta_ad_id)
        ).first()

    def upsert(
        self,
        db: Session,
        user_id: int,
        meta_ad_account_id: str,
        ad_data: Dict[str, Any],
        mapped_info: Dict[str, Any]
    ) -> MetaAd:
        """
        Idempotently upsert a MetaAd record for a given user & ad account.
        Updates metadata, statuses, creative details, and engagement mapping fields.
        """
        meta_ad_id_str = str(ad_data.get("id", ""))
        name = ad_data.get("name")
        campaign = ad_data.get("campaign") or {}
        campaign_id = str(campaign.get("id") or ad_data.get("campaign_id") or "") or None
        campaign_name = campaign.get("name")

        adset = ad_data.get("adset") or {}
        adset_id = str(adset.get("id") or ad_data.get("adset_id") or "") or None
        adset_name = adset.get("name")

        effective_status = ad_data.get("effective_status")
        configured_status = ad_data.get("configured_status") or ad_data.get("status")

        # Creative & Engagement object mapping details from mapped_info
        creative_id = mapped_info.get("creative_id")
        fb_page_id = mapped_info.get("facebook_page_id")
        fb_post_id = mapped_info.get("facebook_post_id")
        ig_account_id = mapped_info.get("instagram_account_id")
        ig_media_id = mapped_info.get("instagram_media_id")
        obj_type = mapped_info.get("engagement_object_type", "UNKNOWN")
        obj_id = mapped_info.get("engagement_object_id")
        mapping_status = mapped_info.get("mapping_status", "NOT_AVAILABLE")

        # Find linked DB ad account if exists
        raw_acct_id = str(meta_ad_account_id)
        acct_prefixed = raw_acct_id if raw_acct_id.startswith("act_") else f"act_{raw_acct_id}"
        acct_db = db.query(MetaAdAccount).filter(
            MetaAdAccount.user_id == user_id,
            MetaAdAccount.meta_ad_account_id.in_([acct_prefixed, raw_acct_id])
        ).first()
        ad_account_db_id = acct_db.id if acct_db else None

        existing = self.get_by_user_and_ad_id(db, user_id, meta_ad_id_str)
        now = datetime.now(timezone.utc)

        metadata_payload = {
            "last_synced_at": now.isoformat(),
            "raw_ad": ad_data,
            "mapped_info": mapped_info
        }

        if existing:
            existing.meta_ad_account_id = acct_prefixed
            if ad_account_db_id:
                existing.ad_account_db_id = ad_account_db_id
            existing.name = name or existing.name
            existing.campaign_id = campaign_id or existing.campaign_id
            existing.campaign_name = campaign_name or existing.campaign_name
            existing.adset_id = adset_id or existing.adset_id
            existing.adset_name = adset_name or existing.adset_name
            existing.effective_status = effective_status or existing.effective_status
            existing.configured_status = configured_status or existing.configured_status
            existing.creative_id = creative_id or existing.creative_id
            existing.facebook_page_id = fb_page_id or existing.facebook_page_id
            existing.facebook_post_id = fb_post_id or existing.facebook_post_id
            existing.instagram_account_id = ig_account_id or existing.instagram_account_id
            existing.instagram_media_id = ig_media_id or existing.instagram_media_id
            existing.engagement_object_type = obj_type or existing.engagement_object_type
            existing.engagement_object_id = obj_id or existing.engagement_object_id
            existing.mapping_status = mapping_status or existing.mapping_status
            existing.updated_at = now

            curr_meta = dict(existing.metadata_json or {})
            curr_meta.update(metadata_payload)
            existing.metadata_json = curr_meta

            db.commit()
            db.refresh(existing)
            return existing
        else:
            new_ad = MetaAd(
                user_id=user_id,
                meta_ad_account_id=acct_prefixed,
                ad_account_db_id=ad_account_db_id,
                meta_ad_id=meta_ad_id_str,
                name=name,
                campaign_id=campaign_id,
                campaign_name=campaign_name,
                adset_id=adset_id,
                adset_name=adset_name,
                effective_status=effective_status,
                configured_status=configured_status,
                creative_id=creative_id,
                facebook_page_id=fb_page_id,
                facebook_post_id=fb_post_id,
                instagram_account_id=ig_account_id,
                instagram_media_id=ig_media_id,
                engagement_object_type=obj_type,
                engagement_object_id=obj_id,
                mapping_status=mapping_status,
                metadata_json=metadata_payload,
                created_at=now,
                updated_at=now
            )
            db.add(new_ad)
            db.commit()
            db.refresh(new_ad)
            return new_ad

    def sync_ads_for_user(
        self,
        db: Session,
        user_id: int,
        meta_ad_account_id: str,
        raw_ads: List[Dict[str, Any]],
        mappings_map: Dict[str, Dict[str, Any]]
    ) -> List[MetaAd]:
        """
        Synchronize list of raw Ads returned from Meta Graph API for a user in a single optimized database transaction.
        Preserves tenant isolation, unique constraint (user_id + meta_ad_id), and idempotent upsert semantics.
        """
        if not raw_ads:
            return []

        raw_acct_id = str(meta_ad_account_id)
        acct_prefixed = raw_acct_id if raw_acct_id.startswith("act_") else f"act_{raw_acct_id}"
        unprefixed_id = raw_acct_id.replace("act_", "")

        # 1. Fetch linked DB ad account once
        acct_db = db.query(MetaAdAccount).filter(
            MetaAdAccount.user_id == user_id,
            MetaAdAccount.meta_ad_account_id.in_([acct_prefixed, unprefixed_id])
        ).first()
        ad_account_db_id = acct_db.id if acct_db else None

        # 2. Bulk load existing MetaAd records for this user and account
        existing_ads = db.query(MetaAd).filter(
            MetaAd.user_id == user_id,
            MetaAd.meta_ad_account_id.in_([acct_prefixed, unprefixed_id])
        ).all()
        existing_map = {ad.meta_ad_id: ad for ad in existing_ads}

        now = datetime.now(timezone.utc)
        synced = []

        for ad_data in raw_ads:
            meta_ad_id_str = str(ad_data.get("id", ""))
            if not meta_ad_id_str:
                continue

            mapped_info = mappings_map.get(meta_ad_id_str, {})
            name = ad_data.get("name")

            campaign = ad_data.get("campaign") or {}
            campaign_id = str(campaign.get("id") or ad_data.get("campaign_id") or "") or None
            campaign_name = campaign.get("name")

            adset = ad_data.get("adset") or {}
            adset_id = str(adset.get("id") or ad_data.get("adset_id") or "") or None
            adset_name = adset.get("name")

            effective_status = ad_data.get("effective_status")
            configured_status = ad_data.get("configured_status") or ad_data.get("status")

            creative_id = mapped_info.get("creative_id")
            fb_page_id = mapped_info.get("facebook_page_id")
            fb_post_id = mapped_info.get("facebook_post_id")
            ig_account_id = mapped_info.get("instagram_account_id")
            ig_media_id = mapped_info.get("instagram_media_id")
            obj_type = mapped_info.get("engagement_object_type", "UNKNOWN")
            obj_id = mapped_info.get("engagement_object_id")
            mapping_status = mapped_info.get("mapping_status", "NOT_AVAILABLE")

            metadata_payload = {
                "last_synced_at": now.isoformat(),
                "raw_ad": ad_data,
                "mapped_info": mapped_info
            }

            existing = existing_map.get(meta_ad_id_str)
            if existing:
                existing.meta_ad_account_id = acct_prefixed
                if ad_account_db_id:
                    existing.ad_account_db_id = ad_account_db_id
                existing.name = name or existing.name
                existing.campaign_id = campaign_id or existing.campaign_id
                existing.campaign_name = campaign_name or existing.campaign_name
                existing.adset_id = adset_id or existing.adset_id
                existing.adset_name = adset_name or existing.adset_name
                existing.effective_status = effective_status or existing.effective_status
                existing.configured_status = configured_status or existing.configured_status
                existing.creative_id = creative_id or existing.creative_id
                existing.facebook_page_id = fb_page_id or existing.facebook_page_id
                existing.facebook_post_id = fb_post_id or existing.facebook_post_id
                existing.instagram_account_id = ig_account_id or existing.instagram_account_id
                existing.instagram_media_id = ig_media_id or existing.instagram_media_id
                existing.engagement_object_type = obj_type or existing.engagement_object_type
                existing.engagement_object_id = obj_id or existing.engagement_object_id
                existing.mapping_status = mapping_status or existing.mapping_status
                existing.updated_at = now

                curr_meta = dict(existing.metadata_json or {})
                curr_meta.update(metadata_payload)
                existing.metadata_json = curr_meta
                synced.append(existing)
            else:
                new_ad = MetaAd(
                    user_id=user_id,
                    meta_ad_account_id=acct_prefixed,
                    ad_account_db_id=ad_account_db_id,
                    meta_ad_id=meta_ad_id_str,
                    name=name,
                    campaign_id=campaign_id,
                    campaign_name=campaign_name,
                    adset_id=adset_id,
                    adset_name=adset_name,
                    effective_status=effective_status,
                    configured_status=configured_status,
                    creative_id=creative_id,
                    facebook_page_id=fb_page_id,
                    facebook_post_id=fb_post_id,
                    instagram_account_id=ig_account_id,
                    instagram_media_id=ig_media_id,
                    engagement_object_type=obj_type,
                    engagement_object_id=obj_id,
                    mapping_status=mapping_status,
                    metadata_json=metadata_payload,
                    created_at=now,
                    updated_at=now
                )
                db.add(new_ad)
                existing_map[meta_ad_id_str] = new_ad
                synced.append(new_ad)

        db.commit()
        for ad_obj in synced:
            db.refresh(ad_obj)
        return synced

meta_ad_repo = MetaAdRepository()

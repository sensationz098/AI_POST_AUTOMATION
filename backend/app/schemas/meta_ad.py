from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

class MetaAdResponse(BaseModel):
    id: int
    user_id: int
    meta_ad_account_id: str
    ad_account_db_id: Optional[int] = None
    meta_ad_id: str
    name: Optional[str] = None
    campaign_id: Optional[str] = None
    campaign_name: Optional[str] = None
    adset_id: Optional[str] = None
    adset_name: Optional[str] = None
    effective_status: Optional[str] = None
    configured_status: Optional[str] = None
    creative_id: Optional[str] = None

    facebook_page_id: Optional[str] = None
    facebook_post_id: Optional[str] = None
    instagram_account_id: Optional[str] = None
    instagram_media_id: Optional[str] = None
    engagement_object_type: Optional[str] = None
    engagement_object_id: Optional[str] = None
    mapping_status: str

    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class MetaAdSyncResponse(BaseModel):
    success: bool
    message: str
    synced_count: int
    mapped_count: int
    partially_mapped_count: int
    unmapped_count: int
    ads_fetched: Optional[int] = None
    ads_synced: Optional[int] = None
    unique_creatives: Optional[int] = None
    creatives_enriched: Optional[int] = None
    creative_fetch_failures: Optional[int] = None
    inline_creatives_resolved: Optional[int] = None
    creatives_requiring_fallback: Optional[int] = None
    creative_cache_hits: Optional[int] = None
    mapping_summary: Optional[Dict[str, int]] = None
    ads: List[MetaAdResponse]

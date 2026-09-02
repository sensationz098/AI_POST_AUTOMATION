import time
import secrets
import logging
from typing import Dict, Any, Optional, List
from urllib.parse import quote
from fastapi import APIRouter, Depends, status, Query, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

from app.core.database import get_db
from app.core.config import settings
from app.schemas.meta import MetaConnectRequest, MetaAccountResponse
from app.schemas.meta_ad_account import MetaAdAccountResponse, MetaAdAccountSyncResponse
from app.schemas.meta_ad import MetaAdResponse, MetaAdSyncResponse
from app.repositories.brand_repository import brand_repo
from app.repositories.social_account_repository import social_account_repo
from app.services.meta_service import meta_service
from app.api.v1.deps import get_current_user
from app.models.user import User
from app.models.brand import BrandProfile

from app.core.redis import set_oauth_state, pop_oauth_state

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/meta", tags=["Meta Graph Integration"])

@router.get("/oauth/start")
def start_meta_oauth(
    redirect: bool = Query(True),
    current_user: User = Depends(get_current_user)
):
    """
    Generate Meta OAuth Authorization URL for Facebook Pages & Instagram Business accounts.
    Includes cryptographically secure CSRF state token tied to current user session in Redis.
    """
    state_token = secrets.token_urlsafe(32)
    set_oauth_state(state_token, current_user.id, ttl_seconds=900)

    auth_url = meta_service.get_authorization_url(state_token)
    if redirect:
        return RedirectResponse(url=auth_url, status_code=307)
    return {
        "authorization_url": auth_url,
        "state": state_token,
        "app_id_configured": bool(settings.META_APP_ID and settings.META_APP_ID != "your-meta-app-id")
    }

@router.get("/oauth/callback")
def meta_oauth_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Server-side OAuth Callback endpoint registered in Meta Developer Dashboard.
    Exchanges code for long-lived access token, discovers authorized Facebook Pages
    & linked Instagram accounts, and saves credentials securely in DB.
    """
    frontend_base = settings.FRONTEND_URL.rstrip('/')

    # 1. Handle user cancellation or Meta authorization errors
    if error or error_description:
        err_msg = error_description or error or "Meta authorization cancelled by user"
        logger.warning(f"Meta OAuth Callback Error: {err_msg}")
        return RedirectResponse(url=f"{frontend_base}/meta-connect?error={quote(err_msg)}")

    # 2. Verify CSRF State from Redis
    user_id = pop_oauth_state(state) if state else None
    if not user_id:
        logger.error("Meta OAuth Callback failed: Invalid or expired state token.")
        return RedirectResponse(url=f"{frontend_base}/meta-connect?error={quote('Invalid or expired OAuth state token. Please try again.')}")

    if not code:
        return RedirectResponse(url=f"{frontend_base}/meta-connect?error={quote('Missing authorization code from Meta.')}")

    try:
        # 3. Server-side token exchange (Never exposes App Secret to browser)
        short_token = meta_service.exchange_code_for_user_token(code)
        long_token = meta_service.get_long_lived_user_token(short_token)

        # 3b. Verify granted permissions safely via Graph API /me/permissions
        token_perm_info = meta_service.inspect_token_permissions(long_token)
        perm_map = token_perm_info.get("permissions", {})
        granted_scopes = [scope for scope, st in perm_map.items() if st == "granted"]
        ads_read_info = meta_service.verify_ads_read_permission(perm_map)
        ads_read_granted = ads_read_info.get("granted", False)

        logger.info(
            f"[META_OAUTH] Meta OAuth completed successfully for user {user_id}. "
            f"Requested permissions include 'ads_read'. "
            f"Granted scopes ({len(granted_scopes)}): {granted_scopes}. "
            f"ads_read_granted={ads_read_granted}"
        )

        # 4. Discover authorized Facebook Pages & linked Instagram accounts via Graph API
        discovered = meta_service.fetch_user_pages_and_instagram_accounts(long_token)
        fb_pages = discovered.get("facebook_pages", [])
        ig_accounts = discovered.get("instagram_accounts", [])

        if not fb_pages and not ig_accounts:
            msg = "Meta authorized successfully, but 0 Facebook Pages or linked Instagram accounts were found. Make sure: 1) The Facebook account owns or manages a Facebook Page. 2) You checked 'Select All Pages' during Meta permission consent. 3) For Instagram posting, the Instagram account is converted to Professional mode and linked to your Page."
            return RedirectResponse(url=f"{frontend_base}/meta-connect?error={quote(msg)}")

        # 5. Save connected accounts in social_accounts table & auto-create matching Brand Profiles
        from app.repositories.brand_repository import brand_repo
        from app.core.security_encryption import encrypt_token
        encrypted_user_token = encrypt_token(long_token)
        saved_fb = 0
        saved_ig = 0

        for p in fb_pages:
            # Automatic Facebook Page Webhook Subscription for 'feed' field
            sub_res = meta_service.subscribe_page_to_webhook(p["account_id"], p["access_token"])
            sub_status = sub_res.get("subscription_status", "failed")
            sub_err = sub_res.get("reason")

            fb_meta = {
                "granted_scopes": granted_scopes or meta_service.REQUIRED_META_OAUTH_SCOPES,
                "ads_read_granted": ads_read_granted,
                "user_access_token": encrypted_user_token,
                "comment_automation_ready": False,
                "comment_automation": {
                    "facebook_webhook_subscription": {
                        "status": sub_status,
                        "last_attempt_at": datetime.now(timezone.utc).isoformat(),
                        "subscribed_fields": ["feed"] if sub_status == "subscribed" else [],
                        "last_error": sub_err
                    }
                }
            }
            social_account_repo.create_or_update(
                db=db,
                user_id=user_id,
                platform="facebook",
                account_id=p["account_id"],
                account_name=p["account_name"],
                access_token=p["access_token"],
                token_type="page_access_token",
                logo_url=p["logo_url"],
                metadata_json=fb_meta
            )
            brand_repo.ensure_brand_profile_exists(db, user_id, p["account_name"], p["logo_url"])
            saved_fb += 1

        for ig in ig_accounts:
            # Automatic Instagram Account Webhook Subscription for 'comments' field
            ig_sub_res = meta_service.subscribe_instagram_account_to_webhook(ig["account_id"], ig["access_token"])
            ig_sub_status = ig_sub_res.get("subscription_status", "failed")
            ig_sub_err = ig_sub_res.get("reason")

            ig_meta = dict(ig.get("metadata") or {})
            existing_ca = dict(ig_meta.get("comment_automation") or {})
            existing_ca.update({
                "instagram_webhook_subscription": {
                    "status": ig_sub_status,
                    "last_attempt_at": datetime.now(timezone.utc).isoformat(),
                    "subscribed_fields": ["comments"] if ig_sub_status == "subscribed" else [],
                    "last_error": ig_sub_err
                }
            })
            ig_meta.update({
                "granted_scopes": granted_scopes or meta_service.REQUIRED_META_OAUTH_SCOPES,
                "ads_read_granted": ads_read_granted,
                "user_access_token": encrypted_user_token,
                "comment_automation_ready": False,
                "comment_automation": existing_ca
            })
            social_account_repo.create_or_update(
                db=db,
                user_id=user_id,
                platform="instagram",
                account_id=ig["account_id"],
                account_name=ig["account_name"],
                access_token=ig["access_token"],
                token_type="page_access_token",
                logo_url=ig["logo_url"],
                metadata_json=ig_meta
            )
            brand_repo.ensure_brand_profile_exists(db, user_id, ig["account_name"], ig["logo_url"])
            saved_ig += 1

        logger.info(f"Successfully processed Meta OAuth for user {user_id}: {saved_fb} FB pages, {saved_ig} IG accounts.")
        return RedirectResponse(url=f"{frontend_base}/meta-connect?connected=true&pages={saved_fb}&ig={saved_ig}")

    except Exception as e:
        logger.error(f"Error during Meta OAuth callback processing: {e}")
        return RedirectResponse(url=f"{frontend_base}/meta-connect?error={quote(str(e))}")

@router.post("/connect", response_model=MetaAccountResponse)
def connect_meta_account(
    request: MetaConnectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Link Facebook Page & Instagram Business account to a Brand Profile."""
    brand_name = request.facebook_page_name or (f"@{request.instagram_username}" if request.instagram_username else "Meta Connected Brand")
    
    brand_logo_url = request.logo_url
    if not brand_logo_url and request.facebook_page_id:
        brand_logo_url = f"https://graph.facebook.com/v19.0/{request.facebook_page_id}/picture?type=large"
    if not brand_logo_url:
        brand_logo_url = "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=120&auto=format&fit=crop&q=80"

    target_brand = None
    if request.brand_id and not request.create_new_brand:
        target_brand = db.query(BrandProfile).filter(
            BrandProfile.id == request.brand_id,
            BrandProfile.user_id == current_user.id
        ).first()

    if not target_brand:
        user_brands = brand_repo.get_by_user(db, current_user.id)
        if user_brands:
            target_brand = user_brands[0]
        else:
            target_brand = BrandProfile(
                name=brand_name,
                logo_url=brand_logo_url,
                brand_colors=["#6366F1", "#06B6D4"],
                tone_of_voice="Professional & Engaging",
                target_audience="Facebook & Instagram Audience",
                cta_style="Direct & Value-driven",
                industry="Social Media Brand",
                user_id=current_user.id
            )
            db.add(target_brand)
            db.commit()
            db.refresh(target_brand)

    if target_brand:
        if request.facebook_page_name or request.instagram_username:
            target_brand.name = brand_name
        if brand_logo_url:
            target_brand.logo_url = brand_logo_url
        db.commit()
        db.refresh(target_brand)

    data = {
        "access_token": request.access_token,
        "facebook_page_id": request.facebook_page_id,
        "facebook_page_name": request.facebook_page_name,
        "instagram_account_id": request.instagram_account_id,
        "instagram_username": request.instagram_username,
        "logo_url": brand_logo_url,
        "is_connected": True,
        "last_synced_at": datetime.now(timezone.utc)
    }
    meta_acc = brand_repo.create_or_update_meta(db, target_brand.id, data)
    return meta_acc

@router.get("/account/{brand_id}", response_model=MetaAccountResponse)
def get_meta_account(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get linked Meta account status for a brand with strict ownership validation."""
    brand = brand_repo.get(db, brand_id)
    if not brand or brand.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand profile not found or access denied"
        )

    meta = brand_repo.get_meta_account(db, brand_id)
    if not meta:
        return MetaAccountResponse(
            id=0,
            brand_id=brand_id,
            facebook_page_id=None,
            facebook_page_name=None,
            instagram_account_id=None,
            instagram_username=None,
            is_connected=False,
            last_synced_at=None,
            created_at=datetime.now(timezone.utc)
        )
    return meta

@router.delete("/disconnect", status_code=status.HTTP_200_OK)
def disconnect_meta_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Disconnect all Meta social accounts and deactivate Meta integration for current user."""
    count = social_account_repo.delete_all_for_user(db, current_user.id)
    return {"message": "Meta accounts disconnected successfully.", "count": count}


@router.post("/ad-accounts/sync", response_model=MetaAdAccountSyncResponse)
def sync_meta_ad_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Discover and sync accessible Meta Ad Accounts for the current authenticated user.
    Verifies ads_read permission, retrieves ad accounts from Meta Graph API GET /me/adaccounts with full pagination,
    and upserts into database. Strictly user-isolated.
    """
    from app.repositories.meta_ad_account_repository import meta_ad_account_repo

    # 1. Retrieve user access token
    user_token = meta_service.get_user_access_token_for_user(db, current_user.id)
    if not user_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No connected Meta account found for this user. Please connect Meta first."
        )

    # 2. Verify ads_read permission is granted
    if not meta_service.has_ads_read_permission(db, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Meta Ads read permission is not granted. Please reconnect Meta and grant ads_read."
        )

    # 3. Fetch Ad Accounts from Meta Graph API with pagination
    try:
        raw_ad_accounts = meta_service.fetch_ad_accounts(user_token)
    except Exception as e:
        logger.error(f"[META_ADS_SYNC] Failed to fetch Ad Accounts from Meta API: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Meta API error during Ad Account discovery: {str(e)}"
        )

    # 4. Upsert/sync into database
    synced = meta_ad_account_repo.sync_ad_accounts_for_user(db, current_user.id, raw_ad_accounts)

    return MetaAdAccountSyncResponse(
        success=True,
        message=f"Successfully synced {len(synced)} Meta Ad Account(s).",
        synced_count=len(synced),
        accounts=synced
    )


@router.get("/ad-accounts", response_model=List[MetaAdAccountResponse])
def get_meta_ad_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve stored Meta Ad Accounts for the current authenticated user.
    Does NOT invoke Meta Graph API. Strictly user-isolated and non-sensitive.
    """
    from app.repositories.meta_ad_account_repository import meta_ad_account_repo
    accounts = meta_ad_account_repo.get_by_user(db, current_user.id)
    return accounts


@router.post("/ad-accounts/{ad_account_id}/ads/sync", response_model=MetaAdSyncResponse)
def sync_meta_ads_for_account(
    ad_account_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Discover Ads for a specific Meta Ad Account and extract creative engagement object mappings.
    Verifies user ownership of Ad Account, ads_read permission, retrieves Ads via Meta Graph API GET /{act_ad_account_id}/ads,
    parses Facebook Page Post ID & Instagram Media ID from Ad Creative data, and idempotently upserts.
    """
    from app.repositories.meta_ad_account_repository import meta_ad_account_repo
    from app.repositories.meta_ad_repository import meta_ad_repo

    sync_start_time = time.time()
    logger.info(f"[META_ADS_SYNC] Starting sync for account {ad_account_id}")

    # 1. Verify user ownership of this Ad Account
    ad_acct = meta_ad_account_repo.get_by_user_and_ad_account_id(db, current_user.id, ad_account_id)
    if not ad_acct:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meta Ad Account not found or access denied."
        )

    # 2. Verify user token & ads_read permission
    user_token = meta_service.get_user_access_token_for_user(db, current_user.id)
    if not user_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No connected Meta account found for this user. Please connect Meta first."
        )

    if not meta_service.has_ads_read_permission(db, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Meta Ads read permission is not granted. Please reconnect Meta and grant ads_read."
        )

    # 3. Fetch Ads from Meta Graph API
    start_ad_disc = time.time()
    try:
        raw_ads = meta_service.fetch_ads_for_ad_account(user_token, ad_account_id)
    except Exception as e:
        logger.error(f"[META_ADS_SYNC] Failed to fetch Ads for account {ad_account_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Meta API error during Ad discovery: {str(e)}"
        )
    disc_duration = time.time() - start_ad_disc
    logger.info(f"[META_ADS_SYNC] Ad discovery completed: fetched {len(raw_ads)} ads in {disc_duration:.2f}s")

    # 4. Process creative resolution (Inline -> DB Cache -> Fallback Fetch)
    existing_ads = meta_ad_repo.get_by_ad_account(db, current_user.id, ad_account_id)
    enrich_result = meta_service.process_creative_enrichment(
        user_access_token=user_token,
        raw_ads=raw_ads,
        existing_ads=existing_ads,
        max_workers=10
    )
    creative_cache = enrich_result["creative_cache"]
    metrics = enrich_result["metrics"]

    unique_creatives_count = len(creative_cache)
    creatives_enriched = sum(1 for c in creative_cache.values() if c is not None)
    creative_fetch_failures = sum(1 for c in creative_cache.values() if c is None)

    # 5. Extract engagement object mappings
    start_map = time.time()
    logger.info(f"[META_ADS_SYNC] Starting engagement mapping for {len(raw_ads)} ads")
    mappings_map = {}
    for ad_data in raw_ads:
        ad_id = str(ad_data.get("id", ""))
        creative_id = None
        creative_obj = ad_data.get("creative") or ad_data.get("adcreative")
        if isinstance(creative_obj, dict):
            creative_id = creative_obj.get("id")

        creative_data = creative_cache.get(str(creative_id)) if creative_id else None
        creative_fetch_failed = (creative_id is not None and creative_data is None)

        mapping = meta_service.extract_engagement_mapping(ad_data, creative_data=creative_data)
        if creative_fetch_failed and mapping.get("mapping_status") != "MAPPED":
            mapping["mapping_status"] = "ERROR"

        if ad_id:
            mappings_map[ad_id] = mapping
    logger.info(f"[META_ADS_SYNC] Engagement mapping completed in {time.time() - start_map:.2f}s")

    # 6. Upsert / sync into database in a single transaction
    start_db = time.time()
    logger.info(f"[META_ADS_SYNC] Starting database persistence for {len(raw_ads)} ads")
    synced_ads = meta_ad_repo.sync_ads_for_user(db, current_user.id, ad_account_id, raw_ads, mappings_map)
    db_duration = time.time() - start_db
    logger.info(f"[META_ADS_SYNC] Database persistence completed in {db_duration:.2f}s")

    mapped_cnt = sum(1 for a in synced_ads if a.mapping_status == "MAPPED")
    partially_cnt = sum(1 for a in synced_ads if a.mapping_status == "PARTIALLY_MAPPED")
    not_avail_cnt = sum(1 for a in synced_ads if a.mapping_status in ("NOT_AVAILABLE", "UNSUPPORTED"))
    error_cnt = sum(1 for a in synced_ads if a.mapping_status == "ERROR")
    unmapped_cnt = not_avail_cnt + error_cnt

    total_sync_duration = time.time() - sync_start_time

    logger.info(
        f"[META_ADS_SYNC] Sync completed successfully in {total_sync_duration:.2f}s: "
        f"fetched={len(raw_ads)}, synced={len(synced_ads)}, mapped={mapped_cnt}, "
        f"partially_mapped={partially_cnt}, not_available={not_avail_cnt}, errors={error_cnt}"
    )

    return MetaAdSyncResponse(
        success=True,
        message=f"Successfully synced {len(synced_ads)} Meta Ad(s) for account {ad_account_id}.",
        synced_count=len(synced_ads),
        mapped_count=mapped_cnt,
        partially_mapped_count=partially_cnt,
        unmapped_count=unmapped_cnt,
        ads_fetched=len(raw_ads),
        ads_synced=len(synced_ads),
        unique_creatives=unique_creatives_count,
        creatives_enriched=creatives_enriched,
        creative_fetch_failures=creative_fetch_failures,
        inline_creatives_resolved=metrics.get("inline_creatives_resolved"),
        creatives_requiring_fallback=metrics.get("creatives_requiring_fallback"),
        creative_cache_hits=metrics.get("creative_cache_hits"),
        mapping_summary={
            "mapped": mapped_cnt,
            "partially_mapped": partially_cnt,
            "not_available": not_avail_cnt,
            "error": error_cnt
        },
        ads=synced_ads
    )


@router.get("/ad-accounts/{ad_account_id}/ads", response_model=List[MetaAdResponse])
def get_meta_ads_for_account(
    ad_account_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve cached discovered Ads for a Meta Ad Account belonging to the current user.
    Enforces tenant ownership validation and does NOT invoke Meta API directly.
    """
    from app.repositories.meta_ad_account_repository import meta_ad_account_repo
    from app.repositories.meta_ad_repository import meta_ad_repo

    # 1. Verify user ownership of Ad Account
    ad_acct = meta_ad_account_repo.get_by_user_and_ad_account_id(db, current_user.id, ad_account_id)
    if not ad_acct:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meta Ad Account not found or access denied."
        )

    # 2. Retrieve Ads for this user and account
    ads = meta_ad_repo.get_by_ad_account(db, current_user.id, ad_account_id)
    return ads


@router.post("/ad-accounts/{ad_account_id}/comments/sync", response_model=Dict[str, Any])
def sync_meta_ad_comments(
    ad_account_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Synchronize user comments for Meta Ads in a specific Ad Account.
    Validates tenant ownership of the Meta Ad Account.
    Fetches comments from backing Facebook post IDs (effective_object_story_id) and persists them in DB.
    Returns clear sync metrics.
    """
    from app.repositories.meta_ad_account_repository import meta_ad_account_repo

    # 1. Verify user ownership of Ad Account
    ad_acct = meta_ad_account_repo.get_by_user_and_ad_account_id(db, current_user.id, ad_account_id)
    if not ad_acct:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meta Ad Account not found or access denied."
        )

    # 2. Execute Comment Sync via meta_service
    res = meta_service.sync_comments_for_meta_ads(
        db=db,
        user_id=current_user.id,
        meta_ad_account_id=ad_account_id
    )
    return res



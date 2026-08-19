import secrets
import logging
from typing import Dict, Any, Optional
from urllib.parse import quote
from fastapi import APIRouter, Depends, status, Query, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

from app.core.database import get_db
from app.core.config import settings
from app.schemas.meta import MetaConnectRequest, MetaAccountResponse
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

        # 4. Discover authorized Facebook Pages & linked Instagram accounts via Graph API
        discovered = meta_service.fetch_user_pages_and_instagram_accounts(long_token)
        fb_pages = discovered.get("facebook_pages", [])
        ig_accounts = discovered.get("instagram_accounts", [])

        if not fb_pages and not ig_accounts:
            msg = "Meta authorized successfully, but 0 Facebook Pages or linked Instagram accounts were found. Make sure: 1) The Facebook account owns or manages a Facebook Page. 2) You checked 'Select All Pages' during Meta permission consent. 3) For Instagram posting, the Instagram account is converted to Professional mode and linked to your Page."
            return RedirectResponse(url=f"{frontend_base}/meta-connect?error={quote(msg)}")

        # 5. Save connected accounts in social_accounts table & auto-create matching Brand Profiles
        from app.repositories.brand_repository import brand_repo
        saved_fb = 0
        saved_ig = 0

        for p in fb_pages:
            social_account_repo.create_or_update(
                db=db,
                user_id=user_id,
                platform="facebook",
                account_id=p["account_id"],
                account_name=p["account_name"],
                access_token=p["access_token"],
                token_type="page_access_token",
                logo_url=p["logo_url"]
            )
            brand_repo.ensure_brand_profile_exists(db, user_id, p["account_name"], p["logo_url"])
            saved_fb += 1

        for ig in ig_accounts:
            social_account_repo.create_or_update(
                db=db,
                user_id=user_id,
                platform="instagram",
                account_id=ig["account_id"],
                account_name=ig["account_name"],
                access_token=ig["access_token"],
                token_type="page_access_token",
                logo_url=ig["logo_url"],
                metadata_json=ig.get("metadata")
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

    # Sync connected accounts into social_accounts table as independent social accounts
    if request.facebook_page_id:
        social_account_repo.create_or_update(
            db=db,
            user_id=current_user.id,
            platform="facebook",
            account_id=request.facebook_page_id,
            account_name=request.facebook_page_name or "Facebook Page",
            access_token=request.access_token,
            brand_id=target_brand.id,
            logo_url=brand_logo_url
        )

    if request.instagram_account_id or request.instagram_username:
        ig_name = request.instagram_username or "instagram_account"
        if not ig_name.startswith("@"):
            ig_name = f"@{ig_name}"
        social_account_repo.create_or_update(
            db=db,
            user_id=current_user.id,
            platform="instagram",
            account_id=request.instagram_account_id or "ig_account",
            account_name=ig_name,
            access_token=request.access_token,
            brand_id=target_brand.id,
            logo_url=brand_logo_url
        )

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


import secrets
import logging
from typing import Dict, Any, Optional, List
from urllib.parse import quote
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, status, Query, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.core.redis import set_oauth_state, pop_oauth_state
from app.core.security_encryption import encrypt_token
from app.repositories.social_account_repository import social_account_repo
from app.repositories.brand_repository import brand_repo
from app.services.youtube_service import (
    youtube_service,
    YouTubeOAuthException,
    YouTubeChannelNotFoundException,
    YouTubeAPIException,
)
from app.schemas.youtube import YouTubeOAuthStartResponse, YouTubeChannelInfo, YouTubeConnectResponse
from app.schemas.social_account import SocialAccountResponse
from app.api.v1.deps import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/youtube", tags=["YouTube Integration"])

@router.get("/oauth/start")
def start_youtube_oauth(
    redirect: bool = Query(True),
    current_user: User = Depends(get_current_user)
):
    """
    Generate Google OAuth 2.0 Authorization URL for connecting YouTube Channel.
    Includes cryptographically secure CSRF state token tied to current user session in Redis.
    """
    state_token = secrets.token_urlsafe(32)
    set_oauth_state(state_token, current_user.id, ttl_seconds=900)

    auth_url = youtube_service.get_authorization_url(state_token)
    if redirect:
        return RedirectResponse(url=auth_url, status_code=307)
    return {
        "authorization_url": auth_url,
        "state": state_token,
        "client_id_configured": bool(settings.YOUTUBE_CLIENT_ID and not settings.YOUTUBE_CLIENT_ID.startswith("your-"))
    }

@router.get("/oauth/callback")
def youtube_oauth_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Server-side Google OAuth Callback endpoint registered in Google Cloud Console.
    Exchanges code for access & refresh tokens, discovers authenticated YouTube channel
    via YouTube Data API v3 channels.list (mine=true), and saves credentials securely.
    """
    frontend_base = settings.FRONTEND_URL.rstrip('/')

    # 1. Handle user cancellation or Google authorization errors
    if error or error_description:
        err_msg = error_description or error or "Google authorization cancelled by user"
        logger.warning(f"[YOUTUBE_OAUTH] OAuth Callback Error: {err_msg}")
        return RedirectResponse(url=f"{frontend_base}/meta-connect?error={quote(err_msg)}")

    # 2. Verify CSRF State from Redis
    user_id = pop_oauth_state(state) if state else None
    if not user_id:
        logger.error("[YOUTUBE_OAUTH] OAuth Callback failed: Invalid or expired state token.")
        return RedirectResponse(url=f"{frontend_base}/meta-connect?error={quote('Invalid or expired OAuth state token. Please try again.')}")

    if not code:
        return RedirectResponse(url=f"{frontend_base}/meta-connect?error={quote('Missing authorization code from Google.')}")

    try:
        # 3. Server-side token exchange (Never exposes Client Secret to browser)
        token_data = youtube_service.exchange_code_for_tokens(code)
        access_token = token_data["access_token"]
        raw_refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)
        token_type = token_data.get("token_type", "Bearer")
        scope = token_data.get("scope", "")

        # 4. Discover authenticated YouTube Channel via Data API v3
        channel = youtube_service.fetch_authenticated_channel(access_token)
        channel_id = channel["channel_id"]
        channel_title = channel["title"]
        logo_url = channel.get("logo_url")
        custom_url = channel.get("custom_url")
        uploads_playlist_id = channel.get("uploads_playlist_id")

        # 5. Handle refresh token encryption & preservation on re-auth
        existing_acc = social_account_repo.get_by_account_id(db, user_id, "youtube", channel_id)
        if raw_refresh_token:
            encrypted_refresh_token = encrypt_token(raw_refresh_token)
        elif existing_acc and existing_acc.metadata_json:
            encrypted_refresh_token = existing_acc.metadata_json.get("refresh_token")
        else:
            encrypted_refresh_token = None

        meta_json = {
            "refresh_token": encrypted_refresh_token,
            "custom_url": custom_url,
            "uploads_playlist_id": uploads_playlist_id,
            "subscriber_count": channel.get("subscriber_count"),
            "video_count": channel.get("video_count"),
            "view_count": channel.get("view_count"),
            "granted_scopes": scope.split(" ") if scope else youtube_service.REQUIRED_YOUTUBE_SCOPES,
        }

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        # 6. Save or update connected YouTube account in social_accounts table
        account = social_account_repo.create_or_update(
            db=db,
            user_id=user_id,
            platform="youtube",
            account_id=channel_id,
            account_name=channel_title,
            access_token=access_token,
            token_type=token_type,
            expires_at=expires_at,
            logo_url=logo_url,
            metadata_json=meta_json
        )

        # 7. Auto-create matching Brand Profile if one doesn't exist
        brand_repo.ensure_brand_profile_exists(db, user_id, channel_title, logo_url)

        logger.info(
            f"[YOUTUBE_OAUTH] Successfully connected YouTube channel '{channel_title}' ({channel_id}) "
            f"for user {user_id} (SocialAccount ID: {account.id})."
        )

        return RedirectResponse(
            url=f"{frontend_base}/meta-connect?youtube_connected=true&channel_title={quote(channel_title)}&channel_id={quote(channel_id)}"
        )

    except YouTubeChannelNotFoundException as e:
        logger.warning(f"[YOUTUBE_OAUTH] Channel not found for user {user_id}: {e}")
        return RedirectResponse(url=f"{frontend_base}/meta-connect?error={quote(str(e))}")
    except YouTubeOAuthException as e:
        logger.error(f"[YOUTUBE_OAUTH] OAuth error during callback for user {user_id}: {e.message}")
        return RedirectResponse(url=f"{frontend_base}/meta-connect?error={quote(e.message)}")
    except YouTubeAPIException as e:
        logger.error(f"[YOUTUBE_OAUTH] YouTube API error during callback for user {user_id}: {e.message}")
        return RedirectResponse(url=f"{frontend_base}/meta-connect?error={quote(e.message)}")
    except Exception as e:
        logger.error(f"[YOUTUBE_OAUTH] Unexpected error during callback processing for user {user_id}: {e}")
        return RedirectResponse(url=f"{frontend_base}/meta-connect?error={quote('An unexpected error occurred while connecting your YouTube channel.')}")

@router.get("/channels", response_model=List[SocialAccountResponse])
def get_connected_youtube_channels(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve list of connected YouTube Channels for current authenticated user.
    Strictly user-isolated and never exposes access tokens or refresh tokens.
    """
    accounts = social_account_repo.get_by_user_and_platform(db, current_user.id, "youtube")
    return accounts

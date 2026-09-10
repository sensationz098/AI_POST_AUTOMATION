import secrets
import logging
from typing import Dict, Any, Optional, List
from urllib.parse import quote
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, status, Query, HTTPException, Request, Header
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.core.redis import (
    set_oauth_state,
    pop_oauth_state,
    set_upload_session,
    get_upload_session,
    update_upload_session,
    delete_upload_session,
)
from app.core.security_encryption import encrypt_token, decrypt_token
from app.repositories.social_account_repository import social_account_repo
from app.repositories.brand_repository import brand_repo
from app.services.youtube_service import (
    youtube_service,
    YouTubeOAuthException,
    YouTubeChannelNotFoundException,
    YouTubeAPIException,
)
from app.schemas.youtube import (
    YouTubeOAuthStartResponse,
    YouTubeChannelInfo,
    YouTubeConnectResponse,
    YouTubeUploadInitiateRequest,
    YouTubeUploadInitiateResponse,
    YouTubeUploadChunkResponse,
    YouTubeUploadStatusResponse,
)
from app.schemas.social_account import SocialAccountResponse
from app.api.v1.deps import get_current_user
from app.models.user import User

MAX_PROOF_OF_CONCEPT_CHUNK_BYTES = 5 * 1024 * 1024  # 5 MB maximum bound for proof-of-concept chunk


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

@router.post("/upload/initiate", response_model=YouTubeUploadInitiateResponse)
def initiate_youtube_upload(
    payload: YouTubeUploadInitiateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Initiate YouTube Resumable Upload Session (Milestone 2A Proof-of-Concept).
    Verifies user ownership of YouTube SocialAccount, obtains server-side access token,
    and calls Google Resumable Upload endpoint.
    Returns upload session ID (tokens/credentials are never exposed).
    """
    # 1. Validate SocialAccount ownership & platform
    account = social_account_repo.get_by_id(db, payload.social_account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="YouTube channel account not found or access denied."
        )
    if account.platform != "youtube":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Account is not a YouTube platform account (found: {account.platform})."
        )

    # 2. Get valid access token (refreshes automatically if near expiry)
    try:
        access_token = youtube_service.get_valid_access_token_for_account(db, account)
    except Exception as e:
        logger.error(f"[YOUTUBE_UPLOAD] Token resolution failed for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Failed to authenticate with YouTube: {str(e)}"
        )

    # 3. Call Google Resumable Upload initiate endpoint
    try:
        session_url = youtube_service.initiate_resumable_upload(
            access_token=access_token,
            title=payload.title,
            description=payload.description or "",
            privacy_status=payload.privacy_status or "private",
            mime_type=payload.mime_type or "video/mp4",
            file_size_bytes=payload.file_size_bytes,
        )
    except YouTubeAPIException as e:
        logger.error(f"[YOUTUBE_UPLOAD] Resumable init API error: {e.message}")
        raise HTTPException(
            status_code=e.status_code if e.status_code and e.status_code >= 400 else 502,
            detail=f"YouTube upload initialization failed: {e.message}"
        )
    except Exception as e:
        logger.error(f"[YOUTUBE_UPLOAD] Unexpected error during init: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating YouTube upload session."
        )

    # 4. Generate unique upload_id & store session securely in Redis (with encrypted session_url)
    upload_id = f"ytu_{secrets.token_urlsafe(24)}"
    session_data = {
        "upload_id": upload_id,
        "user_id": current_user.id,
        "social_account_id": account.id,
        "channel_id": account.account_id,
        "channel_title": account.account_name,
        "title": payload.title,
        "file_size_bytes": payload.file_size_bytes,
        "mime_type": payload.mime_type or "video/mp4",
        "privacy_status": payload.privacy_status or "private",
        "encrypted_session_url": encrypt_token(session_url),
        "status": "INITIATED",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    set_upload_session(upload_id, session_data, ttl_seconds=86400)

    logger.info(f"[YOUTUBE_UPLOAD] User {current_user.id} initiated upload {upload_id} for channel {account.account_id}")

    return YouTubeUploadInitiateResponse(
        upload_id=upload_id,
        channel_id=account.account_id,
        channel_title=account.account_name,
        title=payload.title,
        file_size_bytes=payload.file_size_bytes,
        mime_type=payload.mime_type or "video/mp4",
        status="INITIATED",
        message="Resumable upload session initiated successfully."
    )

@router.put("/upload/{upload_id}/chunk", response_model=YouTubeUploadChunkResponse)
async def upload_youtube_chunk(
    upload_id: str,
    request: Request,
    content_range: str = Header(..., alias="Content-Range", description="e.g. bytes 0-2097151/5242880"),
    content_type: str = Header("video/mp4", alias="Content-Type"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Proxy a single binary video chunk to YouTube Resumable Upload Session (Milestone 2A Proof-of-Concept).
    Enforces maximum chunk size, validates user ownership, and uses server-side OAuth credentials.
    Returns confirmed Range and next byte offset from YouTube response.
    """
    # 1. Retrieve session and verify tenant ownership
    session_data = get_upload_session(upload_id)
    if not session_data or session_data.get("user_id") != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload session not found or access denied."
        )

    # 2. Read request body bytes & validate bounded chunk size
    chunk_bytes = await request.body()
    if not chunk_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chunk payload cannot be empty."
        )
    if len(chunk_bytes) > MAX_PROOF_OF_CONCEPT_CHUNK_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Chunk size {len(chunk_bytes)} bytes exceeds maximum allowed chunk size ({MAX_PROOF_OF_CONCEPT_CHUNK_BYTES} bytes)."
        )

    # 3. Decrypt session URL
    encrypted_url = session_data.get("encrypted_session_url")
    if not encrypted_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Corrupted upload session data."
        )
    session_url = decrypt_token(encrypted_url)
    if not session_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to decrypt upload session URL."
        )

    # 4. Get valid server-side access token
    account = social_account_repo.get_by_id(db, session_data["social_account_id"])
    if not account or account.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated YouTube account not found."
        )
    access_token = youtube_service.get_valid_access_token_for_account(db, account)

    # 5. Forward chunk to YouTube
    try:
        result = youtube_service.upload_resumable_chunk(
            resumable_session_url=session_url,
            chunk_bytes=chunk_bytes,
            content_range=content_range,
            mime_type=content_type,
            access_token=access_token,
        )
    except YouTubeAPIException as e:
        logger.error(f"[YOUTUBE_UPLOAD] Chunk upload API error for {upload_id}: {e.message}")
        raise HTTPException(
            status_code=e.status_code if e.status_code and e.status_code >= 400 else 502,
            detail=f"YouTube chunk transmission failed: {e.message}"
        )
    except Exception as e:
        logger.error(f"[YOUTUBE_UPLOAD] Unexpected error during chunk proxy for {upload_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to forward video chunk to YouTube."
        )

    # Update session in Redis
    if result.get("is_complete"):
        update_upload_session(upload_id, {
            "status": "COMPLETED",
            "video_id": result.get("video_id"),
            "video_url": result.get("video_url"),
        })
    else:
        update_upload_session(upload_id, {
            "status": "RESUME_INCOMPLETE",
            "last_byte_received": result.get("last_byte_received"),
            "next_byte_offset": result.get("next_byte_offset"),
        })

    return YouTubeUploadChunkResponse(
        upload_id=upload_id,
        status=result["status"],
        http_status=result["http_status"],
        range_header=result.get("range_header"),
        last_byte_received=result.get("last_byte_received"),
        next_byte_offset=result.get("next_byte_offset"),
        total_bytes=session_data.get("file_size_bytes", 0),
        is_complete=result.get("is_complete", False),
        video_id=result.get("video_id"),
        video_url=result.get("video_url"),
    )

@router.get("/upload/{upload_id}/status", response_model=YouTubeUploadStatusResponse)
def get_youtube_upload_status(
    upload_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Query YouTube upload session status to determine confirmed byte range and next offset.
    Strictly tenant-isolated.
    """
    session_data = get_upload_session(upload_id)
    if not session_data or session_data.get("user_id") != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload session not found or access denied."
        )

    # If already marked completed in session
    if session_data.get("status") == "COMPLETED" and session_data.get("video_id"):
        return YouTubeUploadStatusResponse(
            upload_id=upload_id,
            channel_id=session_data["channel_id"],
            title=session_data["title"],
            file_size_bytes=session_data["file_size_bytes"],
            mime_type=session_data["mime_type"],
            status="COMPLETED",
            http_status=200,
            last_byte_received=session_data["file_size_bytes"] - 1,
            next_byte_offset=session_data["file_size_bytes"],
            is_complete=True,
            video_id=session_data.get("video_id"),
            video_url=session_data.get("video_url"),
        )

    # Query YouTube for live Range status
    encrypted_url = session_data.get("encrypted_session_url")
    session_url = decrypt_token(encrypted_url) if encrypted_url else None
    if not session_url:
        raise HTTPException(status_code=500, detail="Corrupted upload session.")

    account = social_account_repo.get_by_id(db, session_data["social_account_id"])
    access_token = youtube_service.get_valid_access_token_for_account(db, account) if account else None

    try:
        status_res = youtube_service.query_resumable_status(
            resumable_session_url=session_url,
            total_file_size=session_data["file_size_bytes"],
            mime_type=session_data["mime_type"],
            access_token=access_token,
        )
    except Exception as e:
        logger.error(f"[YOUTUBE_UPLOAD] Error querying status from YouTube: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to query YouTube upload status: {str(e)}")

    return YouTubeUploadStatusResponse(
        upload_id=upload_id,
        channel_id=session_data["channel_id"],
        title=session_data["title"],
        file_size_bytes=session_data["file_size_bytes"],
        mime_type=session_data["mime_type"],
        status=status_res["status"],
        http_status=status_res["http_status"],
        range_header=status_res.get("range_header"),
        last_byte_received=status_res.get("last_byte_received"),
        next_byte_offset=status_res.get("next_byte_offset"),
        is_complete=status_res.get("is_complete", False),
        video_id=status_res.get("video_id"),
        video_url=status_res.get("video_url"),
    )


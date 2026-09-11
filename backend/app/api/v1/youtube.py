import os
import base64
import secrets
import logging
from typing import Dict, Any, Optional, List
from urllib.parse import quote
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, status, Query, HTTPException, Request, Header, File, UploadFile
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
from app.repositories.youtube_upload_repository import youtube_upload_repo
from app.models.youtube_upload import YouTubeUpload, YouTubeUploadStatus
from app.tasks.youtube_tasks import (
    poll_youtube_video_processing_task,
    check_and_update_youtube_processing_status,
)
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
    YouTubeUploadDetailResponse,
    YouTubeThumbnailUploadResponse,
    YouTubeThumbnailRetryResponse,
    YouTubeUploadCancelResponse,
    YouTubeUploadListResponse,
    YouTubeVideoDetailResponse,
    YouTubeVideoUpdateRequest,
)
from app.schemas.social_account import SocialAccountResponse
from app.api.v1.deps import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/youtube", tags=["YouTube Integration"])

@router.get("/oauth/start")
def start_youtube_oauth(
    redirect: bool = Query(True),
    brand_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Start YouTube OAuth flow.
    Generates cryptographically secure CSRF state token stored in Redis with 10-minute TTL,
    and returns or redirects to Google OAuth 2.0 authorization URL.
    """
    if not settings.YOUTUBE_CLIENT_ID or not settings.YOUTUBE_CLIENT_SECRET:
        if not settings.YOUTUBE_MOCK_MODE:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="YouTube OAuth is not configured on this server (missing YOUTUBE_CLIENT_ID or YOUTUBE_CLIENT_SECRET)."
            )

    # 1. Generate secure CSRF state
    state = secrets.token_urlsafe(32)
    set_oauth_state(state, current_user.id, ttl_seconds=600)

    # 2. Build authorization URL
    auth_url = youtube_service.get_authorization_url(state=state)

    logger.info(f"[YOUTUBE_OAUTH] Initiated OAuth flow for user {current_user.id}, state={state[:8]}...")

    if redirect:
        return RedirectResponse(url=auth_url)
    
    return YouTubeOAuthStartResponse(
        authorization_url=auth_url,
        state=state,
        client_id_configured=bool(settings.YOUTUBE_CLIENT_ID and settings.YOUTUBE_CLIENT_SECRET)
    )

@router.get("/oauth/callback")
def youtube_oauth_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Google OAuth 2.0 Callback Handler.
    1. Validates CSRF state against Redis (one-time pop).
    2. Exchanges authorization code server-side for access token & refresh token.
    3. Fetches authenticated YouTube channel info via YouTube Data API v3.
    4. Encrypts and persists tokens in social_accounts table.
    5. Redirects to frontend /meta-connect with success/error query params.
    """
    frontend_base = settings.FRONTEND_URL.rstrip('/')
    
    # 1. Handle user cancellation or Google error
    if error:
        err_msg = error_description or error
        logger.warning(f"[YOUTUBE_OAUTH] OAuth callback error from Google: {error} ({err_msg})")
        return RedirectResponse(url=f"{frontend_base}/meta-connect?error={quote(f'Google authorization failed: {err_msg}')}")

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
            metadata_json=meta_json,
        )

        # 7. Ensure brand profile exists for this YouTube channel
        brand_repo.ensure_brand_profile_exists(
            db=db,
            user_id=user_id,
            account_name=channel_title,
            logo_url=logo_url,
        )

        logger.info(
            f"[YOUTUBE_OAUTH] Successfully connected YouTube channel '{channel_title}' "
            f"(id={channel_id}) for user {user_id}."
        )

        return RedirectResponse(
            url=f"{frontend_base}/meta-connect?youtube_connected=true&channel_id={quote(channel_id)}&channel_title={quote(channel_title)}"
        )

    except YouTubeChannelNotFoundException as e:
        err_text = getattr(e, "message", str(e))
        logger.error(f"[YOUTUBE_OAUTH] No YouTube channel found on Google account for user {user_id}: {err_text}")
        return RedirectResponse(url=f"{frontend_base}/meta-connect?error={quote(err_text)}")
    except YouTubeOAuthException as e:
        err_text = getattr(e, "message", str(e))
        logger.error(f"[YOUTUBE_OAUTH] OAuth exchange failed for user {user_id}: {err_text}")
        return RedirectResponse(url=f"{frontend_base}/meta-connect?error={quote(f'Failed to connect YouTube: {err_text}')}")
    except Exception as e:
        logger.error(f"[YOUTUBE_OAUTH] Unexpected error in callback for user {user_id}: {e}")
        return RedirectResponse(url=f"{frontend_base}/meta-connect?error={quote('An unexpected error occurred while connecting your YouTube account.')}")

@router.get("/channels", response_model=List[SocialAccountResponse])
def list_connected_youtube_channels(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve list of connected YouTube Channels for current authenticated user.
    Strictly user-isolated and never exposes access tokens or refresh tokens.
    """
    accounts = social_account_repo.get_by_user_and_platform(db, current_user.id, "youtube")
    return accounts

# ─── Resumable Upload Endpoints (Milestone 2B) ───────────────────────────────

@router.post("/upload-thumbnail", response_model=YouTubeThumbnailUploadResponse)
async def upload_youtube_thumbnail(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload and validate custom thumbnail for YouTube videos.
    Enforces image format (image/jpeg, image/png) and max size (2 MB per YouTube requirements).
    Streams image into trusted media storage (Cloudinary or fallback).
    """
    filename = file.filename or "thumbnail.jpg"
    content_type = (file.content_type or "").lower()

    # 1. Validate MIME type strictly (JPEG, PNG)
    valid_mimes = ["image/jpeg", "image/jpg", "image/png"]
    has_valid_ext = any(filename.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png"])
    if (content_type and content_type not in valid_mimes) or (not content_type and not has_valid_ext):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image format. YouTube custom thumbnails must be JPEG or PNG format."
        )

    # 2. Check file size (max 2 MB = 2 * 1024 * 1024 bytes)
    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)

    MAX_THUMBNAIL_BYTES = 2 * 1024 * 1024
    if file_size > MAX_THUMBNAIL_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Thumbnail size ({file_size / (1024*1024):.2f} MB) exceeds maximum allowed limit of 2 MB."
        )
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Thumbnail file cannot be empty."
        )

    # 3. Upload to trusted application storage
    from app.services.cloudinary_service import upload_media_to_cloudinary
    storage_url = upload_media_to_cloudinary(file.file, filename_prefix="yt_thumb", media_type="image")

    if not storage_url:
        # Fallback to base64 data URI if Cloudinary is unconfigured
        file.file.seek(0)
        raw_bytes = file.file.read()
        b64 = base64.b64encode(raw_bytes).decode("utf-8")
        actual_mime = "image/png" if filename.lower().endswith(".png") else "image/jpeg"
        storage_url = f"data:{actual_mime};base64,{b64}"

    logger.info(f"[YOUTUBE_THUMBNAIL] User {current_user.id} uploaded thumbnail {filename} ({file_size} bytes)")

    return YouTubeThumbnailUploadResponse(
        thumbnail_url=storage_url,
        filename=filename,
        file_size_bytes=file_size,
    )

@router.post("/upload/initiate", response_model=YouTubeUploadInitiateResponse)
def initiate_youtube_upload(
    payload: YouTubeUploadInitiateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Initiate a production YouTube Resumable Upload Session.
    Enforces idempotency (reuses active session if matching client_mutation_id is passed).
    Verifies user ownership of YouTube SocialAccount, obtains server-side access token,
    creates YouTube resumable session URL with Google, and creates persistent YouTubeUpload record.
    Returns opaque upload_id and configured chunk_size_bytes.
    """
    # 1. Idempotency Check: if client provided mutation key, check for existing active upload
    if payload.client_mutation_id:
        existing_upload = youtube_upload_repo.get_by_mutation_id(
            db, user_id=current_user.id, client_mutation_id=payload.client_mutation_id
        )
        if existing_upload and existing_upload.encrypted_session_url:
            logger.info(f"[YOUTUBE_UPLOAD] Idempotent request: reusing existing upload {existing_upload.upload_id} for mutation key {payload.client_mutation_id}")
            return YouTubeUploadInitiateResponse(
                upload_id=existing_upload.upload_id,
                client_mutation_id=existing_upload.client_mutation_id,
                channel_id=existing_upload.channel_id,
                channel_title=existing_upload.social_account.account_name if existing_upload.social_account else "YouTube Channel",
                title=existing_upload.title,
                file_size_bytes=existing_upload.file_size_bytes,
                chunk_size_bytes=settings.YOUTUBE_UPLOAD_CHUNK_SIZE,
                mime_type=existing_upload.mime_type,
                privacy_status=existing_upload.privacy_status,
                status=existing_upload.upload_status,
                thumbnail_url=existing_upload.thumbnail_url,
                thumbnail_status=existing_upload.thumbnail_status,
                next_byte_offset=existing_upload.bytes_uploaded,
                message="Resumed existing active upload session."
            )

    # 2. Validate SocialAccount ownership & platform
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

    # 3. Get valid access token (refreshes automatically if near expiry)
    try:
        access_token = youtube_service.get_valid_access_token_for_account(db, account)
    except Exception as e:
        logger.error(f"[YOUTUBE_UPLOAD] Token resolution failed for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Failed to authenticate with YouTube: {str(e)}"
        )

    # 4. Call Google Resumable Upload initiate endpoint
    try:
        session_url = youtube_service.initiate_resumable_upload(
            access_token=access_token,
            title=payload.title,
            description=payload.description or "",
            privacy_status=payload.privacy_status or "private",
            mime_type=payload.mime_type or "video/mp4",
            file_size_bytes=payload.file_size_bytes,
            tags=payload.tags,
            category_id=payload.category_id,
            made_for_kids=payload.made_for_kids,
            publish_at=payload.publish_at,
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

    # 5. Generate unique upload_id & persist YouTubeUpload record in PostgreSQL
    upload_id = f"ytu_{secrets.token_urlsafe(24)}"
    encrypted_url = encrypt_token(session_url)

    upload_record = youtube_upload_repo.create(
        db=db,
        upload_id=upload_id,
        user_id=current_user.id,
        social_account_id=account.id,
        channel_id=account.account_id,
        title=payload.title,
        description=payload.description or "",
        privacy_status=payload.privacy_status or "private",
        original_filename=payload.filename,
        mime_type=payload.mime_type or "video/mp4",
        file_size_bytes=payload.file_size_bytes,
        encrypted_session_url=encrypted_url,
        client_mutation_id=payload.client_mutation_id,
        thumbnail_url=payload.thumbnail_url,
        metadata_json={
            "channel_title": account.account_name,
            "thumbnail_url": payload.thumbnail_url,
        },
    )

    # Cache session in Redis for fast access
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
        "encrypted_session_url": encrypted_url,
        "thumbnail_url": payload.thumbnail_url,
        "thumbnail_status": "PENDING" if payload.thumbnail_url else None,
        "thumbnail_error": None,
        "status": YouTubeUploadStatus.INITIATED.value,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    set_upload_session(upload_id, session_data, ttl_seconds=86400)

    logger.info(f"[YOUTUBE_UPLOAD] User {current_user.id} initiated upload {upload_id} for channel {account.account_id}")

    return YouTubeUploadInitiateResponse(
        upload_id=upload_id,
        client_mutation_id=payload.client_mutation_id,
        channel_id=account.account_id,
        channel_title=account.account_name,
        title=payload.title,
        file_size_bytes=payload.file_size_bytes,
        chunk_size_bytes=settings.YOUTUBE_UPLOAD_CHUNK_SIZE,
        mime_type=payload.mime_type or "video/mp4",
        privacy_status=payload.privacy_status or "private",
        status=upload_record.upload_status,
        thumbnail_url=payload.thumbnail_url,
        thumbnail_status=upload_record.thumbnail_status,
        next_byte_offset=0,
        message="Resumable upload session initiated successfully."
    )

@router.put("/upload/{upload_id}/chunk", response_model=YouTubeUploadChunkResponse)
async def upload_youtube_chunk(
    upload_id: str,
    request: Request,
    content_range: str = Header(..., alias="Content-Range", description="e.g. bytes 0-8388607/20971520"),
    content_type: str = Header("video/mp4", alias="Content-Type"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Proxy a single binary video chunk to YouTube Resumable Upload Session.
    Enforces maximum chunk size, validates user ownership, checks for cancellation,
    and forwards bounded chunk via server-side OAuth credentials.
    On HTTP 308: updates byte progress and returns authoritative next offset.
    On HTTP 200/201: marks upload complete and kicks off background Celery video processing polling.
    """
    # 1. Retrieve persistent upload record & verify tenant ownership
    upload = youtube_upload_repo.get_by_upload_id_and_user(db, upload_id, current_user.id)
    if not upload:
        # Check fallback in redis
        session_data = get_upload_session(upload_id)
        if not session_data or session_data.get("user_id") != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Upload session not found or access denied."
            )
        social_acc_id = session_data["social_account_id"]
        total_file_size = session_data.get("file_size_bytes", 0)
        encrypted_url = session_data.get("encrypted_session_url")
        current_status = session_data.get("status", YouTubeUploadStatus.INITIATED.value)
    else:
        social_acc_id = upload.social_account_id
        total_file_size = upload.file_size_bytes
        encrypted_url = upload.encrypted_session_url
        current_status = upload.upload_status

    # 2. Check upload status lifecycle
    if current_status == YouTubeUploadStatus.CANCELLED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Upload session was cancelled and cannot accept further chunks."
        )
    if current_status == YouTubeUploadStatus.FAILED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload session has failed and cannot accept further chunks."
        )

    # 3. Read bounded request body bytes (Never load full multi-GB video into memory)
    chunk_bytes = await request.body()
    if not chunk_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chunk payload cannot be empty."
        )
    if len(chunk_bytes) > settings.YOUTUBE_UPLOAD_CHUNK_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Chunk size {len(chunk_bytes)} bytes exceeds maximum configured chunk size ({settings.YOUTUBE_UPLOAD_CHUNK_SIZE} bytes)."
        )

    # 4. Decrypt session URL
    if not encrypted_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Corrupted upload session data (missing session URL)."
        )
    session_url = decrypt_token(encrypted_url)
    if not session_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to decrypt upload session capability URL."
        )

    # 5. Get valid server-side access token
    account = social_account_repo.get_by_id(db, social_acc_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated YouTube account not found."
        )
    access_token = youtube_service.get_valid_access_token_for_account(db, account)

    # 6. Forward chunk to YouTube
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
        if upload:
            youtube_upload_repo.mark_failed(db, upload_id, f"YouTube chunk transmission failed: {e.message}")
        raise HTTPException(
            status_code=e.status_code if e.status_code and e.status_code >= 400 else 502,
            detail=f"YouTube chunk transmission failed: {e.message}"
        )
    except Exception as e:
        logger.error(f"[YOUTUBE_UPLOAD] Unexpected error during chunk proxy for {upload_id}: {e}")
        if upload:
            youtube_upload_repo.mark_failed(db, upload_id, "Failed to forward video chunk to YouTube.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to forward video chunk to YouTube."
        )

    is_complete = result.get("is_complete", False)
    last_byte_received = (total_file_size - 1) if (is_complete and total_file_size > 0) else result.get("last_byte_received")
    next_byte_offset = None if is_complete else result.get("next_byte_offset")
    bytes_uploaded = total_file_size if is_complete else ((last_byte_received + 1) if last_byte_received is not None else 0)
    pct = round((bytes_uploaded / total_file_size * 100.0), 2) if total_file_size > 0 else (100.0 if is_complete else 0.0)

    # 7. Update DB and Redis records
    if is_complete:
        video_id = result.get("video_id")
        video_url = result.get("video_url")
        if upload:
            youtube_upload_repo.mark_completed(db, upload_id, video_id or "", video_url or "")

        # Check for custom thumbnail application
        thumb_url = (upload.thumbnail_url if upload else None)
        thumb_status = (upload.thumbnail_status if upload else None)
        thumb_error = (upload.thumbnail_error if upload else None)

        if not thumb_url:
            cached_session = get_upload_session(upload_id)
            if cached_session:
                thumb_url = cached_session.get("thumbnail_url")
                thumb_status = cached_session.get("thumbnail_status")
                thumb_error = cached_session.get("thumbnail_error")

        # Apply custom thumbnail if thumbnail_url is present and not yet applied
        if thumb_url and video_id and thumb_status != "APPLIED":
            try:
                youtube_service.apply_thumbnail_from_storage(
                    access_token=access_token,
                    video_id=video_id,
                    thumbnail_url=thumb_url,
                )
                thumb_status = "APPLIED"
                thumb_error = None
                if upload:
                    youtube_upload_repo.update_thumbnail_status(db, upload_id, "APPLIED")
                logger.info(f"[YOUTUBE_UPLOAD] Custom thumbnail successfully applied to video {video_id} for upload {upload_id}")
            except Exception as e:
                thumb_status = "FAILED"
                thumb_error = str(getattr(e, "message", e))
                if upload:
                    youtube_upload_repo.update_thumbnail_status(db, upload_id, "FAILED", error=thumb_error)
                logger.warning(f"[YOUTUBE_UPLOAD] Thumbnail application failed for video {video_id} (upload {upload_id}): {thumb_error}. Video publication remains successful.")
        
        update_upload_session(upload_id, {
            "status": YouTubeUploadStatus.PROCESSING.value,
            "video_id": video_id,
            "video_url": video_url,
            "thumbnail_url": thumb_url,
            "thumbnail_status": thumb_status,
            "thumbnail_error": thumb_error,
            "last_byte_received": last_byte_received,
        })

        # Trigger background Celery task for processing status tracking
        try:
            poll_youtube_video_processing_task.delay(upload_id=upload_id, attempt=1)
            logger.info(f"[YOUTUBE_UPLOAD] Enqueued Celery video processing polling for upload {upload_id}, video_id={video_id}")
        except Exception as e:
            logger.warning(f"[YOUTUBE_UPLOAD] Failed to enqueue Celery task for {upload_id} (will rely on polling): {e}")

    else:
        if upload:
            youtube_upload_repo.update_progress(
                db, upload_id, bytes_uploaded=bytes_uploaded, total_bytes=total_file_size, status=YouTubeUploadStatus.UPLOADING.value
            )

        update_upload_session(upload_id, {
            "status": YouTubeUploadStatus.UPLOADING.value,
            "last_byte_received": last_byte_received,
            "next_byte_offset": next_byte_offset,
        })

    return YouTubeUploadChunkResponse(
        upload_id=upload_id,
        status=YouTubeUploadStatus.PROCESSING.value if is_complete else result["status"],
        http_status=result["http_status"],
        range_header=result.get("range_header"),
        last_byte_received=last_byte_received,
        next_byte_offset=next_byte_offset,
        total_bytes=total_file_size,
        bytes_uploaded=bytes_uploaded,
        progress_percentage=min(pct, 100.0),
        is_complete=is_complete,
        video_id=result.get("video_id"),
        video_url=result.get("video_url"),
        thumbnail_url=thumb_url if is_complete else (upload.thumbnail_url if upload else None),
        thumbnail_status=thumb_status if is_complete else (upload.thumbnail_status if upload else None),
        thumbnail_error=thumb_error if is_complete else (upload.thumbnail_error if upload else None),
    )

@router.get("/upload/{upload_id}/status", response_model=YouTubeUploadStatusResponse)
def get_youtube_upload_status(
    upload_id: str,
    refresh: bool = Query(False, description="Explicitly query Google YouTube API instead of returning DB cache"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get YouTube upload status and confirmed byte range.
    Strictly tenant-isolated.
    By default, reads database state directly to avoid hitting YouTube rate limits.
    If refresh=True, performs a controlled live query against YouTube and updates DB.
    """
    upload = youtube_upload_repo.get_by_upload_id_and_user(db, upload_id, current_user.id)
    if not upload:
        # Check fallback session cache
        session_data = get_upload_session(upload_id)
        if not session_data or session_data.get("user_id") != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Upload session not found or access denied."
            )
        total_size = session_data.get("file_size_bytes", 0)
        is_finished = session_data.get("status") in (
            YouTubeUploadStatus.PROCESSING.value,
            YouTubeUploadStatus.READY.value
        )
        return YouTubeUploadStatusResponse(
            upload_id=upload_id,
            channel_id=session_data["channel_id"],
            title=session_data["title"],
            file_size_bytes=total_size,
            bytes_uploaded=total_size if is_finished else (session_data.get("last_byte_received", 0) + 1 if session_data.get("last_byte_received") is not None else 0),
            progress_percentage=100.0 if is_finished else 0.0,
            mime_type=session_data["mime_type"],
            status=session_data.get("status", "INITIATED"),
            http_status=200 if is_finished else 308,
            range_header=None,
            last_byte_received=(total_size - 1) if is_finished and total_size > 0 else session_data.get("last_byte_received"),
            next_byte_offset=None if is_finished else session_data.get("next_byte_offset"),
            is_complete=is_finished,
            video_id=session_data.get("video_id"),
            video_url=session_data.get("video_url"),
            thumbnail_url=session_data.get("thumbnail_url"),
            thumbnail_status=session_data.get("thumbnail_status"),
            thumbnail_error=session_data.get("thumbnail_error"),
        )

    # Controlled live refresh if client requested it
    if refresh:
        account = social_account_repo.get_by_id(db, upload.social_account_id)
        access_token = youtube_service.get_valid_access_token_for_account(db, account) if account else None

        # Case A: In PROCESSING state -> query videos.list for video encoding completion
        if upload.upload_status == YouTubeUploadStatus.PROCESSING.value and upload.video_id:
            try:
                check_and_update_youtube_processing_status(db, upload_id)
                db.refresh(upload)
            except Exception as e:
                logger.warning(f"[YOUTUBE_STATUS] Live processing query failed for {upload_id}: {e}")

        # Case B: In UPLOADING / INITIATED state -> query resumable session Range
        elif upload.upload_status in (YouTubeUploadStatus.INITIATED.value, YouTubeUploadStatus.UPLOADING.value) and upload.encrypted_session_url:
            session_url = decrypt_token(upload.encrypted_session_url)
            if session_url:
                try:
                    status_res = youtube_service.query_resumable_status(
                        resumable_session_url=session_url,
                        total_file_size=upload.file_size_bytes,
                        mime_type=upload.mime_type,
                        access_token=access_token,
                    )
                    if status_res.get("is_complete"):
                        youtube_upload_repo.mark_completed(
                            db, upload_id, status_res.get("video_id") or "", status_res.get("video_url") or ""
                        )
                    elif status_res.get("last_byte_received") is not None:
                        bytes_up = status_res["last_byte_received"] + 1
                        youtube_upload_repo.update_progress(
                            db, upload_id, bytes_uploaded=bytes_up, total_bytes=upload.file_size_bytes, status=YouTubeUploadStatus.UPLOADING.value
                        )
                    db.refresh(upload)
                except Exception as e:
                    logger.warning(f"[YOUTUBE_STATUS] Live Range query failed for {upload_id}: {e}")

    # Build safe response strictly from DB record
    is_complete = upload.upload_status in (
        YouTubeUploadStatus.PROCESSING.value,
        YouTubeUploadStatus.READY.value,
    )
    last_byte = (upload.file_size_bytes - 1) if is_complete else (upload.bytes_uploaded - 1 if upload.bytes_uploaded > 0 else None)
    next_offset = None if is_complete else (upload.bytes_uploaded if upload.bytes_uploaded < upload.file_size_bytes else None)

    return YouTubeUploadStatusResponse(
        upload_id=upload.upload_id,
        channel_id=upload.channel_id,
        title=upload.title,
        file_size_bytes=upload.file_size_bytes,
        bytes_uploaded=upload.bytes_uploaded,
        progress_percentage=upload.progress_percentage,
        mime_type=upload.mime_type,
        status=upload.upload_status,
        http_status=200 if is_complete else 308,
        range_header=None,
        last_byte_received=last_byte,
        next_byte_offset=next_offset,
        is_complete=is_complete,
        processing_status=upload.processing_status,
        processing_failure_reason=upload.processing_failure_reason,
        video_id=upload.video_id,
        video_url=upload.video_url,
        thumbnail_url=upload.thumbnail_url,
        thumbnail_status=upload.thumbnail_status,
        thumbnail_error=upload.thumbnail_error,
        error_message=upload.error_message,
        created_at=upload.created_at,
        updated_at=upload.updated_at,
        completed_at=upload.completed_at,
    )

@router.post("/upload/{upload_id}/thumbnail/retry", response_model=YouTubeThumbnailRetryResponse)
@router.post("/{upload_id}/thumbnail/retry", response_model=YouTubeThumbnailRetryResponse)
def retry_youtube_thumbnail(
    upload_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retry applying custom thumbnail for an existing uploaded YouTube video.
    Strictly tenant-isolated.
    """
    upload = youtube_upload_repo.get_by_upload_id_and_user(db, upload_id, current_user.id)
    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="YouTube upload record not found or access denied."
        )

    if not upload.video_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot apply thumbnail: Video has not yet been assigned a YouTube video ID."
        )

    if not upload.thumbnail_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No thumbnail URL is associated with this upload."
        )

    account = social_account_repo.get_by_id(db, upload.social_account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connected YouTube channel not found or access denied."
        )

    access_token = youtube_service.get_valid_access_token_for_account(db, account)

    try:
        youtube_service.apply_thumbnail_from_storage(
            access_token=access_token,
            video_id=upload.video_id,
            thumbnail_url=upload.thumbnail_url,
        )
        youtube_upload_repo.update_thumbnail_status(db, upload_id, "APPLIED")
        update_upload_session(upload_id, {
            "thumbnail_status": "APPLIED",
            "thumbnail_error": None,
        })
        logger.info(f"[YOUTUBE_THUMBNAIL] Successfully applied retried thumbnail for upload {upload_id}, video_id={upload.video_id}")
        return YouTubeThumbnailRetryResponse(
            success=True,
            upload_id=upload_id,
            thumbnail_status="APPLIED",
            thumbnail_error=None,
            message="Thumbnail applied successfully."
        )
    except Exception as e:
        err_msg = str(getattr(e, "message", e))
        youtube_upload_repo.update_thumbnail_status(db, upload_id, "FAILED", error=err_msg)
        update_upload_session(upload_id, {
            "thumbnail_status": "FAILED",
            "thumbnail_error": err_msg,
        })
        logger.warning(f"[YOUTUBE_THUMBNAIL] Thumbnail retry failed for upload {upload_id}: {err_msg}")
        return YouTubeThumbnailRetryResponse(
            success=False,
            upload_id=upload_id,
            thumbnail_status="FAILED",
            thumbnail_error=err_msg,
            message=f"Thumbnail application failed: {err_msg}"
        )

@router.post("/upload/{upload_id}/cancel", response_model=YouTubeUploadCancelResponse)
def cancel_youtube_upload(
    upload_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Cancel an active YouTube video upload.
    Marks application-level upload status as CANCELLED, preventing further chunk uploads and background processing.
    Attempts best-effort remote notification to Google capability URI.
    """
    upload = youtube_upload_repo.get_by_upload_id_and_user(db, upload_id, current_user.id)
    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload session not found or access denied."
        )

    if upload.upload_status in (
        YouTubeUploadStatus.READY.value,
        YouTubeUploadStatus.FAILED.value,
        YouTubeUploadStatus.CANCELLED.value,
    ):
        return YouTubeUploadCancelResponse(
            success=True,
            upload_id=upload_id,
            status=upload.upload_status,
            message=f"Upload is already in {upload.upload_status} state."
        )

    # 1. Mark CANCELLED in DB
    youtube_upload_repo.mark_cancelled(db, upload_id)
    delete_upload_session(upload_id)

    # 2. Best-effort remote notification to Google (does not raise if unsupported)
    if upload.encrypted_session_url:
        session_url = decrypt_token(upload.encrypted_session_url)
        account = social_account_repo.get_by_id(db, upload.social_account_id)
        access_token = youtube_service.get_valid_access_token_for_account(db, account) if account else None
        if session_url:
            youtube_service.cancel_resumable_upload_session(session_url, upload.file_size_bytes, access_token)

    logger.info(f"[YOUTUBE_UPLOAD] User {current_user.id} cancelled upload {upload_id}.")

    return YouTubeUploadCancelResponse(
        success=True,
        upload_id=upload_id,
        status=YouTubeUploadStatus.CANCELLED.value,
        message="Upload session was cancelled successfully."
    )

@router.get("/uploads", response_model=YouTubeUploadListResponse)
def list_user_youtube_uploads(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List historical and active YouTube uploads for the current authenticated user.
    Strictly user-isolated.
    """
    items = youtube_upload_repo.list_by_user(db, current_user.id, limit=limit, offset=offset)
    return YouTubeUploadListResponse(
        items=[YouTubeUploadDetailResponse.from_orm(it) for it in items],
        total=len(items)
    )

# ─── Post-Upload Video Editing Endpoints ─────────────────────────────────────

def _resolve_youtube_account_for_video(
    db: Session,
    user_id: int,
    video_id: str,
    social_account_id: Optional[int] = None,
):
    """
    Resolve and verify that the authenticated user owns a connected YouTube channel
    associated with the requested video_id.
    Prevents cross-tenant access to unauthorized YouTube videos.
    """
    # 1. If explicit social_account_id passed, verify user owns it
    if social_account_id:
        acc = social_account_repo.get_by_id(db, social_account_id)
        if not acc or acc.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Connected YouTube channel not found or access denied."
            )
        if acc.platform != "youtube":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Specified account is not a YouTube channel."
            )
        return acc

    # 2. Check if a local youtube_upload record exists for this user and video_id
    upload = youtube_upload_repo.get_by_video_id_and_user(db, video_id, user_id)
    if upload:
        acc = social_account_repo.get_by_id(db, upload.social_account_id)
        if acc and acc.user_id == user_id:
            return acc

    # 3. Otherwise check user's connected YouTube channels
    user_accounts = social_account_repo.get_by_user_and_platform(db, user_id, "youtube")
    if not user_accounts:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No connected YouTube account found for your profile. Please connect your YouTube channel first."
        )

    # If single connected account, return it
    if len(user_accounts) == 1:
        return user_accounts[0]

    # For multiple channels without explicit account_id or DB record, test channel ID match
    for acc in user_accounts:
        try:
            token = youtube_service.get_valid_access_token_for_account(db, acc)
            details = youtube_service.get_video_details(token, video_id)
            if details.get("channel_id") == acc.account_id:
                return acc
        except Exception:
            continue

    return user_accounts[0]

@router.get("/videos/{video_id}", response_model=YouTubeVideoDetailResponse)
def get_youtube_video(
    video_id: str,
    social_account_id: Optional[int] = Query(None, description="Optional SocialAccount ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fetch existing YouTube video metadata for viewing and editing.
    Strictly tenant-isolated. Validates user ownership of the associated YouTube channel.
    Calls YouTube Data API v3 (GET videos.list with part=snippet,status).
    """
    account = _resolve_youtube_account_for_video(db, current_user.id, video_id, social_account_id)
    try:
        access_token = youtube_service.get_valid_access_token_for_account(db, account)
    except Exception as e:
        logger.error(f"[YOUTUBE_VIDEO] Authentication resolution failed for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Failed to authenticate with YouTube: {str(e)}"
        )

    try:
        video_data = youtube_service.get_video_details(access_token, video_id)
    except YouTubeAPIException as e:
        logger.error(f"[YOUTUBE_VIDEO] Error fetching video details for {video_id}: {e.message}")
        raise HTTPException(
            status_code=e.status_code if e.status_code and e.status_code >= 400 else 502,
            detail=f"YouTube video retrieval failed: {e.message}"
        )
    except Exception as e:
        logger.error(f"[YOUTUBE_VIDEO] Unexpected error fetching video {video_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve video details from YouTube."
        )

    return YouTubeVideoDetailResponse(
        video_id=video_data["video_id"],
        channel_id=video_data["channel_id"],
        channel_title=video_data.get("channel_title") or account.account_name,
        title=video_data["title"],
        description=video_data.get("description", ""),
        tags=video_data.get("tags", []),
        category_id=video_data.get("category_id"),
        privacy_status=video_data.get("privacy_status", "private"),
        made_for_kids=video_data.get("made_for_kids", False),
        thumbnail_url=video_data.get("thumbnail_url"),
        video_url=video_data.get("video_url"),
    )

@router.put("/videos/{video_id}", response_model=YouTubeVideoDetailResponse)
def update_youtube_video(
    video_id: str,
    payload: YouTubeVideoUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update metadata for an already-published YouTube video (title, description, tags, category, privacy, made-for-kids, thumbnail).
    Strictly tenant-isolated. Preserves video_id and never invokes the video upload/chunk engine.
    Fetches full resource first to ensure all required fields are safely merged before calling PUT videos.update.
    """
    account = _resolve_youtube_account_for_video(db, current_user.id, video_id, payload.social_account_id)
    try:
        access_token = youtube_service.get_valid_access_token_for_account(db, account)
    except Exception as e:
        logger.error(f"[YOUTUBE_VIDEO] Authentication resolution failed for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Failed to authenticate with YouTube: {str(e)}"
        )

    # Validate privacy status if supplied
    if payload.privacy_status and payload.privacy_status not in ("public", "private", "unlisted"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid privacy status. Allowed values are 'public', 'private', or 'unlisted'."
        )

    # 1. Update Video Metadata via YouTube Data API v3 (videos.update)
    update_dict = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else payload.dict(exclude_unset=True)
    try:
        updated_data = youtube_service.update_video_metadata(access_token, video_id, update_dict)
    except YouTubeAPIException as e:
        logger.error(f"[YOUTUBE_VIDEO] Error updating video metadata for {video_id}: {e.message}")
        raise HTTPException(
            status_code=e.status_code if e.status_code and e.status_code >= 400 else 502,
            detail=f"YouTube video update failed: {e.message}"
        )
    except Exception as e:
        logger.error(f"[YOUTUBE_VIDEO] Unexpected error updating video {video_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update video metadata on YouTube."
        )

    # 2. If a new trusted custom thumbnail was provided, apply it via existing thumbnail service
    thumb_url = payload.thumbnail_url
    if thumb_url:
        try:
            youtube_service.apply_thumbnail_from_storage(
                access_token=access_token,
                video_id=video_id,
                thumbnail_url=thumb_url,
            )
            updated_data["thumbnail_url"] = thumb_url
            logger.info(f"[YOUTUBE_VIDEO] Custom thumbnail updated for video {video_id}")
        except Exception as e:
            logger.warning(f"[YOUTUBE_VIDEO] Thumbnail application failed during video edit for {video_id}: {e}")

    # 3. Synchronize local database record if present
    youtube_upload_repo.update_metadata_by_video_id(
        db=db,
        video_id=video_id,
        user_id=current_user.id,
        title=updated_data.get("title"),
        description=updated_data.get("description"),
        privacy_status=updated_data.get("privacy_status"),
        thumbnail_url=thumb_url or updated_data.get("thumbnail_url"),
    )

    return YouTubeVideoDetailResponse(
        video_id=updated_data["video_id"],
        channel_id=updated_data["channel_id"],
        channel_title=updated_data.get("channel_title") or account.account_name,
        title=updated_data["title"],
        description=updated_data.get("description", ""),
        tags=updated_data.get("tags", []),
        category_id=updated_data.get("category_id"),
        privacy_status=updated_data.get("privacy_status", "private"),
        made_for_kids=updated_data.get("made_for_kids", False),
        thumbnail_url=updated_data.get("thumbnail_url"),
        video_url=updated_data.get("video_url"),
    )

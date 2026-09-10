import logging
import requests
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security_encryption import encrypt_token, decrypt_token, mask_token
from app.models.social_account import SocialAccount

logger = logging.getLogger(__name__)

class YouTubeOAuthException(Exception):
    """Exception raised for YouTube OAuth exchange/refresh errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}

class YouTubeChannelNotFoundException(Exception):
    """Exception raised when Google user does not own any YouTube channel."""
    pass

class YouTubeAPIException(Exception):
    """Exception raised for YouTube Data API v3 communication errors."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

class YouTubeService:
    GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GOOGLE_UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
    YOUTUBE_API_BASE_URL = "https://www.googleapis.com/youtube/v3"

    REQUIRED_YOUTUBE_SCOPES = [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube.readonly",
    ]

    def get_authorization_url(self, state: str) -> str:
        """
        Generate Google OAuth 2.0 Authorization URL for YouTube channel connection.
        Enforces offline access, consent prompt (to obtain refresh token), and minimum required scope.
        """
        params = {
            "client_id": settings.YOUTUBE_CLIENT_ID or "",
            "redirect_uri": settings.YOUTUBE_REDIRECT_URI,
            "response_type": "code",
            "scope": " ".join(self.REQUIRED_YOUTUBE_SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
            "include_granted_scopes": "true",
        }
        logger.info(
            f"[YOUTUBE_OAUTH] Generated authorization URL with redirect_uri={settings.YOUTUBE_REDIRECT_URI}, "
            f"scopes={self.REQUIRED_YOUTUBE_SCOPES}"
        )
        return f"{self.GOOGLE_AUTH_URL}?{urlencode(params)}"

    def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code with Google token endpoint for access and refresh tokens.
        Never exposes Client Secret to frontend or unmasked logs.
        """
        payload = {
            "code": code,
            "client_id": settings.YOUTUBE_CLIENT_ID,
            "client_secret": settings.YOUTUBE_CLIENT_SECRET,
            "redirect_uri": settings.YOUTUBE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        try:
            response = requests.post(self.GOOGLE_TOKEN_URL, data=payload, headers=headers, timeout=20)
            data = response.json()
        except Exception as e:
            logger.error(f"[YOUTUBE_OAUTH] Failed to reach Google token endpoint: {e}")
            raise YouTubeOAuthException(f"Failed to communicate with Google token service: {str(e)}")

        if response.status_code != 200:
            err_detail = data.get("error_description") or data.get("error") or "Unknown token exchange failure"
            logger.error(f"[YOUTUBE_OAUTH] Google token exchange rejected ({response.status_code}): {err_detail}")
            raise YouTubeOAuthException(f"Google authorization failed: {err_detail}", status_code=response.status_code, details=data)

        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        expires_in = data.get("expires_in", 3600)
        token_type = data.get("token_type", "Bearer")
        scope = data.get("scope", "")

        if not access_token:
            raise YouTubeOAuthException("No access token returned by Google OAuth endpoint.")

        logger.info(
            f"[YOUTUBE_OAUTH] Successfully exchanged authorization code for tokens. "
            f"access_token={mask_token(access_token)}, has_refresh_token={bool(refresh_token)}, expires_in={expires_in}s"
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": int(expires_in),
            "token_type": token_type,
            "scope": scope,
        }

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Use offline refresh token to obtain a fresh access token from Google.
        """
        payload = {
            "refresh_token": refresh_token,
            "client_id": settings.YOUTUBE_CLIENT_ID,
            "client_secret": settings.YOUTUBE_CLIENT_SECRET,
            "grant_type": "refresh_token",
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        try:
            response = requests.post(self.GOOGLE_TOKEN_URL, data=payload, headers=headers, timeout=20)
            data = response.json()
        except Exception as e:
            logger.error(f"[YOUTUBE_OAUTH] Failed to refresh Google token: {e}")
            raise YouTubeOAuthException(f"Failed to communicate with Google token refresh service: {str(e)}")

        if response.status_code != 200:
            err_detail = data.get("error_description") or data.get("error") or "Unknown token refresh failure"
            logger.error(f"[YOUTUBE_OAUTH] Google token refresh rejected ({response.status_code}): {err_detail}")
            raise YouTubeOAuthException(f"Token refresh failed: {err_detail}", status_code=response.status_code, details=data)

        new_access_token = data.get("access_token")
        expires_in = data.get("expires_in", 3600)
        token_type = data.get("token_type", "Bearer")

        if not new_access_token:
            raise YouTubeOAuthException("No access token returned in refresh response.")

        logger.info(f"[YOUTUBE_OAUTH] Successfully refreshed access token. expires_in={expires_in}s")
        return {
            "access_token": new_access_token,
            "expires_in": int(expires_in),
            "token_type": token_type,
        }

    def fetch_authenticated_channel(self, access_token: str) -> Dict[str, Any]:
        """
        Call YouTube Data API v3 (channels.list with mine=true) to retrieve authenticated user's YouTube channel.
        Retrieves: channel ID, channel title, channel thumbnails, uploads playlist ID, custom URL, and statistics.
        """
        url = f"{self.YOUTUBE_API_BASE_URL}/channels"
        params = {
            "part": "snippet,contentDetails,statistics",
            "mine": "true",
        }
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

        try:
            response = requests.get(url, params=params, headers=headers, timeout=20)
            data = response.json()
        except Exception as e:
            logger.error(f"[YOUTUBE_API] Failed to fetch channel details: {e}")
            raise YouTubeAPIException(f"Failed to communicate with YouTube API: {str(e)}")

        if response.status_code != 200:
            err_msg = data.get("error", {}).get("message") or f"HTTP {response.status_code}"
            logger.error(f"[YOUTUBE_API] channels.list error ({response.status_code}): {err_msg}")
            raise YouTubeAPIException(f"YouTube Data API error: {err_msg}", status_code=response.status_code)

        items = data.get("items", [])
        if not items:
            logger.warning("[YOUTUBE_API] Google account authorized successfully, but 0 YouTube channels were found.")
            raise YouTubeChannelNotFoundException(
                "Google account authorized successfully, but no YouTube channel was found. "
                "Please make sure your Google account has a YouTube channel created at youtube.com."
            )

        channel = items[0]
        channel_id = channel.get("id")
        snippet = channel.get("snippet", {})
        title = snippet.get("title", "YouTube Channel")
        custom_url = snippet.get("customUrl")
        thumbnails = snippet.get("thumbnails", {})
        logo_url = (
            thumbnails.get("high", {}).get("url")
            or thumbnails.get("medium", {}).get("url")
            or thumbnails.get("default", {}).get("url")
        )

        content_details = channel.get("contentDetails", {})
        uploads_playlist_id = content_details.get("relatedPlaylists", {}).get("uploads")

        statistics = channel.get("statistics", {})
        subscriber_count = statistics.get("subscriberCount")
        video_count = statistics.get("videoCount")
        view_count = statistics.get("viewCount")

        logger.info(
            f"[YOUTUBE_API] Discovered YouTube channel: id={channel_id}, title='{title}', "
            f"custom_url={custom_url}, uploads_playlist={uploads_playlist_id}"
        )

        return {
            "channel_id": channel_id,
            "title": title,
            "custom_url": custom_url,
            "logo_url": logo_url,
            "uploads_playlist_id": uploads_playlist_id,
            "subscriber_count": subscriber_count,
            "video_count": video_count,
            "view_count": view_count,
            "raw_snippet": snippet,
        }

    def get_valid_access_token_for_account(self, db: Session, account: SocialAccount) -> str:
        """
        Get a valid, unexpired access token for a connected YouTube SocialAccount.
        Automatically refreshes the token using the encrypted refresh token if expired or near expiry (< 5 mins).
        """
        if account.platform != "youtube":
            raise ValueError(f"Account {account.id} is not a YouTube account (platform={account.platform}).")

        now_utc = datetime.now(timezone.utc)
        needs_refresh = False

        if not account.expires_at:
            needs_refresh = True
        else:
            exp = account.expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if (exp - now_utc) < timedelta(minutes=5):
                needs_refresh = True

        if not needs_refresh:
            decrypted = decrypt_token(account.access_token)
            if decrypted:
                return decrypted

        # Token needs refresh
        meta = account.metadata_json or {}
        enc_refresh = meta.get("refresh_token")
        if not enc_refresh:
            logger.error(f"[YOUTUBE_SERVICE] Cannot refresh token for account {account.id}: No refresh token stored.")
            raise YouTubeOAuthException("No refresh token stored for this YouTube channel. Please reconnect the account.")

        plain_refresh = decrypt_token(enc_refresh)
        if not plain_refresh:
            raise YouTubeOAuthException("Failed to decrypt YouTube refresh token.")

        refresh_data = self.refresh_access_token(plain_refresh)
        new_access_token = refresh_data["access_token"]
        expires_in = refresh_data.get("expires_in", 3600)

        account.access_token = encrypt_token(new_access_token)
        account.expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        account.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(account)

        logger.info(f"[YOUTUBE_SERVICE] Successfully updated refreshed access token for account {account.id}")
        return new_access_token

    def initiate_resumable_upload(
        self,
        access_token: str,
        title: str,
        description: str = "",
        privacy_status: str = "private",
        mime_type: str = "video/mp4",
        file_size_bytes: Optional[int] = None,
        tags: Optional[List[str]] = None,
        category_id: Optional[str] = None,
        made_for_kids: Optional[bool] = False,
    ) -> str:
        """
        Create a YouTube resumable upload session on Google servers.
        Never logs or leaks access_token. Returns the session Location URL.
        """
        url = f"{self.GOOGLE_UPLOAD_URL}?uploadType=resumable&part=snippet,status"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": mime_type,
        }
        if file_size_bytes:
            headers["X-Upload-Content-Length"] = str(file_size_bytes)

        snippet_data: Dict[str, Any] = {
            "title": title,
            "description": description or "",
        }
        if tags and len(tags) > 0:
            snippet_data["tags"] = tags
        if category_id:
            snippet_data["categoryId"] = str(category_id)

        status_data: Dict[str, Any] = {
            "privacyStatus": privacy_status or "private",
        }
        if made_for_kids is not None:
            status_data["selfDeclaredMadeForKids"] = bool(made_for_kids)

        body = {
            "snippet": snippet_data,
            "status": status_data,
        }

        try:
            response = requests.post(url, json=body, headers=headers, timeout=30)
        except Exception as e:
            logger.error(f"[YOUTUBE_UPLOAD] Network error initiating resumable upload: {e}")
            raise YouTubeAPIException(f"Failed to connect to YouTube upload service: {str(e)}")

        if response.status_code != 200:
            err_text = response.text[:200]
            try:
                err_data = response.json()
                err_text = err_data.get("error", {}).get("message") or err_text
            except Exception:
                pass
            logger.error(f"[YOUTUBE_UPLOAD] Resumable upload init failed ({response.status_code}): {err_text}")
            raise YouTubeAPIException(f"YouTube upload initialization error: {err_text}", status_code=response.status_code)

        location = response.headers.get("Location")
        if not location:
            logger.error("[YOUTUBE_UPLOAD] YouTube returned HTTP 200 without Location header.")
            raise YouTubeAPIException("YouTube did not return a Location header for resumable upload session.", status_code=502)

        logger.info(f"[YOUTUBE_UPLOAD] Successfully created resumable upload session for video '{title}'.")
        return location

    def upload_resumable_chunk(
        self,
        resumable_session_url: str,
        chunk_bytes: bytes,
        content_range: str,
        mime_type: str = "video/mp4",
        access_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Forward a single binary chunk to YouTube resumable session URL.
        Handles HTTP 308 (Resume Incomplete) with Range header, and HTTP 200/201 (Completed).
        """
        headers = {
            "Content-Type": mime_type,
            "Content-Range": content_range,
            "Content-Length": str(len(chunk_bytes)),
        }
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"

        try:
            response = requests.put(resumable_session_url, data=chunk_bytes, headers=headers, timeout=60)
        except Exception as e:
            logger.error(f"[YOUTUBE_UPLOAD] Network error during chunk upload: {e}")
            raise YouTubeAPIException(f"Failed to transmit chunk to YouTube: {str(e)}")

        # HTTP 308: Resume Incomplete (Standard YouTube resumable response for intermediate chunks)
        if response.status_code == 308:
            range_header = response.headers.get("Range", "")
            last_byte = None
            if range_header and "-" in range_header:
                parts = range_header.replace("bytes=", "").split("-")
                if len(parts) == 2 and parts[1].isdigit():
                    last_byte = int(parts[1])
            next_offset = (last_byte + 1) if last_byte is not None else None

            logger.info(f"[YOUTUBE_UPLOAD] Chunk accepted (HTTP 308). Range: {range_header}, next_byte_offset: {next_offset}")
            return {
                "status": "RESUME_INCOMPLETE",
                "http_status": 308,
                "range_header": range_header,
                "last_byte_received": last_byte,
                "next_byte_offset": next_offset,
                "is_complete": False,
            }

        # HTTP 200 or 201: Final chunk completed
        if response.status_code in (200, 201):
            try:
                data = response.json()
            except Exception:
                data = {}
            video_id = data.get("id")
            logger.info(f"[YOUTUBE_UPLOAD] Upload complete (HTTP {response.status_code}). Video ID: {video_id}")
            return {
                "status": "COMPLETED",
                "http_status": response.status_code,
                "video_id": video_id,
                "video_url": f"https://www.youtube.com/watch?v={video_id}" if video_id else None,
                "is_complete": True,
            }

        # Other status codes: 4xx, 5xx
        err_msg = f"HTTP {response.status_code}"
        try:
            err_data = response.json()
            err_msg = err_data.get("error", {}).get("message") or err_msg
        except Exception:
            pass
        logger.error(f"[YOUTUBE_UPLOAD] Chunk upload rejected by YouTube ({response.status_code}): {err_msg}")
        raise YouTubeAPIException(f"YouTube upload rejected: {err_msg}", status_code=response.status_code)

    def query_resumable_status(
        self,
        resumable_session_url: str,
        total_file_size: int,
        mime_type: str = "video/mp4",
        access_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Query YouTube for current confirmed uploaded range (Google Resumable Upload protocol).
        Uses PUT with Content-Range: bytes */total_size and empty body.
        """
        headers = {
            "Content-Type": mime_type,
            "Content-Range": f"bytes */{total_file_size}",
            "Content-Length": "0",
        }
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"

        try:
            response = requests.put(resumable_session_url, headers=headers, timeout=30)
        except Exception as e:
            logger.error(f"[YOUTUBE_UPLOAD] Error querying upload status: {e}")
            raise YouTubeAPIException(f"Failed to query upload status: {str(e)}")

        if response.status_code == 308:
            range_header = response.headers.get("Range", "")
            last_byte = None
            if range_header and "-" in range_header:
                parts = range_header.replace("bytes=", "").split("-")
                if len(parts) == 2 and parts[1].isdigit():
                    last_byte = int(parts[1])
            next_offset = (last_byte + 1) if last_byte is not None else 0

            return {
                "status": "RESUME_INCOMPLETE",
                "http_status": 308,
                "range_header": range_header,
                "last_byte_received": last_byte,
                "next_byte_offset": next_offset,
                "is_complete": False,
            }

        if response.status_code in (200, 201):
            data = response.json() if response.text else {}
            video_id = data.get("id")
            return {
                "status": "COMPLETED",
                "http_status": response.status_code,
                "video_id": video_id,
                "video_url": f"https://www.youtube.com/watch?v={video_id}" if video_id else None,
                "is_complete": True,
            }

        raise YouTubeAPIException(f"Unexpected status response: HTTP {response.status_code}", status_code=response.status_code)

    def fetch_video_processing_status(self, access_token: str, video_id: str) -> Dict[str, Any]:
        """
        Query YouTube Data API v3 (videos.list with part=processingDetails,status,snippet)
        to monitor background video processing (encoding/quality check) after upload completion.
        Never logs access_token.
        """
        url = f"{self.YOUTUBE_API_BASE_URL}/videos"
        params = {
            "part": "processingDetails,status,snippet",
            "id": video_id,
        }
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

        try:
            response = requests.get(url, params=params, headers=headers, timeout=20)
            data = response.json()
        except Exception as e:
            logger.error(f"[YOUTUBE_PROCESSING] Error querying video processing status for {video_id}: {e}")
            raise YouTubeAPIException(f"Failed to query video processing details: {str(e)}")

        if response.status_code != 200:
            err_msg = data.get("error", {}).get("message") or f"HTTP {response.status_code}"
            logger.error(f"[YOUTUBE_PROCESSING] videos.list error ({response.status_code}): {err_msg}")
            raise YouTubeAPIException(f"YouTube processing query error: {err_msg}", status_code=response.status_code)

        items = data.get("items", [])
        if not items:
            logger.warning(f"[YOUTUBE_PROCESSING] Video {video_id} not found in videos.list.")
            return {
                "video_id": video_id,
                "found": False,
                "processing_status": "unknown",
                "upload_status": "unknown",
                "is_ready": False,
                "is_failed": False,
                "video_url": f"https://www.youtube.com/watch?v={video_id}",
            }

        item = items[0]
        processing_details = item.get("processingDetails", {})
        status_info = item.get("status", {})
        snippet = item.get("snippet", {})

        proc_status = processing_details.get("processingStatus")  # "processing", "succeeded", "failed", "terminated"
        proc_failure_reason = processing_details.get("processingFailureReason")
        upload_status = status_info.get("uploadStatus")  # "uploaded", "processed", "failed", "rejected"
        rejection_reason = status_info.get("rejectionReason")
        privacy_status = status_info.get("privacyStatus")

        is_ready = proc_status == "succeeded" or upload_status == "processed"
        is_failed = proc_status in ("failed", "terminated") or upload_status in ("failed", "rejected")
        failure_reason = proc_failure_reason or rejection_reason

        return {
            "video_id": video_id,
            "found": True,
            "title": snippet.get("title"),
            "processing_status": proc_status or upload_status or "processing",
            "processing_failure_reason": failure_reason,
            "upload_status": upload_status,
            "privacy_status": privacy_status,
            "is_ready": is_ready,
            "is_failed": is_failed,
            "video_url": f"https://www.youtube.com/watch?v={video_id}",
        }

    def cancel_resumable_upload_session(
        self,
        resumable_session_url: str,
        total_file_size: int,
        access_token: Optional[str] = None,
    ) -> bool:
        """
        Best-effort remote notification to Google's resumable session URI via DELETE (Google resumable upload spec).
        Does not raise on 4xx/5xx because application-level cancellation is authoritative.
        """
        headers = {
            "Content-Length": "0",
            "Content-Range": f"bytes */{total_file_size}",
        }
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"

        try:
            response = requests.delete(resumable_session_url, headers=headers, timeout=10)
            logger.info(f"[YOUTUBE_UPLOAD] Remote session cancellation returned HTTP {response.status_code}")
            return response.status_code in (200, 404, 410)
        except Exception as e:
            logger.warning(f"[YOUTUBE_UPLOAD] Remote session cancellation request failed (best-effort): {e}")
            return False

youtube_service = YouTubeService()

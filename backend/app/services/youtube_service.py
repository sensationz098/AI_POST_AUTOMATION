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
    YOUTUBE_API_BASE_URL = "https://www.googleapis.com/youtube/v3"

    REQUIRED_YOUTUBE_SCOPES = [
        "https://www.googleapis.com/auth/youtube.upload",
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

youtube_service = YouTubeService()

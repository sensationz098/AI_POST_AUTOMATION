import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

from app.models.user import User
from app.models.social_account import SocialAccount
from app.models.brand import BrandProfile
from app.core.redis import set_oauth_state, pop_oauth_state
from app.core.security_encryption import encrypt_token, decrypt_token
from app.services.youtube_service import (
    youtube_service,
    YouTubeOAuthException,
    YouTubeChannelNotFoundException,
    YouTubeAPIException,
)

def get_auth_headers(client, email="yt_user@socialai.com"):
    reg_payload = {
        "email": email,
        "password": "Password123!",
        "full_name": "YouTube Creator",
        "role": "Editor"
    }
    client.post("/api/v1/auth/register", json=reg_payload)
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_youtube_oauth_start_requires_authentication(client):
    """GET /api/v1/youtube/oauth/start must return 401 Unauthorized without authentication."""
    res = client.get("/api/v1/youtube/oauth/start", follow_redirects=False)
    assert res.status_code == 401

def test_youtube_oauth_scopes_configuration():
    """Verify that REQUIRED_YOUTUBE_SCOPES includes both upload and readonly scopes."""
    assert "https://www.googleapis.com/auth/youtube.upload" in youtube_service.REQUIRED_YOUTUBE_SCOPES
    assert "https://www.googleapis.com/auth/youtube.readonly" in youtube_service.REQUIRED_YOUTUBE_SCOPES
    assert "https://www.googleapis.com/auth/youtube" in youtube_service.REQUIRED_YOUTUBE_SCOPES
    assert len(youtube_service.REQUIRED_YOUTUBE_SCOPES) >= 3

def test_youtube_oauth_start_generates_state_and_redirects(client):
    """GET /api/v1/youtube/oauth/start generates state in Redis and redirects to Google OAuth endpoint."""
    headers = get_auth_headers(client, "yt_start@socialai.com")

    with patch("app.core.config.settings.YOUTUBE_CLIENT_ID", "mock_id_123"), \
         patch("app.core.config.settings.YOUTUBE_CLIENT_SECRET", "mock_secret_456"):
        res = client.get("/api/v1/youtube/oauth/start", headers=headers, follow_redirects=False)
    assert res.status_code == 307
    location = res.headers.get("location", "")

    assert "https://accounts.google.com/o/oauth2/v2/auth" in location
    assert "youtube.upload" in location
    assert "youtube.readonly" in location
    assert "youtube" in location
    assert "access_type=offline" in location
    assert "prompt=consent" in location
    assert "response_type=code" in location
    assert "state=" in location

def test_youtube_oauth_start_json_mode(client):
    """GET /api/v1/youtube/oauth/start?redirect=false returns JSON with authorization URL and state token."""
    headers = get_auth_headers(client, "yt_json@socialai.com")

    with patch("app.core.config.settings.YOUTUBE_CLIENT_ID", "mock_id_123"), \
         patch("app.core.config.settings.YOUTUBE_CLIENT_SECRET", "mock_secret_456"):
        res = client.get("/api/v1/youtube/oauth/start?redirect=false", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "authorization_url" in data
    assert "state" in data
    assert "https://accounts.google.com/o/oauth2/v2/auth" in data["authorization_url"]
    assert "youtube.upload" in data["authorization_url"]
    assert "youtube.readonly" in data["authorization_url"]
    assert "youtube" in data["authorization_url"]
    assert "access_type=offline" in data["authorization_url"]
    assert "prompt=consent" in data["authorization_url"]
    assert len(data["state"]) > 20

def test_youtube_oauth_callback_rejects_invalid_or_expired_state(client):
    """OAuth callback must reject missing, invalid, or expired state tokens."""
    res = client.get("/api/v1/youtube/oauth/callback?code=mock_code&state=invalid_state", follow_redirects=False)
    assert res.status_code == 307
    location = res.headers.get("location", "")
    assert "error=" in location
    assert "state" in location.lower() or "expired" in location.lower()

def test_youtube_oauth_callback_handles_user_denial(client):
    """OAuth callback must cleanly handle user cancellation / error returned by Google."""
    res = client.get("/api/v1/youtube/oauth/callback?error=access_denied&error_description=User+denied+consent", follow_redirects=False)
    assert res.status_code == 307
    location = res.headers.get("location", "")
    assert "error=" in location
    assert "denied" in location.lower()

def test_youtube_oauth_callback_handles_missing_code(client):
    """OAuth callback must handle missing code parameter with valid state."""
    state_token = "valid_state_missing_code_123"
    set_oauth_state(state_token, user_id=1, ttl_seconds=900)

    res = client.get(f"/api/v1/youtube/oauth/callback?state={state_token}", follow_redirects=False)
    assert res.status_code == 307
    location = res.headers.get("location", "")
    assert "error=" in location
    assert "code" in location.lower()

def test_youtube_oauth_callback_success(client, db_session):
    """OAuth callback successfully exchanges code, discovers channel, encrypts tokens, and persists account."""
    headers = get_auth_headers(client, "yt_success@socialai.com")
    user = db_session.query(User).filter(User.email == "yt_success@socialai.com").first()
    assert user is not None

    state_token = "valid_state_token_success_456"
    set_oauth_state(state_token, user_id=user.id, ttl_seconds=900)

    mock_tokens = {
        "access_token": "ya29.mock_access_token_12345",
        "refresh_token": "1//mock_refresh_token_67890",
        "expires_in": 3600,
        "token_type": "Bearer",
        "scope": (
            "https://www.googleapis.com/auth/youtube.upload "
            "https://www.googleapis.com/auth/youtube.readonly "
            "https://www.googleapis.com/auth/youtube"
        ),
    }

    mock_channel = {
        "channel_id": "UC1234567890abcdef",
        "title": "Tech Innovations Channel",
        "custom_url": "@techinnovations",
        "logo_url": "https://yt3.ggpht.com/mock_avatar.jpg",
        "uploads_playlist_id": "UU1234567890abcdef",
        "subscriber_count": "15400",
        "video_count": "42",
        "view_count": "890000",
    }

    with patch("app.services.youtube_service.youtube_service.exchange_code_for_tokens", return_value=mock_tokens), \
         patch("app.services.youtube_service.youtube_service.fetch_authenticated_channel", return_value=mock_channel):
        res = client.get(f"/api/v1/youtube/oauth/callback?code=valid_google_code&state={state_token}", follow_redirects=False)

    assert res.status_code == 307
    location = res.headers.get("location", "")
    assert "youtube_connected=true" in location
    assert "Tech" in location and "Channel" in location
    assert "UC1234567890abcdef" in location

    # Verify SocialAccount in database
    account = db_session.query(SocialAccount).filter(
        SocialAccount.user_id == user.id,
        SocialAccount.platform == "youtube",
        SocialAccount.account_id == "UC1234567890abcdef"
    ).first()

    assert account is not None
    assert account.account_name == "Tech Innovations Channel"
    assert account.logo_url == "https://yt3.ggpht.com/mock_avatar.jpg"
    assert account.status == "CONNECTED"
    assert account.token_type == "Bearer"
    assert account.expires_at is not None

    # Verify access token is encrypted at rest and can be decrypted
    assert account.access_token.startswith("enc_gAAAAA")
    assert decrypt_token(account.access_token) == "ya29.mock_access_token_12345"

    # Verify refresh token is encrypted in metadata_json
    meta = account.metadata_json or {}
    assert "refresh_token" in meta
    assert meta["refresh_token"].startswith("enc_gAAAAA")
    assert decrypt_token(meta["refresh_token"]) == "1//mock_refresh_token_67890"
    assert meta["custom_url"] == "@techinnovations"
    assert meta["uploads_playlist_id"] == "UU1234567890abcdef"
    assert meta["subscriber_count"] == "15400"

    # Verify BrandProfile was created
    brand = db_session.query(BrandProfile).filter(
        BrandProfile.user_id == user.id,
        BrandProfile.name == "Tech Innovations Channel"
    ).first()
    assert brand is not None

def test_youtube_oauth_callback_no_channel_found(client, db_session):
    """OAuth callback must handle case when Google account has no YouTube channel."""
    headers = get_auth_headers(client, "yt_no_chan@socialai.com")
    user = db_session.query(User).filter(User.email == "yt_no_chan@socialai.com").first()

    state_token = "valid_state_no_channel_789"
    set_oauth_state(state_token, user_id=user.id, ttl_seconds=900)

    mock_tokens = {
        "access_token": "ya29.mock_token_no_chan",
        "refresh_token": "1//mock_refresh_no_chan",
        "expires_in": 3600,
        "token_type": "Bearer",
    }

    with patch("app.services.youtube_service.youtube_service.exchange_code_for_tokens", return_value=mock_tokens), \
         patch("app.services.youtube_service.youtube_service.fetch_authenticated_channel", side_effect=YouTubeChannelNotFoundException("No YouTube channel found.")):
        res = client.get(f"/api/v1/youtube/oauth/callback?code=code_no_chan&state={state_token}", follow_redirects=False)

    assert res.status_code == 307
    location = res.headers.get("location", "")
    assert "error=" in location
    assert "No" in location and "channel" in location

def test_youtube_oauth_duplicate_reconnection(client, db_session):
    """Reconnecting the same channel updates access token and preserves refresh token if not returned by Google."""
    headers = get_auth_headers(client, "yt_dup@socialai.com")
    user = db_session.query(User).filter(User.email == "yt_dup@socialai.com").first()

    # Create existing account with encrypted refresh token
    existing_acc = SocialAccount(
        user_id=user.id,
        platform="youtube",
        account_id="UC_DUPLICATE_TEST_999",
        account_name="Duplicate Test Channel",
        access_token=encrypt_token("old_access_token"),
        token_type="Bearer",
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        status="CONNECTED",
        metadata_json={"refresh_token": encrypt_token("initial_refresh_token_xyz")}
    )
    db_session.add(existing_acc)
    db_session.commit()

    state_token = "state_reconnect_test_111"
    set_oauth_state(state_token, user_id=user.id, ttl_seconds=900)

    # Google re-auth response without new refresh_token
    mock_tokens = {
        "access_token": "new_refreshed_access_token_456",
        "refresh_token": None,
        "expires_in": 7200,
        "token_type": "Bearer",
        "scope": "https://www.googleapis.com/auth/youtube.upload",
    }

    mock_channel = {
        "channel_id": "UC_DUPLICATE_TEST_999",
        "title": "Duplicate Test Channel Renamed",
        "logo_url": "https://yt3.ggpht.com/new_avatar.jpg",
    }

    with patch("app.services.youtube_service.youtube_service.exchange_code_for_tokens", return_value=mock_tokens), \
         patch("app.services.youtube_service.youtube_service.fetch_authenticated_channel", return_value=mock_channel):
        res = client.get(f"/api/v1/youtube/oauth/callback?code=reauth_code&state={state_token}", follow_redirects=False)

    assert res.status_code == 307

    # Verify only 1 account exists
    accounts = db_session.query(SocialAccount).filter(
        SocialAccount.user_id == user.id,
        SocialAccount.platform == "youtube",
        SocialAccount.account_id == "UC_DUPLICATE_TEST_999"
    ).all()
    assert len(accounts) == 1

    updated = accounts[0]
    assert updated.account_name == "Duplicate Test Channel Renamed"
    assert decrypt_token(updated.access_token) == "new_refreshed_access_token_456"
    assert decrypt_token(updated.metadata_json.get("refresh_token")) == "initial_refresh_token_xyz"

def test_youtube_tenant_isolation(client, db_session):
    """User A cannot access User B's YouTube accounts."""
    headers_a = get_auth_headers(client, "user_a@socialai.com")
    headers_b = get_auth_headers(client, "user_b@socialai.com")
    user_a = db_session.query(User).filter(User.email == "user_a@socialai.com").first()
    user_b = db_session.query(User).filter(User.email == "user_b@socialai.com").first()

    # Add account for User A
    acc_a = SocialAccount(
        user_id=user_a.id,
        platform="youtube",
        account_id="UC_USER_A_CHANNEL",
        account_name="User A Gaming",
        access_token=encrypt_token("tok_a"),
        status="CONNECTED"
    )
    db_session.add(acc_a)
    db_session.commit()

    # User A sees account
    res_a = client.get("/api/v1/youtube/channels", headers=headers_a)
    assert res_a.status_code == 200
    assert len(res_a.json()) == 1
    assert res_a.json()[0]["account_id"] == "UC_USER_A_CHANNEL"

    # User B sees 0 accounts
    res_b = client.get("/api/v1/youtube/channels", headers=headers_b)
    assert res_b.status_code == 200
    assert len(res_b.json()) == 0

    # User B also sees 0 in generic /social-accounts/
    res_b_social = client.get("/api/v1/social-accounts/", headers=headers_b)
    assert res_b_social.status_code == 200
    assert len(res_b_social.json()) == 0

def test_youtube_token_refresh_service_logic(db_session):
    """youtube_service.get_valid_access_token_for_account refreshes expired token and commits to DB."""
    user = User(email="yt_refresh_test@socialai.com", hashed_password="pw", full_name="YT", role="Editor")
    db_session.add(user)
    db_session.commit()

    account = SocialAccount(
        user_id=user.id,
        platform="youtube",
        account_id="UC_REFRESH_CHANNEL",
        account_name="Refresh Channel",
        access_token=encrypt_token("expired_access_token"),
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=10),
        status="CONNECTED",
        metadata_json={"refresh_token": encrypt_token("valid_refresh_token_abc")}
    )
    db_session.add(account)
    db_session.commit()

    mock_refresh_resp = {
        "access_token": "fresh_new_access_token_xyz",
        "expires_in": 3600,
        "token_type": "Bearer",
    }

    with patch.object(youtube_service, "refresh_access_token", return_value=mock_refresh_resp):
        token = youtube_service.get_valid_access_token_for_account(db_session, account)

    assert token == "fresh_new_access_token_xyz"
    assert decrypt_token(account.access_token) == "fresh_new_access_token_xyz"
    exp = account.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    assert exp > datetime.now(timezone.utc)


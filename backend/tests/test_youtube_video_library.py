import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

from app.models.user import User
from app.models.social_account import SocialAccount
from app.core.security_encryption import encrypt_token
from app.services.youtube_service import (
    youtube_service,
    YouTubeAPIException,
)


def get_auth_headers(client, email="yt_lib_user@socialai.com"):
    reg_payload = {
        "email": email,
        "password": "Password123!",
        "full_name": "YouTube Library User",
        "role": "Editor"
    }
    client.post("/api/v1/auth/register", json=reg_payload)
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_mock_youtube_account(db_session, user_id, account_id="UC_LIB_CHAN_01", platform="youtube", metadata_json=None):
    effective_meta = metadata_json if metadata_json is not None else {
        "refresh_token": encrypt_token("mock_lib_refresh_token"),
        "uploads_playlist_id": "UU_LIB_CHAN_01",
    }
    acc = SocialAccount(
        user_id=user_id,
        platform=platform,
        account_id=account_id,
        account_name="Library Test Channel",
        access_token=encrypt_token("mock_lib_access_token"),
        token_type="Bearer",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        status="CONNECTED",
        metadata_json=effective_meta
    )
    db_session.add(acc)
    db_session.commit()
    db_session.refresh(acc)
    return acc


# ─── 1. Authentication & Security Tests ───────────────────────────────────────

def test_list_videos_requires_auth(client):
    """GET /api/v1/youtube/videos returns 401 without authentication."""
    res = client.get("/api/v1/youtube/videos")
    assert res.status_code == 401


def test_list_videos_requires_connected_account(client, db_session):
    """User without a connected YouTube channel receives 403 Forbidden."""
    headers = get_auth_headers(client, "no_yt_channel@socialai.com")
    res = client.get("/api/v1/youtube/videos", headers=headers)
    assert res.status_code == 403
    assert "No connected YouTube account found" in res.json()["detail"]


def test_list_videos_cross_tenant_isolation(client, db_session):
    """User B cannot specify or access User A's connected YouTube channel."""
    user_a = User(email="user_a_lib@socialai.com", hashed_password="pw", full_name="User A Lib", role="Editor")
    db_session.add(user_a)
    db_session.commit()
    db_session.refresh(user_a)

    acc_a = create_mock_youtube_account(db_session, user_a.id, account_id="UC_USER_A_LIB")

    # User B logs in
    headers_b = get_auth_headers(client, "user_b_lib@socialai.com")

    # User B tries to pass social_account_id belonging to User A
    res = client.get(f"/api/v1/youtube/videos?social_account_id={acc_a.id}", headers=headers_b)
    assert res.status_code == 404
    assert "access denied" in res.json()["detail"].lower()


# ─── 2. Channel Video Listing & Details Resolution ────────────────────────────

def test_list_channel_videos_success(client, db_session):
    """Authenticated user successfully retrieves channel videos with metadata."""
    headers = get_auth_headers(client, "happy_lib_user@socialai.com")
    user = db_session.query(User).filter(User.email == "happy_lib_user@socialai.com").first()
    create_mock_youtube_account(db_session, user.id)

    mock_playlist_items = {
        "items": [
            {
                "snippet": {
                    "title": "Tutorial Video 1",
                    "description": "First test video tutorial",
                    "publishedAt": "2026-09-01T10:00:00Z",
                    "channelId": "UC_LIB_CHAN_01",
                    "channelTitle": "Library Test Channel",
                    "thumbnails": {
                        "high": {"url": "https://i.ytimg.com/vi/vid_001/hqdefault.jpg"}
                    }
                },
                "contentDetails": {
                    "videoId": "vid_001"
                }
            },
            {
                "snippet": {
                    "title": "Tutorial Video 2",
                    "description": "Second test video tutorial",
                    "publishedAt": "2026-09-05T12:00:00Z",
                    "channelId": "UC_LIB_CHAN_01",
                    "channelTitle": "Library Test Channel",
                    "thumbnails": {
                        "maxres": {"url": "https://i.ytimg.com/vi/vid_002/maxresdefault.jpg"}
                    }
                },
                "contentDetails": {
                    "videoId": "vid_002"
                }
            }
        ],
        "nextPageToken": "CDIQAA",
        "prevPageToken": None,
        "pageInfo": {
            "totalResults": 42,
            "resultsPerPage": 2
        }
    }

    mock_video_details = {
        "items": [
            {
                "id": "vid_001",
                "snippet": {
                    "title": "Tutorial Video 1",
                    "description": "First test video tutorial",
                    "publishedAt": "2026-09-01T10:00:00Z",
                    "channelId": "UC_LIB_CHAN_01",
                    "channelTitle": "Library Test Channel",
                    "thumbnails": {
                        "high": {"url": "https://i.ytimg.com/vi/vid_001/hqdefault.jpg"}
                    }
                },
                "status": {
                    "privacyStatus": "public",
                    "uploadStatus": "processed"
                }
            },
            {
                "id": "vid_002",
                "snippet": {
                    "title": "Tutorial Video 2",
                    "description": "Second test video tutorial",
                    "publishedAt": "2026-09-05T12:00:00Z",
                    "channelId": "UC_LIB_CHAN_01",
                    "channelTitle": "Library Test Channel",
                    "thumbnails": {
                        "maxres": {"url": "https://i.ytimg.com/vi/vid_002/maxresdefault.jpg"}
                    }
                },
                "status": {
                    "privacyStatus": "unlisted",
                    "uploadStatus": "processed"
                }
            }
        ]
    }

    def mock_requests_get(url, *args, **kwargs):
        mock_res = MagicMock()
        mock_res.status_code = 200
        if "playlistItems" in url:
            mock_res.json.return_value = mock_playlist_items
        elif "videos" in url:
            mock_res.json.return_value = mock_video_details
        else:
            mock_res.json.return_value = {}
        return mock_res

    with patch("requests.get", side_effect=mock_requests_get):
        res = client.get("/api/v1/youtube/videos?limit=20", headers=headers)

    assert res.status_code == 200
    data = res.json()
    assert "videos" in data
    assert len(data["videos"]) == 2
    assert data["next_page_token"] == "CDIQAA"
    assert data["prev_page_token"] is None
    assert data["total_results"] == 42
    assert data["channel_id"] == "UC_LIB_CHAN_01"

    # Verify first video properties
    v1 = data["videos"][0]
    assert v1["video_id"] == "vid_001"
    assert v1["title"] == "Tutorial Video 1"
    assert v1["privacy_status"] == "public"
    assert v1["thumbnail_url"] == "https://i.ytimg.com/vi/vid_001/hqdefault.jpg"
    assert v1["video_url"] == "https://www.youtube.com/watch?v=vid_001"

    # Verify second video properties
    v2 = data["videos"][1]
    assert v2["video_id"] == "vid_002"
    assert v2["title"] == "Tutorial Video 2"
    assert v2["privacy_status"] == "unlisted"
    assert v2["thumbnail_url"] == "https://i.ytimg.com/vi/vid_002/maxresdefault.jpg"


def test_list_channel_videos_auto_discovers_uploads_playlist(client, db_session):
    """If metadata_json lacks uploads_playlist_id, calls channels.list to discover it."""
    headers = get_auth_headers(client, "discover_user@socialai.com")
    user = db_session.query(User).filter(User.email == "discover_user@socialai.com").first()
    # Account without uploads_playlist_id in metadata
    create_mock_youtube_account(db_session, user.id, account_id="UC_DISCOVER", metadata_json={})

    mock_channel_data = {
        "channel_id": "UC_DISCOVER",
        "title": "Discovered Channel",
        "uploads_playlist_id": "UU_DISCOVER",
    }

    mock_playlist_items = {
        "items": [
            {
                "snippet": {
                    "title": "Discovered Video",
                    "channelId": "UC_DISCOVER",
                },
                "contentDetails": {"videoId": "vid_disc_99"}
            }
        ],
        "pageInfo": {"totalResults": 1}
    }

    mock_video_details = {
        "items": [
            {
                "id": "vid_disc_99",
                "snippet": {"title": "Discovered Video", "channelId": "UC_DISCOVER"},
                "status": {"privacyStatus": "private"}
            }
        ]
    }

    def mock_requests_get(url, *args, **kwargs):
        mock_res = MagicMock()
        mock_res.status_code = 200
        if "playlistItems" in url:
            mock_res.json.return_value = mock_playlist_items
        elif "videos" in url:
            mock_res.json.return_value = mock_video_details
        else:
            mock_res.json.return_value = {}
        return mock_res

    with patch.object(youtube_service, "fetch_authenticated_channel", return_value=mock_channel_data) as mock_fetch:
        with patch("requests.get", side_effect=mock_requests_get):
            res = client.get("/api/v1/youtube/videos", headers=headers)

    assert res.status_code == 200
    mock_fetch.assert_called_once()
    assert len(res.json()["videos"]) == 1
    assert res.json()["videos"][0]["video_id"] == "vid_disc_99"


def test_list_channel_videos_pagination(client, db_session):
    """Passing page_token forwards token to YouTube playlistItems API."""
    headers = get_auth_headers(client, "page_user@socialai.com")
    user = db_session.query(User).filter(User.email == "page_user@socialai.com").first()
    create_mock_youtube_account(db_session, user.id)

    captured_params = {}

    def mock_requests_get(url, params=None, *args, **kwargs):
        if "playlistItems" in url:
            captured_params.update(params or {})
            mock_res = MagicMock()
            mock_res.status_code = 200
            mock_res.json.return_value = {
                "items": [],
                "nextPageToken": "NEXT_PAGE_TOKEN",
                "prevPageToken": "PREV_PAGE_TOKEN",
                "pageInfo": {"totalResults": 50}
            }
            return mock_res
        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_res.json.return_value = {"items": []}
        return mock_res

    with patch("requests.get", side_effect=mock_requests_get):
        res = client.get("/api/v1/youtube/videos?page_token=PAGE_TWO_TOKEN&limit=15", headers=headers)

    assert res.status_code == 200
    assert captured_params.get("pageToken") == "PAGE_TWO_TOKEN"
    assert captured_params.get("maxResults") == 15
    assert res.json()["next_page_token"] == "NEXT_PAGE_TOKEN"
    assert res.json()["prev_page_token"] == "PREV_PAGE_TOKEN"


def test_list_videos_empty_channel(client, db_session):
    """Channel with 0 videos returns empty list and 200 OK."""
    headers = get_auth_headers(client, "empty_channel_user@socialai.com")
    user = db_session.query(User).filter(User.email == "empty_channel_user@socialai.com").first()
    create_mock_youtube_account(db_session, user.id)

    def mock_requests_get(url, *args, **kwargs):
        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_res.json.return_value = {"items": [], "pageInfo": {"totalResults": 0}}
        return mock_res

    with patch("requests.get", side_effect=mock_requests_get):
        res = client.get("/api/v1/youtube/videos", headers=headers)

    assert res.status_code == 200
    data = res.json()
    assert data["videos"] == []
    assert data["total_results"] == 0


# ─── 3. Error Handling & Security ─────────────────────────────────────────────

def test_list_videos_youtube_401_handled(client, db_session):
    """YouTube 401 returns handled HTTP 401 response without leaking secrets."""
    headers = get_auth_headers(client, "yt_401_user@socialai.com")
    user = db_session.query(User).filter(User.email == "yt_401_user@socialai.com").first()
    create_mock_youtube_account(db_session, user.id)

    def mock_requests_get(url, *args, **kwargs):
        mock_res = MagicMock()
        mock_res.status_code = 401
        mock_res.json.return_value = {
            "error": {"code": 401, "message": "Invalid Credentials"}
        }
        return mock_res

    with patch("requests.get", side_effect=mock_requests_get):
        res = client.get("/api/v1/youtube/videos", headers=headers)

    assert res.status_code == 401
    assert "Invalid Credentials" in res.json()["detail"]


def test_list_videos_youtube_403_quota_handled(client, db_session):
    """YouTube 403 quota exceeded returns handled HTTP 403 error."""
    headers = get_auth_headers(client, "yt_403_user@socialai.com")
    user = db_session.query(User).filter(User.email == "yt_403_user@socialai.com").first()
    create_mock_youtube_account(db_session, user.id)

    def mock_requests_get(url, *args, **kwargs):
        mock_res = MagicMock()
        mock_res.status_code = 403
        mock_res.json.return_value = {
            "error": {"code": 403, "message": "The request cannot be completed because you have exceeded your quota."}
        }
        return mock_res

    with patch("requests.get", side_effect=mock_requests_get):
        res = client.get("/api/v1/youtube/videos", headers=headers)

    assert res.status_code == 403
    assert "exceeded your quota" in res.json()["detail"]


def test_list_videos_youtube_429_rate_limit_handled(client, db_session):
    """YouTube 429 rate limit is safely handled."""
    headers = get_auth_headers(client, "yt_429_user@socialai.com")
    user = db_session.query(User).filter(User.email == "yt_429_user@socialai.com").first()
    create_mock_youtube_account(db_session, user.id)

    def mock_requests_get(url, *args, **kwargs):
        mock_res = MagicMock()
        mock_res.status_code = 429
        mock_res.json.return_value = {
            "error": {"code": 429, "message": "Too Many Requests"}
        }
        return mock_res

    with patch("requests.get", side_effect=mock_requests_get):
        res = client.get("/api/v1/youtube/videos", headers=headers)

    assert res.status_code == 429
    assert "Too Many Requests" in res.json()["detail"]


def test_list_videos_no_token_exposure(client, db_session):
    """Response never contains any access tokens, client secrets, or sensitive hashes."""
    headers = get_auth_headers(client, "yt_sec_user@socialai.com")
    user = db_session.query(User).filter(User.email == "yt_sec_user@socialai.com").first()
    create_mock_youtube_account(db_session, user.id)

    mock_playlist = {
        "items": [
            {
                "snippet": {"title": "Safe Video", "channelId": "UC_SAFE"},
                "contentDetails": {"videoId": "vid_safe_1"}
            }
        ],
        "pageInfo": {"totalResults": 1}
    }
    mock_vids = {
        "items": [
            {
                "id": "vid_safe_1",
                "snippet": {"title": "Safe Video", "channelId": "UC_SAFE"},
                "status": {"privacyStatus": "public"}
            }
        ]
    }

    def mock_requests_get(url, *args, **kwargs):
        mock_res = MagicMock()
        mock_res.status_code = 200
        if "playlistItems" in url:
            mock_res.json.return_value = mock_playlist
        elif "videos" in url:
            mock_res.json.return_value = mock_vids
        return mock_res

    with patch("requests.get", side_effect=mock_requests_get):
        res = client.get("/api/v1/youtube/videos", headers=headers)

    raw_text = res.text.lower()
    assert "access_token" not in raw_text
    assert "client_secret" not in raw_text
    assert "refresh_token" not in raw_text

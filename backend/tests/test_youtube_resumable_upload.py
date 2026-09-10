import pytest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

from app.models.user import User
from app.models.social_account import SocialAccount
from app.core.redis import set_upload_session, get_upload_session
from app.core.security_encryption import encrypt_token, decrypt_token
from app.services.youtube_service import (
    youtube_service,
    YouTubeAPIException,
    YouTubeOAuthException,
)

def get_auth_headers(client, email="yt_upload_user@socialai.com"):
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

def create_mock_youtube_account(db_session, user_id, account_id="UC_TEST_CHAN_01", platform="youtube"):
    acc = SocialAccount(
        user_id=user_id,
        platform=platform,
        account_id=account_id,
        account_name="Test Creator Channel",
        access_token=encrypt_token("mock_access_token_12345"),
        token_type="Bearer",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        status="CONNECTED",
        metadata_json={"refresh_token": encrypt_token("mock_refresh_token_67890")}
    )
    db_session.add(acc)
    db_session.commit()
    db_session.refresh(acc)
    return acc

# ─── 1. Initiation Endpoint Tests ───────────────────────────────────────────

def test_upload_initiate_requires_authentication(client):
    """POST /api/v1/youtube/upload/initiate must return 401 without auth."""
    payload = {
        "social_account_id": 1,
        "title": "My Video",
        "file_size_bytes": 10485760,
    }
    res = client.post("/api/v1/youtube/upload/initiate", json=payload)
    assert res.status_code == 401

def test_upload_initiate_nonexistent_account(client, db_session):
    """POST /api/v1/youtube/upload/initiate returns 404 for non-existent account."""
    headers = get_auth_headers(client, "yt_init_404@socialai.com")
    payload = {
        "social_account_id": 99999,
        "title": "My Video",
        "file_size_bytes": 10485760,
    }
    res = client.post("/api/v1/youtube/upload/initiate", json=payload, headers=headers)
    assert res.status_code == 404

def test_upload_initiate_cross_tenant_account_rejected(client, db_session):
    """POST /api/v1/youtube/upload/initiate rejects account owned by another tenant."""
    headers_user1 = get_auth_headers(client, "tenant1@socialai.com")
    headers_user2 = get_auth_headers(client, "tenant2@socialai.com")

    user1 = db_session.query(User).filter(User.email == "tenant1@socialai.com").first()
    acc1 = create_mock_youtube_account(db_session, user1.id, "UC_USER1_CHAN")

    # User 2 tries to initiate using User 1's account
    payload = {
        "social_account_id": acc1.id,
        "title": "Hijacked Upload",
        "file_size_bytes": 5242880,
    }
    res = client.post("/api/v1/youtube/upload/initiate", json=payload, headers=headers_user2)
    assert res.status_code == 404

def test_upload_initiate_non_youtube_platform_rejected(client, db_session):
    """POST /api/v1/youtube/upload/initiate rejects non-YouTube platform account."""
    headers = get_auth_headers(client, "yt_fb_test@socialai.com")
    user = db_session.query(User).filter(User.email == "yt_fb_test@socialai.com").first()
    fb_acc = create_mock_youtube_account(db_session, user.id, "FB_PAGE_123", platform="facebook")

    payload = {
        "social_account_id": fb_acc.id,
        "title": "Facebook Upload Attempt",
        "file_size_bytes": 5242880,
    }
    res = client.post("/api/v1/youtube/upload/initiate", json=payload, headers=headers)
    assert res.status_code == 400
    assert "not a YouTube platform" in res.json()["detail"]

def test_upload_initiate_success(client, db_session):
    """POST /api/v1/youtube/upload/initiate successfully creates session on Google, saves to Redis, and hides tokens."""
    headers = get_auth_headers(client, "yt_init_success@socialai.com")
    user = db_session.query(User).filter(User.email == "yt_init_success@socialai.com").first()
    acc = create_mock_youtube_account(db_session, user.id, "UC_SUCCESS_CHAN")

    mock_google_session_url = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&upload_id=mock_session_abc123"

    payload = {
        "social_account_id": acc.id,
        "title": "Awesome Tech Tutorial",
        "description": "Learn python in 10 minutes",
        "privacy_status": "unlisted",
        "filename": "tutorial.mp4",
        "mime_type": "video/mp4",
        "file_size_bytes": 5242880,
    }

    with patch.object(youtube_service, "initiate_resumable_upload", return_value=mock_google_session_url) as mock_init:
        res = client.post("/api/v1/youtube/upload/initiate", json=payload, headers=headers)

    assert res.status_code == 200
    data = res.json()
    assert "upload_id" in data
    assert data["upload_id"].startswith("ytu_")
    assert data["channel_id"] == "UC_SUCCESS_CHAN"
    assert data["title"] == "Awesome Tech Tutorial"
    assert data["file_size_bytes"] == 5242880
    assert data["status"] == "INITIATED"

    # CRITICAL SECURITY: Never leak Google access tokens or OAuth credentials
    assert "access_token" not in data
    assert "refresh_token" not in data
    assert "client_secret" not in data
    assert "mock_access_token" not in json.dumps(data)

    # Verify session stored in Redis
    session = get_upload_session(data["upload_id"])
    assert session is not None
    assert session["user_id"] == user.id
    assert session["channel_id"] == "UC_SUCCESS_CHAN"
    assert decrypt_token(session["encrypted_session_url"]) == mock_google_session_url

    # Verify initiate_resumable_upload was called with correct decrypted token & metadata
    mock_init.assert_called_once_with(
        access_token="mock_access_token_12345",
        title="Awesome Tech Tutorial",
        description="Learn python in 10 minutes",
        privacy_status="unlisted",
        mime_type="video/mp4",
        file_size_bytes=5242880
    )

def test_upload_initiate_missing_location_header_error(client, db_session):
    """POST /api/v1/youtube/upload/initiate handles Google missing Location header cleanly."""
    headers = get_auth_headers(client, "yt_init_err@socialai.com")
    user = db_session.query(User).filter(User.email == "yt_init_err@socialai.com").first()
    acc = create_mock_youtube_account(db_session, user.id, "UC_ERR_CHAN")

    payload = {
        "social_account_id": acc.id,
        "title": "Error Video",
        "file_size_bytes": 5242880,
    }

    with patch.object(youtube_service, "initiate_resumable_upload", side_effect=YouTubeAPIException("YouTube did not return a Location header for resumable upload session.", status_code=502)):
        res = client.post("/api/v1/youtube/upload/initiate", json=payload, headers=headers)

    assert res.status_code == 502
    assert "Location header" in res.json()["detail"]

# ─── 2. Chunk Upload Endpoint Tests ─────────────────────────────────────────

def test_upload_chunk_requires_authentication(client):
    """PUT /api/v1/youtube/upload/{upload_id}/chunk requires authentication."""
    headers = {"Content-Range": "bytes 0-1048575/5242880", "Content-Type": "video/mp4"}
    res = client.put("/api/v1/youtube/upload/ytu_mock_123/chunk", data=b"x" * 1024, headers=headers)
    assert res.status_code == 401

def test_upload_chunk_cross_tenant_rejected(client, db_session):
    """PUT /api/v1/youtube/upload/{upload_id}/chunk rejects session owned by another user."""
    headers_user1 = get_auth_headers(client, "chunk_u1@socialai.com")
    headers_user2 = get_auth_headers(client, "chunk_u2@socialai.com")

    user1 = db_session.query(User).filter(User.email == "chunk_u1@socialai.com").first()
    acc1 = create_mock_youtube_account(db_session, user1.id, "UC_U1_CHAN")

    upload_id = "ytu_test_cross_tenant_999"
    session_data = {
        "upload_id": upload_id,
        "user_id": user1.id,
        "social_account_id": acc1.id,
        "channel_id": "UC_U1_CHAN",
        "title": "User 1 Video",
        "file_size_bytes": 5242880,
        "mime_type": "video/mp4",
        "encrypted_session_url": encrypt_token("https://google.com/upload/mock"),
        "status": "INITIATED",
    }
    set_upload_session(upload_id, session_data)

    req_headers = {
        **headers_user2,
        "Content-Range": "bytes 0-2097151/5242880",
        "Content-Type": "video/mp4",
    }
    res = client.put(f"/api/v1/youtube/upload/{upload_id}/chunk", data=b"x" * 2097152, headers=req_headers)
    assert res.status_code == 404

def test_upload_chunk_size_bounded(client, db_session):
    """PUT /api/v1/youtube/upload/{upload_id}/chunk rejects chunks exceeding max bound."""
    headers = get_auth_headers(client, "chunk_bound@socialai.com")
    user = db_session.query(User).filter(User.email == "chunk_bound@socialai.com").first()
    acc = create_mock_youtube_account(db_session, user.id, "UC_BOUND_CHAN")

    upload_id = "ytu_test_bound_chunk_111"
    session_data = {
        "upload_id": upload_id,
        "user_id": user.id,
        "social_account_id": acc.id,
        "channel_id": "UC_BOUND_CHAN",
        "title": "Bounded Chunk Video",
        "file_size_bytes": 20971520,
        "mime_type": "video/mp4",
        "encrypted_session_url": encrypt_token("https://google.com/upload/mock"),
        "status": "INITIATED",
    }
    set_upload_session(upload_id, session_data)

    # Try sending 6 MB chunk (exceeds 5 MB proof-of-concept bound)
    large_payload = b"x" * (6 * 1024 * 1024)
    req_headers = {
        **headers,
        "Content-Range": "bytes 0-6291455/20971520",
        "Content-Type": "video/mp4",
    }
    res = client.put(f"/api/v1/youtube/upload/{upload_id}/chunk", data=large_payload, headers=req_headers)
    assert res.status_code == 413
    assert "exceeds maximum allowed chunk size" in res.json()["detail"]

def test_upload_chunk_empty_body_rejected(client, db_session):
    """PUT /api/v1/youtube/upload/{upload_id}/chunk rejects empty chunk."""
    headers = get_auth_headers(client, "chunk_empty@socialai.com")
    user = db_session.query(User).filter(User.email == "chunk_empty@socialai.com").first()
    acc = create_mock_youtube_account(db_session, user.id, "UC_EMPTY_CHAN")

    upload_id = "ytu_test_empty_chunk_222"
    session_data = {
        "upload_id": upload_id,
        "user_id": user.id,
        "social_account_id": acc.id,
        "channel_id": "UC_EMPTY_CHAN",
        "title": "Empty Chunk Video",
        "file_size_bytes": 5242880,
        "mime_type": "video/mp4",
        "encrypted_session_url": encrypt_token("https://google.com/upload/mock"),
        "status": "INITIATED",
    }
    set_upload_session(upload_id, session_data)

    req_headers = {
        **headers,
        "Content-Range": "bytes 0-0/5242880",
        "Content-Type": "video/mp4",
    }
    res = client.put(f"/api/v1/youtube/upload/{upload_id}/chunk", data=b"", headers=req_headers)
    assert res.status_code == 400

def test_upload_chunk_handles_youtube_308_resume_incomplete(client, db_session):
    """PUT /api/v1/youtube/upload/{upload_id}/chunk correctly handles HTTP 308, parses Range, and returns next offset."""
    headers = get_auth_headers(client, "chunk_308@socialai.com")
    user = db_session.query(User).filter(User.email == "chunk_308@socialai.com").first()
    acc = create_mock_youtube_account(db_session, user.id, "UC_308_CHAN")

    upload_id = "ytu_test_308_chunk_333"
    session_data = {
        "upload_id": upload_id,
        "user_id": user.id,
        "social_account_id": acc.id,
        "channel_id": "UC_308_CHAN",
        "title": "308 Resume Video",
        "file_size_bytes": 5242880,
        "mime_type": "video/mp4",
        "encrypted_session_url": encrypt_token("https://google.com/upload/mock"),
        "status": "INITIATED",
    }
    set_upload_session(upload_id, session_data)

    mock_308_result = {
        "status": "RESUME_INCOMPLETE",
        "http_status": 308,
        "range_header": "bytes=0-2097151",
        "last_byte_received": 2097151,
        "next_byte_offset": 2097152,
        "is_complete": False,
    }

    chunk_2mb = b"v" * 2097152  # 2 MB chunk
    req_headers = {
        **headers,
        "Content-Range": "bytes 0-2097151/5242880",
        "Content-Type": "video/mp4",
    }

    with patch.object(youtube_service, "upload_resumable_chunk", return_value=mock_308_result) as mock_upload:
        res = client.put(f"/api/v1/youtube/upload/{upload_id}/chunk", data=chunk_2mb, headers=req_headers)

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "RESUME_INCOMPLETE"
    assert data["http_status"] == 308
    assert data["range_header"] == "bytes=0-2097151"
    assert data["last_byte_received"] == 2097151
    assert data["next_byte_offset"] == 2097152
    assert data["is_complete"] is False
    assert data["total_bytes"] == 5242880

    # Ensure no secrets exposed
    assert "access_token" not in data
    assert "mock_access_token" not in json.dumps(data)

    # Verify upload_resumable_chunk called correctly
    mock_upload.assert_called_once_with(
        resumable_session_url="https://google.com/upload/mock",
        chunk_bytes=chunk_2mb,
        content_range="bytes 0-2097151/5242880",
        mime_type="video/mp4",
        access_token="mock_access_token_12345"
    )

def test_upload_chunk_handles_final_completion(client, db_session):
    """PUT /api/v1/youtube/upload/{upload_id}/chunk handles final chunk (HTTP 200/201) returning Video ID."""
    headers = get_auth_headers(client, "chunk_complete@socialai.com")
    user = db_session.query(User).filter(User.email == "chunk_complete@socialai.com").first()
    acc = create_mock_youtube_account(db_session, user.id, "UC_COMP_CHAN")

    upload_id = "ytu_test_complete_chunk_444"
    session_data = {
        "upload_id": upload_id,
        "user_id": user.id,
        "social_account_id": acc.id,
        "channel_id": "UC_COMP_CHAN",
        "title": "Completed Video",
        "file_size_bytes": 1048576,
        "mime_type": "video/mp4",
        "encrypted_session_url": encrypt_token("https://google.com/upload/mock"),
        "status": "INITIATED",
    }
    set_upload_session(upload_id, session_data)

    mock_completed_result = {
        "status": "COMPLETED",
        "http_status": 200,
        "video_id": "dQw4w9WgXcQ",
        "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "is_complete": True,
    }

    final_chunk = b"v" * 1048576  # 1 MB final chunk
    req_headers = {
        **headers,
        "Content-Range": "bytes 0-1048575/1048576",
        "Content-Type": "video/mp4",
    }

    with patch.object(youtube_service, "upload_resumable_chunk", return_value=mock_completed_result):
        res = client.put(f"/api/v1/youtube/upload/{upload_id}/chunk", data=final_chunk, headers=req_headers)

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "COMPLETED"
    assert data["http_status"] == 200
    assert data["video_id"] == "dQw4w9WgXcQ"
    assert data["video_url"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert data["is_complete"] is True

# ─── 3. Status Query Endpoint Tests ─────────────────────────────────────────

def test_upload_status_query_success(client, db_session):
    """GET /api/v1/youtube/upload/{upload_id}/status queries Google and returns confirmed Range offset."""
    headers = get_auth_headers(client, "status_query@socialai.com")
    user = db_session.query(User).filter(User.email == "status_query@socialai.com").first()
    acc = create_mock_youtube_account(db_session, user.id, "UC_QUERY_CHAN")

    upload_id = "ytu_test_status_query_555"
    session_data = {
        "upload_id": upload_id,
        "user_id": user.id,
        "social_account_id": acc.id,
        "channel_id": "UC_QUERY_CHAN",
        "title": "Status Query Video",
        "file_size_bytes": 10485760,
        "mime_type": "video/mp4",
        "encrypted_session_url": encrypt_token("https://google.com/upload/mock"),
        "status": "RESUME_INCOMPLETE",
    }
    set_upload_session(upload_id, session_data)

    mock_status_result = {
        "status": "RESUME_INCOMPLETE",
        "http_status": 308,
        "range_header": "bytes=0-4194303",
        "last_byte_received": 4194303,
        "next_byte_offset": 4194304,
        "is_complete": False,
    }

    with patch.object(youtube_service, "query_resumable_status", return_value=mock_status_result) as mock_query:
        res = client.get(f"/api/v1/youtube/upload/{upload_id}/status", headers=headers)

    assert res.status_code == 200
    data = res.json()
    assert data["upload_id"] == upload_id
    assert data["status"] == "RESUME_INCOMPLETE"
    assert data["range_header"] == "bytes=0-4194303"
    assert data["last_byte_received"] == 4194303
    assert data["next_byte_offset"] == 4194304
    assert data["is_complete"] is False

    mock_query.assert_called_once_with(
        resumable_session_url="https://google.com/upload/mock",
        total_file_size=10485760,
        mime_type="video/mp4",
        access_token="mock_access_token_12345"
    )

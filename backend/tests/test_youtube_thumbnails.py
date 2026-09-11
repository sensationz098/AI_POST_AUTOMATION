import pytest
import json
import io
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

from app.models.user import User
from app.models.social_account import SocialAccount
from app.models.youtube_upload import YouTubeUpload, YouTubeUploadStatus
from app.core.security_encryption import encrypt_token, decrypt_token
from app.services.youtube_service import (
    youtube_service,
    YouTubeAPIException,
    YouTubeOAuthException,
)
from app.api.v1.youtube import poll_youtube_video_processing_task
from app.repositories.youtube_upload_repository import youtube_upload_repo


def get_auth_headers(client, email="yt_thumb_user@socialai.com"):
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


def create_mock_youtube_account(db_session, user_id, account_id="UC_THUMB_CHAN_01", platform="youtube"):
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


# ─── 1. OAuth Scope Configuration Test ────────────────────────────────────────

def test_youtube_oauth_scopes_include_full_required_set():
    """Verify that REQUIRED_YOUTUBE_SCOPES contains upload, readonly, and youtube."""
    assert "https://www.googleapis.com/auth/youtube.upload" in youtube_service.REQUIRED_YOUTUBE_SCOPES
    assert "https://www.googleapis.com/auth/youtube.readonly" in youtube_service.REQUIRED_YOUTUBE_SCOPES
    assert "https://www.googleapis.com/auth/youtube" in youtube_service.REQUIRED_YOUTUBE_SCOPES
    assert len(youtube_service.REQUIRED_YOUTUBE_SCOPES) >= 3


# ─── 2. Thumbnail Media Upload Endpoint Validation Tests ───────────────────────

def test_upload_thumbnail_endpoint_requires_auth(client):
    """POST /api/v1/youtube/upload-thumbnail returns 401 without authentication."""
    file_data = io.BytesIO(b"fake image bytes")
    res = client.post(
        "/api/v1/youtube/upload-thumbnail",
        files={"file": ("thumbnail.jpg", file_data, "image/jpeg")}
    )
    assert res.status_code == 401


def test_upload_thumbnail_endpoint_valid_image(client, db_session):
    """POST /api/v1/youtube/upload-thumbnail succeeds with valid JPEG/PNG <= 2MB."""
    headers = get_auth_headers(client, "yt_thumb_valid@socialai.com")
    file_data = io.BytesIO(b"\xff\xd8\xff\xe0" + b"\x00" * 1024)  # Small fake JPEG header + bytes

    with patch("app.services.cloudinary_service.upload_media_to_cloudinary", return_value="https://res.cloudinary.com/demo/image/upload/v1234/yt_thumb.jpg"):
        res = client.post(
            "/api/v1/youtube/upload-thumbnail",
            files={"file": ("cover.jpg", file_data, "image/jpeg")},
            headers=headers
        )

    assert res.status_code == 200
    data = res.json()
    assert "thumbnail_url" in data
    assert data["thumbnail_url"] == "https://res.cloudinary.com/demo/image/upload/v1234/yt_thumb.jpg"
    assert data["filename"] == "cover.jpg"
    assert data["file_size_bytes"] > 0


def test_upload_thumbnail_endpoint_rejects_invalid_mime(client, db_session):
    """POST /api/v1/youtube/upload-thumbnail rejects non-image or invalid format with 400."""
    headers = get_auth_headers(client, "yt_thumb_invalid_mime@socialai.com")
    file_data = io.BytesIO(b"PDF document content")

    res = client.post(
        "/api/v1/youtube/upload-thumbnail",
        files={"file": ("document.pdf", file_data, "application/pdf")},
        headers=headers
    )
    assert res.status_code == 400
    assert "Invalid image format" in res.json()["detail"]


def test_upload_thumbnail_endpoint_rejects_oversized_file(client, db_session):
    """POST /api/v1/youtube/upload-thumbnail rejects image exceeding 2 MB limit with 413."""
    headers = get_auth_headers(client, "yt_thumb_oversized@socialai.com")
    # 2.5 MB payload
    file_data = io.BytesIO(b"\x00" * int(2.5 * 1024 * 1024))

    res = client.post(
        "/api/v1/youtube/upload-thumbnail",
        files={"file": ("giant_cover.png", file_data, "image/png")},
        headers=headers
    )
    assert res.status_code in (413, 400)
    assert "exceeds maximum allowed limit of 2 MB" in res.json()["detail"]


# ─── 3. Video Publish Without Thumbnail (Regression Protection) ───────────────

def test_video_publish_without_thumbnail_succeeds(client, db_session):
    """Publishing a video without a thumbnail retains existing behavior (thumbnail is null/omitted)."""
    headers = get_auth_headers(client, "yt_no_thumb@socialai.com")
    user = db_session.query(User).filter(User.email == "yt_no_thumb@socialai.com").first()
    acc = create_mock_youtube_account(db_session, user.id, "UC_NO_THUMB_CHAN")

    mock_google_session = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&upload_id=no_thumb_sess"

    init_payload = {
        "social_account_id": acc.id,
        "title": "Video Without Thumbnail",
        "file_size_bytes": 1024,
    }

    with patch.object(youtube_service, "initiate_resumable_upload", return_value=mock_google_session):
        init_res = client.post("/api/v1/youtube/upload/initiate", json=init_payload, headers=headers)

    assert init_res.status_code == 200
    upload_id = init_res.json()["upload_id"]

    # Upload final chunk
    chunk_data = b"video bytes"
    with patch.object(youtube_service, "upload_resumable_chunk", return_value={
        "status": "COMPLETED",
        "http_status": 200,
        "video_id": "vid_no_thumb_999",
        "video_url": "https://www.youtube.com/watch?v=vid_no_thumb_999",
        "is_complete": True,
    }):
        with patch.object(youtube_service, "set_video_thumbnail") as mock_set_thumb:
            with patch.object(poll_youtube_video_processing_task, "delay"):
                chunk_res = client.put(
                    f"/api/v1/youtube/upload/{upload_id}/chunk",
                    content=chunk_data,
                    headers={
                        **headers,
                        "Content-Range": "bytes 0-1023/1024",
                        "Content-Type": "video/mp4",
                    }
                )

    assert chunk_res.status_code == 200
    data = chunk_res.json()
    assert data["is_complete"] is True
    assert data["video_id"] == "vid_no_thumb_999"
    assert data["thumbnail_url"] is None
    assert data["thumbnail_status"] is None
    # Verify set_video_thumbnail was NOT called
    mock_set_thumb.assert_not_called()


# ─── 4. Video Publish With Thumbnail (Success Flow) ───────────────────────────

def test_video_publish_with_thumbnail_success(client, db_session):
    """Publishing video with valid thumbnail URL calls thumbnails.set on video completion."""
    headers = get_auth_headers(client, "yt_with_thumb@socialai.com")
    user = db_session.query(User).filter(User.email == "yt_with_thumb@socialai.com").first()
    acc = create_mock_youtube_account(db_session, user.id, "UC_WITH_THUMB_CHAN")

    mock_google_session = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&upload_id=with_thumb_sess"
    thumbnail_url = "https://res.cloudinary.com/demo/image/upload/v1234/my_thumb.jpg"

    init_payload = {
        "social_account_id": acc.id,
        "title": "Video With Awesome Thumbnail",
        "file_size_bytes": 1024,
        "thumbnail_url": thumbnail_url,
    }

    with patch.object(youtube_service, "initiate_resumable_upload", return_value=mock_google_session):
        init_res = client.post("/api/v1/youtube/upload/initiate", json=init_payload, headers=headers)

    assert init_res.status_code == 200
    upload_id = init_res.json()["upload_id"]
    assert init_res.json()["thumbnail_url"] == thumbnail_url
    assert init_res.json()["thumbnail_status"] == "PENDING"

    # Upload final chunk
    chunk_data = b"video bytes"
    with patch.object(youtube_service, "upload_resumable_chunk", return_value={
        "status": "COMPLETED",
        "http_status": 200,
        "video_id": "vid_with_thumb_888",
        "video_url": "https://www.youtube.com/watch?v=vid_with_thumb_888",
        "is_complete": True,
    }):
        with patch.object(youtube_service, "apply_thumbnail_from_storage", return_value={"status": "success"}) as mock_apply:
            with patch.object(poll_youtube_video_processing_task, "delay"):
                chunk_res = client.put(
                    f"/api/v1/youtube/upload/{upload_id}/chunk",
                    content=chunk_data,
                    headers={
                        **headers,
                        "Content-Range": "bytes 0-1023/1024",
                        "Content-Type": "video/mp4",
                    }
                )

    assert chunk_res.status_code == 200
    data = chunk_res.json()
    assert data["is_complete"] is True
    assert data["video_id"] == "vid_with_thumb_888"
    assert data["thumbnail_status"] == "APPLIED"
    assert data["thumbnail_url"] == thumbnail_url
    mock_apply.assert_called_once()

    # Verify status endpoint reflects APPLIED thumbnail
    status_res = client.get(f"/api/v1/youtube/upload/{upload_id}/status", headers=headers)
    assert status_res.status_code == 200
    st_data = status_res.json()
    assert st_data["thumbnail_status"] == "APPLIED"
    assert st_data["thumbnail_url"] == thumbnail_url


# ─── 5. Video Publish Succeeds but Thumbnail Application Fails (Invariant) ────

def test_video_publish_succeeds_when_thumbnail_application_fails(client, db_session):
    """CRITICAL: If thumbnail application fails, the video publish MUST remain successful."""
    headers = get_auth_headers(client, "yt_thumb_fail@socialai.com")
    user = db_session.query(User).filter(User.email == "yt_thumb_fail@socialai.com").first()
    acc = create_mock_youtube_account(db_session, user.id, "UC_THUMB_FAIL_CHAN")

    mock_google_session = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&upload_id=thumb_fail_sess"
    thumbnail_url = "https://res.cloudinary.com/demo/image/upload/v1234/bad_thumb.jpg"

    init_payload = {
        "social_account_id": acc.id,
        "title": "Video With Failing Thumbnail",
        "file_size_bytes": 1024,
        "thumbnail_url": thumbnail_url,
    }

    with patch.object(youtube_service, "initiate_resumable_upload", return_value=mock_google_session):
        init_res = client.post("/api/v1/youtube/upload/initiate", json=init_payload, headers=headers)

    assert init_res.status_code == 200
    upload_id = init_res.json()["upload_id"]

    # Final chunk completes video, but thumbnail application raises YouTubeAPIException
    chunk_data = b"video bytes"
    with patch.object(youtube_service, "upload_resumable_chunk", return_value={
        "status": "COMPLETED",
        "http_status": 200,
        "video_id": "vid_thumb_failed_777",
        "video_url": "https://www.youtube.com/watch?v=vid_thumb_failed_777",
        "is_complete": True,
    }):
        with patch.object(youtube_service, "apply_thumbnail_from_storage", side_effect=YouTubeAPIException("YouTube thumbnail rejected: Invalid dimensions")):
            with patch.object(poll_youtube_video_processing_task, "delay"):
                chunk_res = client.put(
                    f"/api/v1/youtube/upload/{upload_id}/chunk",
                    content=chunk_data,
                    headers={
                        **headers,
                        "Content-Range": "bytes 0-1023/1024",
                        "Content-Type": "video/mp4",
                    }
                )

    # Status must still be 200 OK (video completed), not 500 or failed video
    assert chunk_res.status_code == 200
    data = chunk_res.json()
    assert data["is_complete"] is True
    assert data["video_id"] == "vid_thumb_failed_777"
    assert data["thumbnail_status"] == "FAILED"
    assert "Invalid dimensions" in (data["thumbnail_error"] or "")

    # Check database status
    db_rec = youtube_upload_repo.get_by_upload_id(db_session, upload_id)
    assert db_rec is not None
    assert db_rec.upload_status == YouTubeUploadStatus.PROCESSING.value  # Video is not failed!
    assert db_rec.thumbnail_status == "FAILED"
    assert "Invalid dimensions" in db_rec.thumbnail_error


# ─── 6. Thumbnail Retry Endpoint Tests ────────────────────────────────────────

def test_retry_thumbnail_application_success(client, db_session):
    """POST /api/v1/youtube/upload/{upload_id}/thumbnail/retry reapplies thumbnail and updates status to APPLIED."""
    headers = get_auth_headers(client, "yt_retry_user@socialai.com")
    user = db_session.query(User).filter(User.email == "yt_retry_user@socialai.com").first()
    acc = create_mock_youtube_account(db_session, user.id, "UC_RETRY_CHAN")

    # Create upload in failed thumbnail state
    upload = youtube_upload_repo.create(
        db=db_session,
        upload_id="ytu_retry_test_123",
        user_id=user.id,
        social_account_id=acc.id,
        channel_id=acc.account_id,
        title="Retry Thumbnail Video",
        file_size_bytes=2048,
        thumbnail_url="https://res.cloudinary.com/demo/image/upload/v1/retry_cover.jpg",
    )
    youtube_upload_repo.mark_completed(db_session, upload.upload_id, "vid_retry_123", "https://www.youtube.com/watch?v=vid_retry_123")
    youtube_upload_repo.update_thumbnail_status(db_session, upload.upload_id, "FAILED", error="Previous network timeout")

    with patch.object(youtube_service, "apply_thumbnail_from_storage", return_value={"status": "success"}) as mock_apply:
        res = client.post(f"/api/v1/youtube/upload/{upload.upload_id}/thumbnail/retry", headers=headers)

    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["thumbnail_status"] == "APPLIED"
    assert data["thumbnail_error"] is None

    # Verify DB was updated
    db_session.refresh(upload)
    assert upload.thumbnail_status == "APPLIED"
    assert upload.thumbnail_error is None


def test_retry_thumbnail_cross_tenant_isolation(client, db_session):
    """User B cannot retry thumbnail for User A's upload (enforces tenant isolation)."""
    headers_user_a = get_auth_headers(client, "user_a_thumb@socialai.com")
    headers_user_b = get_auth_headers(client, "user_b_thumb@socialai.com")

    user_a = db_session.query(User).filter(User.email == "user_a_thumb@socialai.com").first()
    acc_a = create_mock_youtube_account(db_session, user_a.id, "UC_USER_A_CHAN")

    upload_a = youtube_upload_repo.create(
        db=db_session,
        upload_id="ytu_user_a_secret_thumb",
        user_id=user_a.id,
        social_account_id=acc_a.id,
        channel_id=acc_a.account_id,
        title="User A Video",
        file_size_bytes=1024,
        thumbnail_url="https://res.cloudinary.com/demo/image/upload/v1/user_a.jpg",
    )
    youtube_upload_repo.mark_completed(db_session, upload_a.upload_id, "vid_user_a_123", "https://www.youtube.com/watch?v=vid_user_a_123")

    # User B attempts to retry User A's thumbnail
    res = client.post(f"/api/v1/youtube/upload/{upload_a.upload_id}/thumbnail/retry", headers=headers_user_b)
    assert res.status_code == 404


# ─── 7. Scheduled Publish With Thumbnail ──────────────────────────────────────

def test_scheduled_publish_with_thumbnail(client, db_session):
    """Scheduled YouTube video upload passes publish_at and applies thumbnail."""
    headers = get_auth_headers(client, "yt_sched_thumb@socialai.com")
    user = db_session.query(User).filter(User.email == "yt_sched_thumb@socialai.com").first()
    acc = create_mock_youtube_account(db_session, user.id, "UC_SCHED_THUMB_CHAN")

    mock_google_session = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&upload_id=sched_thumb_sess"
    thumbnail_url = "https://res.cloudinary.com/demo/image/upload/v1/sched_cover.jpg"
    publish_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

    init_payload = {
        "social_account_id": acc.id,
        "title": "Scheduled Video With Cover",
        "file_size_bytes": 1024,
        "thumbnail_url": thumbnail_url,
        "publish_at": publish_time,
    }

    with patch.object(youtube_service, "initiate_resumable_upload", return_value=mock_google_session) as mock_init:
        init_res = client.post("/api/v1/youtube/upload/initiate", json=init_payload, headers=headers)

    assert init_res.status_code == 200
    upload_id = init_res.json()["upload_id"]
    assert init_res.json()["thumbnail_url"] == thumbnail_url

    # Check initiate_resumable_upload was called with publish_at
    mock_init.assert_called_once()
    call_kwargs = mock_init.call_args[1]
    assert call_kwargs.get("publish_at") is not None

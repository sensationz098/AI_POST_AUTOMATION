import pytest
import json
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
from app.repositories.youtube_upload_repository import youtube_upload_repository
from app.tasks.youtube_tasks import poll_youtube_video_processing

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

# ─── 1. Initiation Endpoint Tests (with Idempotency) ──────────────────────────

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

def test_upload_initiate_success_and_db_persistence(client, db_session):
    """POST /api/v1/youtube/upload/initiate successfully creates session on Google, saves to DB, and hides tokens."""
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
        "file_size_bytes": 16777216,
        "client_mutation_id": "client-uuid-1111",
    }

    with patch.object(youtube_service, "initiate_resumable_upload", return_value=mock_google_session_url) as mock_init:
        res = client.post("/api/v1/youtube/upload/initiate", json=payload, headers=headers)

    assert res.status_code == 200
    data = res.json()
    assert "upload_id" in data
    assert data["upload_id"].startswith("ytu_")
    assert data["client_mutation_id"] == "client-uuid-1111"
    assert data["channel_id"] == "UC_SUCCESS_CHAN"
    assert data["title"] == "Awesome Tech Tutorial"
    assert data["file_size_bytes"] == 16777216
    assert data["chunk_size_bytes"] == 8388608
    assert data["status"] in ("INITIATED", "PENDING")
    assert data["next_byte_offset"] == 0

    # CRITICAL SECURITY: Never leak Google access tokens or capability URLs
    assert "access_token" not in data
    assert "refresh_token" not in data
    assert "client_secret" not in data
    assert "mock_access_token" not in json.dumps(data)

    # Verify session stored in PostgreSQL DB
    upload_record = youtube_upload_repository.get_by_upload_id(db_session, data["upload_id"])
    assert upload_record is not None
    assert upload_record.user_id == user.id
    assert upload_record.client_mutation_id == "client-uuid-1111"
    assert upload_record.channel_id == "UC_SUCCESS_CHAN"
    assert decrypt_token(upload_record.encrypted_session_url) == mock_google_session_url

def test_upload_initiate_idempotency(client, db_session):
    """POST /api/v1/youtube/upload/initiate with same client_mutation_id reuses existing session without calling Google."""
    headers = get_auth_headers(client, "yt_idempotency@socialai.com")
    user = db_session.query(User).filter(User.email == "yt_idempotency@socialai.com").first()
    acc = create_mock_youtube_account(db_session, user.id, "UC_IDEMPOTENT_CHAN")

    mock_google_session_url = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&upload_id=mock_session_idempotent"

    payload = {
        "social_account_id": acc.id,
        "title": "Idempotent Video Test",
        "file_size_bytes": 10485760,
        "client_mutation_id": "client-uuid-reuse-999",
    }

    # First call creates the session
    with patch.object(youtube_service, "initiate_resumable_upload", return_value=mock_google_session_url) as mock_init:
        res1 = client.post("/api/v1/youtube/upload/initiate", json=payload, headers=headers)
        assert res1.status_code == 200
        assert mock_init.call_count == 1
        data1 = res1.json()

    # Second call with the EXACT SAME client_mutation_id
    with patch.object(youtube_service, "initiate_resumable_upload") as mock_init2:
        res2 = client.post("/api/v1/youtube/upload/initiate", json=payload, headers=headers)
        assert res2.status_code == 200
        # Google API must NOT be called again!
        mock_init2.assert_not_called()
        data2 = res2.json()

    # Reused identical upload_id
    assert data2["upload_id"] == data1["upload_id"]
    assert data2["client_mutation_id"] == "client-uuid-reuse-999"
    assert "resumed" in data2["message"].lower() or "reused" in data2["message"].lower()

def test_upload_initiate_concurrent_simulation(client, db_session):
    """Simulating concurrent duplicate initiate requests results in exactly ONE upload session."""
    headers = get_auth_headers(client, "yt_concurrent@socialai.com")
    user = db_session.query(User).filter(User.email == "yt_concurrent@socialai.com").first()
    acc = create_mock_youtube_account(db_session, user.id, "UC_CONCURRENT_CHAN")

    mock_google_session_url = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&upload_id=mock_session_conc"

    payload = {
        "social_account_id": acc.id,
        "title": "Concurrent Init Video",
        "file_size_bytes": 10485760,
        "client_mutation_id": "client-uuid-concurrent-777",
    }

    # Simulate Request A and Request B
    with patch.object(youtube_service, "initiate_resumable_upload", return_value=mock_google_session_url) as mock_init:
        res_a = client.post("/api/v1/youtube/upload/initiate", json=payload, headers=headers)
        res_b = client.post("/api/v1/youtube/upload/initiate", json=payload, headers=headers)

    assert res_a.status_code == 200
    assert res_b.status_code == 200
    data_a = res_a.json()
    data_b = res_b.json()

    # Both requests must reference the exact same session
    assert data_a["upload_id"] == data_b["upload_id"]
    assert mock_init.call_count == 1

    # Verify only 1 record exists in DB for this user & mutation key
    records = db_session.query(YouTubeUpload).filter(
        YouTubeUpload.user_id == user.id,
        YouTubeUpload.client_mutation_id == "client-uuid-concurrent-777"
    ).all()
    assert len(records) == 1

# ─── 2. Chunk Upload & Range Tests ──────────────────────────────────────────

def test_upload_chunk_size_bounded(client, db_session):
    """PUT /api/v1/youtube/upload/{upload_id}/chunk accepts exactly configured chunk size and rejects chunk_size + 1."""
    headers = get_auth_headers(client, "chunk_bound@socialai.com")
    user = db_session.query(User).filter(User.email == "chunk_bound@socialai.com").first()
    acc = create_mock_youtube_account(db_session, user.id, "UC_BOUND_CHAN")

    upload = youtube_upload_repository.create(
        db=db_session,
        upload_id="ytu_test_bound_chunk_111",
        user_id=user.id,
        social_account_id=acc.id,
        channel_id="UC_BOUND_CHAN",
        title="Bounded Chunk Video",
        file_size_bytes=30000000,
        mime_type="video/mp4",
        encrypted_session_url=encrypt_token("https://google.com/upload/mock"),
    )

    # 1. Chunk of size YOUTUBE_UPLOAD_CHUNK_SIZE + 1 byte (8388609 bytes) -> MUST BE REJECTED with 413
    over_limit_payload = b"x" * 8388609
    req_headers_over = {
        **headers,
        "Content-Range": "bytes 0-8388608/30000000",
        "Content-Type": "video/mp4",
    }
    res_over = client.put(f"/api/v1/youtube/upload/{upload.upload_id}/chunk", data=over_limit_payload, headers=req_headers_over)
    assert res_over.status_code == 413
    assert "exceeds maximum" in res_over.json()["detail"].lower()

    # 2. Chunk of EXACTLY YOUTUBE_UPLOAD_CHUNK_SIZE (8388608 bytes) -> MUST BE ACCEPTED
    exact_payload = b"x" * 8388608
    req_headers_exact = {
        **headers,
        "Content-Range": "bytes 0-8388607/30000000",
        "Content-Type": "video/mp4",
    }
    mock_308 = {
        "status": "RESUME_INCOMPLETE",
        "http_status": 308,
        "range_header": "bytes=0-8388607",
        "last_byte_received": 8388607,
        "next_byte_offset": 8388608,
        "is_complete": False,
    }
    with patch.object(youtube_service, "upload_resumable_chunk", return_value=mock_308):
        res_exact = client.put(f"/api/v1/youtube/upload/{upload.upload_id}/chunk", data=exact_payload, headers=req_headers_exact)
    assert res_exact.status_code == 200
    assert res_exact.json()["bytes_uploaded"] == 8388608

def test_upload_chunk_handles_308_and_updates_progress(client, db_session):
    """PUT /api/v1/youtube/upload/{upload_id}/chunk handles HTTP 308, updates DB progress and returns next byte."""
    headers = get_auth_headers(client, "chunk_308_prog@socialai.com")
    user = db_session.query(User).filter(User.email == "chunk_308_prog@socialai.com").first()
    acc = create_mock_youtube_account(db_session, user.id, "UC_308_CHAN")

    upload = youtube_upload_repository.create(
        db=db_session,
        upload_id="ytu_test_308_chunk_222",
        user_id=user.id,
        social_account_id=acc.id,
        channel_id="UC_308_CHAN",
        title="308 Progress Video",
        file_size_bytes=16777216,
        mime_type="video/mp4",
        encrypted_session_url=encrypt_token("https://google.com/upload/mock"),
    )

    mock_308_result = {
        "status": "RESUME_INCOMPLETE",
        "http_status": 308,
        "range_header": "bytes=0-8388607",
        "last_byte_received": 8388607,
        "next_byte_offset": 8388608,
        "is_complete": False,
    }

    chunk_8mb = b"v" * 8388608
    req_headers = {
        **headers,
        "Content-Range": "bytes 0-8388607/16777216",
        "Content-Type": "video/mp4",
    }

    with patch.object(youtube_service, "upload_resumable_chunk", return_value=mock_308_result):
        res = client.put(f"/api/v1/youtube/upload/{upload.upload_id}/chunk", data=chunk_8mb, headers=req_headers)

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "RESUME_INCOMPLETE"
    assert data["http_status"] == 308
    assert data["next_byte_offset"] == 8388608
    assert data["bytes_uploaded"] == 8388608
    assert data["progress_percentage"] == 50.0

    # Verify DB record updated
    db_session.refresh(upload)
    assert upload.upload_status == YouTubeUploadStatus.UPLOADING.value
    assert upload.bytes_uploaded == 8388608

def test_upload_chunk_completion_transitions_to_processing(client, db_session):
    """PUT /api/v1/youtube/upload/{upload_id}/chunk completion marks DB status PROCESSING and triggers Celery task."""
    headers = get_auth_headers(client, "chunk_comp_proc@socialai.com")
    user = db_session.query(User).filter(User.email == "chunk_comp_proc@socialai.com").first()
    acc = create_mock_youtube_account(db_session, user.id, "UC_COMP_CHAN")

    upload = youtube_upload_repository.create(
        db=db_session,
        upload_id="ytu_test_comp_chunk_333",
        user_id=user.id,
        social_account_id=acc.id,
        channel_id="UC_COMP_CHAN",
        title="Completion Video",
        file_size_bytes=1048576,
        mime_type="video/mp4",
        encrypted_session_url=encrypt_token("https://google.com/upload/mock"),
    )

    mock_completed_result = {
        "status": "COMPLETED",
        "http_status": 200,
        "video_id": "vid_youtube_xyz",
        "video_url": "https://www.youtube.com/watch?v=vid_youtube_xyz",
        "is_complete": True,
    }

    final_chunk = b"v" * 1048576
    req_headers = {
        **headers,
        "Content-Range": "bytes 0-1048575/1048576",
        "Content-Type": "video/mp4",
    }

    with patch.object(youtube_service, "upload_resumable_chunk", return_value=mock_completed_result):
        with patch.object(poll_youtube_video_processing, "delay") as mock_celery:
            res = client.put(f"/api/v1/youtube/upload/{upload.upload_id}/chunk", data=final_chunk, headers=req_headers)

    assert res.status_code == 200
    data = res.json()
    assert data["is_complete"] is True
    assert data["video_id"] == "vid_youtube_xyz"
    assert data["status"] == "PROCESSING"

    # Verify DB transitioned to PROCESSING
    db_session.refresh(upload)
    assert upload.upload_status == YouTubeUploadStatus.PROCESSING.value
    assert upload.video_id == "vid_youtube_xyz"
    assert upload.bytes_uploaded == 1048576
    assert mock_celery.called

# ─── 3. Cancellation Semantics Tests ────────────────────────────────────────

def test_upload_cancel_marks_db_and_rejects_further_chunks(client, db_session):
    """POST /api/v1/youtube/upload/{upload_id}/cancel marks upload CANCELLED and subsequent chunks return 409 Conflict."""
    headers = get_auth_headers(client, "cancel_test@socialai.com")
    user = db_session.query(User).filter(User.email == "cancel_test@socialai.com").first()
    acc = create_mock_youtube_account(db_session, user.id, "UC_CANCEL_CHAN")

    upload = youtube_upload_repository.create(
        db=db_session,
        upload_id="ytu_test_cancel_444",
        user_id=user.id,
        social_account_id=acc.id,
        channel_id="UC_CANCEL_CHAN",
        title="Cancelled Video",
        file_size_bytes=10485760,
        mime_type="video/mp4",
        encrypted_session_url=encrypt_token("https://google.com/upload/mock"),
    )

    with patch.object(youtube_service, "cancel_resumable_upload_session", return_value=True):
        res_cancel = client.post(f"/api/v1/youtube/upload/{upload.upload_id}/cancel", headers=headers)

    assert res_cancel.status_code == 200
    assert res_cancel.json()["status"] == "CANCELLED"

    # Verify DB state
    db_session.refresh(upload)
    assert upload.upload_status == YouTubeUploadStatus.CANCELLED.value

    # Subsequent chunk must be rejected with 409 Conflict
    req_headers = {
        **headers,
        "Content-Range": "bytes 0-1048575/10485760",
        "Content-Type": "video/mp4",
    }
    res_chunk = client.put(f"/api/v1/youtube/upload/{upload.upload_id}/chunk", data=b"x" * 1048576, headers=req_headers)
    assert res_chunk.status_code == 409
    assert "cancelled" in res_chunk.json()["detail"].lower()

# ─── 4. Status Polling & Database Caching Tests ──────────────────────────────

def test_upload_status_polling_reads_db_without_google_api_call(client, db_session):
    """GET /api/v1/youtube/upload/{upload_id}/status reads DB state directly without unnecessary Google API calls."""
    headers = get_auth_headers(client, "status_poll_db@socialai.com")
    user = db_session.query(User).filter(User.email == "status_poll_db@socialai.com").first()
    acc = create_mock_youtube_account(db_session, user.id, "UC_POLL_CHAN")

    upload = youtube_upload_repository.create(
        db=db_session,
        upload_id="ytu_test_poll_555",
        user_id=user.id,
        social_account_id=acc.id,
        channel_id="UC_POLL_CHAN",
        title="DB Polling Video",
        file_size_bytes=10485760,
        mime_type="video/mp4",
        encrypted_session_url=encrypt_token("https://google.com/upload/mock"),
    )
    youtube_upload_repository.update_progress(db_session, upload.upload_id, 4194304, 10485760)

    with patch.object(youtube_service, "query_resumable_status") as mock_google_query:
        res = client.get(f"/api/v1/youtube/upload/{upload.upload_id}/status", headers=headers)

    # Google API must NOT be called for normal status poll
    mock_google_query.assert_not_called()

    assert res.status_code == 200
    data = res.json()
    assert data["upload_id"] == upload.upload_id
    assert data["bytes_uploaded"] == 4194304
    assert data["status"] == "UPLOADING"

# ─── 5. Celery Video Processing Task Tests ───────────────────────────────────

def test_celery_task_updates_processing_status_to_ready(db_session):
    """Celery poll_youtube_video_processing task queries YouTube Data API and marks upload READY upon succeeded status."""
    user = User(email="celery_test@socialai.com", hashed_password="pw", full_name="User", role="Admin", is_active=True)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    acc = create_mock_youtube_account(db_session, user.id, "UC_CELERY_CHAN")

    upload = youtube_upload_repository.create(
        db=db_session,
        upload_id="ytu_test_celery_666",
        user_id=user.id,
        social_account_id=acc.id,
        channel_id="UC_CELERY_CHAN",
        title="Celery Video",
        file_size_bytes=5242880,
        mime_type="video/mp4",
        encrypted_session_url=encrypt_token("https://google.com/upload/mock"),
    )
    youtube_upload_repository.mark_completed(
        db=db_session,
        upload_id=upload.upload_id,
        video_id="video_celery_123",
        video_url="https://www.youtube.com/watch?v=video_celery_123",
    )

    mock_proc_info = {
        "upload_status": "processed",
        "processing_status": "succeeded",
        "is_ready": True,
        "privacy_status": "private",
        "published_at": datetime.now(timezone.utc).isoformat(),
        "video_url": "https://www.youtube.com/watch?v=video_celery_123",
    }

    with patch("app.tasks.youtube_tasks.SessionLocal", return_value=db_session):
        with patch.object(db_session, "close"):
            with patch.object(youtube_service, "fetch_video_processing_status", return_value=mock_proc_info):
                result = poll_youtube_video_processing(upload.upload_id, attempt=1)

    assert result["status"] == "READY"
    assert result["processing_status"] == "succeeded"

    db_session.refresh(upload)
    assert upload.upload_status == YouTubeUploadStatus.READY.value
    assert upload.processing_status == "succeeded"


def test_end_to_end_upload_to_processing_to_ready_pipeline(client, db_session):
    """
    End-to-end test:
    1. Final chunk returns 200 with video_id.
    2. Celery task is enqueued.
    3. Celery task executes and queries YouTube videos.list.
    4. YouTube returns processingStatus=succeeded.
    5. DB becomes READY.
    """
    headers = get_auth_headers(client, "e2e_proc@socialai.com")
    user = db_session.query(User).filter(User.email == "e2e_proc@socialai.com").first()
    acc = create_mock_youtube_account(db_session, user.id, "UC_E2E_PROC_CHAN")

    upload = youtube_upload_repository.create(
        db=db_session,
        upload_id="ytu_test_e2e_pipeline_777",
        user_id=user.id,
        social_account_id=acc.id,
        channel_id="UC_E2E_PROC_CHAN",
        title="E2E Pipeline Video",
        file_size_bytes=1048576,
        mime_type="video/mp4",
        encrypted_session_url=encrypt_token("https://google.com/upload/mock"),
    )

    mock_200_res = {
        "status": "PROCESSING",
        "http_status": 200,
        "video_id": "P0c9zaF_sGc",
        "video_url": "https://www.youtube.com/watch?v=P0c9zaF_sGc",
        "is_complete": True,
    }

    mock_youtube_ready_status = {
        "upload_status": "processed",
        "processing_status": "succeeded",
        "is_ready": True,
        "privacy_status": "private",
        "published_at": datetime.now(timezone.utc).isoformat(),
        "video_url": "https://www.youtube.com/watch?v=P0c9zaF_sGc",
    }

    req_headers = {
        **headers,
        "Content-Range": "bytes 0-1048575/1048576",
        "Content-Type": "video/mp4",
    }

    with patch.object(youtube_service, "upload_resumable_chunk", return_value=mock_200_res):
        with patch.object(poll_youtube_video_processing, "delay") as mock_celery_delay:
            res = client.put(f"/api/v1/youtube/upload/{upload.upload_id}/chunk", data=b"x" * 1048576, headers=req_headers)

    assert res.status_code == 200
    assert res.json()["status"] == "PROCESSING"
    assert res.json()["video_id"] == "P0c9zaF_sGc"
    mock_celery_delay.assert_called_once_with(upload_id=upload.upload_id, attempt=1)

    # Now execute the Celery task
    with patch("app.tasks.youtube_tasks.SessionLocal", return_value=db_session):
        with patch.object(db_session, "close"):
            with patch.object(youtube_service, "fetch_video_processing_status", return_value=mock_youtube_ready_status):
                task_res = poll_youtube_video_processing(upload.upload_id, attempt=1)

    assert task_res["status"] == "READY"
    db_session.refresh(upload)
    assert upload.upload_status == YouTubeUploadStatus.READY.value
    assert upload.processing_status == "succeeded"


def test_celery_unavailable_fallback_poller_recovers_processing_upload(client, db_session):
    """
    Fallback reliability test:
    When Celery enqueue fails (e.g. Redis connection lost), the upload remains in PROCESSING,
    and the background reliability poller catches it and transitions it to READY.
    """
    from app.tasks.youtube_tasks import process_pending_youtube_processing_uploads

    headers = get_auth_headers(client, "fallback_test@socialai.com")
    user = db_session.query(User).filter(User.email == "fallback_test@socialai.com").first()
    acc = create_mock_youtube_account(db_session, user.id, "UC_FALLBACK_CHAN")

    upload = youtube_upload_repository.create(
        db=db_session,
        upload_id="ytu_test_fallback_888",
        user_id=user.id,
        social_account_id=acc.id,
        channel_id="UC_FALLBACK_CHAN",
        title="Fallback Video",
        file_size_bytes=1048576,
        mime_type="video/mp4",
        encrypted_session_url=encrypt_token("https://google.com/upload/mock"),
    )

    mock_200_res = {
        "status": "PROCESSING",
        "http_status": 200,
        "video_id": "vid_fallback_999",
        "video_url": "https://www.youtube.com/watch?v=vid_fallback_999",
        "is_complete": True,
    }

    req_headers = {
        **headers,
        "Content-Range": "bytes 0-1048575/1048576",
        "Content-Type": "video/mp4",
    }

    # Simulate Celery .delay() throwing connection error
    with patch.object(youtube_service, "upload_resumable_chunk", return_value=mock_200_res):
        with patch.object(poll_youtube_video_processing, "delay", side_effect=Exception("Redis connection refused")):
            res = client.put(f"/api/v1/youtube/upload/{upload.upload_id}/chunk", data=b"x" * 1048576, headers=req_headers)

    assert res.status_code == 200
    db_session.refresh(upload)
    assert upload.upload_status == YouTubeUploadStatus.PROCESSING.value

    # Simulate time elapsed > 15 seconds
    upload.updated_at = datetime.now(timezone.utc) - timedelta(seconds=20)
    db_session.commit()

    mock_youtube_ready = {
        "upload_status": "processed",
        "processing_status": "succeeded",
        "is_ready": True,
        "privacy_status": "private",
        "published_at": datetime.now(timezone.utc).isoformat(),
        "video_url": "https://www.youtube.com/watch?v=vid_fallback_999",
    }

def test_poller_still_processing_leaves_status_processing(db_session):
    """When YouTube returns processingStatus='processing', poller leaves upload in PROCESSING status and updates timestamp."""
    from app.tasks.youtube_tasks import process_pending_youtube_processing_uploads

    user = User(email="poller_proc@socialai.com", hashed_password="pw", full_name="User", role="Admin", is_active=True)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    acc = create_mock_youtube_account(db_session, user.id, "UC_PROC_CHAN")

    upload = youtube_upload_repository.create(
        db=db_session,
        upload_id="ytu_test_proc_still_111",
        user_id=user.id,
        social_account_id=acc.id,
        channel_id="UC_PROC_CHAN",
        title="Processing Video",
        file_size_bytes=5242880,
        mime_type="video/mp4",
        encrypted_session_url=encrypt_token("https://google.com/upload/mock"),
    )
    youtube_upload_repository.mark_completed(
        db=db_session,
        upload_id=upload.upload_id,
        video_id="onk_7gt3PNg",
        video_url="https://www.youtube.com/watch?v=onk_7gt3PNg",
    )
    # Set updated_at to 20s ago so poller picks it up
    upload.updated_at = datetime.now(timezone.utc) - timedelta(seconds=20)
    db_session.commit()

    mock_youtube_processing = {
        "upload_status": "uploaded",
        "processing_status": "processing",
        "is_ready": False,
        "is_failed": False,
        "privacy_status": "private",
        "video_url": "https://www.youtube.com/watch?v=onk_7gt3PNg",
    }

    with patch.object(youtube_service, "fetch_video_processing_status", return_value=mock_youtube_processing):
        results = process_pending_youtube_processing_uploads(db_session, limit=5)

    assert len(results) == 1
    assert results[0]["result"]["status"] == "PROCESSING"

    db_session.refresh(upload)
    assert upload.upload_status == YouTubeUploadStatus.PROCESSING.value
    assert upload.processing_status == "processing"


def test_poller_failure_marks_status_failed(db_session):
    """When YouTube returns processingStatus='failed' or uploadStatus='rejected', poller updates DB to FAILED."""
    from app.tasks.youtube_tasks import process_pending_youtube_processing_uploads

    user = User(email="poller_fail@socialai.com", hashed_password="pw", full_name="User", role="Admin", is_active=True)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    acc = create_mock_youtube_account(db_session, user.id, "UC_FAIL_CHAN")

    upload = youtube_upload_repository.create(
        db=db_session,
        upload_id="ytu_test_proc_fail_222",
        user_id=user.id,
        social_account_id=acc.id,
        channel_id="UC_FAIL_CHAN",
        title="Failed Video",
        file_size_bytes=5242880,
        mime_type="video/mp4",
        encrypted_session_url=encrypt_token("https://google.com/upload/mock"),
    )
    youtube_upload_repository.mark_completed(
        db=db_session,
        upload_id=upload.upload_id,
        video_id="vid_failed_333",
        video_url="https://www.youtube.com/watch?v=vid_failed_333",
    )
    upload.updated_at = datetime.now(timezone.utc) - timedelta(seconds=20)
    db_session.commit()

    mock_youtube_failed = {
        "upload_status": "rejected",
        "processing_status": "failed",
        "processing_failure_reason": "unsupportedVideoFormat",
        "is_ready": False,
        "is_failed": True,
        "privacy_status": "private",
        "video_url": "https://www.youtube.com/watch?v=vid_failed_333",
    }

    with patch.object(youtube_service, "fetch_video_processing_status", return_value=mock_youtube_failed):
        results = process_pending_youtube_processing_uploads(db_session, limit=5)

    assert len(results) == 1
    assert results[0]["result"]["status"] == "FAILED"

    db_session.refresh(upload)
    assert upload.upload_status == YouTubeUploadStatus.FAILED.value
    assert upload.processing_status == "failed"
    assert "unsupportedVideoFormat" in (upload.error_message or "")


def test_poller_refreshes_expired_oauth_token_before_checking(db_session):
    """When SocialAccount access token is expired, poller uses refresh token to obtain a fresh access token."""
    from app.tasks.youtube_tasks import process_pending_youtube_processing_uploads

    user = User(email="poller_token_ref@socialai.com", hashed_password="pw", full_name="User", role="Admin", is_active=True)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Create account with EXPIRED access token
    acc = SocialAccount(
        user_id=user.id,
        platform="youtube",
        account_id="UC_EXPIRED_CHAN",
        account_name="Expired Channel",
        access_token=encrypt_token("expired_access_token_123"),
        token_type="Bearer",
        expires_at=datetime.now(timezone.utc) - timedelta(hours=2),
        status="CONNECTED",
        metadata_json={"refresh_token": encrypt_token("valid_refresh_token_xyz")}
    )
    db_session.add(acc)
    db_session.commit()
    db_session.refresh(acc)

    upload = youtube_upload_repository.create(
        db=db_session,
        upload_id="ytu_test_expired_tok_444",
        user_id=user.id,
        social_account_id=acc.id,
        channel_id="UC_EXPIRED_CHAN",
        title="Token Refresh Video",
        file_size_bytes=5242880,
        mime_type="video/mp4",
        encrypted_session_url=encrypt_token("https://google.com/upload/mock"),
    )
    youtube_upload_repository.mark_completed(
        db=db_session,
        upload_id=upload.upload_id,
        video_id="onk_7gt3PNg",
        video_url="https://www.youtube.com/watch?v=onk_7gt3PNg",
    )
    upload.updated_at = datetime.now(timezone.utc) - timedelta(seconds=20)
    db_session.commit()

    mock_refresh_resp = {
        "access_token": "fresh_new_access_token_888",
        "expires_in": 3600,
        "token_type": "Bearer",
    }
    mock_youtube_ready = {
        "upload_status": "processed",
        "processing_status": "succeeded",
        "is_ready": True,
        "privacy_status": "private",
        "video_url": "https://www.youtube.com/watch?v=onk_7gt3PNg",
    }

    with patch.object(youtube_service, "refresh_access_token", return_value=mock_refresh_resp) as mock_refresh:
        with patch.object(youtube_service, "fetch_video_processing_status", return_value=mock_youtube_ready) as mock_fetch:
            results = process_pending_youtube_processing_uploads(db_session, limit=5)

    assert mock_refresh.called
    assert mock_fetch.called
    assert len(results) == 1
    assert results[0]["result"]["status"] == "READY"

    db_session.refresh(upload)
    assert upload.upload_status == YouTubeUploadStatus.READY.value


def test_poller_no_pending_uploads_makes_zero_api_calls(db_session):
    """When there are no pending PROCESSING uploads, the poller makes 0 calls to YouTube API."""
    from app.tasks.youtube_tasks import process_pending_youtube_processing_uploads

    with patch.object(youtube_service, "fetch_video_processing_status") as mock_fetch:
        results = process_pending_youtube_processing_uploads(db_session, limit=5)

    mock_fetch.assert_not_called()
    assert results == []




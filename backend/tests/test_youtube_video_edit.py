import pytest
import io
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

from app.models.user import User
from app.models.social_account import SocialAccount
from app.models.youtube_upload import YouTubeUpload, YouTubeUploadStatus
from app.core.security_encryption import encrypt_token
from app.services.youtube_service import (
    youtube_service,
    YouTubeAPIException,
)
from app.repositories.youtube_upload_repository import youtube_upload_repo


def get_auth_headers(client, email="yt_edit_user@socialai.com"):
    reg_payload = {
        "email": email,
        "password": "Password123!",
        "full_name": "YouTube Video Editor",
        "role": "Editor"
    }
    client.post("/api/v1/auth/register", json=reg_payload)
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_mock_youtube_account(db_session, user_id, account_id="UC_EDIT_CHAN_01", platform="youtube"):
    acc = SocialAccount(
        user_id=user_id,
        platform=platform,
        account_id=account_id,
        account_name="Edit Test Channel",
        access_token=encrypt_token("mock_edit_access_token"),
        token_type="Bearer",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        status="CONNECTED",
        metadata_json={"refresh_token": encrypt_token("mock_edit_refresh_token")}
    )
    db_session.add(acc)
    db_session.commit()
    db_session.refresh(acc)
    return acc


def create_mock_youtube_upload(db_session, user_id, social_account_id, video_id="vid_edit_123"):
    upload = youtube_upload_repo.create(
        db=db_session,
        upload_id=f"ytu_{video_id}",
        user_id=user_id,
        social_account_id=social_account_id,
        channel_id="UC_EDIT_CHAN_01",
        title="Original Video Title",
        description="Original video description",
        file_size_bytes=10 * 1024 * 1024,
        privacy_status="private",
        thumbnail_url="https://res.cloudinary.com/demo/image/upload/v1/old_thumb.jpg",
    )
    youtube_upload_repo.mark_completed(
        db=db_session,
        upload_id=f"ytu_{video_id}",
        video_id=video_id,
        video_url=f"https://www.youtube.com/watch?v={video_id}"
    )
    db_session.refresh(upload)
    return upload


# ─── 1. Authentication & Security Tests ───────────────────────────────────────

def test_get_video_details_requires_auth(client):
    """GET /api/v1/youtube/videos/{video_id} returns 401 without authentication."""
    res = client.get("/api/v1/youtube/videos/vid_test_123")
    assert res.status_code == 401


def test_put_video_details_requires_auth(client):
    """PUT /api/v1/youtube/videos/{video_id} returns 401 without authentication."""
    res = client.put("/api/v1/youtube/videos/vid_test_123", json={"title": "New Title"})
    assert res.status_code == 401


def test_video_access_cross_tenant_isolation(client, db_session):
    """User B cannot view or edit User A's YouTube video."""
    user_a = db_session.query(User).filter(User.email == "user_a@socialai.com").first()
    if not user_a:
        user_a = User(email="user_a@socialai.com", hashed_password="pw", full_name="User A", role="Editor")
        db_session.add(user_a)
        db_session.commit()
        db_session.refresh(user_a)

    acc_a = create_mock_youtube_account(db_session, user_a.id, account_id="UC_USER_A")
    create_mock_youtube_upload(db_session, user_a.id, acc_a.id, video_id="vid_user_a_only")

    # User B logs in
    headers_b = get_auth_headers(client, "user_b_attacker@socialai.com")

    # User B tries to access User A's video without having connected YouTube account
    res = client.get("/api/v1/youtube/videos/vid_user_a_only", headers=headers_b)
    assert res.status_code in (403, 404)

    # User B tries to update User A's video
    res_put = client.put(
        "/api/v1/youtube/videos/vid_user_a_only",
        json={"title": "Hacked Title"},
        headers=headers_b
    )
    assert res_put.status_code in (403, 404)


# ─── 2. GET Video Metadata Tests ──────────────────────────────────────────────

def test_get_video_details_success(client, db_session):
    """GET /api/v1/youtube/videos/{video_id} returns formatted metadata from YouTube."""
    headers = get_auth_headers(client, "yt_edit_getter@socialai.com")
    user = db_session.query(User).filter(User.email == "yt_edit_getter@socialai.com").first()
    acc = create_mock_youtube_account(db_session, user.id, account_id="UC_GET_CHAN")
    create_mock_youtube_upload(db_session, user.id, acc.id, video_id="vid_get_success")

    mock_yt_response = {
        "items": [
            {
                "id": "vid_get_success",
                "snippet": {
                    "channelId": "UC_GET_CHAN",
                    "channelTitle": "Edit Test Channel",
                    "title": "My Awesome YouTube Video",
                    "description": "Full description of my video.",
                    "tags": ["tech", "ai", "coding"],
                    "categoryId": "28",
                    "thumbnails": {
                        "high": {"url": "https://i.ytimg.com/vi/vid_get_success/hqdefault.jpg"}
                    }
                },
                "status": {
                    "privacyStatus": "public",
                    "selfDeclaredMadeForKids": False,
                    "uploadStatus": "processed"
                }
            }
        ]
    }

    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_yt_response

        res = client.get("/api/v1/youtube/videos/vid_get_success", headers=headers)

    assert res.status_code == 200
    data = res.json()
    assert data["video_id"] == "vid_get_success"
    assert data["title"] == "My Awesome YouTube Video"
    assert data["description"] == "Full description of my video."
    assert data["tags"] == ["tech", "ai", "coding"]
    assert data["category_id"] == "28"
    assert data["privacy_status"] == "public"
    assert data["made_for_kids"] is False
    assert data["thumbnail_url"] == "https://i.ytimg.com/vi/vid_get_success/hqdefault.jpg"
    assert data["video_url"] == "https://www.youtube.com/watch?v=vid_get_success"


# ─── 3. PUT Video Metadata Update Tests ───────────────────────────────────────

def test_update_video_metadata_title_and_description(client, db_session):
    """PUT /api/v1/youtube/videos/{video_id} successfully updates title and description."""
    headers = get_auth_headers(client, "yt_edit_title@socialai.com")
    user = db_session.query(User).filter(User.email == "yt_edit_title@socialai.com").first()
    acc = create_mock_youtube_account(db_session, user.id, account_id="UC_TITLE_CHAN")
    create_mock_youtube_upload(db_session, user.id, acc.id, video_id="vid_title_update")

    mock_existing = {
        "items": [{
            "id": "vid_title_update",
            "snippet": {
                "channelId": "UC_TITLE_CHAN",
                "title": "Old Title",
                "description": "Old description",
                "tags": ["old"],
                "categoryId": "28",
            },
            "status": {
                "privacyStatus": "private",
                "selfDeclaredMadeForKids": False,
            }
        }]
    }

    mock_updated_response = {
        "id": "vid_title_update",
        "snippet": {
            "channelId": "UC_TITLE_CHAN",
            "title": "Brand New Updated Title",
            "description": "Brand new detailed description.",
            "tags": ["old"],
            "categoryId": "28",
        },
        "status": {
            "privacyStatus": "private",
            "selfDeclaredMadeForKids": False,
        }
    }

    with patch("requests.get") as mock_get, patch("requests.put") as mock_put:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_existing

        mock_put.return_value.status_code = 200
        mock_put.return_value.json.return_value = mock_updated_response

        payload = {
            "title": "Brand New Updated Title",
            "description": "Brand new detailed description."
        }
        res = client.put("/api/v1/youtube/videos/vid_title_update", json=payload, headers=headers)

    assert res.status_code == 200
    data = res.json()
    assert data["video_id"] == "vid_title_update"
    assert data["title"] == "Brand New Updated Title"
    assert data["description"] == "Brand new detailed description."

    # Verify that requests.put was sent with merged payload containing both id, snippet, and status
    assert mock_put.called
    sent_body = mock_put.call_args[1]["json"]
    assert sent_body["id"] == "vid_title_update"
    assert sent_body["snippet"]["title"] == "Brand New Updated Title"
    assert sent_body["snippet"]["tags"] == ["old"]  # Preserved!
    assert sent_body["snippet"]["categoryId"] == "28"  # Preserved!
    assert sent_body["status"]["privacyStatus"] == "private"  # Preserved!


def test_update_video_tags_and_category(client, db_session):
    """PUT /api/v1/youtube/videos/{video_id} updates tags and category while preserving title."""
    headers = get_auth_headers(client, "yt_edit_tags@socialai.com")
    user = db_session.query(User).filter(User.email == "yt_edit_tags@socialai.com").first()
    acc = create_mock_youtube_account(db_session, user.id, account_id="UC_TAGS_CHAN")
    create_mock_youtube_upload(db_session, user.id, acc.id, video_id="vid_tags_update")

    mock_existing = {
        "items": [{
            "id": "vid_tags_update",
            "snippet": {
                "channelId": "UC_TAGS_CHAN",
                "title": "Preserved Video Title",
                "description": "Preserved description",
                "tags": ["old_tag"],
                "categoryId": "28",
            },
            "status": {
                "privacyStatus": "unlisted",
                "selfDeclaredMadeForKids": False,
            }
        }]
    }

    mock_updated = {
        "id": "vid_tags_update",
        "snippet": {
            "channelId": "UC_TAGS_CHAN",
            "title": "Preserved Video Title",
            "description": "Preserved description",
            "tags": ["react", "nextjs", "fastapi"],
            "categoryId": "27",  # Education
        },
        "status": {
            "privacyStatus": "unlisted",
            "selfDeclaredMadeForKids": False,
        }
    }

    with patch("requests.get") as mock_get, patch("requests.put") as mock_put:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_existing

        mock_put.return_value.status_code = 200
        mock_put.return_value.json.return_value = mock_updated

        payload = {
            "tags": ["react", "nextjs", "fastapi"],
            "category_id": "27"
        }
        res = client.put("/api/v1/youtube/videos/vid_tags_update", json=payload, headers=headers)

    assert res.status_code == 200
    data = res.json()
    assert data["tags"] == ["react", "nextjs", "fastapi"]
    assert data["category_id"] == "27"
    assert data["title"] == "Preserved Video Title"


def test_update_video_privacy_and_made_for_kids(client, db_session):
    """PUT /api/v1/youtube/videos/{video_id} updates privacy status and madeForKids declaration."""
    headers = get_auth_headers(client, "yt_edit_privacy@socialai.com")
    user = db_session.query(User).filter(User.email == "yt_edit_privacy@socialai.com").first()
    acc = create_mock_youtube_account(db_session, user.id, account_id="UC_PRIV_CHAN")
    create_mock_youtube_upload(db_session, user.id, acc.id, video_id="vid_priv_update")

    mock_existing = {
        "items": [{
            "id": "vid_priv_update",
            "snippet": {
                "channelId": "UC_PRIV_CHAN",
                "title": "Public Launch",
                "description": "Launch desc",
                "tags": [],
                "categoryId": "28",
            },
            "status": {
                "privacyStatus": "private",
                "selfDeclaredMadeForKids": False,
            }
        }]
    }

    mock_updated = {
        "id": "vid_priv_update",
        "snippet": {
            "channelId": "UC_PRIV_CHAN",
            "title": "Public Launch",
            "description": "Launch desc",
            "tags": [],
            "categoryId": "28",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": True,
        }
    }

    with patch("requests.get") as mock_get, patch("requests.put") as mock_put:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_existing

        mock_put.return_value.status_code = 200
        mock_put.return_value.json.return_value = mock_updated

        payload = {
            "privacy_status": "public",
            "made_for_kids": True
        }
        res = client.put("/api/v1/youtube/videos/vid_priv_update", json=payload, headers=headers)

    assert res.status_code == 200
    data = res.json()
    assert data["privacy_status"] == "public"
    assert data["made_for_kids"] is True


def test_update_video_invalid_privacy_status_rejected(client, db_session):
    """PUT /api/v1/youtube/videos/{video_id} rejects invalid privacy status with 400."""
    headers = get_auth_headers(client, "yt_invalid_priv@socialai.com")
    user = db_session.query(User).filter(User.email == "yt_invalid_priv@socialai.com").first()
    acc = create_mock_youtube_account(db_session, user.id, account_id="UC_INV_CHAN")
    create_mock_youtube_upload(db_session, user.id, acc.id, video_id="vid_inv_priv")

    res = client.put(
        "/api/v1/youtube/videos/vid_inv_priv",
        json={"privacy_status": "super_secret"},
        headers=headers
    )
    assert res.status_code == 400


def test_update_video_with_custom_thumbnail(client, db_session):
    """PUT /api/v1/youtube/videos/{video_id} applies custom thumbnail when thumbnail_url is provided."""
    headers = get_auth_headers(client, "yt_edit_thumb@socialai.com")
    user = db_session.query(User).filter(User.email == "yt_edit_thumb@socialai.com").first()
    acc = create_mock_youtube_account(db_session, user.id, account_id="UC_THUMB_EDIT_CHAN")
    create_mock_youtube_upload(db_session, user.id, acc.id, video_id="vid_thumb_edit")

    mock_existing = {
        "items": [{
            "id": "vid_thumb_edit",
            "snippet": {
                "channelId": "UC_THUMB_EDIT_CHAN",
                "title": "Thumbnail Video",
                "description": "Video desc",
                "categoryId": "28",
            },
            "status": {"privacyStatus": "public"}
        }]
    }

    mock_updated = {
        "id": "vid_thumb_edit",
        "snippet": {
            "channelId": "UC_THUMB_EDIT_CHAN",
            "title": "Thumbnail Video",
            "description": "Video desc",
            "categoryId": "28",
        },
        "status": {"privacyStatus": "public"}
    }

    new_thumb_url = "https://res.cloudinary.com/demo/image/upload/v1234/new_edit_thumb.jpg"

    with patch("requests.get") as mock_get, \
         patch("requests.put") as mock_put, \
         patch("app.services.youtube_service.youtube_service.apply_thumbnail_from_storage") as mock_apply_thumb:

        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_existing

        mock_put.return_value.status_code = 200
        mock_put.return_value.json.return_value = mock_updated

        mock_apply_thumb.return_value = {"status": "success"}

        payload = {
            "title": "Thumbnail Video",
            "thumbnail_url": new_thumb_url
        }
        res = client.put("/api/v1/youtube/videos/vid_thumb_edit", json=payload, headers=headers)

    assert res.status_code == 200
    data = res.json()
    assert data["thumbnail_url"] == new_thumb_url
    assert mock_apply_thumb.called
    assert mock_apply_thumb.call_args[1]["video_id"] == "vid_thumb_edit"
    assert mock_apply_thumb.call_args[1]["thumbnail_url"] == new_thumb_url


# ─── 4. Error Handling Tests ──────────────────────────────────────────────────

def test_youtube_api_403_forbidden_handled(client, db_session):
    """PUT /api/v1/youtube/videos/{video_id} returns 403 when YouTube rejects permissions."""
    headers = get_auth_headers(client, "yt_403_user@socialai.com")
    user = db_session.query(User).filter(User.email == "yt_403_user@socialai.com").first()
    acc = create_mock_youtube_account(db_session, user.id, account_id="UC_403_CHAN")
    create_mock_youtube_upload(db_session, user.id, acc.id, video_id="vid_403_test")

    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 403
        mock_get.return_value.json.return_value = {
            "error": {
                "message": "The user is not authorized to edit this video."
            }
        }

        res = client.get("/api/v1/youtube/videos/vid_403_test", headers=headers)

    assert res.status_code == 403
    assert "not authorized" in res.json()["detail"].lower()


def test_youtube_api_404_not_found_handled(client, db_session):
    """GET /api/v1/youtube/videos/{video_id} returns 404 when video does not exist on YouTube."""
    headers = get_auth_headers(client, "yt_404_user@socialai.com")
    user = db_session.query(User).filter(User.email == "yt_404_user@socialai.com").first()
    acc = create_mock_youtube_account(db_session, user.id, account_id="UC_404_CHAN")
    create_mock_youtube_upload(db_session, user.id, acc.id, video_id="vid_404_test")

    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"items": []}

        res = client.get("/api/v1/youtube/videos/vid_404_test", headers=headers)

    assert res.status_code == 404


# ─── 5. Invariant Tests: Video ID Preserved & Upload Engine Untouched ──────────

def test_video_id_and_upload_engine_invariant(client, db_session):
    """Verify that editing video metadata maintains the identical video_id and NEVER invokes upload chunk engine."""
    headers = get_auth_headers(client, "yt_invariant_user@socialai.com")
    user = db_session.query(User).filter(User.email == "yt_invariant_user@socialai.com").first()
    acc = create_mock_youtube_account(db_session, user.id, account_id="UC_INV_CHAN_01")
    original_video_id = "ABC123XYZ"
    create_mock_youtube_upload(db_session, user.id, acc.id, video_id=original_video_id)

    mock_existing = {
        "items": [{
            "id": original_video_id,
            "snippet": {
                "channelId": "UC_INV_CHAN_01",
                "title": "Original Invariant Title",
                "description": "Original",
                "categoryId": "28",
            },
            "status": {"privacyStatus": "private"}
        }]
    }

    mock_updated = {
        "id": original_video_id,
        "snippet": {
            "channelId": "UC_INV_CHAN_01",
            "title": "Updated Invariant Title",
            "description": "Original",
            "categoryId": "28",
        },
        "status": {"privacyStatus": "private"}
    }

    with patch("requests.get") as mock_get, \
         patch("requests.put") as mock_put, \
         patch("app.services.youtube_service.youtube_service.initiate_resumable_upload") as mock_initiate, \
         patch("app.services.youtube_service.youtube_service.upload_resumable_chunk") as mock_chunk:

        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_existing

        mock_put.return_value.status_code = 200
        mock_put.return_value.json.return_value = mock_updated

        res = client.put(
            f"/api/v1/youtube/videos/{original_video_id}",
            json={"title": "Updated Invariant Title"},
            headers=headers
        )

    assert res.status_code == 200
    data = res.json()

    # Invariant 1: video_id remains exactly ABC123XYZ
    assert data["video_id"] == original_video_id

    # Invariant 2: upload engine methods were NEVER invoked
    assert not mock_initiate.called
    assert not mock_chunk.called

    # Invariant 3: local DB record title was updated
    local_record = youtube_upload_repo.get_by_video_id_and_user(db_session, original_video_id, user.id)
    assert local_record is not None
    assert local_record.title == "Updated Invariant Title"
    assert local_record.video_id == original_video_id

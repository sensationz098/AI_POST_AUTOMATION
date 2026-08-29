import pytest
from unittest.mock import patch, MagicMock
from app.services.meta_service import meta_service, MetaPublishException, is_ambiguous_meta_error
from app.services.publisher_service import InstagramPublisher

def test_is_ambiguous_meta_error_helper():
    assert is_ambiguous_meta_error(403, 4, 2207051, "Application request limit reached") is True
    assert is_ambiguous_meta_error(429, 4, None, "Too many requests") is True
    assert is_ambiguous_meta_error(500, None, None, "Internal Server Error") is True
    assert is_ambiguous_meta_error(400, 100, None, "Invalid parameter") is False

def test_instagram_publish_ambiguous_error_published_verified_success():
    """Verify 403 Application request limit reached triggers verification, succeeds if post exists on IG."""
    with patch("requests.post") as mock_post, patch("requests.get") as mock_get:
        # 1. Container creation response
        mock_container_res = MagicMock(status_code=200)
        mock_container_res.json.return_value = {"id": "180831187734431"}

        # 2. Container status FINISHED
        mock_status_res = MagicMock(status_code=200)
        mock_status_res.json.return_value = {"status_code": "FINISHED"}
        mock_get.side_effect = [
            mock_status_res, # Status poll
            # Verification calls (if requests.get is used inside verify helper)
            MagicMock(status_code=200, json=lambda: {"status_code": "FINISHED"}),
            MagicMock(status_code=200, json=lambda: {"data": [{"id": "published_media_777", "caption": "Test Post"}]})
        ]

        # 3. Media publish response: 403 Rate Limit Error
        mock_publish_res = MagicMock(status_code=403)
        mock_publish_res.json.return_value = {
            "error": {
                "message": "Application request limit reached",
                "code": 4,
                "error_subcode": 2207051
            }
        }
        mock_post.side_effect = [mock_container_res, mock_publish_res]

        with patch.object(meta_service, "verify_instagram_container_published") as mock_verify:
            mock_verify.return_value = {
                "is_published": True,
                "published_media_id": "published_media_777",
                "verified_via": "user_media_list"
            }

            res = meta_service.publish_to_instagram_business(
                ig_user_id="17841400000000000",
                access_token="valid_token_123",
                caption="Test Post",
                image_url="https://example.com/image.jpg",
                is_video=False
            )

            assert res["container_id"] == "180831187734431"
            assert res["id"] == "published_media_777"
            assert res["status"] == "published"
            assert res.get("was_ambiguous_verified") is True
            mock_verify.assert_called_once()

def test_instagram_publish_ambiguous_error_not_published_raises_exception():
    """Verify 403 Application request limit reached raises exception if post is NOT verified on IG."""
    with patch("requests.post") as mock_post, patch("requests.get") as mock_get:
        mock_container_res = MagicMock(status_code=200)
        mock_container_res.json.return_value = {"id": "180831187734431"}

        mock_status_res = MagicMock(status_code=200)
        mock_status_res.json.return_value = {"status_code": "FINISHED"}
        mock_get.return_value = mock_status_res

        mock_publish_res = MagicMock(status_code=403)
        mock_publish_res.json.return_value = {
            "error": {
                "message": "Application request limit reached",
                "code": 4,
                "error_subcode": 2207051
            }
        }
        mock_post.side_effect = [mock_container_res, mock_publish_res]

        with patch.object(meta_service, "verify_instagram_container_published") as mock_verify:
            mock_verify.return_value = {"is_published": False}

            with pytest.raises(MetaPublishException) as exc_info:
                meta_service.publish_to_instagram_business(
                    ig_user_id="17841400000000000",
                    access_token="valid_token_123",
                    caption="Test Post",
                    image_url="https://example.com/image.jpg",
                    is_video=False
                )

            assert exc_info.value.status_code == 403
            assert exc_info.value.error_code == 4
            assert exc_info.value.error_subcode == 2207051

def test_instagram_publish_existing_container_reuse():
    """Verify passing existing_container_id uses verify_instagram_container_published to prevent duplicate creation."""
    with patch.object(meta_service, "verify_instagram_container_published") as mock_verify:
        mock_verify.return_value = {
            "is_published": True,
            "published_media_id": "media_reused_888",
            "verified_via": "user_media_list"
        }

        res = meta_service.publish_to_instagram_business(
            ig_user_id="17841400000000000",
            access_token="valid_token_123",
            caption="Reuse Container Test",
            image_url="https://example.com/image.jpg",
            is_video=False,
            existing_container_id="existing_container_999"
        )

        assert res["container_id"] == "existing_container_999"
        assert res["id"] == "media_reused_888"
        assert res["was_retry_verified"] is True
        mock_verify.assert_called_once()

def test_instagram_on_container_created_callback_invoked():
    """Verify on_container_created callback is invoked immediately upon creation."""
    callback_mock = MagicMock()

    with patch("requests.post") as mock_post, patch("requests.get") as mock_get:
        mock_container_res = MagicMock(status_code=200)
        mock_container_res.json.return_value = {"id": "new_created_container_555"}

        mock_status_res = MagicMock(status_code=200)
        mock_status_res.json.return_value = {"status_code": "FINISHED"}
        mock_get.return_value = mock_status_res

        mock_publish_res = MagicMock(status_code=200)
        mock_publish_res.json.return_value = {"id": "published_media_555"}
        mock_post.side_effect = [mock_container_res, mock_publish_res]

        res = meta_service.publish_to_instagram_business(
            ig_user_id="17841400000000000",
            access_token="valid_token_123",
            caption="Callback Test",
            image_url="https://example.com/image.jpg",
            is_video=False,
            on_container_created=callback_mock
        )

        assert res["container_id"] == "new_created_container_555"
        callback_mock.assert_called_once_with("new_created_container_555")

# ---------------------------------------------------------------------------
# TARGETED VERIFICATION SAFETY TESTS (TEST 1 - TEST 6)
# ---------------------------------------------------------------------------
from datetime import datetime, timezone, timedelta

def test_fallback_verify_exact_caption_and_valid_timestamp_success():
    """TEST 1: Exact caption match + timestamp inside allowed publish attempt window succeeds."""
    now = datetime.now(timezone.utc)
    valid_ts = now.isoformat()

    with patch("requests.get") as mock_get:
        # Container check returns FINISHED (falls through to account media check)
        c_res = MagicMock(status_code=200)
        c_res.json.return_value = {"status_code": "FINISHED"}

        # Account media list returns 1 post with exact caption and valid timestamp
        m_res = MagicMock(status_code=200)
        m_res.json.return_value = {
            "data": [
                {"id": "media_exact_101", "caption": "Exact Caption Match", "timestamp": valid_ts}
            ]
        }
        mock_get.side_effect = [c_res, m_res]

        res = meta_service.verify_instagram_container_published(
            ig_user_id="17841400000000000",
            creation_id="container_101",
            access_token="valid_token",
            caption="Exact Caption Match",
            publish_started_at=now
        )

        assert res["is_published"] is True
        assert res["published_media_id"] == "media_exact_101"
        assert res["verification_source"] == "account_media_list"

def test_fallback_verify_substring_caption_rejected():
    """TEST 2: Substring / partial caption match is REJECTED."""
    now = datetime.now(timezone.utc)
    valid_ts = now.isoformat()

    with patch("requests.get") as mock_get:
        c_res = MagicMock(status_code=200)
        c_res.json.return_value = {"status_code": "FINISHED"}

        # Account has "Sale", target is "Big Summer Sale"
        m_res = MagicMock(status_code=200)
        m_res.json.return_value = {
            "data": [
                {"id": "media_old_sale", "caption": "Sale", "timestamp": valid_ts}
            ]
        }
        mock_get.side_effect = [c_res, m_res]

        res = meta_service.verify_instagram_container_published(
            ig_user_id="17841400000000000",
            creation_id="container_102",
            access_token="valid_token",
            caption="Big Summer Sale",
            publish_started_at=now
        )

        assert res["is_published"] is False
        assert res["verification_source"] == "verification_failed"

def test_fallback_verify_older_post_outside_time_window_rejected():
    """TEST 3: Older post with identical caption outside publish window is REJECTED."""
    now = datetime.now(timezone.utc)
    old_ts = (now - timedelta(hours=2)).isoformat() # 2 hours old (outside 15 min window)

    with patch("requests.get") as mock_get:
        c_res = MagicMock(status_code=200)
        c_res.json.return_value = {"status_code": "FINISHED"}

        m_res = MagicMock(status_code=200)
        m_res.json.return_value = {
            "data": [
                {"id": "media_old_post", "caption": "Daily Update", "timestamp": old_ts}
            ]
        }
        mock_get.side_effect = [c_res, m_res]

        res = meta_service.verify_instagram_container_published(
            ig_user_id="17841400000000000",
            creation_id="container_103",
            access_token="valid_token",
            caption="Daily Update",
            publish_started_at=now
        )

        assert res["is_published"] is False
        assert res["verification_source"] == "verification_failed"

def test_fallback_verify_concurrent_identical_captions_fails_conservatively():
    """TEST 4: Two concurrent posts with identical captions return conservative failure (>1 matches)."""
    now = datetime.now(timezone.utc)
    valid_ts = now.isoformat()

    with patch("requests.get") as mock_get:
        c_res = MagicMock(status_code=200)
        c_res.json.return_value = {"status_code": "FINISHED"}

        # Account media returns TWO items matching exact caption inside timestamp window
        m_res = MagicMock(status_code=200)
        m_res.json.return_value = {
            "data": [
                {"id": "media_job_a", "caption": "Concurrent Flash Sale", "timestamp": valid_ts},
                {"id": "media_job_b", "caption": "Concurrent Flash Sale", "timestamp": valid_ts}
            ]
        }
        mock_get.side_effect = [c_res, m_res]

        res = meta_service.verify_instagram_container_published(
            ig_user_id="17841400000000000",
            creation_id="container_104",
            access_token="valid_token",
            caption="Concurrent Flash Sale",
            publish_started_at=now
        )

        # Must fail conservatively (is_published=False) to avoid arbitrarily assigning media ID
        assert res["is_published"] is False
        assert res["verification_source"] == "verification_failed"

def test_direct_container_status_published_success():
    """TEST 5: Direct container status == PUBLISHED succeeds immediately without media list fallback."""
    with patch("requests.get") as mock_get:
        c_res = MagicMock(status_code=200)
        c_res.json.return_value = {"status_code": "PUBLISHED", "id": "pub_media_direct_555"}
        mock_get.return_value = c_res

        res = meta_service.verify_instagram_container_published(
            ig_user_id="17841400000000000",
            creation_id="container_105",
            access_token="valid_token",
            caption="Any Caption"
        )

        assert res["is_published"] is True
        assert res["published_media_id"] == "pub_media_direct_555"
        assert res["verification_source"] == "container_status"
        assert mock_get.call_count == 1 # Media list endpoint was NOT called

def test_container_status_finished_does_not_mean_published():
    """TEST 6: Container status == FINISHED does NOT automatically mean published."""
    with patch("requests.get") as mock_get:
        c_res = MagicMock(status_code=200)
        c_res.json.return_value = {"status_code": "FINISHED"}

        m_res = MagicMock(status_code=200)
        m_res.json.return_value = {"data": []} # Empty media list
        mock_get.side_effect = [c_res, m_res]

        res = meta_service.verify_instagram_container_published(
            ig_user_id="17841400000000000",
            creation_id="container_106",
            access_token="valid_token",
            caption="Unpublished Post"
        )

        assert res["is_published"] is False
        assert res["verification_source"] == "verification_failed"

def test_fallback_verify_missing_timestamp_rejected():
    """Verify media item with exact caption match but missing or None timestamp is REJECTED."""
    now = datetime.now(timezone.utc)

    with patch("requests.get") as mock_get:
        c_res = MagicMock(status_code=200)
        c_res.json.return_value = {"status_code": "FINISHED"}

        # Media item has exact caption match but timestamp is None / missing
        m_res = MagicMock(status_code=200)
        m_res.json.return_value = {
            "data": [
                {"id": "media_no_ts", "caption": "Exact Caption", "timestamp": None}
            ]
        }
        mock_get.side_effect = [c_res, m_res]

        res = meta_service.verify_instagram_container_published(
            ig_user_id="17841400000000000",
            creation_id="container_107",
            access_token="valid_token",
            caption="Exact Caption",
            publish_started_at=now
        )

        assert res["is_published"] is False
        assert res["verification_source"] == "verification_failed"



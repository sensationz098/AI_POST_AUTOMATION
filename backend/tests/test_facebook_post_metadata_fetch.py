import pytest
from unittest.mock import patch, MagicMock
from app.services.meta_service import meta_service
from app.services.publisher_service import FacebookPublisher, PublishingEngine
from app.models.social_account import SocialAccount
from app.models.publishing_batch import JobStatus


def test_facebook_video_metadata_fetch_requests_video_compatible_fields():
    """Verify fetch_facebook_post_info with media_type='video' requests description/title instead of message."""
    with patch("requests.get") as mock_get:
        mock_res = MagicMock(status_code=200)
        mock_res.json.return_value = {
            "id": "1234567890",
            "description": "Facebook Video Description",
            "title": "Video Title",
            "permalink_url": "https://www.facebook.com/watch/?v=1234567890",
            "created_time": "2026-03-01T12:00:00+00:00",
            "picture": "https://example.com/thumb.jpg"
        }
        mock_get.return_value = mock_res

        res = meta_service.fetch_facebook_post_info("1234567890", "valid_token", media_type="video")

        assert res is not None
        assert res["id"] == "1234567890"
        assert res["permalink_url"] == "https://www.facebook.com/watch/?v=1234567890"
        assert res["message"] == "Facebook Video Description"  # Normalized
        assert res["full_picture"] == "https://example.com/thumb.jpg"  # Normalized

        # Assert requested fields did NOT include 'message'
        assert mock_get.call_count == 1
        requested_fields = mock_get.call_args.kwargs["params"]["fields"]
        assert "message" not in requested_fields
        assert "description" in requested_fields
        assert "title" in requested_fields
        assert "permalink_url" in requested_fields


def test_facebook_image_metadata_fetch_requests_post_fields():
    """Verify fetch_facebook_post_info with media_type='image' requests standard post fields."""
    with patch("requests.get") as mock_get:
        mock_res = MagicMock(status_code=200)
        mock_res.json.return_value = {
            "id": "page1_post1",
            "message": "Facebook Photo Post Caption",
            "permalink_url": "https://www.facebook.com/page1/posts/post1",
            "created_time": "2026-03-01T12:00:00+00:00",
            "full_picture": "https://example.com/photo.jpg"
        }
        mock_get.return_value = mock_res

        res = meta_service.fetch_facebook_post_info("page1_post1", "valid_token", media_type="image")

        assert res is not None
        assert res["id"] == "page1_post1"
        assert res["permalink_url"] == "https://www.facebook.com/page1/posts/post1"
        assert res["message"] == "Facebook Photo Post Caption"

        assert mock_get.call_count == 1
        requested_fields = mock_get.call_args.kwargs["params"]["fields"]
        assert "message" in requested_fields
        assert "full_picture" in requested_fields
        assert "permalink_url" in requested_fields


def test_facebook_metadata_fetch_falls_back_gracefully_on_nonexisting_field_error():
    """Verify that if initial request fails with (#100) nonexisting field (e.g. Video fetched without media_type), it retries fallback fields."""
    with patch("requests.get") as mock_get:
        # First call fails with OAuthException #100 nonexisting field
        err_res = MagicMock(status_code=400)
        err_res.text = '{"error": {"message": "(#100) Tried accessing nonexisting field (message)", "type": "OAuthException", "code": 100}}'
        err_res.json.return_value = {"error": {"message": "(#100) Tried accessing nonexisting field (message)", "code": 100}}

        # Second call (fallback) succeeds
        success_res = MagicMock(status_code=200)
        success_res.json.return_value = {
            "id": "1234567890",
            "description": "Recovered Video Caption",
            "permalink_url": "https://www.facebook.com/watch/?v=1234567890",
            "created_time": "2026-03-01T12:00:00+00:00",
            "picture": "https://example.com/vid_thumb.jpg"
        }

        mock_get.side_effect = [err_res, success_res]

        # Call without media_type (defaults to post fields first)
        res = meta_service.fetch_facebook_post_info("1234567890", "valid_token")

        assert res is not None
        assert res["id"] == "1234567890"
        assert res["permalink_url"] == "https://www.facebook.com/watch/?v=1234567890"
        assert res["message"] == "Recovered Video Caption"
        assert mock_get.call_count == 2


def test_facebook_metadata_fetch_returns_none_cleanly_on_total_failure():
    """Verify that if all Graph API attempts fail, fetch_facebook_post_info returns None without raising exception."""
    with patch("requests.get") as mock_get:
        mock_res = MagicMock(status_code=404)
        mock_res.text = '{"error": {"message": "Object not found", "code": 803}}'
        mock_get.return_value = mock_res

        res = meta_service.fetch_facebook_post_info("nonexistent_id", "valid_token")
        assert res is None


def test_facebook_publishing_job_succeeds_even_if_metadata_fetch_fails():
    """Verify that if metadata fetch completely fails or raises, the publishing job still finishes as SUCCESS."""
    engine = PublishingEngine()

    acc = SocialAccount(
        id=101,
        user_id=1,
        brand_id=1,
        platform="facebook",
        account_id="100020003000",
        account_name="Test Facebook Page",
        access_token="valid_token",
        status="CONNECTED"
    )

    with patch.object(engine.fb_publisher, "publish", return_value="fb_post_99999"), \
         patch.object(meta_service, "fetch_facebook_post_info", return_value=None), \
         patch("app.services.publisher_service.social_account_repo.get_by_id", return_value=acc), \
         patch("app.services.publisher_service.publishing_repo.update_job_status") as mock_update_status:

        result = engine.process_single_job_in_thread(
            job_id=50,
            social_account_id=101,
            caption="Test FB Post",
            public_media_url="https://res.cloudinary.com/test/video.mp4",
            is_video=True
        )

        assert result["status"] == "SUCCESS"
        assert result["external_id"] == "fb_post_99999"

        # Confirm update_job_status was called with JobStatus.SUCCESS
        success_calls = [c for c in mock_update_status.call_args_list if c.args[2] == JobStatus.SUCCESS.value]
        assert len(success_calls) >= 1

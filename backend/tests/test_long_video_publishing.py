import pytest
from unittest.mock import patch, MagicMock
import requests
from app.core.config import settings
from app.services.meta_service import meta_service, MetaGraphService
from app.services.publisher_service import FacebookPublisher, InstagramPublisher, classify_error

def test_short_video_instagram_publishing_success():
    """Verify ~13 second short video container finishes processing quickly and publishes successfully."""
    with patch("requests.post") as mock_post, patch("requests.get") as mock_get:
        # Step 1 Container Creation Response
        mock_container_res = MagicMock()
        mock_container_res.status_code = 200
        mock_container_res.json.return_value = {"id": "container_123"}

        # Step 3 Media Publish Response
        mock_publish_res = MagicMock()
        mock_publish_res.status_code = 200
        mock_publish_res.json.return_value = {"id": "published_ig_media_999"}

        mock_post.side_effect = [mock_container_res, mock_publish_res]

        # Step 2 Container Status Poll Response
        mock_status_res = MagicMock()
        mock_status_res.status_code = 200
        mock_status_res.json.return_value = {"status_code": "FINISHED"}
        mock_get.return_value = mock_status_res

        res = meta_service.publish_to_instagram_business(
            ig_user_id="17841400000000000",
            access_token="valid_token_123",
            caption="Short Video Reel Test",
            image_url="https://example.com/short_video.mp4",
            is_video=True
        )

        assert res["container_id"] == "container_123"
        assert res["id"] == "published_ig_media_999"
        assert res["status"] == "published"
        assert mock_post.call_count == 2
        assert mock_get.call_count == 1

def test_long_video_instagram_publishing_bounded_polling_success():
    """Verify long video >30s polls multiple times with status IN_PROGRESS before reaching FINISHED and publishing."""
    with patch("requests.post") as mock_post, patch("requests.get") as mock_get, patch("time.sleep") as mock_sleep:
        # Step 1 Container Creation
        mock_container_res = MagicMock()
        mock_container_res.status_code = 200
        mock_container_res.json.return_value = {"id": "container_long_456"}

        # Step 3 Media Publish
        mock_publish_res = MagicMock()
        mock_publish_res.status_code = 200
        mock_publish_res.json.return_value = {"id": "published_ig_media_888"}

        mock_post.side_effect = [mock_container_res, mock_publish_res]

        # Step 2 Polling Sequence: IN_PROGRESS -> IN_PROGRESS -> FINISHED
        mock_poll1 = MagicMock(status_code=200)
        mock_poll1.json.return_value = {"status_code": "IN_PROGRESS", "status": "Video processing 20%"}

        mock_poll2 = MagicMock(status_code=200)
        mock_poll2.json.return_value = {"status_code": "IN_PROGRESS", "status": "Video processing 75%"}

        mock_poll3 = MagicMock(status_code=200)
        mock_poll3.json.return_value = {"status_code": "FINISHED", "status": "Video ready"}

        mock_get.side_effect = [mock_poll1, mock_poll2, mock_poll3]

        res = meta_service.publish_to_instagram_business(
            ig_user_id="17841400000000000",
            access_token="valid_token_123",
            caption="Long Video Reel Test",
            image_url="https://example.com/long_video.mp4",
            is_video=True
        )

        assert res["container_id"] == "container_long_456"
        assert res["id"] == "published_ig_media_888"
        assert mock_get.call_count == 3
        assert mock_sleep.call_count == 2  # Slept twice between polls

def test_instagram_container_polling_timeout_fails_without_publish():
    """Verify that if container stays IN_PROGRESS past max wait time, system aborts without publishing."""
    with patch("requests.post") as mock_post, patch("requests.get") as mock_get, patch("time.sleep"):
        mock_container_res = MagicMock(status_code=200)
        mock_container_res.json.return_value = {"id": "container_timeout_789"}
        mock_post.return_value = mock_container_res

        mock_poll_res = MagicMock(status_code=200)
        mock_poll_res.json.return_value = {"status_code": "IN_PROGRESS"}
        mock_get.return_value = mock_poll_res

        # Set ultra-short timeout for testing
        with patch.object(settings, "META_VIDEO_PROCESSING_MAX_SECONDS", 0.2), \
             patch.object(settings, "META_VIDEO_POLL_INITIAL_SECONDS", 0.05):
            
            with pytest.raises(Exception) as exc_info:
                meta_service.publish_to_instagram_business(
                    ig_user_id="17841400000000000",
                    access_token="valid_token_123",
                    caption="Timeout Reel Test",
                    image_url="https://example.com/huge_video.mp4",
                    is_video=True
                )

            assert "timed out on Meta servers" in str(exc_info.value)
            # Ensure media_publish endpoint was NEVER called (only 1 post call for container creation)
            assert mock_post.call_count == 1

def test_instagram_container_error_state_fails():
    """Verify that if Meta container enters ERROR, publishing fails immediately with Meta's error message."""
    with patch("requests.post") as mock_post, patch("requests.get") as mock_get:
        mock_container_res = MagicMock(status_code=200)
        mock_container_res.json.return_value = {"id": "container_err_101"}
        mock_post.return_value = mock_container_res

        mock_poll_res = MagicMock(status_code=200)
        mock_poll_res.json.return_value = {
            "status_code": "ERROR",
            "status": "The video aspect ratio is not supported for Reels."
        }
        mock_get.return_value = mock_poll_res

        with pytest.raises(Exception) as exc_info:
            meta_service.publish_to_instagram_business(
                ig_user_id="17841400000000000",
                access_token="valid_token_123",
                caption="Aspect Ratio Error Reel",
                image_url="https://example.com/bad_aspect_video.mp4",
                is_video=True
            )

        assert "IG Container processing failed on Meta servers (ERROR)" in str(exc_info.value)
        assert "aspect ratio" in str(exc_info.value)
        assert mock_post.call_count == 1

def test_instagram_container_expired_state_fails():
    """Verify that if Meta container EXPIRES, publishing fails cleanly."""
    with patch("requests.post") as mock_post, patch("requests.get") as mock_get:
        mock_container_res = MagicMock(status_code=200)
        mock_container_res.json.return_value = {"id": "container_exp_202"}
        mock_post.return_value = mock_container_res

        mock_poll_res = MagicMock(status_code=200)
        mock_poll_res.json.return_value = {"status_code": "EXPIRED"}
        mock_get.return_value = mock_poll_res

        with pytest.raises(Exception) as exc_info:
            meta_service.publish_to_instagram_business(
                ig_user_id="17841400000000000",
                access_token="valid_token_123",
                caption="Expired Reel Test",
                image_url="https://example.com/old_video.mp4",
                is_video=True
            )

        assert "EXPIRED" in str(exc_info.value)

def test_facebook_video_upload_timeout_handling():
    """Verify that Facebook long video upload network HTTP timeout raises a clear timeout exception."""
    with patch("requests.post") as mock_post:
        mock_post.side_effect = requests.exceptions.Timeout("Connection timed out after 120s")

        with pytest.raises(Exception) as exc_info:
            meta_service.publish_to_facebook_page(
                page_id="100500100",
                access_token="valid_token_fb",
                message="Long Facebook Video",
                image_url="https://example.com/large_fb_video.mp4",
                is_video=True
            )

        assert "Facebook video upload network HTTP timeout" in str(exc_info.value)

def test_no_false_success_without_published_id():
    """Verify that InstagramPublisher requires a published ID and does NOT treat container_id as success."""
    publisher = InstagramPublisher()
    acc = MagicMock(account_id="17841400000000000", access_token="token_123")

    with patch("app.services.publisher_service.meta_service.publish_to_instagram_business") as mock_pub:
        # Return response missing published "id"
        mock_pub.return_value = {"container_id": "container_only_id", "id": None}

        with pytest.raises(Exception) as exc_info:
            publisher.publish(acc, "Caption", "https://example.com/video.mp4", is_video=True)

        assert "returned no published media ID" in str(exc_info.value)

def test_video_url_validation_rejects_blob_and_data_without_fallback():
    """Verify that video publishing rejects blob: and data: URLs without falling back to JPEG photo."""
    ig_pub = InstagramPublisher()
    fb_pub = FacebookPublisher()
    acc = MagicMock(account_id="12345", access_token="token_123")

    with pytest.raises(Exception) as exc_info_ig:
        ig_pub.publish(acc, "Caption", "blob:http://localhost/3847293", is_video=True)
    assert "Video publishing requires a publicly accessible HTTPS URL" in str(exc_info_ig.value)

    with pytest.raises(Exception) as exc_info_fb:
        fb_pub.publish(acc, "Caption", "data:video/mp4;base64,AAAA...", is_video=True)
    assert "Video publishing requires a publicly accessible HTTPS URL" in str(exc_info_fb.value)

def test_classify_error_timeout():
    """Verify error classification returns PUBLISH_TIMEOUT for timeout messages."""
    code, msg = classify_error("IG Video container processing timed out on Meta servers after 300s")
    assert code == "PUBLISH_TIMEOUT"

import pytest
import io
from PIL import Image
from unittest.mock import patch, MagicMock
from app.services.meta_service import meta_service

def _create_mock_image_bytes(fmt="JPEG", width=1080, height=1920):
    """Helper to create fake image bytes with given format and size."""
    img = Image.new("RGB", (width, height), color="red")
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()

def test_instagram_video_without_thumbnail_sends_no_cover_url():
    """Verify video without thumbnail sends no cover_url and creates 1 container."""
    with patch("requests.post") as mock_post, patch("requests.get") as mock_get:
        # Container creation response
        mock_container_res = MagicMock(status_code=200)
        mock_container_res.json.return_value = {"id": "ig_container_100"}

        # Container status polling response
        mock_status_res = MagicMock(status_code=200)
        mock_status_res.json.return_value = {"status_code": "FINISHED", "id": "ig_container_100"}

        # Media publish response
        mock_publish_res = MagicMock(status_code=200)
        mock_publish_res.json.return_value = {"id": "ig_media_100"}

        mock_post.side_effect = [mock_container_res, mock_publish_res]
        mock_get.return_value = mock_status_res

        res = meta_service.publish_to_instagram_business(
            ig_user_id="123456789",
            access_token="valid_token",
            caption="Video without thumbnail",
            image_url="https://cdn.example.com/reel.mp4",
            is_video=True,
            thumbnail_url=None
        )

        assert res["id"] == "ig_media_100"

        # Verify container creation call payload
        container_call_data = mock_post.call_args_list[0].kwargs["data"]
        assert container_call_data["media_type"] == "REELS"
        assert "cover_url" not in container_call_data

        # Verify exactly one container creation call occurred
        container_calls = [c for c in mock_post.call_args_list if "/media" in c.args[0] and "/media_publish" not in c.args[0]]
        assert len(container_calls) == 1

def test_instagram_video_with_valid_thumbnail_sends_cover_url():
    """Verify valid JPEG thumbnail sends cover_url and creates 1 container."""
    valid_bytes = _create_mock_image_bytes(fmt="JPEG", width=1080, height=1920)

    with patch("requests.post") as mock_post, patch("requests.get") as mock_get, patch("app.services.meta_service.logger.info") as mock_log_info:
        # GET response for thumbnail validation
        mock_thumb_res = MagicMock(status_code=200, content=valid_bytes)
        mock_thumb_res.headers = {"Content-Type": "image/jpeg"}
        mock_thumb_res.url = "https://cdn.example.com/cover.jpg"

        # Status GET response during polling
        mock_status_res = MagicMock(status_code=200)
        mock_status_res.json.return_value = {"status_code": "FINISHED", "id": "ig_container_200"}

        mock_get.side_effect = [mock_thumb_res, mock_status_res]

        mock_container_res = MagicMock(status_code=200)
        mock_container_res.json.return_value = {"id": "ig_container_200"}

        mock_publish_res = MagicMock(status_code=200)
        mock_publish_res.json.return_value = {"id": "ig_media_200"}

        mock_post.side_effect = [mock_container_res, mock_publish_res]

        res = meta_service.publish_to_instagram_business(
            ig_user_id="123456789",
            access_token="valid_token",
            caption="Video with valid thumbnail",
            image_url="https://cdn.example.com/reel.mp4",
            is_video=True,
            thumbnail_url="https://cdn.example.com/cover.jpg"
        )

        assert res["id"] == "ig_media_200"

        # Verify cover_url attached to container creation payload
        container_call_data = mock_post.call_args_list[0].kwargs["data"]
        assert container_call_data.get("cover_url") == "https://cdn.example.com/cover.jpg"

        # Confirm diagnostics were logged
        logs = [call.args[0] for call in mock_log_info.call_args_list]
        assert any("INSTAGRAM_COVER_DIAGNOSTICS" in log for log in logs)
        assert any("INSTAGRAM_CONTAINER_REQUEST" in log for log in logs)

        # Confirm exactly one container creation call occurred
        container_calls = [c for c in mock_post.call_args_list if "/media" in c.args[0] and "/media_publish" not in c.args[0]]
        assert len(container_calls) == 1

def test_instagram_video_with_invalid_thumbnail_format_fallback():
    """Verify invalid thumbnail format (WEBP) falls back to sending no cover_url, creates 1 container, and succeeds."""
    webp_bytes = _create_mock_image_bytes(fmt="WEBP", width=1080, height=1920)

    with patch("requests.post") as mock_post, patch("requests.get") as mock_get, patch("app.services.meta_service.logger.warning") as mock_log_warn:
        mock_thumb_res = MagicMock(status_code=200, content=webp_bytes)
        mock_thumb_res.headers = {"Content-Type": "image/webp"}
        mock_thumb_res.url = "https://cdn.example.com/cover.webp"

        mock_status_res = MagicMock(status_code=200)
        mock_status_res.json.return_value = {"status_code": "FINISHED", "id": "ig_container_300"}

        mock_get.side_effect = [mock_thumb_res, mock_status_res]

        mock_container_res = MagicMock(status_code=200)
        mock_container_res.json.return_value = {"id": "ig_container_300"}

        mock_publish_res = MagicMock(status_code=200)
        mock_publish_res.json.return_value = {"id": "ig_media_300"}

        mock_post.side_effect = [mock_container_res, mock_publish_res]

        res = meta_service.publish_to_instagram_business(
            ig_user_id="123456789",
            access_token="valid_token",
            caption="Video with invalid WEBP thumbnail",
            image_url="https://cdn.example.com/reel.mp4",
            is_video=True,
            thumbnail_url="https://cdn.example.com/cover.webp"
        )

        assert res["id"] == "ig_media_300"

        # Verify cover_url was omitted due to WEBP format rejection
        container_call_data = mock_post.call_args_list[0].kwargs["data"]
        assert "cover_url" not in container_call_data

        # Verify fallback and validation logs
        warn_logs = [call.args[0] for call in mock_log_warn.call_args_list]
        assert any("INSTAGRAM_COVER_VALIDATION_FAILED" in log for log in warn_logs)
        assert any("INSTAGRAM_COVER_SKIPPED_FALLBACK" in log for log in warn_logs)

        # Confirm exactly one container creation call occurred
        container_calls = [c for c in mock_post.call_args_list if "/media" in c.args[0] and "/media_publish" not in c.args[0]]
        assert len(container_calls) == 1

def test_instagram_video_with_unreachable_thumbnail_fallback():
    """Verify HTTP 404 thumbnail URL falls back to sending no cover_url, creates 1 container, and succeeds."""
    with patch("requests.post") as mock_post, patch("requests.get") as mock_get, patch("app.services.meta_service.logger.warning") as mock_log_warn:
        mock_thumb_res = MagicMock(status_code=404, content=b"Not Found")
        mock_thumb_res.headers = {"Content-Type": "text/html"}
        mock_thumb_res.url = "https://cdn.example.com/missing.jpg"

        mock_status_res = MagicMock(status_code=200)
        mock_status_res.json.return_value = {"status_code": "FINISHED", "id": "ig_container_400"}

        mock_get.side_effect = [mock_thumb_res, mock_status_res]

        mock_container_res = MagicMock(status_code=200)
        mock_container_res.json.return_value = {"id": "ig_container_400"}

        mock_publish_res = MagicMock(status_code=200)
        mock_publish_res.json.return_value = {"id": "ig_media_400"}

        mock_post.side_effect = [mock_container_res, mock_publish_res]

        res = meta_service.publish_to_instagram_business(
            ig_user_id="123456789",
            access_token="valid_token",
            caption="Video with 404 thumbnail",
            image_url="https://cdn.example.com/reel.mp4",
            is_video=True,
            thumbnail_url="https://cdn.example.com/missing.jpg"
        )

        assert res["id"] == "ig_media_400"

        # Verify cover_url was omitted
        container_call_data = mock_post.call_args_list[0].kwargs["data"]
        assert "cover_url" not in container_call_data

        # Verify fallback logs
        warn_logs = [call.args[0] for call in mock_log_warn.call_args_list]
        assert any("INSTAGRAM_COVER_VALIDATION_FAILED" in log for log in warn_logs)
        assert any("INSTAGRAM_COVER_SKIPPED_FALLBACK" in log for log in warn_logs)

        # Confirm exactly one container creation call occurred
        container_calls = [c for c in mock_post.call_args_list if "/media" in c.args[0] and "/media_publish" not in c.args[0]]
        assert len(container_calls) == 1

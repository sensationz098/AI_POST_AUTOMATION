import pytest
from unittest.mock import patch, MagicMock
from app.services.meta_service import meta_service

def test_facebook_video_with_thumbnail_success():
    """Verify Facebook video creation and subsequent custom thumbnail upload succeed."""
    with patch("requests.post") as mock_post, patch("requests.get") as mock_get:
        # Video upload response
        mock_vid_res = MagicMock(status_code=200)
        mock_vid_res.json.return_value = {"id": "fb_video_12345"}

        # Thumbnail download response (GET image URL)
        mock_thumb_dl = MagicMock(status_code=200, content=b"fake_image_bytes")
        mock_thumb_dl.headers = {"Content-Type": "image/jpeg"}
        mock_get.return_value = mock_thumb_dl

        # Thumbnail upload response (POST /{video_id}/thumbnails)
        mock_thumb_up = MagicMock(status_code=200)
        mock_thumb_up.json.return_value = {"success": True}

        # Sequence of POST requests: 1. video upload, 2. thumbnail upload
        mock_post.side_effect = [mock_vid_res, mock_thumb_up]

        res = meta_service.publish_to_facebook_page(
            page_id="100020003000",
            access_token="valid_page_token",
            message="Test Video with Thumbnail",
            image_url="https://cdn.example.com/video.mp4",
            is_video=True,
            thumbnail_url="https://cdn.example.com/thumb.jpg"
        )

        assert res["id"] == "fb_video_12345"

        # Assert POST calls
        assert mock_post.call_count == 2

        # 1st POST: Video Creation to /{page_id}/videos
        vid_call_url = mock_post.call_args_list[0].args[0]
        vid_call_data = mock_post.call_args_list[0].kwargs.get("data", {})
        assert "/videos" in vid_call_url
        assert vid_call_data["file_url"] == "https://cdn.example.com/video.mp4"
        assert "files" not in mock_post.call_args_list[0].kwargs or mock_post.call_args_list[0].kwargs["files"] is None

        # 2nd POST: Thumbnail Upload to /{video_id}/thumbnails
        thumb_call_url = mock_post.call_args_list[1].args[0]
        thumb_call_data = mock_post.call_args_list[1].kwargs.get("data", {})
        thumb_call_files = mock_post.call_args_list[1].kwargs.get("files", {})
        assert "/fb_video_12345/thumbnails" in thumb_call_url
        assert thumb_call_data["is_preferred"] == "true"
        assert "source" in thumb_call_files

        # Confirm video creation call count == 1
        video_creation_calls = [c for c in mock_post.call_args_list if "/videos" in c.args[0]]
        assert len(video_creation_calls) == 1

def test_facebook_video_without_thumbnail():
    """Verify Facebook video creation without thumbnail only calls video endpoint once and never calls thumbnails endpoint."""
    with patch("requests.post") as mock_post, patch("requests.get") as mock_get:
        mock_vid_res = MagicMock(status_code=200)
        mock_vid_res.json.return_value = {"id": "fb_video_67890"}
        mock_post.return_value = mock_vid_res

        res = meta_service.publish_to_facebook_page(
            page_id="100020003000",
            access_token="valid_page_token",
            message="Test Video without Thumbnail",
            image_url="https://cdn.example.com/video.mp4",
            is_video=True,
            thumbnail_url=None
        )

        assert res["id"] == "fb_video_67890"

        # Assert only video upload occurred
        assert mock_post.call_count == 1
        video_creation_calls = [c for c in mock_post.call_args_list if "/videos" in c.args[0]]
        assert len(video_creation_calls) == 1
        assert mock_get.call_count == 0

def test_facebook_thumbnail_download_failure_gracefully_handled():
    """Verify video upload succeeds even if thumbnail image download fails (e.g. HTTP 404)."""
    with patch("requests.post") as mock_post, patch("requests.get") as mock_get, patch("app.services.meta_service.logger.error") as mock_log_err:
        mock_vid_res = MagicMock(status_code=200)
        mock_vid_res.json.return_value = {"id": "fb_video_11111"}
        mock_post.return_value = mock_vid_res

        # Thumbnail GET returns 404
        mock_thumb_dl = MagicMock(status_code=404)
        mock_get.return_value = mock_thumb_dl

        res = meta_service.publish_to_facebook_page(
            page_id="100020003000",
            access_token="valid_page_token",
            message="Test Video Thumbnail 404",
            image_url="https://cdn.example.com/video.mp4",
            is_video=True,
            thumbnail_url="https://cdn.example.com/broken_thumb.jpg"
        )

        assert res["id"] == "fb_video_11111"

        # Confirm video creation endpoint called exactly once and thumbnails endpoint never called
        video_creation_calls = [c for c in mock_post.call_args_list if "/videos" in c.args[0]]
        assert len(video_creation_calls) == 1
        assert mock_post.call_count == 1

        # Confirm failure trace logged
        error_logs = [call.args[0] for call in mock_log_err.call_args_list]
        assert any("FACEBOOK_THUMBNAIL_UPLOAD_FAILED" in log for log in error_logs)

def test_facebook_thumbnail_endpoint_failure_gracefully_handled():
    """Verify video upload succeeds even if thumbnail endpoint returns an API error (e.g. HTTP 500)."""
    with patch("requests.post") as mock_post, patch("requests.get") as mock_get, patch("app.services.meta_service.logger.error") as mock_log_err:
        mock_vid_res = MagicMock(status_code=200)
        mock_vid_res.json.return_value = {"id": "fb_video_22222"}

        mock_thumb_dl = MagicMock(status_code=200, content=b"fake_image_bytes")
        mock_thumb_dl.headers = {"Content-Type": "image/jpeg"}
        mock_get.return_value = mock_thumb_dl

        # Thumbnail POST endpoint returns 500 Internal Server Error
        mock_thumb_err = MagicMock(status_code=500, text="Meta API Thumbnail Error")
        mock_post.side_effect = [mock_vid_res, mock_thumb_err]

        res = meta_service.publish_to_facebook_page(
            page_id="100020003000",
            access_token="valid_page_token",
            message="Test Video Thumbnail 500",
            image_url="https://cdn.example.com/video.mp4",
            is_video=True,
            thumbnail_url="https://cdn.example.com/thumb.jpg"
        )

        assert res["id"] == "fb_video_22222"

        # Confirm video creation endpoint called exactly once
        video_creation_calls = [c for c in mock_post.call_args_list if "/videos" in c.args[0]]
        assert len(video_creation_calls) == 1

        # Confirm failure trace logged
        error_logs = [call.args[0] for call in mock_log_err.call_args_list]
        assert any("FACEBOOK_THUMBNAIL_UPLOAD_FAILED" in log for log in error_logs)

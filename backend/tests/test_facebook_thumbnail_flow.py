import pytest
from unittest.mock import patch, MagicMock
from app.services.meta_service import meta_service

def test_facebook_video_without_thumbnail():
    """Verify Facebook video creation without thumbnail only calls video endpoint once and never polls or uploads thumbnail."""
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

def test_facebook_video_with_thumbnail_processing_sequence_ready():
    """Verify status polling sequence (processing -> processing -> ready) triggers thumbnail upload and verification after ready."""
    with patch("requests.post") as mock_post, patch("requests.get") as mock_get, patch("time.sleep") as mock_sleep:
        # Video upload response
        mock_vid_res = MagicMock(status_code=200)
        mock_vid_res.json.return_value = {"id": "fb_video_12345"}

        # GET side effect sequence:
        # 1. Poll 1: processing
        # 2. Poll 2: processing
        # 3. Poll 3: ready
        # 4. Download thumbnail image bytes
        # 5. Verify thumbnail endpoint
        poll1 = MagicMock(status_code=200)
        poll1.json.return_value = {"status": {"video_status": "processing"}}

        poll2 = MagicMock(status_code=200)
        poll2.json.return_value = {"status": {"video_status": "processing"}}

        poll3 = MagicMock(status_code=200)
        poll3.json.return_value = {"status": {"video_status": "ready"}}

        thumb_dl = MagicMock(status_code=200, content=b"fake_image_bytes")
        thumb_dl.headers = {"Content-Type": "image/jpeg"}

        verify_res = MagicMock(status_code=200)
        verify_res.json.return_value = {
            "data": [
                {"id": "fb_thumb_999", "is_preferred": True}
            ]
        }

        mock_get.side_effect = [poll1, poll2, poll3, thumb_dl, verify_res]

        # Thumbnail POST upload response
        mock_thumb_up = MagicMock(status_code=200)
        mock_thumb_up.json.return_value = {"id": "fb_thumb_999", "success": True}

        mock_post.side_effect = [mock_vid_res, mock_thumb_up]

        res = meta_service.publish_to_facebook_page(
            page_id="100020003000",
            access_token="valid_page_token",
            message="Test Video with Thumbnail Sequence",
            image_url="https://cdn.example.com/video.mp4",
            is_video=True,
            thumbnail_url="https://cdn.example.com/thumb.jpg"
        )

        assert res["id"] == "fb_video_12345"

        # Confirm 2 POST requests (1. video creation, 2. thumbnail upload)
        assert mock_post.call_count == 2

        # 1st POST: Video Creation
        vid_call_url = mock_post.call_args_list[0].args[0]
        vid_call_data = mock_post.call_args_list[0].kwargs.get("data", {})
        assert "/videos" in vid_call_url
        assert vid_call_data["file_url"] == "https://cdn.example.com/video.mp4"

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

def test_facebook_video_processing_timeout_skips_thumbnail_safely():
    """Verify processing status timeout skips thumbnail upload without retrying video creation or failing post."""
    with patch("requests.post") as mock_post, patch("requests.get") as mock_get, patch("time.sleep") as mock_sleep:
        mock_vid_res = MagicMock(status_code=200)
        mock_vid_res.json.return_value = {"id": "fb_video_timeout_1"}
        mock_post.return_value = mock_vid_res

        # All status polls return "processing"
        poll_res = MagicMock(status_code=200)
        poll_res.json.return_value = {"status": {"video_status": "processing"}}
        mock_get.return_value = poll_res

        res = meta_service.publish_to_facebook_page(
            page_id="100020003000",
            access_token="valid_page_token",
            message="Test Video Timeout",
            image_url="https://cdn.example.com/video.mp4",
            is_video=True,
            thumbnail_url="https://cdn.example.com/thumb.jpg"
        )

        assert res["id"] == "fb_video_timeout_1"

        # Confirm video creation called exactly once
        video_creation_calls = [c for c in mock_post.call_args_list if "/videos" in c.args[0]]
        assert len(video_creation_calls) == 1
        assert mock_post.call_count == 1  # No thumbnail POST call executed

def test_facebook_video_processing_terminal_failure_skips_thumbnail_safely():
    """Verify terminal video processing failure (error) stops polling and preserves created video ID."""
    with patch("requests.post") as mock_post, patch("requests.get") as mock_get:
        mock_vid_res = MagicMock(status_code=200)
        mock_vid_res.json.return_value = {"id": "fb_video_failed_1"}
        mock_post.return_value = mock_vid_res

        poll_fail = MagicMock(status_code=200)
        poll_fail.json.return_value = {"status": {"video_status": "error"}}
        mock_get.return_value = poll_fail

        res = meta_service.publish_to_facebook_page(
            page_id="100020003000",
            access_token="valid_page_token",
            message="Test Video Processing Fail",
            image_url="https://cdn.example.com/video.mp4",
            is_video=True,
            thumbnail_url="https://cdn.example.com/thumb.jpg"
        )

        assert res["id"] == "fb_video_failed_1"

        # Confirm video creation called exactly once
        video_creation_calls = [c for c in mock_post.call_args_list if "/videos" in c.args[0]]
        assert len(video_creation_calls) == 1
        assert mock_post.call_count == 1

def test_facebook_thumbnail_upload_failure_preserves_video():
    """Verify video upload succeeds even if thumbnail POST endpoint returns HTTP 500 error."""
    with patch("requests.post") as mock_post, patch("requests.get") as mock_get:
        mock_vid_res = MagicMock(status_code=200)
        mock_vid_res.json.return_value = {"id": "fb_video_500_err"}

        poll_ready = MagicMock(status_code=200)
        poll_ready.json.return_value = {"status": {"video_status": "ready"}}

        thumb_dl = MagicMock(status_code=200, content=b"fake_image_bytes")
        thumb_dl.headers = {"Content-Type": "image/jpeg"}

        mock_get.side_effect = [poll_ready, thumb_dl]

        # Thumbnail POST returns 500
        mock_thumb_err = MagicMock(status_code=500, text="Meta API Error")
        mock_post.side_effect = [mock_vid_res, mock_thumb_err]

        res = meta_service.publish_to_facebook_page(
            page_id="100020003000",
            access_token="valid_page_token",
            message="Test Video Thumbnail 500",
            image_url="https://cdn.example.com/video.mp4",
            is_video=True,
            thumbnail_url="https://cdn.example.com/thumb.jpg"
        )

        assert res["id"] == "fb_video_500_err"

        # Video creation called exactly once
        video_creation_calls = [c for c in mock_post.call_args_list if "/videos" in c.args[0]]
        assert len(video_creation_calls) == 1

def test_facebook_thumbnail_verification_success():
    """Verify thumbnail verification logs success when uploaded thumbnail ID is preferred."""
    with patch("requests.post") as mock_post, patch("requests.get") as mock_get, patch("app.services.meta_service.logger.info") as mock_log_info:
        mock_vid_res = MagicMock(status_code=200)
        mock_vid_res.json.return_value = {"id": "fb_vid_ver_1"}

        poll_ready = MagicMock(status_code=200)
        poll_ready.json.return_value = {"status": {"video_status": "ready"}}

        thumb_dl = MagicMock(status_code=200, content=b"fake_image_bytes")
        thumb_dl.headers = {"Content-Type": "image/jpeg"}

        verify_res = MagicMock(status_code=200)
        verify_res.json.return_value = {
            "data": [
                {"id": "thumb_abc_123", "is_preferred": True}
            ]
        }

        mock_get.side_effect = [poll_ready, thumb_dl, verify_res]

        mock_thumb_up = MagicMock(status_code=200)
        mock_thumb_up.json.return_value = {"id": "thumb_abc_123", "success": True}

        mock_post.side_effect = [mock_vid_res, mock_thumb_up]

        res = meta_service.publish_to_facebook_page(
            page_id="100020003000",
            access_token="valid_page_token",
            message="Test Verification Success",
            image_url="https://cdn.example.com/video.mp4",
            is_video=True,
            thumbnail_url="https://cdn.example.com/thumb.jpg"
        )

        assert res["id"] == "fb_vid_ver_1"

        logs = [call.args[0] for call in mock_log_info.call_args_list]
        assert any("FACEBOOK_THUMBNAIL_VERIFIED_SUCCESS" in log for log in logs)

def test_facebook_thumbnail_verification_failure_logged_safely():
    """Verify thumbnail verification failure is logged without crashing or retrying video creation."""
    with patch("requests.post") as mock_post, patch("requests.get") as mock_get, patch("app.services.meta_service.logger.warning") as mock_log_warn:
        mock_vid_res = MagicMock(status_code=200)
        mock_vid_res.json.return_value = {"id": "fb_vid_ver_2"}

        poll_ready = MagicMock(status_code=200)
        poll_ready.json.return_value = {"status": {"video_status": "ready"}}

        thumb_dl = MagicMock(status_code=200, content=b"fake_image_bytes")
        thumb_dl.headers = {"Content-Type": "image/jpeg"}

        # Verification returns empty items or missing uploaded ID
        verify_res = MagicMock(status_code=200)
        verify_res.json.return_value = {"data": []}

        mock_get.side_effect = [poll_ready, thumb_dl, verify_res]

        mock_thumb_up = MagicMock(status_code=200)
        mock_thumb_up.json.return_value = {"id": "thumb_xyz_789", "success": True}

        mock_post.side_effect = [mock_vid_res, mock_thumb_up]

        res = meta_service.publish_to_facebook_page(
            page_id="100020003000",
            access_token="valid_page_token",
            message="Test Verification Failure Logged",
            image_url="https://cdn.example.com/video.mp4",
            is_video=True,
            thumbnail_url="https://cdn.example.com/thumb.jpg"
        )

        assert res["id"] == "fb_vid_ver_2"

        warn_logs = [call.args[0] for call in mock_log_warn.call_args_list]
        assert any("FACEBOOK_THUMBNAIL_VERIFICATION_FAILED" in log for log in warn_logs)

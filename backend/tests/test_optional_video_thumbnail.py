import pytest
from datetime import datetime
from unittest.mock import patch
from sqlalchemy.orm import Session
from app.models.post import Post, PostStatus
from app.schemas.post import PostCreate
from app.services.post_service import post_service
from app.services.meta_service import meta_service


def get_auth_token_and_user(client):
    email = f"thumbuser_{datetime.utcnow().timestamp()}@socialai.com"
    reg_payload = {"email": email, "password": "Password123!", "full_name": "Thumbnail Tester", "role": "Admin"}
    client.post("/api/v1/auth/register", json=reg_payload)
    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    brand_res = client.post("/api/v1/brands/", json={"name": "Thumb Brand", "tone_of_voice": "Professional"}, headers=headers)
    brand_id = brand_res.json()["id"]
    user_id = brand_res.json()["user_id"]

    return headers, brand_id, user_id


def test_video_post_no_thumbnail_default_behavior(client, db_session: Session):
    """Verify that a video post with no thumbnail (NONE) publishes using the exact existing pipeline."""
    headers, brand_id, user_id = get_auth_token_and_user(client)
    post_in = PostCreate(
        brand_id=brand_id,
        title="No Thumb Video",
        caption="Video without cover",
        hashtags=["#video"],
        image_url="https://example.com/video.mp4",
        media_type="video",
        thumbnail_type="NONE",
        thumbnail_url=None,
        platforms=["facebook", "instagram"]
    )
    post = post_service.create_post(db_session, user_id, post_in)
    assert post.thumbnail_type == "NONE"
    assert post.thumbnail_url is None
    assert post.thumbnail_offset_ms is None

    # Test publishing logic with mock Meta Graph calls
    with patch("app.services.meta_service.requests.get") as mock_get, \
         patch("app.services.meta_service.requests.post") as mock_post:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"status_code": "FINISHED"}

        mock_post.return_value.status_code = 200
        mock_post.return_value.json.side_effect = [
            {"id": "fb_vid_123"},
            {"id": "ig_container_123"},
            {"id": "ig_media_123"}
        ]
        res_fb = meta_service.publish_to_facebook_page(
            page_id="12345",
            access_token="valid_token",
            message="Caption",
            image_url="https://example.com/video.mp4",
            is_video=True,
            thumbnail_url=None
        )
        assert res_fb["id"] == "fb_vid_123"
        # Confirm no files parameter (thumb) was attached
        _, kwargs = mock_post.call_args_list[0]
        assert kwargs.get("files") is None

        res_ig = meta_service.publish_to_instagram_business(
            ig_user_id="67890",
            access_token="valid_token",
            caption="Caption",
            image_url="https://example.com/video.mp4",
            is_video=True,
            thumbnail_url=None
        )
        assert res_ig["id"] == "ig_media_123"
        # Confirm cover_url was NOT in container creation payload
        data = mock_post.call_args_list[1][1]["data"]
        assert "cover_url" not in data


def test_video_post_custom_thumbnail_publishing(client, db_session: Session):
    """Verify custom thumbnail cover_url for IG Reels and thumb file for FB Videos."""
    headers, brand_id, user_id = get_auth_token_and_user(client)
    thumb_url = "https://res.cloudinary.com/demo/image/upload/v1234/custom_thumb.jpg"
    post_in = PostCreate(
        brand_id=brand_id,
        title="Custom Thumb Video",
        caption="Video with custom thumbnail cover",
        hashtags=["#reels"],
        image_url="https://example.com/reel.mp4",
        media_type="video",
        thumbnail_type="CUSTOM",
        thumbnail_url=thumb_url,
        platforms=["facebook", "instagram"]
    )
    post = post_service.create_post(db_session, user_id, post_in)
    assert post.thumbnail_type == "CUSTOM"
    assert post.thumbnail_url == thumb_url

    with patch("app.services.meta_service.requests.get") as mock_get, \
         patch("app.services.meta_service.requests.post") as mock_post:

        import io
        from PIL import Image
        img = Image.new("RGB", (1080, 1920), color="blue")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        valid_jpg_bytes = buf.getvalue()

        mock_get.return_value.status_code = 200
        mock_get.return_value.content = valid_jpg_bytes
        mock_get.return_value.headers = {"Content-Type": "image/jpeg"}
        mock_get.return_value.json.return_value = {"status_code": "FINISHED"}

        mock_post.return_value.status_code = 200
        mock_post.return_value.json.side_effect = [
            {"id": "fb_vid_999"},
            {"id": "ig_container_999"},
            {"id": "ig_media_999"}
        ]

        # Publish FB
        res_fb = meta_service.publish_to_facebook_page(
            page_id="12345",
            access_token="valid_token",
            message="Caption",
            image_url="https://example.com/reel.mp4",
            is_video=True,
            thumbnail_url=thumb_url
        )
        assert mock_get.called
        assert res_fb["id"] == "fb_vid_999"

        # 1st POST: Video Creation (no inline thumb files)
        fb_vid_kwargs = mock_post.call_args_list[0][1]
        assert "files" not in fb_vid_kwargs or fb_vid_kwargs["files"] is None

        # 2nd POST: Thumbnail Upload to /{video_id}/thumbnails
        fb_thumb_url = mock_post.call_args_list[1][0][0]
        fb_thumb_kwargs = mock_post.call_args_list[1][1]
        assert "/fb_vid_999/thumbnails" in fb_thumb_url
        assert fb_thumb_kwargs["files"] is not None
        assert "source" in fb_thumb_kwargs["files"]
        assert fb_thumb_kwargs["data"]["is_preferred"] == "true"

        # Publish IG
        meta_service.publish_to_instagram_business(
            ig_user_id="67890",
            access_token="valid_token",
            caption="Caption",
            image_url="https://example.com/reel.mp4",
            is_video=True,
            thumbnail_url=thumb_url
        )
        ig_payload = mock_post.call_args_list[2][1]["data"]
        assert ig_payload.get("cover_url") == thumb_url


def test_video_post_choose_frame_thumbnail(client, db_session: Session):
    """Verify frame selection thumbnail fields (FRAME type & timestamp offset) are saved and retrieved."""
    headers, brand_id, user_id = get_auth_token_and_user(client)
    frame_url = "https://res.cloudinary.com/demo/image/upload/v1234/frame_4200ms.jpg"
    post_in = PostCreate(
        brand_id=brand_id,
        title="Frame Selection Video",
        caption="Reel with frame cover",
        hashtags=["#frame"],
        image_url="https://example.com/reel.mp4",
        media_type="video",
        thumbnail_type="FRAME",
        thumbnail_url=frame_url,
        thumbnail_offset_ms=4200,
        platforms=["facebook", "instagram"]
    )
    post = post_service.create_post(db_session, user_id, post_in)
    assert post.thumbnail_type == "FRAME"
    assert post.thumbnail_url == frame_url
    assert post.thumbnail_offset_ms == 4200

    fetched = post_service.get_post(db_session, post.id, user_id)
    assert fetched.thumbnail_type == "FRAME"
    assert fetched.thumbnail_url == frame_url
    assert fetched.thumbnail_offset_ms == 4200


def test_backward_compatibility_legacy_post(client, db_session: Session):
    """Verify legacy posts created without thumbnail fields default to NONE and work seamlessly."""
    headers, brand_id, user_id = get_auth_token_and_user(client)
    post_in = PostCreate(
        brand_id=brand_id,
        caption="Legacy post without thumbnail attributes",
        image_url="https://example.com/photo.jpg",
        platforms=["facebook"]
    )
    post = post_service.create_post(db_session, user_id, post_in)
    assert post.thumbnail_type in ["NONE", None]
    assert post.thumbnail_url is None
    assert post.thumbnail_offset_ms is None


def test_image_post_ignores_thumbnail_on_publish(client, db_session: Session):
    """Verify that photo posts ignore thumbnail parameters during publishing."""
    headers, brand_id, user_id = get_auth_token_and_user(client)
    with patch("app.services.meta_service.requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"id": "fb_photo_100"}

        meta_service.publish_to_facebook_page(
            page_id="12345",
            access_token="valid_token",
            message="Photo post",
            image_url="https://example.com/photo.jpg",
            is_video=False,
            thumbnail_url="https://example.com/ignored_thumb.jpg"
        )
        fb_kwargs = mock_post.call_args_list[0][1]
        assert fb_kwargs.get("files") is None


def test_base64_thumbnail_upload_to_cloudinary(client, db_session: Session):
    """Verify raw Base64 thumbnail data is converted to Cloudinary CDN URL before database insert."""
    headers, brand_id, user_id = get_auth_token_and_user(client)
    base64_thumb = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBD..."
    cdn_url = "https://res.cloudinary.com/demo/image/upload/v123/uploaded_thumb.jpg"

    with patch("app.services.post_service.upload_media_to_cloudinary", return_value=cdn_url) as mock_upload:
        post_in = PostCreate(
            brand_id=brand_id,
            caption="Base64 thumbnail post",
            image_url="https://example.com/video.mp4",
            media_type="video",
            thumbnail_type="CUSTOM",
            thumbnail_url=base64_thumb,
            platforms=["facebook"]
        )
        post = post_service.create_post(db_session, user_id, post_in)
        assert mock_upload.called
        assert post.thumbnail_url == cdn_url
        assert not post.thumbnail_url.startswith("data:")

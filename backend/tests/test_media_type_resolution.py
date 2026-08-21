import pytest
import logging
from unittest.mock import MagicMock, patch
from app.services.publisher_service import resolve_media_type
from app.core.logging_config import sanitize_url, setup_logging

def test_resolve_media_type_explicit_override():
    """Verify explicit passed media_type takes highest priority over URL string."""
    # Video extension in URL, but explicit passed as 'image'
    resolved, is_video = resolve_media_type(
        explicit_media_type="image",
        stored_media_type=None,
        media_url="https://res.cloudinary.com/demo/video/upload/v12345/sample.mp4"
    )
    assert resolved == "image"
    assert is_video is False

    # Image extension in URL, but explicit passed as 'video'
    resolved, is_video = resolve_media_type(
        explicit_media_type="video",
        stored_media_type=None,
        media_url="https://res.cloudinary.com/demo/image/upload/v12345/sample.jpg"
    )
    assert resolved == "video"
    assert is_video is True


def test_resolve_media_type_stored_model_priority():
    """Verify stored DB media_type takes priority when explicit_media_type is None."""
    resolved, is_video = resolve_media_type(
        explicit_media_type=None,
        stored_media_type="video",
        media_url="https://res.cloudinary.com/demo/image/upload/v12345/custom_media_asset"
    )
    assert resolved == "video"
    assert is_video is True


def test_resolve_media_type_legacy_url_fallback():
    """Verify fallback to URL string inference when explicit and stored types are absent."""
    # Video URL without extension but containing 'video' keyword
    resolved, is_video = resolve_media_type(
        explicit_media_type=None,
        stored_media_type=None,
        media_url="https://res.cloudinary.com/demo/video/upload/v12345/sample"
    )
    assert resolved == "video"
    assert is_video is True

    # Image URL
    resolved, is_video = resolve_media_type(
        explicit_media_type=None,
        stored_media_type=None,
        media_url="https://res.cloudinary.com/demo/image/upload/v12345/sample.png"
    )
    assert resolved == "image"
    assert is_video is False


def test_sanitize_url_redacts_tokens_and_base64():
    """Verify sanitize_url redacts access_token query params and truncates base64 strings."""
    url_with_token = "https://graph.facebook.com/v19.0/12345/videos?access_token=EAABwz12345secret&file_url=https://example.com/video.mp4"
    sanitized = sanitize_url(url_with_token)
    assert "EAABwz12345secret" not in sanitized
    assert "access_token=[REDACTED]" in sanitized

    base64_url = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    sanitized_b64 = sanitize_url(base64_url)
    assert "data:image/png;base64," in sanitized_b64
    assert "[BASE64_DATA_TRUNCATED]" in sanitized_b64


def test_setup_logging_configures_stdout_handler():
    """Verify setup_logging sets root logger level to INFO and creates StreamHandler."""
    setup_logging()
    root_logger = logging.getLogger()
    assert root_logger.level == logging.INFO
    assert len(root_logger.handlers) >= 1
    assert isinstance(root_logger.handlers[0], logging.StreamHandler)


def test_post_model_and_schemas_media_type_field_alignment():
    """Verify SQLAlchemy Post model and Pydantic schemas align on media_type field."""
    from app.models.post import Post
    from app.schemas.post import PostCreate, PostUpdate, PostResponse
    from app.schemas.social_account import MultiPublishRequest

    # 1. Verify SQLAlchemy model has media_type attribute
    assert hasattr(Post, "media_type")
    assert Post.media_type.property.columns[0].nullable is True

    # 2. Verify Pydantic schemas include media_type
    create_schema = PostCreate(brand_id=1, caption="Test", media_type="video")
    assert create_schema.media_type == "video"

    update_schema = PostUpdate(media_type="image")
    assert update_schema.media_type == "image"

    multi_req = MultiPublishRequest(post_id=10, social_account_ids=[1, 2], media_type="video")
    assert multi_req.media_type == "video"


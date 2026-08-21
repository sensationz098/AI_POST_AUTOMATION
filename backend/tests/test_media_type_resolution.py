import pytest
import logging
from unittest.mock import MagicMock, patch
from app.services.media_service import resolve_media_type, upload_base64_to_public_https
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
    assert "access_token=" in sanitized and "REDACTED" in sanitized


    base64_url = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    sanitized_b64 = sanitize_url(base64_url)
    assert "data:image/png" in sanitized_b64
    assert "length=" in sanitized_b64



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


def test_posts_router_logger_defined():
    """Verify that backend/app/api/v1/posts.py module defines 'logger' to prevent NameError on trace logs."""
    import app.api.v1.posts as posts_module
    assert hasattr(posts_module, "logger")
    assert posts_module.logger is not None
    assert isinstance(posts_module.logger, logging.Logger)


def test_create_post_small_image_base64_uploads_to_cloudinary():
    """Verify small image base64 is uploaded to Cloudinary and HTTPS URL saved with media_type='image'."""
    from app.services.post_service import PostService
    from app.schemas.post import PostCreate

    service = PostService()
    db = MagicMock()
    
    # Mock brand check
    db.query.return_value.filter.return_value.first.return_value = MagicMock(id=1, user_id=1)

    image_base64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    post_in = PostCreate(brand_id=1, caption="Test Image", image_url=image_base64)

    with patch("app.services.post_service.upload_media_to_cloudinary") as mock_upload, \
         patch("app.services.post_service.post_repo.create") as mock_create:
        
        mock_upload.return_value = "https://res.cloudinary.com/demo/image/upload/v12345/sample.png"
        mock_create.return_value = MagicMock(id=101, media_type="image", image_url="https://res.cloudinary.com/demo/image/upload/v12345/sample.png")

        res = service.create_post(db=db, user_id=1, post_in=post_in)

        # 1. Cloudinary upload called with resource_type image
        mock_upload.assert_called_once_with(image_base64, media_type="image")

        # 2. Database receive ONLY HTTPS URL and media_type='image' (never raw base64)
        created_data = mock_create.call_args[0][1]
        assert created_data["image_url"] == "https://res.cloudinary.com/demo/image/upload/v12345/sample.png"
        assert created_data["media_type"] == "image"
        assert not created_data["image_url"].startswith("data:")


def test_create_post_mp4_video_base64_uploads_to_cloudinary_video():
    """Verify MP4 video base64 is uploaded to Cloudinary with media_type='video' and HTTPS URL saved."""
    from app.services.post_service import PostService
    from app.schemas.post import PostCreate

    service = PostService()
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = MagicMock(id=1, user_id=1)

    video_base64 = "data:video/mp4;base64,AAAAIGZ0eXBpc29tAAACAGlzb21pc28yYXZjMW1wNDEAAAAIZnJlZQ=="
    post_in = PostCreate(brand_id=1, caption="Test Reel", image_url=video_base64, media_type="video")

    with patch("app.services.post_service.upload_media_to_cloudinary") as mock_upload, \
         patch("app.services.post_service.post_repo.create") as mock_create:
        
        mock_upload.return_value = "https://res.cloudinary.com/demo/video/upload/v12345/reel.mp4"
        mock_create.return_value = MagicMock(id=102, media_type="video", image_url="https://res.cloudinary.com/demo/video/upload/v12345/reel.mp4")

        res = service.create_post(db=db, user_id=1, post_in=post_in)

        # 1. Cloudinary upload called with media_type video
        mock_upload.assert_called_once_with(video_base64, media_type="video")

        # 2. DB receives ONLY HTTPS URL and media_type='video'
        created_data = mock_create.call_args[0][1]
        assert created_data["image_url"] == "https://res.cloudinary.com/demo/video/upload/v12345/reel.mp4"
        assert created_data["media_type"] == "video"


def test_create_post_existing_cloudinary_url_skips_duplicate_upload():
    """Verify existing Cloudinary HTTPS URL is preserved without duplicate upload."""
    from app.services.post_service import PostService
    from app.schemas.post import PostCreate

    service = PostService()
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = MagicMock(id=1, user_id=1)

    cdn_url = "https://res.cloudinary.com/demo/video/upload/v12345/existing_clip.mp4"
    post_in = PostCreate(brand_id=1, caption="Existing CDN Clip", image_url=cdn_url)

    with patch("app.services.post_service.upload_media_to_cloudinary") as mock_upload, \
         patch("app.services.post_service.post_repo.create") as mock_create:
        
        service.create_post(db=db, user_id=1, post_in=post_in)

        # Duplicate upload should NOT occur for existing Cloudinary URL
        mock_upload.assert_not_called()

        created_data = mock_create.call_args[0][1]
        assert created_data["image_url"] == cdn_url
        assert created_data["media_type"] == "video"


def test_large_base64_video_payload_never_inserted_into_db():
    """Verify large 45MB simulated base64 string is uploaded to CDN and NEVER passed raw to DB insert."""
    from app.services.post_service import PostService
    from app.schemas.post import PostCreate

    service = PostService()
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = MagicMock(id=1, user_id=1)

    # 1MB simulated payload header for testing
    huge_base64 = "data:video/mp4;base64," + ("A" * 1000000)
    post_in = PostCreate(brand_id=1, caption="33s Video Test", image_url=huge_base64)

    with patch("app.services.post_service.upload_media_to_cloudinary") as mock_upload, \
         patch("app.services.post_service.post_repo.create") as mock_create:
        
        mock_upload.return_value = "https://res.cloudinary.com/demo/video/upload/v999/large_33s_video.mp4"
        mock_create.return_value = MagicMock(id=103)

        service.create_post(db=db, user_id=1, post_in=post_in)

        created_data = mock_create.call_args[0][1]
        # Raw base64 MUST NEVER reach post_repo.create
        assert created_data["image_url"] != huge_base64
        assert created_data["image_url"] == "https://res.cloudinary.com/demo/video/upload/v999/large_33s_video.mp4"
        assert created_data["media_type"] == "video"


def test_batch_status_aggregation_all_success():
    """Verify batch with 2 successful jobs calculates status=SUCCESS, 2 successful, 0 failed."""
    from app.repositories.publishing_repository import PublishingRepository
    from app.models.publishing_batch import PublishingBatch, PublishingJob, BatchStatus, JobStatus

    repo = PublishingRepository()
    db = MagicMock()

    batch = PublishingBatch(id=1, total_targets=2, status=BatchStatus.PROCESSING.value, successful_targets=0, failed_targets=0)
    job1 = PublishingJob(id=101, batch_id=1, status=JobStatus.SUCCESS.value)
    job2 = PublishingJob(id=102, batch_id=1, status=JobStatus.SUCCESS.value)

    db.query.return_value.filter.return_value.first.return_value = batch
    db.query.return_value.filter.return_value.all.return_value = [job1, job2]

    updated = repo.update_batch_summary(db, batch_id=1)
    assert updated.status == BatchStatus.SUCCESS.value
    assert updated.total_targets == 2
    assert updated.successful_targets == 2
    assert updated.failed_targets == 0


def test_batch_status_aggregation_partial_success():
    """Verify batch with 1 success and 1 failed job calculates status=PARTIAL_SUCCESS, 1 successful, 1 failed."""
    from app.repositories.publishing_repository import PublishingRepository
    from app.models.publishing_batch import PublishingBatch, PublishingJob, BatchStatus, JobStatus

    repo = PublishingRepository()
    db = MagicMock()

    batch = PublishingBatch(id=2, total_targets=2, status=BatchStatus.PROCESSING.value, successful_targets=0, failed_targets=0)
    job1 = PublishingJob(id=103, batch_id=2, status=JobStatus.SUCCESS.value)
    job2 = PublishingJob(id=104, batch_id=2, status=JobStatus.FAILED.value)

    db.query.return_value.filter.return_value.first.return_value = batch
    db.query.return_value.filter.return_value.all.return_value = [job1, job2]

    updated = repo.update_batch_summary(db, batch_id=2)
    assert updated.status == BatchStatus.PARTIAL_SUCCESS.value
    assert updated.total_targets == 2
    assert updated.successful_targets == 1
    assert updated.failed_targets == 1


def test_batch_status_aggregation_all_failed():
    """Verify batch with 2 failed jobs calculates status=FAILED, 0 successful, 2 failed."""
    from app.repositories.publishing_repository import PublishingRepository
    from app.models.publishing_batch import PublishingBatch, PublishingJob, BatchStatus, JobStatus

    repo = PublishingRepository()
    db = MagicMock()

    batch = PublishingBatch(id=3, total_targets=2, status=BatchStatus.PROCESSING.value, successful_targets=0, failed_targets=0)
    job1 = PublishingJob(id=105, batch_id=3, status=JobStatus.FAILED.value)
    job2 = PublishingJob(id=106, batch_id=3, status=JobStatus.FAILED.value)

    db.query.return_value.filter.return_value.first.return_value = batch
    db.query.return_value.filter.return_value.all.return_value = [job1, job2]

    updated = repo.update_batch_summary(db, batch_id=3)
    assert updated.status == BatchStatus.FAILED.value
    assert updated.total_targets == 2
    assert updated.successful_targets == 0
    assert updated.failed_targets == 2





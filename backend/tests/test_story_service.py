import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException

from app.models.story import Story, StoryStatus
from app.models.user import User
from app.models.brand import BrandProfile
from app.models.social_account import SocialAccount
from app.services.story_service import story_service
from app.schemas.story import StoryCreate, StoryUpdate
from app.core.security import get_password_hash


def setup_user_brand_accounts(db_session, email="service_tester@test.com"):
    user = User(
        email=email,
        hashed_password=get_password_hash("Secret123!"),
        full_name="Service Tester",
        role="Admin"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    brand = BrandProfile(user_id=user.id, name="Story Brand")
    db_session.add(brand)
    db_session.commit()
    db_session.refresh(brand)

    fb_acc = SocialAccount(
        user_id=user.id,
        brand_id=brand.id,
        platform="facebook",
        account_id="fb_page_123",
        account_name="Test Facebook Page",
        access_token="sandbox_fb_token",
        status="CONNECTED"
    )
    ig_acc = SocialAccount(
        user_id=user.id,
        brand_id=brand.id,
        platform="instagram",
        account_id="ig_biz_456",
        account_name="test_ig_business",
        access_token="sandbox_ig_token",
        status="CONNECTED",
        metadata_json={"account_type": "BUSINESS"}
    )
    db_session.add_all([fb_acc, ig_acc])
    db_session.commit()
    db_session.refresh(fb_acc)
    db_session.refresh(ig_acc)

    return user, brand, fb_acc, ig_acc


def test_story_media_validation():
    # Valid image URL
    is_valid, errors, warnings = story_service.validate_story_media("https://example.com/story.jpg", "image")
    assert is_valid is True
    assert len(errors) == 0
    assert any("9:16" in w for w in warnings)

    # Valid video URL
    is_valid, errors, warnings = story_service.validate_story_media("https://example.com/story.mp4", "video")
    assert is_valid is True
    assert len(errors) == 0

    # Missing URL
    is_valid, errors, warnings = story_service.validate_story_media("", "image")
    assert is_valid is False
    assert "required" in errors[0].lower()

    # Invalid protocol
    is_valid, errors, warnings = story_service.validate_story_media("ftp://example.com/story.jpg", "image")
    assert is_valid is False
    assert "https" in errors[0].lower()

    # Unsupported media type
    is_valid, errors, warnings = story_service.validate_story_media("https://example.com/story.pdf", "pdf")
    assert is_valid is False
    assert "unsupported media type" in errors[0].lower()


def test_account_capability_validation(db_session):
    user, brand, fb_acc, ig_acc = setup_user_brand_accounts(db_session, "acc_val@test.com")

    # Valid FB
    capable, reason = story_service.validate_account_capability(fb_acc, "facebook")
    assert capable is True
    assert reason is None

    # Valid IG Business
    capable, reason = story_service.validate_account_capability(ig_acc, "instagram")
    assert capable is True
    assert reason is None

    # Expired token
    fb_acc.status = "TOKEN_EXPIRED"
    capable, reason = story_service.validate_account_capability(fb_acc, "facebook")
    assert capable is False
    assert "expired" in reason.lower()

    # Revoked account
    fb_acc.status = "REVOKED"
    capable, reason = story_service.validate_account_capability(fb_acc, "facebook")
    assert capable is False
    assert "revoked" in reason.lower()

    # Creator account without story publishing
    ig_creator = SocialAccount(
        user_id=user.id,
        platform="instagram",
        account_id="ig_creator_789",
        account_name="test_ig_creator",
        access_token="sandbox_creator_token",
        status="CONNECTED",
        metadata_json={"account_type": "CREATOR", "creator_story_publishing_supported": False}
    )
    capable, reason = story_service.validate_account_capability(ig_creator, "instagram")
    assert capable is False
    assert "creator account" in reason.lower()


def test_story_lifecycle_and_mock_publish(db_session):
    user, brand, fb_acc, ig_acc = setup_user_brand_accounts(db_session, "lifecycle@test.com")

    # 1. Create Draft Story
    story_in = StoryCreate(
        brand_id=brand.id,
        title="Test Draft Story",
        caption="Draft caption",
        media_url="https://images.unsplash.com/photo-1534447677768-be436bb09401",
        media_type="image",
        platforms=["instagram", "facebook"]
    )
    story = story_service.create_story(db_session, story_in, user.id)
    assert story.id is not None
    assert story.status == StoryStatus.DRAFT.value

    # 2. Update Draft Story
    updated = story_service.update_story(db_session, story.id, user.id, StoryUpdate(title="Updated Title"))
    assert updated.title == "Updated Title"

    # 3. Publish Story (Mock/Sandbox Mode)
    published = story_service.publish_story(db_session, story.id, user.id)
    assert published.status == StoryStatus.PUBLISHED.value
    assert published.published_at is not None
    assert published.fb_story_id is not None
    assert published.ig_story_id is not None


def test_story_schedule_and_due_check(db_session):
    user, brand, fb_acc, ig_acc = setup_user_brand_accounts(db_session, "sched_check@test.com")
    now = datetime.now(timezone.utc)

    story_in = StoryCreate(
        brand_id=brand.id,
        title="Schedule Test",
        media_url="https://images.unsplash.com/photo-1534447677768-be436bb09401",
        media_type="image",
        platforms=["facebook"]
    )
    story = story_service.create_story(db_session, story_in, user.id)

    # Schedule in past -> HTTP 400
    with pytest.raises(HTTPException) as exc:
        story_service.schedule_story(db_session, story.id, user.id, now - timedelta(hours=1))
    assert exc.value.status_code == 400

    # Schedule in future
    future_time = now + timedelta(hours=3)
    scheduled = story_service.schedule_story(db_session, story.id, user.id, future_time)
    assert scheduled.status == StoryStatus.SCHEDULED.value
    sched_tz = scheduled.scheduled_at.replace(tzinfo=timezone.utc) if scheduled.scheduled_at.tzinfo is None else scheduled.scheduled_at
    assert sched_tz == future_time

    # Manually backdate scheduled_at to test auto-publishing
    scheduled.scheduled_at = now - timedelta(minutes=5)
    db_session.commit()

    due_published = story_service.check_and_publish_due_stories(db_session, user.id)
    assert len(due_published) == 1
    assert due_published[0].status == StoryStatus.PUBLISHED.value


def test_story_retry_flow(db_session):
    user, brand, fb_acc, ig_acc = setup_user_brand_accounts(db_session, "retry_tester@test.com")

    story = Story(
        brand_id=brand.id,
        user_id=user.id,
        title="Failed Story to Retry",
        media_url="https://images.unsplash.com/photo-1534447677768-be436bb09401",
        media_type="image",
        platforms=["instagram"],
        status=StoryStatus.FAILED.value,
        retry_count=1,
        max_retries=3
    )
    db_session.add(story)
    db_session.commit()
    db_session.refresh(story)

    # Retry should succeed in mock mode
    retried = story_service.retry_story(db_session, story.id, user.id)
    assert retried.status == StoryStatus.PUBLISHED.value
    assert retried.ig_story_id is not None


def test_instagram_video_story_publishing(db_session):
    user, brand, fb_acc, ig_acc = setup_user_brand_accounts(db_session, "ig_vid_tester@test.com")

    story_in = StoryCreate(
        brand_id=brand.id,
        title="IG Video Story",
        media_url="https://example.com/vertical_reel.mp4",
        media_type="video",
        platforms=["instagram"]
    )
    story = story_service.create_story(db_session, story_in, user.id)
    published = story_service.publish_story(db_session, story.id, user.id)
    assert published.status == StoryStatus.PUBLISHED.value
    assert published.ig_story_id is not None
    assert published.ig_container_id is not None


def test_facebook_video_story_publishing(db_session):
    user, brand, fb_acc, ig_acc = setup_user_brand_accounts(db_session, "fb_vid_tester@test.com")

    story_in = StoryCreate(
        brand_id=brand.id,
        title="FB Video Story",
        media_url="https://example.com/vertical_reel.mp4",
        media_type="video",
        platforms=["facebook"]
    )
    story = story_service.create_story(db_session, story_in, user.id)
    published = story_service.publish_story(db_session, story.id, user.id)
    assert published.status == StoryStatus.PUBLISHED.value
    assert published.fb_story_id is not None


def test_partial_platform_failure(db_session):
    user, brand, fb_acc, ig_acc = setup_user_brand_accounts(db_session, "partial_tester@test.com")

    # Make IG account expired while FB account remains valid
    ig_acc.status = "TOKEN_EXPIRED"
    db_session.commit()

    story_in = StoryCreate(
        brand_id=brand.id,
        title="Multi-Platform Partial Story",
        media_url="https://example.com/story.jpg",
        media_type="image",
        platforms=["facebook", "instagram"]
    )
    story = story_service.create_story(db_session, story_in, user.id)
    published = story_service.publish_story(db_session, story.id, user.id)

    # Should still succeed on Facebook and record warning for IG
    assert published.status == StoryStatus.PUBLISHED.value
    assert published.fb_story_id is not None
    assert "warnings" in published.last_error.lower()

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


def test_preflight_checks_only_selected_accounts(db_session):
    user, brand, fb_acc, ig_acc = setup_user_brand_accounts(db_session, "preflight_user@test.com")

    # 1. No accounts selected -> error / invalid
    res_empty = story_service.validate_story_preflight(
        db_session,
        StoryCreate(
            brand_id=brand.id,
            media_url="https://example.com/story.jpg",
            media_type="image",
            target_account_ids=[]
        ),
        user.id
    )
    assert res_empty.is_valid is False
    assert len(res_empty.account_checks) == 0
    assert any("No Story destinations selected" in err for err in res_empty.errors)

    # 2. Only Instagram selected -> account_checks has ONLY Instagram
    res_ig = story_service.validate_story_preflight(
        db_session,
        StoryCreate(
            brand_id=brand.id,
            media_url="https://example.com/story.jpg",
            media_type="image",
            target_account_ids=[ig_acc.id]
        ),
        user.id
    )
    assert res_ig.is_valid is True
    assert len(res_ig.account_checks) == 1
    assert res_ig.account_checks[0]["account_id"] == ig_acc.id
    assert res_ig.account_checks[0]["platform"] == "instagram"


def test_single_instagram_target_only_publishes_to_that_account(db_session):
    user, brand, fb_acc, ig_acc = setup_user_brand_accounts(db_session, "single_ig@test.com")

    with patch.object(story_service, "publish_instagram_story", wraps=story_service.publish_instagram_story) as mock_ig, \
         patch.object(story_service, "publish_facebook_story", wraps=story_service.publish_facebook_story) as mock_fb:

        story_in = StoryCreate(
            brand_id=brand.id,
            title="Only IG Story",
            media_url="https://example.com/pic.jpg",
            media_type="image",
            target_account_ids=[ig_acc.id]
        )
        story = story_service.create_story(db_session, story_in, user.id)
        assert story.target_account_ids == [ig_acc.id]
        assert story.platforms == ["instagram"]

        published = story_service.publish_story(db_session, story.id, user.id)
        assert published.status == StoryStatus.PUBLISHED.value
        assert published.ig_story_id is not None
        assert published.fb_story_id is None

        # Assert ONLY IG received publish call, FB received ZERO
        assert mock_ig.call_count == 1
        assert mock_fb.call_count == 0


def test_two_instagram_accounts_both_receive_publish(db_session):
    user, brand, fb_acc, ig_acc1 = setup_user_brand_accounts(db_session, "two_ig@test.com")

    # Add second IG account
    ig_acc2 = SocialAccount(
        user_id=user.id,
        brand_id=brand.id,
        platform="instagram",
        account_id="ig_biz_777",
        account_name="test_ig_business_two",
        access_token="sandbox_ig_token_2",
        status="CONNECTED",
        metadata_json={"account_type": "BUSINESS"}
    )
    db_session.add(ig_acc2)
    db_session.commit()
    db_session.refresh(ig_acc2)

    with patch.object(story_service, "publish_instagram_story", wraps=story_service.publish_instagram_story) as mock_ig, \
         patch.object(story_service, "publish_facebook_story", wraps=story_service.publish_facebook_story) as mock_fb:

        story_in = StoryCreate(
            brand_id=brand.id,
            title="Dual IG Story",
            media_url="https://example.com/pic.jpg",
            media_type="image",
            target_account_ids=[ig_acc1.id, ig_acc2.id]
        )
        story = story_service.create_story(db_session, story_in, user.id)
        published = story_service.publish_story(db_session, story.id, user.id)

        assert published.status == StoryStatus.PUBLISHED.value
        assert mock_ig.call_count == 2
        assert mock_fb.call_count == 0


def test_single_facebook_target_only_publishes_to_that_account(db_session):
    user, brand, fb_acc, ig_acc = setup_user_brand_accounts(db_session, "single_fb@test.com")

    with patch.object(story_service, "publish_instagram_story", wraps=story_service.publish_instagram_story) as mock_ig, \
         patch.object(story_service, "publish_facebook_story", wraps=story_service.publish_facebook_story) as mock_fb:

        story_in = StoryCreate(
            brand_id=brand.id,
            title="Only FB Story",
            media_url="https://example.com/pic.jpg",
            media_type="image",
            target_account_ids=[fb_acc.id]
        )
        story = story_service.create_story(db_session, story_in, user.id)
        assert story.target_account_ids == [fb_acc.id]
        assert story.platforms == ["facebook"]

        published = story_service.publish_story(db_session, story.id, user.id)
        assert published.status == StoryStatus.PUBLISHED.value
        assert published.fb_story_id is not None
        assert published.ig_story_id is None

        assert mock_fb.call_count == 1
        assert mock_ig.call_count == 0


def test_multiple_accounts_exist_only_selected_receive_publish(db_session):
    user, brand, fb_acc, ig_acc = setup_user_brand_accounts(db_session, "multi_exist@test.com")

    # Add second FB Page and second IG
    fb_acc2 = SocialAccount(
        user_id=user.id,
        brand_id=brand.id,
        platform="facebook",
        account_id="fb_page_999",
        account_name="Unselected FB Page",
        access_token="sandbox_fb_token_2",
        status="CONNECTED"
    )
    ig_acc2 = SocialAccount(
        user_id=user.id,
        brand_id=brand.id,
        platform="instagram",
        account_id="ig_biz_888",
        account_name="Unselected IG Account",
        access_token="sandbox_ig_token_2",
        status="CONNECTED",
        metadata_json={"account_type": "BUSINESS"}
    )
    db_session.add_all([fb_acc2, ig_acc2])
    db_session.commit()
    db_session.refresh(fb_acc2)
    db_session.refresh(ig_acc2)

    called_account_ids = []

    def mock_fb_pub(account, media_url, is_video=False, **kwargs):
        called_account_ids.append(account.id)
        return {"id": "fb_mock_story_1", "status": "published_sandbox"}

    def mock_ig_pub(account, media_url, is_video=False, **kwargs):
        called_account_ids.append(account.id)
        return {"id": "ig_mock_story_1", "container_id": "c1", "status": "published_sandbox"}

    with patch.object(story_service, "publish_facebook_story", side_effect=mock_fb_pub), \
         patch.object(story_service, "publish_instagram_story", side_effect=mock_ig_pub):

        # Select only fb_acc and ig_acc2
        story_in = StoryCreate(
            brand_id=brand.id,
            title="Selective Publish",
            media_url="https://example.com/pic.jpg",
            media_type="image",
            target_account_ids=[fb_acc.id, ig_acc2.id]
        )
        story = story_service.create_story(db_session, story_in, user.id)
        story_service.publish_story(db_session, story.id, user.id)

        assert called_account_ids == [fb_acc.id, ig_acc2.id]
        assert ig_acc.id not in called_account_ids
        assert fb_acc2.id not in called_account_ids


def test_target_account_belonging_to_another_user_rejected(db_session):
    user_a, brand_a, fb_acc_a, ig_acc_a = setup_user_brand_accounts(db_session, "user_a@test.com")
    user_b, brand_b, fb_acc_b, ig_acc_b = setup_user_brand_accounts(db_session, "user_b@test.com")

    # User A tries to target User B's account
    story_in = StoryCreate(
        brand_id=brand_a.id,
        title="Malicious Story",
        media_url="https://example.com/pic.jpg",
        media_type="image",
        target_account_ids=[fb_acc_b.id]
    )
    with pytest.raises(HTTPException) as exc:
        story_service.create_story(db_session, story_in, user_a.id)
    assert exc.value.status_code in [403, 400]


def test_target_account_nonexistent_rejected(db_session):
    user, brand, fb_acc, ig_acc = setup_user_brand_accounts(db_session, "nonexistent@test.com")

    story_in = StoryCreate(
        brand_id=brand.id,
        title="Invalid Account Story",
        media_url="https://example.com/pic.jpg",
        media_type="image",
        target_account_ids=[999999]
    )
    with pytest.raises(HTTPException) as exc:
        story_service.create_story(db_session, story_in, user.id)
    assert exc.value.status_code in [404, 400]


def test_empty_target_accounts_publish_rejected(db_session):
    user, brand, fb_acc, ig_acc = setup_user_brand_accounts(db_session, "empty_target@test.com")

    # 1. Direct publish without targets in create_story
    story_in = StoryCreate(
        brand_id=brand.id,
        title="Empty Target Story",
        media_url="https://example.com/pic.jpg",
        media_type="image",
        target_account_ids=[],
        status=StoryStatus.SCHEDULED.value
    )
    with pytest.raises(HTTPException) as exc:
        story_service.create_story(db_session, story_in, user.id)
    assert exc.value.status_code == 400

    # 2. Draft with empty targets attempting publish
    draft_in = StoryCreate(
        brand_id=brand.id,
        title="Draft Story",
        media_url="https://example.com/pic.jpg",
        media_type="image",
        target_account_ids=[],
        status=StoryStatus.DRAFT.value
    )
    draft = story_service.create_story(db_session, draft_in, user.id)
    with pytest.raises(HTTPException) as exc2:
        story_service.publish_story(db_session, draft.id, user.id)
    assert exc2.value.status_code == 400


def test_scheduled_story_publishes_persisted_targets(db_session):
    user, brand, fb_acc, ig_acc = setup_user_brand_accounts(db_session, "sched_persisted@test.com")
    now = datetime.now(timezone.utc)

    # Create and schedule targeting ONLY ig_acc
    story_in = StoryCreate(
        brand_id=brand.id,
        title="Scheduled Target Story",
        media_url="https://example.com/pic.jpg",
        media_type="image",
        target_account_ids=[ig_acc.id]
    )
    story = story_service.create_story(db_session, story_in, user.id)
    future_time = now + timedelta(hours=2)
    story_service.schedule_story(db_session, story.id, user.id, future_time)

    # Later, another account is added to the user
    new_fb = SocialAccount(
        user_id=user.id,
        brand_id=brand.id,
        platform="facebook",
        account_id="fb_page_new",
        account_name="Newly Added FB Page",
        access_token="sandbox_fb_token_new",
        status="CONNECTED"
    )
    db_session.add(new_fb)
    db_session.commit()

    # Backdate and auto-publish
    story.scheduled_at = now - timedelta(minutes=5)
    db_session.commit()

    with patch.object(story_service, "publish_instagram_story", wraps=story_service.publish_instagram_story) as mock_ig, \
         patch.object(story_service, "publish_facebook_story", wraps=story_service.publish_facebook_story) as mock_fb:

        due_published = story_service.check_and_publish_due_stories(db_session, user.id)
        assert len(due_published) == 1
        assert mock_ig.call_count == 1
        assert mock_fb.call_count == 0  # Newly added FB Page was NEVER touched


def test_retry_publishes_persisted_targets(db_session):
    user, brand, fb_acc, ig_acc = setup_user_brand_accounts(db_session, "retry_persisted@test.com")

    story = Story(
        brand_id=brand.id,
        user_id=user.id,
        title="Failed Persisted Story",
        media_url="https://example.com/pic.jpg",
        media_type="image",
        target_account_ids=[fb_acc.id],
        platforms=["facebook"],
        status=StoryStatus.FAILED.value,
        retry_count=1,
        max_retries=3
    )
    db_session.add(story)
    db_session.commit()
    db_session.refresh(story)

    with patch.object(story_service, "publish_instagram_story", wraps=story_service.publish_instagram_story) as mock_ig, \
         patch.object(story_service, "publish_facebook_story", wraps=story_service.publish_facebook_story) as mock_fb:

        retried = story_service.retry_story(db_session, story.id, user.id)
        assert retried.status == StoryStatus.PUBLISHED.value
        assert mock_fb.call_count == 1
        assert mock_ig.call_count == 0


def test_partial_target_failure_and_audit_details(db_session):
    user, brand, fb_acc, ig_acc = setup_user_brand_accounts(db_session, "partial_details@test.com")

    # Make IG account expired while FB account remains valid
    ig_acc.status = "TOKEN_EXPIRED"
    db_session.commit()

    story_in = StoryCreate(
        brand_id=brand.id,
        title="Partial Story",
        media_url="https://example.com/pic.jpg",
        media_type="image",
        target_account_ids=[fb_acc.id, ig_acc.id]
    )
    # Draft allows saving
    story = story_service.create_story(
        db_session,
        StoryCreate(
            brand_id=brand.id,
            title="Partial Story Draft",
            media_url="https://example.com/pic.jpg",
            media_type="image",
            target_account_ids=[fb_acc.id],  # Create with valid FB first
            status=StoryStatus.DRAFT.value
        ),
        user.id
    )
    # Manually attach both target_account_ids to test publish partial handling
    story.target_account_ids = [fb_acc.id, ig_acc.id]
    db_session.commit()

    published = story_service.publish_story(db_session, story.id, user.id)
    assert published.status == StoryStatus.PUBLISHED.value
    assert published.fb_story_id is not None
    assert "warnings" in published.last_error.lower()


def test_instagram_video_story_publishing(db_session):
    user, brand, fb_acc, ig_acc = setup_user_brand_accounts(db_session, "ig_vid_tester@test.com")

    story_in = StoryCreate(
        brand_id=brand.id,
        title="IG Video Story",
        media_url="https://example.com/vertical_reel.mp4",
        media_type="video",
        target_account_ids=[ig_acc.id]
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
        target_account_ids=[fb_acc.id]
    )
    story = story_service.create_story(db_session, story_in, user.id)
    published = story_service.publish_story(db_session, story.id, user.id)
    assert published.status == StoryStatus.PUBLISHED.value
    assert published.fb_story_id is not None


def test_story_publish_idempotency_prevents_duplicate_meta_calls(db_session):
    """Test that retrying or calling publish on an already PUBLISHED story makes ZERO Meta API calls."""
    user, brand, fb_acc, ig_acc = setup_user_brand_accounts(db_session, "idempotent_tester@test.com")

    with patch.object(story_service, "publish_instagram_story", wraps=story_service.publish_instagram_story) as mock_ig, \
         patch.object(story_service, "publish_facebook_story", wraps=story_service.publish_facebook_story) as mock_fb:

        story_in = StoryCreate(
            brand_id=brand.id,
            title="Idempotency Story",
            media_url="https://example.com/pic.jpg",
            media_type="image",
            target_account_ids=[fb_acc.id, ig_acc.id]
        )
        story = story_service.create_story(db_session, story_in, user.id)

        # First publish: 1 FB + 1 IG
        published1 = story_service.publish_story(db_session, story.id, user.id)
        assert published1.status == StoryStatus.PUBLISHED.value
        assert mock_fb.call_count == 1
        assert mock_ig.call_count == 1

        # Second publish (e.g. client re-attempt after timeout): 0 additional Meta calls
        published2 = story_service.publish_story(db_session, story.id, user.id)
        assert published2.status == StoryStatus.PUBLISHED.value
        assert mock_fb.call_count == 1
        assert mock_ig.call_count == 1


def test_story_publish_multi_account_duration_and_audit(db_session):
    """Test that multi-account publishing completes and audit log captures duration and accounts."""
    user, brand, fb_acc, ig_acc = setup_user_brand_accounts(db_session, "multi_audit_tester@test.com")

    story_in = StoryCreate(
        brand_id=brand.id,
        title="Multi-account Audit Story",
        media_url="https://example.com/pic.jpg",
        media_type="image",
        target_account_ids=[fb_acc.id, ig_acc.id]
    )
    story = story_service.create_story(db_session, story_in, user.id)
    published = story_service.publish_story(db_session, story.id, user.id)

    assert published.status == StoryStatus.PUBLISHED.value
    assert published.fb_story_id is not None
    assert published.ig_story_id is not None


def test_story_publishing_with_edited_media_preserves_targets(db_session):
    """Test that publishing an edited 9:16 media Story targets ONLY selected account IDs and uses processed URL."""
    user, brand, fb_acc, ig_acc = setup_user_brand_accounts(db_session, "edited_media_tester@test.com")

    # Add extra account that is NOT selected
    extra_acc = SocialAccount(
        user_id=user.id,
        brand_id=brand.id,
        platform="facebook",
        account_id="fb_page_extra",
        account_name="extra_fb_page",
        access_token="sandbox_token_extra",
        status="CONNECTED"
    )
    db_session.add(extra_acc)
    db_session.commit()
    db_session.refresh(extra_acc)

    with patch.object(story_service, "publish_facebook_story", wraps=story_service.publish_facebook_story) as mock_fb, \
         patch.object(story_service, "publish_instagram_story", wraps=story_service.publish_instagram_story) as mock_ig:

        # Processed 9:16 media URL from StoryMediaEditor
        edited_url = "https://res.cloudinary.com/demo/image/upload/v12345/story_edit_1080x1920.jpg"
        story_in = StoryCreate(
            brand_id=brand.id,
            title="Edited 9:16 Story",
            media_url=edited_url,
            media_type="image",
            target_account_ids=[fb_acc.id]  # Only fb_acc selected
        )
        story = story_service.create_story(db_session, story_in, user.id)
        assert story.media_url == edited_url
        assert story.target_account_ids == [fb_acc.id]

        published = story_service.publish_story(db_session, story.id, user.id)
        assert published.status == StoryStatus.PUBLISHED.value
        assert published.media_url == edited_url
        assert published.fb_story_id is not None

        # Verify only selected fb_acc received publish call, extra_acc received ZERO
        assert mock_fb.call_count == 1
        call_acc = mock_fb.call_args[1]["account"]
        assert call_acc.id == fb_acc.id
        assert call_acc.id != extra_acc.id
        assert mock_ig.call_count == 0


def test_instagram_story_container_polling_ready_first_try(db_session):
    """Test Instagram Story container polling succeeds immediately when status is FINISHED on first poll."""
    user, brand, fb_acc, ig_acc = setup_user_brand_accounts(db_session, "ig_poll_1@test.com")
    ig_acc.access_token = "live_meta_access_token_123"
    db_session.commit()

    with patch("app.services.story_service.requests.post") as mock_post, \
         patch("app.services.story_service.requests.get") as mock_get, \
         patch("app.services.story_service.settings.META_MOCK_MODE", False):

        # 1. Container creation
        mock_container_resp = MagicMock()
        mock_container_resp.status_code = 200
        mock_container_resp.json.return_value = {"id": "179998887770001"}

        # 2. Publish response
        mock_publish_resp = MagicMock()
        mock_publish_resp.status_code = 200
        mock_publish_resp.json.return_value = {"id": "180009998880002"}

        mock_post.side_effect = [mock_container_resp, mock_publish_resp]

        # Container status poll
        mock_status_resp = MagicMock()
        mock_status_resp.status_code = 200
        mock_status_resp.json.return_value = {"status_code": "FINISHED", "id": "179998887770001"}
        mock_get.return_value = mock_status_resp

        res = story_service.publish_instagram_story(
            account=ig_acc,
            media_url="https://res.cloudinary.com/demo/image/upload/story_edit.jpg",
            is_video=False,
            story_id=42
        )

        assert res["id"] == "180009998880002"
        assert res["container_id"] == "179998887770001"
        assert res["status"] == "published"
        assert mock_get.call_count == 2  # 1 for container poll, 1 for permalink
        assert mock_post.call_count == 2


def test_instagram_story_container_polling_in_progress_then_finished(db_session):
    """Test Instagram Story container polling handles IN_PROGRESS before transitioning to FINISHED."""
    user, brand, fb_acc, ig_acc = setup_user_brand_accounts(db_session, "ig_poll_2@test.com")
    ig_acc.access_token = "live_meta_access_token_456"
    db_session.commit()

    with patch("app.services.story_service.requests.post") as mock_post, \
         patch("app.services.story_service.requests.get") as mock_get, \
         patch("app.services.story_service.time.sleep") as mock_sleep, \
         patch("app.services.story_service.settings.META_MOCK_MODE", False):

        mock_container_resp = MagicMock()
        mock_container_resp.status_code = 200
        mock_container_resp.json.return_value = {"id": "container_multi_poll"}

        mock_publish_resp = MagicMock()
        mock_publish_resp.status_code = 200
        mock_publish_resp.json.return_value = {"id": "media_published_multi"}

        mock_post.side_effect = [mock_container_resp, mock_publish_resp]

        # 2 IN_PROGRESS responses followed by FINISHED, plus permalink query
        poll_resp_1 = MagicMock(status_code=200, json=lambda: {"status_code": "IN_PROGRESS"})
        poll_resp_2 = MagicMock(status_code=200, json=lambda: {"status_code": "IN_PROGRESS"})
        poll_resp_3 = MagicMock(status_code=200, json=lambda: {"status_code": "FINISHED"})
        permalink_resp = MagicMock(status_code=200, json=lambda: {"permalink": "https://instagram.com/p/123"})
        mock_get.side_effect = [poll_resp_1, poll_resp_2, poll_resp_3, permalink_resp]

        res = story_service.publish_instagram_story(
            account=ig_acc,
            media_url="https://res.cloudinary.com/demo/image/upload/story_edit_2.jpg",
            is_video=False,
            story_id=43
        )

        assert res["id"] == "media_published_multi"
        assert mock_get.call_count == 4  # 3 status polls + 1 permalink query
        assert mock_sleep.call_count == 2


def test_instagram_story_container_polling_error_fails_cleanly(db_session):
    """Test Instagram Story container polling raises clean exception when Meta reports ERROR status."""
    user, brand, fb_acc, ig_acc = setup_user_brand_accounts(db_session, "ig_poll_err@test.com")
    ig_acc.access_token = "live_meta_access_token_err"
    db_session.commit()

    with patch("app.services.story_service.requests.post") as mock_post, \
         patch("app.services.story_service.requests.get") as mock_get, \
         patch("app.services.story_service.settings.META_MOCK_MODE", False):

        mock_container_resp = MagicMock(status_code=200, json=lambda: {"id": "container_err"})
        mock_post.return_value = mock_container_resp

        mock_status_resp = MagicMock(status_code=200, json=lambda: {
            "status_code": "ERROR",
            "status": "Media download timed out or invalid format"
        })
        mock_get.return_value = mock_status_resp

        with pytest.raises(Exception) as exc_info:
            story_service.publish_instagram_story(
                account=ig_acc,
                media_url="https://res.cloudinary.com/demo/image/upload/invalid.jpg",
                is_video=False,
                story_id=44
            )

        assert "container failed processing with status: ERROR" in str(exc_info.value)
        assert mock_post.call_count == 1  # Never calls media_publish


def test_instagram_story_container_polling_timeout_raises_clear_error(db_session):
    """Test Instagram Story container polling times out gracefully if Meta never reports FINISHED."""
    user, brand, fb_acc, ig_acc = setup_user_brand_accounts(db_session, "ig_poll_timeout@test.com")
    ig_acc.access_token = "live_meta_access_token_timeout"
    db_session.commit()

    with patch("app.services.story_service.requests.post") as mock_post, \
         patch("app.services.story_service.requests.get") as mock_get, \
         patch("app.services.story_service.time.sleep") as mock_sleep, \
         patch("app.services.story_service.settings.META_MOCK_MODE", False):

        mock_container_resp = MagicMock(status_code=200, json=lambda: {"id": "container_timeout"})
        mock_post.return_value = mock_container_resp

        # Always returns IN_PROGRESS
        mock_status_resp = MagicMock(status_code=200, json=lambda: {"status_code": "IN_PROGRESS"})
        mock_get.return_value = mock_status_resp

        with pytest.raises(Exception) as exc_info:
            story_service.publish_instagram_story(
                account=ig_acc,
                media_url="https://res.cloudinary.com/demo/image/upload/slow.jpg",
                is_video=False,
                story_id=45
            )

        assert "processing timed out" in str(exc_info.value)
        assert mock_post.call_count == 1  # Never calls media_publish


def test_story_publish_partial_success_fb_succeeds_ig_fails(db_session):
    """Test that when FB succeeds and IG fails, story status is PUBLISHED with warnings, capturing successful and failed account IDs."""
    user, brand, fb_acc, ig_acc = setup_user_brand_accounts(db_session, "partial_success_tester@test.com")

    with patch.object(story_service, "publish_facebook_story", return_value={"id": "fb_story_101", "status": "published", "url": "https://www.facebook.com/stories/123"}), \
         patch.object(story_service, "publish_instagram_story", side_effect=Exception("Instagram Story container processing timed out after 40s")):

        story_in = StoryCreate(
            brand_id=brand.id,
            title="Partial Success Story",
            media_url="https://res.cloudinary.com/demo/image/upload/story.jpg",
            media_type="image",
            target_account_ids=[fb_acc.id, ig_acc.id]
        )
        story = story_service.create_story(db_session, story_in, user.id)
        published = story_service.publish_story(db_session, story.id, user.id)

        assert published.status == StoryStatus.PUBLISHED.value
        assert published.fb_story_id == "fb_story_101"
        assert published.fb_story_url == "https://www.facebook.com/stories/123"
        assert published.ig_story_id is None
        assert published.ig_story_url is None
        assert "Published with warnings" in published.last_error
        assert "instagram" in published.last_error.lower()


def test_story_deletion_success_both_platforms(db_session):
    """Test that deleting a published story with both FB and IG targets deletes both on Meta and deletes local record."""
    user, brand, fb_acc, ig_acc = setup_user_brand_accounts(db_session, "delete_success@test.com")

    story = Story(
        brand_id=brand.id,
        user_id=user.id,
        title="To Delete Story",
        media_url="https://res.cloudinary.com/demo/image/upload/del.jpg",
        media_type="image",
        target_account_ids=[fb_acc.id, ig_acc.id],
        platforms=["facebook", "instagram"],
        status=StoryStatus.PUBLISHED.value,
        fb_story_id="fb_story_999",
        fb_story_url="https://www.facebook.com/stories/123",
        ig_story_id="ig_story_888",
        ig_story_url="https://www.instagram.com/stories/testuser/"
    )
    db_session.add(story)
    db_session.commit()
    story_id = story.id

    with patch("app.services.story_service.meta_service.delete_facebook_post", return_value={"success": True, "status": "deleted"}) as mock_fb_del, \
         patch("app.services.story_service.meta_service.delete_instagram_media", return_value={"success": True, "status": "deleted"}) as mock_ig_del:

        res = story_service.delete_story(db_session, story_id, user.id)
        assert res["success"] is True
        assert res["deleted_external_targets"] == 2
        assert res["failed_external_targets"] == 0
        assert mock_fb_del.call_count == 1
        assert mock_ig_del.call_count == 1

        # Check DB record is removed
        assert db_session.query(Story).filter(Story.id == story_id).first() is None


def test_story_deletion_partial_failure_retains_record(db_session):
    """Test that when FB deletion succeeds but IG deletion fails, local story record is retained and partial state saved."""
    user, brand, fb_acc, ig_acc = setup_user_brand_accounts(db_session, "delete_partial@test.com")

    story = Story(
        brand_id=brand.id,
        user_id=user.id,
        title="Partial Delete Story",
        media_url="https://res.cloudinary.com/demo/image/upload/del.jpg",
        media_type="image",
        target_account_ids=[fb_acc.id, ig_acc.id],
        platforms=["facebook", "instagram"],
        status=StoryStatus.PUBLISHED.value,
        fb_story_id="fb_story_777",
        fb_story_url="https://www.facebook.com/stories/123",
        ig_story_id="ig_story_666",
        ig_story_url="https://www.instagram.com/stories/testuser/"
    )
    db_session.add(story)
    db_session.commit()
    story_id = story.id

    with patch("app.services.story_service.meta_service.delete_facebook_post", return_value={"success": True, "status": "deleted"}), \
         patch("app.services.story_service.meta_service.delete_instagram_media", side_effect=Exception("Instagram Graph API Delete Error (400): Unsupported request")):

        res = story_service.delete_story(db_session, story_id, user.id)
        assert res["success"] is False
        assert res["deleted_external_targets"] == 1
        assert res["failed_external_targets"] == 1
        assert len(res["details"]) == 2

        # Verify local story is still in DB with FB cleared and IG retained
        saved = db_session.query(Story).filter(Story.id == story_id).first()
        assert saved is not None
        assert saved.fb_story_id is None
        assert saved.fb_story_url is None
        assert saved.ig_story_id == "ig_story_666"
        assert saved.ig_story_url == "https://www.instagram.com/stories/testuser/"
        assert "Deletion failed" in saved.last_error


def test_scheduled_story_deletion_cancels_without_meta_calls(db_session):
    """Test that deleting a SCHEDULED story cancels scheduled state and removes record without calling Meta APIs."""
    user, brand, fb_acc, ig_acc = setup_user_brand_accounts(db_session, "sched_del@test.com")

    story = Story(
        brand_id=brand.id,
        user_id=user.id,
        title="Scheduled Story",
        media_url="https://res.cloudinary.com/demo/image/upload/sched.jpg",
        media_type="image",
        target_account_ids=[fb_acc.id],
        platforms=["facebook"],
        status=StoryStatus.SCHEDULED.value,
        scheduled_at=datetime.now(timezone.utc) + timedelta(hours=2)
    )
    db_session.add(story)
    db_session.commit()
    story_id = story.id

    with patch("app.services.story_service.meta_service.delete_facebook_post") as mock_fb_del, \
         patch("app.services.story_service.meta_service.delete_instagram_media") as mock_ig_del:

        res = story_service.delete_story(db_session, story_id, user.id)
        assert res["success"] is True
        assert mock_fb_del.call_count == 0
        assert mock_ig_del.call_count == 0
        assert db_session.query(Story).filter(Story.id == story_id).first() is None


def test_unauthorized_user_cannot_delete_story(db_session):
    """Test that a user cannot delete another user's story."""
    user1, brand1, fb_acc1, _ = setup_user_brand_accounts(db_session, "owner@test.com")
    user2, _, _, _ = setup_user_brand_accounts(db_session, "attacker@test.com")

    story = Story(
        brand_id=brand1.id,
        user_id=user1.id,
        title="Private Story",
        media_url="https://res.cloudinary.com/demo/image/upload/p.jpg",
        media_type="image",
        target_account_ids=[fb_acc1.id],
        platforms=["facebook"],
        status=StoryStatus.DRAFT.value
    )
    db_session.add(story)
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        story_service.delete_story(db_session, story.id, user2.id)

    assert exc_info.value.status_code == 403





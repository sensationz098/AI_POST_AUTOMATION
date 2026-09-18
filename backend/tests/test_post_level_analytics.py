import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from app.models.user import User
from app.models.brand import BrandProfile
from app.models.social_account import SocialAccount
from app.models.post import Post, PostStatus
from app.models.analytics import PostAnalytics
from app.models.publishing_batch import PublishingBatch, PublishingJob, BatchStatus, JobStatus
from app.models.youtube_upload import YouTubeUpload, YouTubeUploadStatus
from app.repositories.analytics_repository import analytics_repo
from app.services.analytics_service import analytics_service
from app.core.security_encryption import encrypt_token
from app.tasks.publish_task import sync_meta_analytics_task

@pytest.fixture
def test_user_and_brand(db_session):
    user = User(
        email="post_analytics_tester@example.com",
        full_name="Post Analytics Tester",
        hashed_password="hashed_pw_test",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    brand = BrandProfile(
        user_id=user.id,
        name="Test Brand",
        industry="Technology"
    )
    db_session.add(brand)
    db_session.commit()
    db_session.refresh(brand)

    return user, brand

@pytest.fixture
def secondary_user_and_brand(db_session):
    user2 = User(
        email="other_analytics_user@example.com",
        full_name="Other User",
        hashed_password="hashed_pw_test2",
        is_active=True
    )
    db_session.add(user2)
    db_session.commit()
    db_session.refresh(user2)

    brand2 = BrandProfile(
        user_id=user2.id,
        name="Other Brand",
        industry="Retail"
    )
    db_session.add(brand2)
    db_session.commit()
    db_session.refresh(brand2)

    return user2, brand2

@patch("app.services.meta_service.meta_service.fetch_instagram_post_metrics")
def test_instagram_post_analytics_sync(mock_ig_metrics, db_session, test_user_and_brand):
    """Test synchronizing post analytics for an Instagram-published post."""
    user, brand = test_user_and_brand
    account = SocialAccount(
        user_id=user.id,
        brand_id=brand.id,
        platform="instagram",
        account_id="ig_acc_123",
        account_name="@testbrand",
        access_token=encrypt_token("valid_ig_token"),
        status="CONNECTED"
    )
    db_session.add(account)
    db_session.commit()

    post = Post(
        user_id=user.id,
        brand_id=brand.id,
        title="Instagram Launch",
        caption="Exciting launch #tech",
        status=PostStatus.PUBLISHED.value,
        ig_media_id="ig_media_9999",
        platforms=["instagram"],
        published_at=datetime.now(timezone.utc)
    )
    db_session.add(post)
    db_session.commit()

    mock_ig_metrics.return_value = {
        "likes": 150,
        "comments": 25,
        "shares": 10,
        "saves": 35,
        "reach": 1200,
        "impressions": 2000
    }

    synced = analytics_service.sync_post_analytics(db_session, post.id)
    assert synced is not None
    assert synced.post_id == post.id
    assert synced.likes == 150
    assert synced.comments == 25
    assert synced.shares == 10
    assert synced.saves == 35
    assert synced.reach == 1200
    assert synced.impressions == 2000
    # Total engagements = 150 + 25 + 10 + 35 = 220; Denominator = 2000; Rate = (220 / 2000) * 100 = 11.0%
    assert synced.engagement_rate == 11.0

@patch("app.services.meta_service.meta_service.fetch_facebook_post_metrics")
def test_facebook_post_analytics_sync(mock_fb_metrics, db_session, test_user_and_brand):
    """Test Facebook post analytics sync, verifying saves is strictly None."""
    user, brand = test_user_and_brand
    account = SocialAccount(
        user_id=user.id,
        brand_id=brand.id,
        platform="facebook",
        account_id="fb_page_123",
        account_name="Test FB Page",
        access_token=encrypt_token("valid_fb_token"),
        status="CONNECTED"
    )
    db_session.add(account)
    db_session.commit()

    post = Post(
        user_id=user.id,
        brand_id=brand.id,
        title="Facebook Update",
        caption="New features released",
        status=PostStatus.PUBLISHED.value,
        fb_post_id="fb_post_8888",
        platforms=["facebook"],
        published_at=datetime.now(timezone.utc)
    )
    db_session.add(post)
    db_session.commit()

    mock_fb_metrics.return_value = {
        "likes": 80,
        "comments": 15,
        "shares": 5,
        "saves": None, # FB does not provide saves
        "reach": 600,
        "impressions": 900
    }

    synced = analytics_service.sync_post_analytics(db_session, post.id)
    assert synced is not None
    assert synced.likes == 80
    assert synced.comments == 15
    assert synced.shares == 5
    assert synced.saves is None
    assert synced.reach == 600
    assert synced.impressions == 900
    # Total engagements = 80 + 15 + 5 = 100; Denominator = 900; Rate = (100 / 900) * 100 = 11.11%
    assert synced.engagement_rate == 11.11

@patch("app.services.youtube_service.youtube_service.fetch_video_statistics")
@patch("app.services.youtube_service.youtube_service.get_valid_access_token_for_account")
def test_youtube_video_statistics_semantics(mock_token, mock_yt_stats, db_session, test_user_and_brand):
    """Test YouTube post sync: viewCount is NOT mapped to impressions; reach, impressions, shares, saves remain None."""
    user, brand = test_user_and_brand
    account = SocialAccount(
        user_id=user.id,
        brand_id=brand.id,
        platform="youtube",
        account_id="yt_channel_123",
        account_name="Tech Channel",
        access_token=encrypt_token("valid_yt_token"),
        status="CONNECTED"
    )
    db_session.add(account)
    db_session.commit()

    post = Post(
        user_id=user.id,
        brand_id=brand.id,
        title="YouTube Video Guide",
        caption="Full video walkthrough of our platform",
        status=PostStatus.PUBLISHED.value,
        platforms=["youtube"],
        published_at=datetime.now(timezone.utc)
    )
    db_session.add(post)
    db_session.commit()

    # Associated completed YouTube upload
    upload = YouTubeUpload(
        upload_id="ytu_test_123",
        user_id=user.id,
        social_account_id=account.id,
        channel_id="yt_channel_123",
        video_id="dQw4w9WgXcQ",
        title="YouTube Video Guide",
        description="Full video walkthrough of our platform",
        file_size_bytes=10485760,
        upload_status=YouTubeUploadStatus.READY.value
    )
    db_session.add(upload)
    db_session.commit()

    mock_token.return_value = "fresh_yt_token"
    mock_yt_stats.return_value = {
        "likes": 250,
        "comments": 45,
        "shares": None,
        "saves": None,
        "reach": None,
        "impressions": None # Strict semantic: views are not impressions
    }

    synced = analytics_service.sync_post_analytics(db_session, post.id)
    assert synced is not None
    assert synced.likes == 250
    assert synced.comments == 45
    assert synced.shares is None
    assert synced.saves is None
    assert synced.reach is None
    assert synced.impressions is None
    # With no impressions/reach denominator, engagement rate is None (not 0.0)
    assert synced.engagement_rate is None

@patch("app.services.meta_service.meta_service.fetch_instagram_post_metrics")
@patch("app.services.meta_service.meta_service.fetch_facebook_post_metrics")
def test_multi_platform_aggregation(mock_fb, mock_ig, db_session, test_user_and_brand):
    """Test aggregating metrics across FB and IG destinations for a multi-platform post."""
    user, brand = test_user_and_brand
    fb_acc = SocialAccount(
        user_id=user.id, brand_id=brand.id, platform="facebook",
        account_id="fb_page_1", account_name="FB Page",
        access_token=encrypt_token("tok_fb"), status="CONNECTED"
    )
    ig_acc = SocialAccount(
        user_id=user.id, brand_id=brand.id, platform="instagram",
        account_id="ig_acc_1", account_name="@ig_acc",
        access_token=encrypt_token("tok_ig"), status="CONNECTED"
    )
    db_session.add_all([fb_acc, ig_acc])
    db_session.commit()

    post = Post(
        user_id=user.id,
        brand_id=brand.id,
        title="Multi-Platform Campaign",
        caption="Campaign across both networks",
        status=PostStatus.PUBLISHED.value,
        fb_post_id="fb_post_1",
        ig_media_id="ig_media_1",
        platforms=["facebook", "instagram"],
        published_at=datetime.now(timezone.utc)
    )
    db_session.add(post)
    db_session.commit()

    mock_fb.return_value = {
        "likes": 100, "comments": 20, "shares": 10,
        "saves": None, "reach": 500, "impressions": 800
    }
    mock_ig.return_value = {
        "likes": 200, "comments": 30, "shares": 15,
        "saves": 40, "reach": 1000, "impressions": 1500
    }

    synced = analytics_service.sync_post_analytics(db_session, post.id)
    assert synced is not None
    # Summed metrics:
    assert synced.likes == 300 # 100 + 200
    assert synced.comments == 50 # 20 + 30
    assert synced.shares == 25 # 10 + 15
    assert synced.saves == 40 # None + 40 -> 40
    assert synced.reach == 1500 # 500 + 1000 (summed, non-deduplicated reach)
    assert synced.impressions == 2300 # 800 + 1500
    # Total engagements = 300 + 50 + 25 + 40 = 415; Denominator = 2300; Rate = (415 / 2300) * 100 = 18.04%
    assert synced.engagement_rate == 18.04

@patch("app.services.meta_service.meta_service.fetch_instagram_post_metrics")
def test_idempotent_post_analytics_upsert(mock_ig, db_session, test_user_and_brand):
    """Test that repeatedly synchronizing the same post updates the row in-place without duplicating."""
    user, brand = test_user_and_brand
    account = SocialAccount(
        user_id=user.id, brand_id=brand.id, platform="instagram",
        account_id="ig_id_777", account_name="@tester",
        access_token=encrypt_token("tok"), status="CONNECTED"
    )
    db_session.add(account)
    db_session.commit()

    post = Post(
        user_id=user.id, brand_id=brand.id,
        caption="Idempotency check", status=PostStatus.PUBLISHED.value,
        ig_media_id="ig_med_777", platforms=["instagram"]
    )
    db_session.add(post)
    db_session.commit()

    mock_ig.return_value = {"likes": 10, "comments": 2, "shares": None, "saves": None, "reach": 100, "impressions": 150}
    snap1 = analytics_service.sync_post_analytics(db_session, post.id)

    # Second sync run with updated values
    mock_ig.return_value = {"likes": 15, "comments": 3, "shares": None, "saves": None, "reach": 120, "impressions": 180}
    snap2 = analytics_service.sync_post_analytics(db_session, post.id)

    assert snap1.id == snap2.id
    assert snap2.likes == 15
    assert snap2.impressions == 180

    total_rows = db_session.query(PostAnalytics).filter(PostAnalytics.post_id == post.id).count()
    assert total_rows == 1

@patch("app.services.meta_service.meta_service.fetch_instagram_post_metrics")
def test_reach_fallback_when_impressions_null(mock_ig, db_session, test_user_and_brand):
    """Test engagement rate calculation falls back to reach when impressions is None."""
    user, brand = test_user_and_brand
    account = SocialAccount(
        user_id=user.id, brand_id=brand.id, platform="instagram",
        account_id="ig_fallback_test", account_name="@fallback",
        access_token=encrypt_token("tok"), status="CONNECTED"
    )
    db_session.add(account)
    db_session.commit()

    post = Post(
        user_id=user.id, brand_id=brand.id,
        caption="Fallback reach test", status=PostStatus.PUBLISHED.value,
        ig_media_id="ig_fallback_media", platforms=["instagram"]
    )
    db_session.add(post)
    db_session.commit()

    mock_ig.return_value = {
        "likes": 50, "comments": 10, "shares": None, "saves": None,
        "reach": 500, "impressions": None
    }

    synced = analytics_service.sync_post_analytics(db_session, post.id)
    assert synced is not None
    assert synced.impressions is None
    assert synced.reach == 500
    # Engagements = 60; Denominator = 500 (reach fallback); Rate = (60 / 500) * 100 = 12.0%
    assert synced.engagement_rate == 12.0

@patch("app.services.meta_service.meta_service.fetch_instagram_post_metrics")
def test_tenant_scoping_isolation(mock_ig, db_session, test_user_and_brand, secondary_user_and_brand):
    """Test that a post cannot be synced using another user's connected social account."""
    user1, brand1 = test_user_and_brand
    user2, brand2 = secondary_user_and_brand

    # User 2 owns Instagram account
    acc2 = SocialAccount(
        user_id=user2.id, brand_id=brand2.id, platform="instagram",
        account_id="user2_ig", account_name="@user2",
        access_token=encrypt_token("user2_tok"), status="CONNECTED"
    )
    db_session.add(acc2)
    db_session.commit()

    # User 1 has a post referencing an IG media ID but has NO connected Instagram account
    post1 = Post(
        user_id=user1.id, brand_id=brand1.id,
        caption="User 1 post without IG account", status=PostStatus.PUBLISHED.value,
        ig_media_id="ig_target_123", platforms=["instagram"]
    )
    db_session.add(post1)
    db_session.commit()

    # Should not resolve acc2 for User 1's post
    synced = analytics_service.sync_post_analytics(db_session, post1.id)
    assert synced is None
    mock_ig.assert_not_called()

@patch("app.services.meta_service.meta_service.fetch_instagram_post_metrics")
def test_single_post_error_isolation_in_batch(mock_ig, db_session, test_user_and_brand):
    """Test that failure in synchronizing one post does not abort the batch."""
    user, brand = test_user_and_brand
    acc = SocialAccount(
        user_id=user.id, brand_id=brand.id, platform="instagram",
        account_id="ig_batch_acc", account_name="@batch",
        access_token=encrypt_token("tok"), status="CONNECTED"
    )
    db_session.add(acc)
    db_session.commit()

    post_failing = Post(
        user_id=user.id, brand_id=brand.id,
        caption="Failing post", status=PostStatus.PUBLISHED.value,
        ig_media_id="failing_media_id", platforms=["instagram"]
    )
    post_healthy = Post(
        user_id=user.id, brand_id=brand.id,
        caption="Healthy post", status=PostStatus.PUBLISHED.value,
        ig_media_id="healthy_media_id", platforms=["instagram"]
    )
    db_session.add_all([post_failing, post_healthy])
    db_session.commit()

    def mock_fetch(media_id, token):
        if media_id == "failing_media_id":
            raise RuntimeError("API Rate limit or deleted media")
        return {"likes": 50, "comments": 5, "shares": 2, "saves": 1, "reach": 400, "impressions": 600}

    mock_ig.side_effect = mock_fetch

    batch_result = analytics_service.sync_all_published_posts_analytics(db_session, limit=50)
    assert batch_result["total_posts"] == 2
    assert batch_result["success"] == 1
    assert batch_result["failed"] == 1

    # Healthy post analytics exists
    healthy_an = analytics_repo.get_by_post(db_session, post_healthy.id)
    assert healthy_an is not None
    assert healthy_an.likes == 50

    # Failing post analytics does not exist
    failing_an = analytics_repo.get_by_post(db_session, post_failing.id)
    assert failing_an is None

@patch("app.services.account_snapshot_service.account_snapshot_service.capture_all_active_snapshots")
@patch("app.services.analytics_service.analytics_service.sync_all_published_posts_analytics")
def test_celery_task_independent_error_isolation(mock_sync_posts, mock_capture_accounts, db_session):
    """Test that Celery task sync_meta_analytics_task executes Block 1 and Block 2 independently."""
    # Scenario: Block 1 fails with Exception, Block 2 should still execute successfully
    mock_capture_accounts.side_effect = RuntimeError("Account snapshot DB error")
    mock_sync_posts.return_value = {"total_posts": 5, "success": 5, "failed": 0}

    res = sync_meta_analytics_task()
    assert res["status"] == "synced"
    assert res["account_snapshots"]["status"] == "ERROR"
    assert res["post_analytics"]["success"] == 5
    mock_capture_accounts.assert_called_once()
    mock_sync_posts.assert_called_once()

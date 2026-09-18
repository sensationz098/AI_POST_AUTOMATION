import pytest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

from app.models.user import User
from app.models.brand import BrandProfile
from app.models.social_account import SocialAccount
from app.models.account_metric_snapshot import AccountMetricSnapshot
from app.repositories.account_metric_snapshot_repository import account_metric_snapshot_repo
from app.services.account_snapshot_service import account_snapshot_service
from app.core.security_encryption import encrypt_token
from app.tasks.publish_task import sync_meta_analytics_task

@pytest.fixture
def test_user_and_brand(db_session):
    user = User(
        email="analytics_tester@example.com",
        full_name="Analytics User",
        hashed_password="hashed_pw_test",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    brand = BrandProfile(
        user_id=user.id,
        name="Test Brand",
        industry="Tech",
        target_audience="Tech enthusiasts"
    )
    db_session.add(brand)
    db_session.commit()
    db_session.refresh(brand)

    return user, brand

@pytest.fixture
def secondary_user_and_brand(db_session):
    user2 = User(
        email="other_user@example.com",
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

def test_snapshot_creation_and_fields(db_session, test_user_and_brand):
    """Test creating an account snapshot with platform-specific fields."""
    user, brand = test_user_and_brand
    account = SocialAccount(
        user_id=user.id,
        brand_id=brand.id,
        platform="instagram",
        account_id="ig_12345",
        account_name="@testbrand",
        access_token=encrypt_token("valid_token"),
        status="CONNECTED"
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)

    today = date(2026, 9, 18)
    snapshot = account_metric_snapshot_repo.upsert_snapshot(
        db=db_session,
        social_account_id=account.id,
        snapshot_date=today,
        followers_count=15420,
        following_count=350,
        media_count=128,
        reach=5400,
        impressions=12000,
        engagement_rate=4.25,
        metadata_json={"media_count_source": "meta_verified_exact_total"}
    )

    assert snapshot.id is not None
    assert snapshot.social_account_id == account.id
    assert snapshot.snapshot_date == today
    assert snapshot.followers_count == 15420
    assert snapshot.following_count == 350
    assert snapshot.media_count == 128
    assert snapshot.reach == 5400
    assert snapshot.impressions == 12000
    assert snapshot.engagement_rate == 4.25
    assert snapshot.metadata_json.get("media_count_source") == "meta_verified_exact_total"
    assert snapshot.created_at is not None

def test_duplicate_same_day_snapshot_idempotency(db_session, test_user_and_brand):
    """Test that running snapshot creation twice for the same date updates in place instead of duplicating."""
    user, brand = test_user_and_brand
    account = SocialAccount(
        user_id=user.id,
        brand_id=brand.id,
        platform="facebook",
        account_id="fb_page_999",
        account_name="Facebook Page",
        access_token=encrypt_token("fb_token"),
        status="CONNECTED"
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)

    snap_date = date(2026, 9, 18)

    # First run
    snap1 = account_metric_snapshot_repo.upsert_snapshot(
        db=db_session,
        social_account_id=account.id,
        snapshot_date=snap_date,
        followers_count=1000,
        media_count=10
    )

    # Second run on same day with updated numbers
    snap2 = account_metric_snapshot_repo.upsert_snapshot(
        db=db_session,
        social_account_id=account.id,
        snapshot_date=snap_date,
        followers_count=1050,
        media_count=11
    )

    # Should be same row
    assert snap1.id == snap2.id
    assert snap2.followers_count == 1050
    assert snap2.media_count == 11

    # Total count in database for this account should be exactly 1
    total = db_session.query(AccountMetricSnapshot).filter(
        AccountMetricSnapshot.social_account_id == account.id
    ).count()
    assert total == 1

def test_date_range_retrieval(db_session, test_user_and_brand):
    """Test retrieving chronological snapshots over a specified date range."""
    user, brand = test_user_and_brand
    account = SocialAccount(
        user_id=user.id,
        brand_id=brand.id,
        platform="youtube",
        account_id="yt_channel_1",
        account_name="Tech Channel",
        access_token=encrypt_token("yt_token"),
        status="CONNECTED"
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)

    # Create 5 consecutive days of snapshots
    base_date = date(2026, 9, 10)
    for i in range(5):
        current_date = base_date + timedelta(days=i)
        account_metric_snapshot_repo.upsert_snapshot(
            db=db_session,
            social_account_id=account.id,
            snapshot_date=current_date,
            followers_count=1000 + (i * 50),
            views_count=50000 + (i * 1200),
            media_count=20 + i
        )

    # Query full range
    all_snaps = account_metric_snapshot_repo.get_snapshots_for_account(
        db=db_session,
        social_account_id=account.id
    )
    assert len(all_snaps) == 5

    # Query filtered date range (2026-09-11 to 2026-09-13)
    filtered = account_metric_snapshot_repo.get_snapshots_for_account(
        db=db_session,
        social_account_id=account.id,
        start_date=date(2026, 9, 11),
        end_date=date(2026, 9, 13)
    )
    assert len(filtered) == 3
    assert filtered[0].snapshot_date == date(2026, 9, 11)
    assert filtered[0].followers_count == 1050
    assert filtered[2].snapshot_date == date(2026, 9, 13)
    assert filtered[2].followers_count == 1150

def test_account_and_user_scoping_isolation(db_session, test_user_and_brand, secondary_user_and_brand):
    """Test that metric snapshots are strictly scoped and never leak across users or brands."""
    user1, brand1 = test_user_and_brand
    user2, brand2 = secondary_user_and_brand

    acc1 = SocialAccount(
        user_id=user1.id,
        brand_id=brand1.id,
        platform="instagram",
        account_id="user1_ig",
        account_name="@user1",
        access_token=encrypt_token("tok1"),
        status="CONNECTED"
    )
    acc2 = SocialAccount(
        user_id=user2.id,
        brand_id=brand2.id,
        platform="instagram",
        account_id="user2_ig",
        account_name="@user2",
        access_token=encrypt_token("tok2"),
        status="CONNECTED"
    )
    db_session.add_all([acc1, acc2])
    db_session.commit()
    db_session.refresh(acc1)
    db_session.refresh(acc2)

    today = date(2026, 9, 18)
    account_metric_snapshot_repo.upsert_snapshot(
        db=db_session,
        social_account_id=acc1.id,
        snapshot_date=today,
        followers_count=500
    )
    account_metric_snapshot_repo.upsert_snapshot(
        db=db_session,
        social_account_id=acc2.id,
        snapshot_date=today,
        followers_count=9000
    )

    # Query User 1 snapshots
    user1_snaps = account_metric_snapshot_repo.get_snapshots_by_user(
        db=db_session,
        user_id=user1.id
    )
    assert len(user1_snaps) == 1
    assert user1_snaps[0].followers_count == 500
    assert user1_snaps[0].social_account_id == acc1.id

    # Query User 2 snapshots
    user2_snaps = account_metric_snapshot_repo.get_snapshots_by_user(
        db=db_session,
        user_id=user2.id
    )
    assert len(user2_snaps) == 1
    assert user2_snaps[0].followers_count == 9000
    assert user2_snaps[0].social_account_id == acc2.id

    # Query via service enforcing tenant ownership
    user1_via_service = account_snapshot_service.get_account_snapshots(
        db=db_session,
        social_account_id=acc2.id, # Attempting to access acc2 with user1 credentials
        user_id=user1.id
    )
    assert user1_via_service == [] # Access denied / scoped out

    # Brand scoping query
    brand1_snaps = account_metric_snapshot_repo.get_snapshots_by_brand(
        db=db_session,
        brand_id=brand1.id,
        user_id=user1.id
    )
    assert len(brand1_snaps) == 1
    assert brand1_snaps[0].social_account_id == acc1.id

def test_nullable_platform_specific_metrics(db_session, test_user_and_brand):
    """Test that platform-specific metrics are correctly nullable for platforms that do not expose them."""
    user, brand = test_user_and_brand
    
    # Facebook Page (has followers, fan_count, media_count; no following_count or views_count)
    fb_acc = SocialAccount(
        user_id=user.id,
        brand_id=brand.id,
        platform="facebook",
        account_id="fb_123",
        account_name="FB Page",
        access_token=encrypt_token("tok_fb"),
        status="CONNECTED"
    )
    # YouTube Channel (has subscribers, views, video_count; no following_count)
    yt_acc = SocialAccount(
        user_id=user.id,
        brand_id=brand.id,
        platform="youtube",
        account_id="yt_123",
        account_name="YT Channel",
        access_token=encrypt_token("tok_yt"),
        status="CONNECTED"
    )
    db_session.add_all([fb_acc, yt_acc])
    db_session.commit()

    fb_snap = account_metric_snapshot_repo.upsert_snapshot(
        db=db_session,
        social_account_id=fb_acc.id,
        snapshot_date=date(2026, 9, 18),
        followers_count=320,
        following_count=None,
        views_count=None,
        media_count=45
    )
    assert fb_snap.followers_count == 320
    assert fb_snap.following_count is None
    assert fb_snap.views_count is None

    yt_snap = account_metric_snapshot_repo.upsert_snapshot(
        db=db_session,
        social_account_id=yt_acc.id,
        snapshot_date=date(2026, 9, 18),
        followers_count=12000,
        following_count=None,
        views_count=845000,
        media_count=67
    )
    assert yt_snap.followers_count == 12000
    assert yt_snap.following_count is None
    assert yt_snap.views_count == 845000
    assert yt_snap.media_count == 67

@patch("app.services.account_snapshot_service.meta_service")
@patch("app.services.account_snapshot_service.youtube_service")
def test_capture_snapshot_for_all_platforms(mock_yt, mock_meta, db_session, test_user_and_brand):
    """Test service capture across Facebook, Instagram, and YouTube platforms."""
    user, brand = test_user_and_brand

    fb_acc = SocialAccount(
        user_id=user.id, brand_id=brand.id, platform="facebook",
        account_id="fb_page_1", account_name="FB Page 1",
        access_token=encrypt_token("fb_token"), status="CONNECTED"
    )
    ig_acc = SocialAccount(
        user_id=user.id, brand_id=brand.id, platform="instagram",
        account_id="ig_page_1", account_name="@ig_page_1",
        access_token=encrypt_token("ig_token"), status="CONNECTED"
    )
    yt_acc = SocialAccount(
        user_id=user.id, brand_id=brand.id, platform="youtube",
        account_id="yt_chan_1", account_name="YT Chan 1",
        access_token=encrypt_token("yt_token"), status="CONNECTED"
    )
    db_session.add_all([fb_acc, ig_acc, yt_acc])
    db_session.commit()

    mock_meta.fetch_facebook_page_metrics.return_value = {
        "followers_count": 850,
        "fan_count": 850,
        "media_count": 42,
        "category": "Marketing",
        "media_count_source": "meta_total_unavailable",
        "is_sandbox": False
    }
    mock_meta.fetch_instagram_account_metrics.return_value = {
        "followers_count": 2300,
        "follows_count": 180,
        "media_count": 95,
        "media_count_source": "meta_verified_exact_total",
        "is_sandbox": False
    }
    mock_yt.get_valid_access_token_for_account.return_value = "fresh_yt_token"
    mock_yt.fetch_authenticated_channel.return_value = {
        "channel_id": "yt_chan_1",
        "title": "YT Chan 1",
        "custom_url": "@ytchan1",
        "subscriber_count": "54000",
        "video_count": "120",
        "view_count": "1500000",
        "uploads_playlist_id": "UU12345"
    }

    test_date = date(2026, 9, 18)

    # Capture FB
    fb_res = account_snapshot_service.capture_snapshot_for_account(db_session, fb_acc, test_date)
    assert fb_res is not None
    assert fb_res.followers_count == 850
    assert fb_res.media_count == 42
    assert fb_res.metadata_json.get("category") == "Marketing"

    # Capture IG
    ig_res = account_snapshot_service.capture_snapshot_for_account(db_session, ig_acc, test_date)
    assert ig_res is not None
    assert ig_res.followers_count == 2300
    assert ig_res.following_count == 180
    assert ig_res.media_count == 95

    # Capture YT
    yt_res = account_snapshot_service.capture_snapshot_for_account(db_session, yt_acc, test_date)
    assert yt_res is not None
    assert yt_res.followers_count == 54000
    assert yt_res.media_count == 120
    assert yt_res.views_count == 1500000

@patch("app.services.account_snapshot_service.meta_service")
def test_one_account_failure_not_stopping_other_accounts(mock_meta, db_session, test_user_and_brand):
    """Test error isolation: failure of one account does not stop or roll back snapshots for other accounts."""
    user, brand = test_user_and_brand

    failing_acc = SocialAccount(
        user_id=user.id, brand_id=brand.id, platform="facebook",
        account_id="failing_fb", account_name="Failing FB",
        access_token=encrypt_token("bad_token"), status="CONNECTED"
    )
    healthy_acc = SocialAccount(
        user_id=user.id, brand_id=brand.id, platform="facebook",
        account_id="healthy_fb", account_name="Healthy FB",
        access_token=encrypt_token("good_token"), status="CONNECTED"
    )
    db_session.add_all([failing_acc, healthy_acc])
    db_session.commit()

    def mock_fetch(page_id, access_token):
        if page_id == "failing_fb":
            raise RuntimeError("OAuth token expired / Meta API error (400)")
        return {
            "followers_count": 1200,
            "fan_count": 1200,
            "media_count": 15,
            "category": "Tech",
            "is_sandbox": False
        }

    mock_meta.fetch_facebook_page_metrics.side_effect = mock_fetch

    test_date = date(2026, 9, 18)
    result = account_snapshot_service.capture_all_active_snapshots(db_session, test_date)

    assert result["total_accounts"] == 2
    assert result["success"] == 1
    assert result["failed"] == 1

    # Verify healthy snapshot was saved
    healthy_snap = account_metric_snapshot_repo.get_by_account_and_date(
        db_session, healthy_acc.id, test_date
    )
    assert healthy_snap is not None
    assert healthy_snap.followers_count == 1200

    # Verify failing snapshot does not exist
    failing_snap = account_metric_snapshot_repo.get_by_account_and_date(
        db_session, failing_acc.id, test_date
    )
    assert failing_snap is None

@patch("app.services.account_snapshot_service.account_snapshot_service.capture_all_active_snapshots")
def test_sync_meta_analytics_celery_task(mock_capture, db_session):
    """Test Celery beat task execution for capturing account snapshots."""
    mock_capture.return_value = {
        "snapshot_date": "2026-09-18",
        "total_accounts": 3,
        "success": 3,
        "failed": 0
    }

    res = sync_meta_analytics_task()
    assert res["status"] == "synced"
    assert res["snapshot_result"]["success"] == 3
    mock_capture.assert_called_once()

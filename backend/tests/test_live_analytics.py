import pytest
from datetime import date, datetime, timezone
from unittest.mock import patch, MagicMock

from app.models.user import User
from app.models.brand import BrandProfile
from app.models.social_account import SocialAccount
from app.models.account_metric_snapshot import AccountMetricSnapshot
from app.core.security_encryption import encrypt_token
from app.services.live_analytics_service import live_analytics_service
from app.repositories.account_metric_snapshot_repository import account_metric_snapshot_repo


def get_auth_headers(client, email="live_analytics_test@socialai.com", password="Password123!"):
    reg_payload = {
        "email": email,
        "password": password,
        "full_name": "Live Analytics Tester",
        "role": "Owner"
    }
    client.post("/api/v1/auth/register", json=reg_payload)
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def live_test_data(db_session, client):
    headers = get_auth_headers(client)
    user = db_session.query(User).filter(User.email == "live_analytics_test@socialai.com").first()

    brand = BrandProfile(
        user_id=user.id,
        name="Live Analytics Brand",
        industry="Tech"
    )
    db_session.add(brand)
    db_session.commit()
    db_session.refresh(brand)

    ig_acc = SocialAccount(
        user_id=user.id,
        brand_id=brand.id,
        platform="instagram",
        account_id="1784149999",
        account_name="live_instagram_biz",
        access_token=encrypt_token("live_ig_token"),
        status="CONNECTED"
    )
    fb_acc = SocialAccount(
        user_id=user.id,
        brand_id=brand.id,
        platform="facebook",
        account_id="1099887766",
        account_name="Live Facebook Page",
        access_token=encrypt_token("live_fb_token"),
        status="CONNECTED"
    )
    yt_acc = SocialAccount(
        user_id=user.id,
        brand_id=brand.id,
        platform="youtube",
        account_id="UC_live_yt_channel",
        account_name="Live YouTube Channel",
        access_token=encrypt_token("live_yt_token"),
        status="CONNECTED"
    )
    db_session.add_all([ig_acc, fb_acc, yt_acc])
    db_session.commit()
    db_session.refresh(ig_acc)
    db_session.refresh(fb_acc)
    db_session.refresh(yt_acc)

    return {
        "user": user,
        "brand": brand,
        "headers": headers,
        "ig_acc": ig_acc,
        "fb_acc": fb_acc,
        "yt_acc": yt_acc
    }


# ==============================================================================
# 1. Platform Normalization Tests (Instagram, Facebook, YouTube)
# ==============================================================================

@patch("app.services.live_analytics_service.meta_service")
def test_live_instagram_normalization(mock_meta, db_session, live_test_data):
    """Test normalized response structure and capabilities for Instagram Business."""
    ig_acc = live_test_data["ig_acc"]
    user = live_test_data["user"]

    mock_meta.fetch_instagram_account_metrics.return_value = {
        "id": "1784149999",
        "username": "live_instagram_biz",
        "name": "Live Instagram Business",
        "followers_count": 14250,
        "follows_count": 312,
        "media_count": 88,
        "media_count_source": "meta_verified_exact_total",
        "is_sandbox": False
    }

    item = live_analytics_service.get_live_account_analytics(db_session, ig_acc)

    assert item.social_account_id == ig_acc.id
    assert item.platform == "instagram"
    assert item.status == "CONNECTED"
    assert item.account.followers == 14250
    assert item.account.following == 312
    assert item.account.media_count == 88
    assert item.account.views_count is None
    assert item.capabilities.followers is True
    assert item.capabilities.following is True
    assert item.capabilities.media_count is True
    assert item.capabilities.views_count is False
    assert item.capabilities.reach is False
    assert item.capabilities.impressions is False
    assert item.capabilities.engagement_rate is False
    assert item.source == "live_platform_api"
    assert item.error_message is None


@patch("app.services.live_analytics_service.meta_service")
def test_live_facebook_normalization(mock_meta, db_session, live_test_data):
    """Test normalized response structure and capabilities for Facebook Page."""
    fb_acc = live_test_data["fb_acc"]

    mock_meta.fetch_facebook_page_metrics.return_value = {
        "id": "1099887766",
        "name": "Live Facebook Page",
        "followers_count": 9400,
        "fan_count": 9400,
        "media_count": 54,
        "category": "Technology Company",
        "media_count_source": "meta_total_unavailable",
        "is_sandbox": False
    }

    item = live_analytics_service.get_live_account_analytics(db_session, fb_acc)

    assert item.social_account_id == fb_acc.id
    assert item.platform == "facebook"
    assert item.account.followers == 9400
    assert item.account.following is None
    assert item.account.media_count == 54
    assert item.account.views_count is None
    assert item.capabilities.followers is True
    assert item.capabilities.following is False
    assert item.capabilities.media_count is True
    assert item.capabilities.views_count is False
    assert item.source == "live_platform_api"


@patch("app.services.live_analytics_service.youtube_service")
def test_live_youtube_normalization(mock_yt, db_session, live_test_data):
    """Test normalized response structure and capabilities for YouTube Channel."""
    yt_acc = live_test_data["yt_acc"]

    mock_yt.get_valid_access_token_for_account.return_value = "fresh_live_yt_token"
    mock_yt.fetch_authenticated_channel.return_value = {
        "channel_id": "UC_live_yt_channel",
        "title": "Live YouTube Channel",
        "subscriber_count": "35000",
        "video_count": "95",
        "view_count": "1200000",
        "uploads_playlist_id": "UU_live_yt_channel"
    }

    item = live_analytics_service.get_live_account_analytics(db_session, yt_acc)

    assert item.social_account_id == yt_acc.id
    assert item.platform == "youtube"
    assert item.account.followers == 35000
    assert item.account.following is None
    assert item.account.media_count == 95
    assert item.account.views_count == 1200000
    assert item.capabilities.followers is True
    assert item.capabilities.following is False
    assert item.capabilities.media_count is True
    assert item.capabilities.views_count is True
    assert item.source == "live_platform_api"


# ==============================================================================
# 2. Strict NULL vs ZERO Preservation
# ==============================================================================

@patch("app.services.live_analytics_service.meta_service")
def test_strict_null_vs_zero_preservation(mock_meta, db_session, live_test_data):
    """Verify that an explicit 0 is returned as 0, and unavailable/missing fields remain None."""
    ig_acc = live_test_data["ig_acc"]

    mock_meta.fetch_instagram_account_metrics.return_value = {
        "id": "1784149999",
        "username": "brand_zero_followers",
        "followers_count": 0,  # Explicit 0 from platform
        "follows_count": 0,    # Explicit 0 from platform
        "media_count": None,   # Unavailable
        "is_sandbox": False
    }

    item = live_analytics_service.get_live_account_analytics(db_session, ig_acc)

    assert item.account.followers == 0
    assert item.account.following == 0
    assert item.account.media_count is None
    assert item.account.views_count is None
    assert item.capabilities.followers is True
    assert item.capabilities.following is True
    assert item.capabilities.media_count is False


# ==============================================================================
# 3. API Failure and Per-Account Error Isolation
# ==============================================================================

@patch("app.services.live_analytics_service.meta_service")
@patch("app.services.live_analytics_service.youtube_service")
def test_per_account_failure_isolation(mock_yt, mock_meta, db_session, live_test_data):
    """Test that a failure in one platform API does not crash the response or prevent other accounts from syncing."""
    user = live_test_data["user"]
    brand = live_test_data["brand"]

    # IG succeeds, FB fails with token error, YT succeeds
    mock_meta.fetch_instagram_account_metrics.return_value = {
        "followers_count": 5000,
        "follows_count": 100,
        "media_count": 20
    }
    mock_meta.fetch_facebook_page_metrics.side_effect = RuntimeError("Meta OAuth Token Invalid / Expired (401)")
    mock_yt.get_valid_access_token_for_account.return_value = "yt_tok"
    mock_yt.fetch_authenticated_channel.return_value = {
        "subscriber_count": "10000",
        "video_count": "50",
        "view_count": "200000"
    }

    response = live_analytics_service.get_live_analytics(
        db=db_session,
        user_id=user.id,
        brand_id=brand.id
    )

    assert len(response.accounts) == 3
    ig_item = next(a for a in response.accounts if a.platform == "instagram")
    fb_item = next(a for a in response.accounts if a.platform == "facebook")
    yt_item = next(a for a in response.accounts if a.platform == "youtube")

    assert ig_item.status == "CONNECTED"
    assert ig_item.account.followers == 5000

    assert fb_item.status == "ERROR"
    assert "Token Invalid" in (fb_item.error_message or "")
    assert fb_item.account.followers is None

    assert yt_item.status == "CONNECTED"
    assert yt_item.account.followers == 10000

    # Summary should sum valid accounts: 5000 + 10000 = 15000
    assert response.summary.total_followers == 15000


# ==============================================================================
# 4. Idempotent Snapshot Persistence upon Live Fetch
# ==============================================================================

@patch("app.services.live_analytics_service.meta_service")
def test_snapshot_persistence_upon_live_fetch(mock_meta, db_session, live_test_data):
    """Verify that calling live analytics immediately persists today's snapshot row idempotently."""
    ig_acc = live_test_data["ig_acc"]
    user = live_test_data["user"]
    today = datetime.now(timezone.utc).date()

    mock_meta.fetch_instagram_account_metrics.return_value = {
        "followers_count": 7800,
        "follows_count": 250,
        "media_count": 45
    }

    # Fetch 1
    live_analytics_service.get_live_account_analytics(db_session, ig_acc)
    snap1 = account_metric_snapshot_repo.get_by_account_and_date(db_session, ig_acc.id, today)
    assert snap1 is not None
    assert snap1.followers_count == 7800
    assert snap1.media_count == 45

    # Fetch 2 on same day with newer numbers
    mock_meta.fetch_instagram_account_metrics.return_value = {
        "followers_count": 7850,
        "follows_count": 250,
        "media_count": 46
    }
    live_analytics_service.get_live_account_analytics(db_session, ig_acc)
    snap2 = account_metric_snapshot_repo.get_by_account_and_date(db_session, ig_acc.id, today)

    # Must update in place (same ID, updated metrics)
    assert snap2.id == snap1.id
    assert snap2.followers_count == 7850
    assert snap2.media_count == 46


# ==============================================================================
# 5. Endpoint & Scoping Tests (GET /api/v1/analytics/live)
# ==============================================================================

@patch("app.services.live_analytics_service.meta_service")
@patch("app.services.live_analytics_service.youtube_service")
def test_live_analytics_endpoint_success(mock_yt, mock_meta, client, live_test_data):
    """Test GET /api/v1/analytics/live returns normalized contract and summary."""
    headers = live_test_data["headers"]
    brand = live_test_data["brand"]

    mock_meta.fetch_instagram_account_metrics.return_value = {
        "followers_count": 12000,
        "follows_count": 400,
        "media_count": 60
    }
    mock_meta.fetch_facebook_page_metrics.return_value = {
        "followers_count": 8000,
        "fan_count": 8000,
        "media_count": 30
    }
    mock_yt.get_valid_access_token_for_account.return_value = "yt_tok"
    mock_yt.fetch_authenticated_channel.return_value = {
        "subscriber_count": "20000",
        "video_count": "100",
        "view_count": "500000"
    }

    res = client.get(f"/api/v1/analytics/live?brand_id={brand.id}", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert "accounts" in data
    assert len(data["accounts"]) == 3
    assert data["summary"]["total_followers"] == 40000  # 12000 + 8000 + 20000
    assert data["fetched_at"] is not None


def test_live_analytics_tenant_isolation(client, live_test_data):
    """Verify that another user cannot access live analytics for unauthorized brands or accounts."""
    user2_headers = get_auth_headers(client, email="other_live_user@socialai.com", password="Password456!")
    brand_id = live_test_data["brand"].id
    acc_id = live_test_data["ig_acc"].id

    # Brand scoping denial
    res_brand = client.get(f"/api/v1/analytics/live?brand_id={brand_id}", headers=user2_headers)
    assert res_brand.status_code == 404

    # Account scoping denial
    res_acc = client.get(f"/api/v1/analytics/live?social_account_id={acc_id}", headers=user2_headers)
    assert res_acc.status_code == 404

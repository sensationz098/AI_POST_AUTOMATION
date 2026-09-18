import pytest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

from app.models.user import User
from app.models.brand import BrandProfile
from app.models.social_account import SocialAccount
from app.models.account_metric_snapshot import AccountMetricSnapshot
from app.models.post import Post, PostStatus
from app.models.analytics import PostAnalytics
from app.models.publishing_batch import PublishingBatch, PublishingJob, BatchStatus, JobStatus
from app.core.security_encryption import encrypt_token

def get_auth_headers(client, email="test_analytics_a3@socialai.com", password="Password123!"):
    reg_payload = {
        "email": email,
        "password": password,
        "full_name": "Analytics A3 Tester",
        "role": "Owner"
    }
    client.post("/api/v1/auth/register", json=reg_payload)
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def seed_data(db_session, client):
    headers = get_auth_headers(client)
    user = db_session.query(User).filter(User.email == "test_analytics_a3@socialai.com").first()

    # Create Brand
    brand = BrandProfile(
        user_id=user.id,
        name="A3 Alpha Brand",
        industry="Technology"
    )
    db_session.add(brand)
    db_session.commit()
    db_session.refresh(brand)

    # Create Social Accounts
    ig_account = SocialAccount(
        user_id=user.id,
        brand_id=brand.id,
        platform="instagram",
        account_id="1784140001",
        account_name="alphabrand_ig",
        access_token=encrypt_token("ig_token_123"),
        status="CONNECTED"
    )
    fb_account = SocialAccount(
        user_id=user.id,
        brand_id=brand.id,
        platform="facebook",
        account_id="100998877",
        account_name="Alpha Brand FB",
        access_token=encrypt_token("fb_token_123"),
        status="CONNECTED"
    )
    yt_account = SocialAccount(
        user_id=user.id,
        brand_id=brand.id,
        platform="youtube",
        account_id="UC_alpha_channel",
        account_name="Alpha Channel YT",
        access_token=encrypt_token("yt_token_123"),
        status="CONNECTED"
    )
    db_session.add_all([ig_account, fb_account, yt_account])
    db_session.commit()
    db_session.refresh(ig_account)
    db_session.refresh(fb_account)
    db_session.refresh(yt_account)

    # Seed Account Snapshots across dates
    d1 = date.today() - timedelta(days=5)
    d2 = date.today() - timedelta(days=2)
    d3 = date.today()

    snap_ig_1 = AccountMetricSnapshot(
        social_account_id=ig_account.id,
        snapshot_date=d1,
        followers_count=1000,
        following_count=100,
        media_count=20,
        reach=5000,
        impressions=7500
    )
    snap_ig_2 = AccountMetricSnapshot(
        social_account_id=ig_account.id,
        snapshot_date=d2,
        followers_count=1050,
        following_count=102,
        media_count=22,
        reach=5200,
        impressions=7800
    )
    snap_ig_3 = AccountMetricSnapshot(
        social_account_id=ig_account.id,
        snapshot_date=d3,
        followers_count=1100,
        following_count=105,
        media_count=25,
        reach=5600,
        impressions=8200
    )

    snap_fb_1 = AccountMetricSnapshot(
        social_account_id=fb_account.id,
        snapshot_date=d1,
        followers_count=2000,
        media_count=40,
        reach=8000,
        impressions=12000
    )
    snap_fb_3 = AccountMetricSnapshot(
        social_account_id=fb_account.id,
        snapshot_date=d3,
        followers_count=2100,
        media_count=45,
        reach=8500,
        impressions=13000
    )

    snap_yt_3 = AccountMetricSnapshot(
        social_account_id=yt_account.id,
        snapshot_date=d3,
        followers_count=5000,
        media_count=15,
        views_count=500000
    )

    db_session.add_all([snap_ig_1, snap_ig_2, snap_ig_3, snap_fb_1, snap_fb_3, snap_yt_3])
    db_session.commit()

    # Seed Posts & PostAnalytics
    # Post 1: Published to both Instagram and Facebook (Multi-destination)
    p1 = Post(
        user_id=user.id,
        brand_id=brand.id,
        title="Post 1 - Multi Platform",
        caption="Multi-destination caption #social",
        platforms=["facebook", "instagram"],
        status=PostStatus.PUBLISHED.value,
        published_at=datetime.now(timezone.utc) - timedelta(days=4)
    )
    db_session.add(p1)
    db_session.commit()
    db_session.refresh(p1)

    # Multi-job batch for Post 1
    batch1 = PublishingBatch(post_id=p1.id, user_id=user.id, status=BatchStatus.SUCCESS.value)
    db_session.add(batch1)
    db_session.commit()
    db_session.refresh(batch1)

    job1_ig = PublishingJob(
        batch_id=batch1.id,
        social_account_id=ig_account.id,
        platform="instagram",
        status=JobStatus.SUCCESS.value,
        external_post_id="ig_p1"
    )
    job1_fb = PublishingJob(
        batch_id=batch1.id,
        social_account_id=fb_account.id,
        platform="facebook",
        status=JobStatus.SUCCESS.value,
        external_post_id="fb_p1"
    )
    db_session.add_all([job1_ig, job1_fb])

    pa1 = PostAnalytics(
        post_id=p1.id,
        likes=100,
        comments=20,
        shares=10,
        saves=5,
        reach=1500,
        impressions=2000,
        engagement_rate=6.75  # (135 / 2000) * 100
    )
    db_session.add(pa1)

    # Post 2: Published to YouTube with views, but impressions is NULL
    p2 = Post(
        user_id=user.id,
        brand_id=brand.id,
        title="Post 2 - YouTube Video",
        caption="YouTube video caption",
        platforms=["youtube"],
        status=PostStatus.PUBLISHED.value,
        published_at=datetime.now(timezone.utc) - timedelta(days=2)
    )
    db_session.add(p2)
    db_session.commit()
    db_session.refresh(p2)

    pa2 = PostAnalytics(
        post_id=p2.id,
        likes=50,
        comments=10,
        shares=None,
        saves=None,
        reach=None,
        impressions=None,
        engagement_rate=None
    )
    db_session.add(pa2)

    # Post 3: Scheduled Post
    p3 = Post(
        user_id=user.id,
        brand_id=brand.id,
        title="Post 3 - Scheduled",
        caption="Upcoming content",
        platforms=["instagram"],
        status=PostStatus.SCHEDULED.value,
        scheduled_at=datetime.now(timezone.utc) + timedelta(days=1)
    )
    db_session.add(p3)

    # Post 4: Failed Post
    p4 = Post(
        user_id=user.id,
        brand_id=brand.id,
        title="Post 4 - Failed",
        caption="Failed publish content",
        platforms=["facebook"],
        status=PostStatus.FAILED.value
    )
    db_session.add(p4)

    db_session.commit()

    return {
        "user": user,
        "brand": brand,
        "headers": headers,
        "ig_account": ig_account,
        "fb_account": fb_account,
        "yt_account": yt_account,
        "posts": [p1, p2, p3, p4]
    }


def test_accounts_snapshots_chronological_and_growth(client, seed_data):
    """Test GET /api/v1/analytics/accounts/snapshots with growth metric calculations."""
    headers = seed_data["headers"]
    ig_acc = seed_data["ig_account"]

    # 1. Single account snapshots
    res = client.get(f"/api/v1/analytics/accounts/snapshots?social_account_id={ig_acc.id}", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_records"] == 3
    assert len(data["snapshots"]) == 3

    # Chronological ordering check
    dates = [s["snapshot_date"] for s in data["snapshots"]]
    assert dates == sorted(dates)

    # Growth calculation: 1000 -> 1100 => +100 change, +10.0% growth
    growth = data["growth"]
    assert growth["initial_followers"] == 1000
    assert growth["current_followers"] == 1100
    assert growth["follower_change"] == 100
    assert growth["follower_growth_rate"] == 10.0
    assert growth["media_count_change"] == 5  # 20 -> 25


def test_accounts_snapshots_date_filtering(client, seed_data):
    """Test date filtering on snapshots."""
    headers = seed_data["headers"]
    ig_acc = seed_data["ig_account"]

    start = (date.today() - timedelta(days=3)).isoformat()
    end = date.today().isoformat()

    res = client.get(
        f"/api/v1/analytics/accounts/snapshots?social_account_id={ig_acc.id}&start_date={start}&end_date={end}",
        headers=headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_records"] == 2
    for s in data["snapshots"]:
        assert s["snapshot_date"] >= start
        assert s["snapshot_date"] <= end


def test_overview_report_deduplication_and_engagement_rate(client, seed_data):
    """
    Test GET /api/v1/analytics/overview-report:
    - total_posts counts distinct logical posts (does not multiply for multi-destinations).
    - total_followers is arithmetic sum across accounts.
    - aggregate_engagement_rate is calculated from aggregate interactions / aggregate impressions (NOT average of rates).
    """
    headers = seed_data["headers"]
    brand = seed_data["brand"]

    res = client.get(f"/api/v1/analytics/overview-report?brand_id={brand.id}", headers=headers)
    assert res.status_code == 200
    data = res.json()

    # Distinct post count check: Total 4 posts (1 published multi-target, 1 published YT, 1 scheduled, 1 failed)
    assert data["total_posts"] == 4
    assert data["published_posts"] == 2
    assert data["scheduled_posts"] == 1
    assert data["failed_posts"] == 1

    # Follower arithmetic sum: IG latest (1100) + FB latest (2100) + YT latest (5000) = 8200
    assert data["total_followers"] == 8200

    # Aggregate metrics:
    # Post 1: likes=100, comments=20, shares=10, saves=5, reach=1500, impressions=2000
    # Post 2: likes=50, comments=10, shares=None, saves=None, reach=None, impressions=None
    # Sums: likes=150, comments=30, shares=10, saves=5, reach=1500, impressions=2000
    assert data["total_likes"] == 150
    assert data["total_comments"] == 30
    assert data["total_shares"] == 10
    assert data["total_saves"] == 5
    assert data["total_reach"] == 1500
    assert data["total_impressions"] == 2000

    # Aggregate Engagement Rate Formula:
    # numerator = 150 + 30 + 10 + 5 = 195
    # denominator = 2000 (impressions)
    # rate = (195 / 2000) * 100 = 9.75%
    assert data["aggregate_engagement_rate"] == 9.75


def test_platform_breakdown(client, seed_data):
    """Test GET /api/v1/analytics/platforms breakdown per platform."""
    headers = seed_data["headers"]
    brand = seed_data["brand"]

    res = client.get(f"/api/v1/analytics/platforms?brand_id={brand.id}", headers=headers)
    assert res.status_code == 200
    data = res.json()
    platforms = {item["platform"]: item for item in data["platforms"]}

    assert "instagram" in platforms
    assert "facebook" in platforms
    assert "youtube" in platforms

    # Instagram
    assert platforms["instagram"]["connected_accounts_count"] == 1
    assert platforms["instagram"]["total_followers"] == 1100
    assert platforms["instagram"]["total_posts"] == 2  # Post 1 (published) & Post 3 (scheduled)

    # YouTube
    assert platforms["youtube"]["connected_accounts_count"] == 1
    assert platforms["youtube"]["total_followers"] == 5000
    assert platforms["youtube"]["total_views"] == 500000
    assert platforms["youtube"]["total_posts"] == 1


def test_posts_performance_pagination_and_sorting(client, seed_data):
    """Test GET /api/v1/analytics/posts with pagination and deterministic NULL-safe sorting."""
    headers = seed_data["headers"]

    # 1. Sort by engagement_rate desc (Post 1 has 6.75, Post 2/3/4 have NULL)
    res = client.get("/api/v1/analytics/posts?order_by=engagement_rate&order_dir=desc", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 4
    items = data["items"]
    assert items[0]["engagement_rate"] == 6.75
    # Remaining items must have None for engagement_rate without crash
    for item in items[1:]:
        assert item["engagement_rate"] is None

    # 2. Sort by likes desc
    res_likes = client.get("/api/v1/analytics/posts?order_by=likes&order_dir=desc", headers=headers)
    assert res_likes.status_code == 200
    items_likes = res_likes.json()["items"]
    assert items_likes[0]["likes"] == 100
    assert items_likes[1]["likes"] == 50

    # 3. Pagination limit & offset
    res_page = client.get("/api/v1/analytics/posts?limit=2&offset=0", headers=headers)
    assert res_page.status_code == 200
    assert len(res_page.json()["items"]) == 2
    assert res_page.json()["total"] == 4


def test_tenant_and_brand_isolation(client, seed_data, db_session):
    """Verify that another user cannot access or view data from seed_data user."""
    # Register secondary user
    user2_headers = get_auth_headers(client, email="user2@socialai.com", password="Password456!")

    # Attempt to query seed_data brand
    brand_id = seed_data["brand"].id
    res = client.get(f"/api/v1/analytics/overview-report?brand_id={brand_id}", headers=user2_headers)
    assert res.status_code == 404

    # Attempt to query seed_data account snapshots
    acc_id = seed_data["ig_account"].id
    res_snap = client.get(f"/api/v1/analytics/accounts/snapshots?social_account_id={acc_id}", headers=user2_headers)
    assert res_snap.status_code == 404

    # Secondary user overview should be empty
    res_overview = client.get("/api/v1/analytics/overview-report", headers=user2_headers)
    assert res_overview.status_code == 200
    assert res_overview.json()["total_posts"] == 0
    assert res_overview.json()["total_followers"] is None


def test_read_only_guarantee_no_external_api_calls(client, seed_data):
    """Verify strictly 0 external API calls (Meta Graph API / YouTube API) occur during read endpoints."""
    headers = seed_data["headers"]
    brand_id = seed_data["brand"].id

    with patch("requests.get") as mock_req_get, \
         patch("requests.post") as mock_req_post, \
         patch("app.services.meta_service.meta_service.fetch_facebook_page_metrics") as mock_meta_fb, \
         patch("app.services.meta_service.meta_service.fetch_instagram_account_metrics") as mock_meta_ig, \
         patch("app.services.youtube_service.youtube_service.fetch_video_statistics") as mock_yt:

        client.get("/api/v1/analytics/accounts/snapshots", headers=headers)
        client.get(f"/api/v1/analytics/overview-report?brand_id={brand_id}", headers=headers)
        client.get(f"/api/v1/analytics/platforms?brand_id={brand_id}", headers=headers)
        client.get(f"/api/v1/analytics/posts?brand_id={brand_id}", headers=headers)

        assert mock_req_get.call_count == 0
        assert mock_req_post.call_count == 0
        assert mock_meta_fb.call_count == 0
        assert mock_meta_ig.call_count == 0
        assert mock_yt.call_count == 0


def test_legacy_dashboard_backward_compatibility(client, seed_data):
    """Ensure legacy endpoints /api/v1/analytics/overview and /brand/{brand_id} continue to work."""
    headers = seed_data["headers"]
    brand_id = seed_data["brand"].id

    res_user = client.get("/api/v1/analytics/overview", headers=headers)
    assert res_user.status_code == 200
    assert "overview" in res_user.json()

    res_brand = client.get(f"/api/v1/analytics/brand/{brand_id}", headers=headers)
    assert res_brand.status_code == 200
    assert "overview" in res_brand.json()

import pytest
from unittest.mock import patch, MagicMock
from app.models.user import User
from app.models.social_account import SocialAccount
from app.models.post import Post
from app.models.brand import BrandProfile
from app.services.analytics_service import analytics_service
from app.services.meta_service import meta_service
from app.core.security_encryption import encrypt_token

def test_dashboard_analytics_account_specific_post_counts(db_session):
    """TEST 1 & 4: Both Facebook and Instagram succeed with distinct accounts and counts."""
    user = User(email="analytics_test1@example.com", full_name="Analytics User", hashed_password="pw", is_active=True)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    brand = BrandProfile(user_id=user.id, name="Test Brand")
    db_session.add(brand)
    db_session.commit()
    db_session.refresh(brand)

    for i in range(3):
        db_session.add(Post(user_id=user.id, brand_id=brand.id, title=f"Post #{i}", caption=f"Body #{i}", status="PUBLISHED"))
    db_session.commit()

    fb1 = SocialAccount(user_id=user.id, platform="facebook", account_id="fb_page_100", account_name="Facebook Page 1", access_token=encrypt_token("tok_fb1"), status="CONNECTED")
    fb2 = SocialAccount(user_id=user.id, platform="facebook", account_id="fb_page_200", account_name="Facebook Page 2", access_token=encrypt_token("tok_fb2"), status="CONNECTED")
    ig1 = SocialAccount(user_id=user.id, platform="instagram", account_id="ig_acc_300", account_name="@ig_account_3", access_token=encrypt_token("tok_ig1"), status="CONNECTED")
    db_session.add_all([fb1, fb2, ig1])
    db_session.commit()

    def mock_fb_metrics(page_id, access_token):
        if page_id == "fb_page_100":
            return {"id": page_id, "name": "Facebook Page 1", "followers_count": 500, "fan_count": 500, "media_count": 114, "is_sandbox": False}
        else:
            return {"id": page_id, "name": "Facebook Page 2", "followers_count": 1200, "fan_count": 1200, "media_count": 167, "is_sandbox": False}

    def mock_ig_metrics(ig_user_id, access_token):
        return {"id": ig_user_id, "username": "ig_account_3", "followers_count": 3500, "media_count": 215, "is_sandbox": False}

    with patch("app.services.analytics_service.meta_service.fetch_facebook_page_metrics", side_effect=mock_fb_metrics), \
         patch("app.services.analytics_service.meta_service.fetch_instagram_account_metrics", side_effect=mock_ig_metrics):

        res = analytics_service.get_user_overview_dashboard(db_session, user.id)

    assert res.overview.published_posts == 3
    accs = res.accounts_list
    assert len(accs) == 3

    fb1_res = next(a for a in accs if a["account_id"] == "fb_page_100")
    fb2_res = next(a for a in accs if a["account_id"] == "fb_page_200")
    ig1_res = next(a for a in accs if a["account_id"] == "ig_acc_300")

    assert fb1_res["media_count"] == 114
    assert fb2_res["media_count"] == 167
    assert ig1_res["media_count"] == 215


def test_facebook_timeout_does_not_break_instagram(db_session):
    """TEST 2: Facebook API times out while Instagram succeeds; Instagram count is preserved."""
    user = User(email="analytics_test2@example.com", full_name="Analytics User 2", hashed_password="pw", is_active=True)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    fb1 = SocialAccount(user_id=user.id, platform="facebook", account_id="fb_slow_100", account_name="Slow Facebook Page", access_token=encrypt_token("tok_fb1"), status="CONNECTED")
    ig1 = SocialAccount(user_id=user.id, platform="instagram", account_id="ig_fast_300", account_name="@fast_ig", access_token=encrypt_token("tok_ig1"), status="CONNECTED")
    db_session.add_all([fb1, ig1])
    db_session.commit()

    def mock_fb_metrics(page_id, access_token):
        # Return media_count None as if timeout occurred
        return {"id": page_id, "name": "Slow Facebook Page", "followers_count": None, "fan_count": None, "media_count": None, "is_sandbox": False}

    def mock_ig_metrics(ig_user_id, access_token):
        return {"id": ig_user_id, "username": "fast_ig", "followers_count": 5000, "media_count": 1370, "is_sandbox": False}

    with patch("app.services.analytics_service.meta_service.fetch_facebook_page_metrics", side_effect=mock_fb_metrics), \
         patch("app.services.analytics_service.meta_service.fetch_instagram_account_metrics", side_effect=mock_ig_metrics):

        res = analytics_service.get_user_overview_dashboard(db_session, user.id)

    accs = res.accounts_list
    assert len(accs) == 2

    fb_res = next(a for a in accs if a["account_id"] == "fb_slow_100")
    ig_res = next(a for a in accs if a["account_id"] == "ig_fast_300")

    assert fb_res["media_count"] is None  # Frontend renders 'Unavailable'
    assert ig_res["media_count"] == 1370  # Instagram still succeeds!


def test_instagram_timeout_does_not_break_facebook(db_session):
    """TEST 3: Instagram API times out while Facebook succeeds; Facebook count is preserved."""
    user = User(email="analytics_test3@example.com", full_name="Analytics User 3", hashed_password="pw", is_active=True)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    fb1 = SocialAccount(user_id=user.id, platform="facebook", account_id="fb_fast_100", account_name="Fast Facebook Page", access_token=encrypt_token("tok_fb1"), status="CONNECTED")
    ig1 = SocialAccount(user_id=user.id, platform="instagram", account_id="ig_slow_300", account_name="@slow_ig", access_token=encrypt_token("tok_ig1"), status="CONNECTED")
    db_session.add_all([fb1, ig1])
    db_session.commit()

    def mock_fb_metrics(page_id, access_token):
        return {"id": page_id, "name": "Fast Facebook Page", "followers_count": 1000, "fan_count": 1000, "media_count": 400, "is_sandbox": False}

    def mock_ig_metrics(ig_user_id, access_token):
        return {"id": ig_user_id, "username": "slow_ig", "followers_count": None, "media_count": None, "is_sandbox": False}

    with patch("app.services.analytics_service.meta_service.fetch_facebook_page_metrics", side_effect=mock_fb_metrics), \
         patch("app.services.analytics_service.meta_service.fetch_instagram_account_metrics", side_effect=mock_ig_metrics):

        res = analytics_service.get_user_overview_dashboard(db_session, user.id)

    accs = res.accounts_list
    assert len(accs) == 2

    fb_res = next(a for a in accs if a["account_id"] == "fb_fast_100")
    ig_res = next(a for a in accs if a["account_id"] == "ig_slow_300")

    assert fb_res["media_count"] == 400
    assert ig_res["media_count"] is None


def test_facebook_api_failure_returns_none_instead_of_25():
    """TEST 5: Facebook API failure returns None for media_count instead of hardcoded 25."""
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": {"message": "Invalid OAuth access token."}}
        mock_get.return_value = mock_response

        res = meta_service.fetch_facebook_page_metrics("fb_fail_page", "invalid_token")

    assert res["media_count"] is None
    assert res["followers_count"] is None
    assert res["media_count"] != 25


def test_instagram_existing_count_logic_unchanged():
    """TEST 6: Instagram media_count fetching relies on direct Graph API media_count field."""
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "17841461326009878",
            "username": "sensationz_performing_arts",
            "followers_count": 23785,
            "media_count": 1370
        }
        mock_get.return_value = mock_response

        res = meta_service.fetch_instagram_account_metrics("17841461326009878", "valid_ig_token")

    assert res["media_count"] == 1370
    assert res["followers_count"] == 23785


def test_facebook_page_post_count_cursor_pagination():
    """TEST 7: Verify fetch_facebook_page_post_count returns exact total only when cursor terminates naturally."""
    with patch("requests.get") as mock_get:
        page1 = MagicMock()
        page1.status_code = 200
        page1.json.return_value = {
            "data": [{"id": f"p_{i}"} for i in range(100)],
            "paging": {"next": "https://graph.facebook.com/v21.0/page1/published_posts?cursor=abc"}
        }

        page2 = MagicMock()
        page2.status_code = 200
        page2.json.return_value = {
            "data": [{"id": f"p_{100+i}"} for i in range(14)],
            "paging": {}
        }

        mock_get.side_effect = [page1, page2]

        count, source = meta_service.fetch_facebook_page_post_count("1257381927456142", "tok_valid")

    assert count == 114
    assert source == "meta_verified_exact_total"


def test_facebook_truncated_cursor_returns_none_and_source_unavailable():
    """Verify that if Facebook cursor does not terminate (truncated at safety cap), count returns None."""
    with patch("requests.get") as mock_get:
        # Generate 5 pages that all have 'next' cursor active
        pages = []
        for p in range(5):
            pm = MagicMock()
            pm.status_code = 200
            pm.json.return_value = {
                "data": [{"id": f"p_{p}_{i}"} for i in range(100)],
                "paging": {"next": f"https://graph.facebook.com/v21.0/page1/published_posts?cursor={p}"}
            }
            pages.append(pm)

        mock_get.side_effect = pages

        count, source = meta_service.fetch_facebook_page_post_count("1001432206614811", "tok_valid")

    assert count is None
    assert source == "meta_total_unavailable"


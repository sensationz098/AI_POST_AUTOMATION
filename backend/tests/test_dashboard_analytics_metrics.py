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
    # 1. Create User
    user = User(email="analytics_test@example.com", full_name="Analytics User", hashed_password="pw", is_active=True)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # 2. Add local published posts (e.g. 5 local posts)
    brand = BrandProfile(user_id=user.id, name="Test Brand")
    db_session.add(brand)
    db_session.commit()
    db_session.refresh(brand)

    for i in range(5):
        db_session.add(Post(user_id=user.id, brand_id=brand.id, title=f"Post #{i}", caption=f"Body #{i}", status="PUBLISHED"))
    db_session.commit()

    # 3. Create 2 Facebook accounts and 1 Instagram account with distinct platform IDs
    fb1 = SocialAccount(
        user_id=user.id,
        platform="facebook",
        account_id="fb_page_100",
        account_name="Facebook Page 1",
        access_token=encrypt_token("tok_fb1"),
        status="CONNECTED"
    )
    fb2 = SocialAccount(
        user_id=user.id,
        platform="facebook",
        account_id="fb_page_200",
        account_name="Facebook Page 2",
        access_token=encrypt_token("tok_fb2"),
        status="CONNECTED"
    )
    ig1 = SocialAccount(
        user_id=user.id,
        platform="instagram",
        account_id="ig_acc_300",
        account_name="@ig_account_3",
        access_token=encrypt_token("tok_ig1"),
        status="CONNECTED"
    )
    db_session.add_all([fb1, fb2, ig1])
    db_session.commit()

    # 4. Mock Meta Graph API responses with distinct platform post counts
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

    # 5. Assert global overview metrics count local application published posts
    assert res.overview.published_posts == 5

    # 6. Assert accounts_list has distinct, account-specific platform media counts
    accs = res.accounts_list
    assert len(accs) == 3

    fb1_res = next(a for a in accs if a["account_id"] == "fb_page_100")
    fb2_res = next(a for a in accs if a["account_id"] == "fb_page_200")
    ig1_res = next(a for a in accs if a["account_id"] == "ig_acc_300")

    # Facebook Page 1 has 114 platform posts (not 25)
    assert fb1_res["media_count"] == 114
    assert fb1_res["followers_count"] == 500

    # Facebook Page 2 has 167 platform posts (not 25)
    assert fb2_res["media_count"] == 167
    assert fb2_res["followers_count"] == 1200

    # Instagram Account has 215 platform posts (unchanged)
    assert ig1_res["media_count"] == 215
    assert ig1_res["followers_count"] == 3500


def test_facebook_api_failure_returns_none_instead_of_25():
    """Verify that a Facebook API query failure returns None for media_count instead of 25."""
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": {"message": "Invalid OAuth access token."}}
        mock_get.return_value = mock_response

        res = meta_service.fetch_facebook_page_metrics("fb_fail_page", "invalid_token")

    assert res["media_count"] is None
    assert res["followers_count"] is None
    assert res["media_count"] != 25


def test_facebook_page_post_count_cursor_pagination():
    """Verify fetch_facebook_page_post_count paginates lightweight cursor items correctly."""
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

        count = meta_service.fetch_facebook_page_post_count("1257381927456142", "tok_valid")

    assert count == 114

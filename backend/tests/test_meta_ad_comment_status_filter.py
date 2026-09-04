import pytest
from app.models.user import User
from app.models.meta_ad import MetaAd
from app.models.social_account import SocialAccount
from app.models.social_comment import SocialComment

def test_meta_ads_status_filtering(client, db_session):
    """Verify GET /social-comments/ads filters by status (ACTIVE, PAUSED, ALL) and returns unreplied/replied metrics."""
    user = User(
        email="ad_filter_test@example.com",
        full_name="Ad Filter Test User",
        hashed_password="hashed_pw",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    acc = SocialAccount(
        user_id=user.id,
        platform="facebook",
        account_id="page_ad_filter_test",
        account_name="Ad Filter Test Page",
        access_token="test_token",
        status="CONNECTED"
    )
    db_session.add(acc)
    db_session.commit()
    db_session.refresh(acc)

    ad_active = MetaAd(
        user_id=user.id,
        meta_ad_account_id="act_100",
        meta_ad_id="ad_active_1",
        name="Active Test Ad",
        effective_status="ACTIVE",
        facebook_page_id="page_ad_filter_test"
    )
    ad_paused = MetaAd(
        user_id=user.id,
        meta_ad_account_id="act_100",
        meta_ad_id="ad_paused_1",
        name="Paused Test Ad",
        effective_status="CAMPAIGN_PAUSED",
        facebook_page_id="page_ad_filter_test"
    )
    db_session.add_all([ad_active, ad_paused])
    db_session.commit()
    db_session.refresh(ad_active)
    db_session.refresh(ad_paused)

    # Add unreplied top-level comment to active ad
    c_unreplied = SocialComment(
        user_id=user.id,
        social_account_id=acc.id,
        platform="facebook",
        external_comment_id="comm_active_unreplied",
        comment_text="Active ad unreplied comment",
        webhook_object="{}",
        meta_ad_id=ad_active.id
    )
    db_session.add(c_unreplied)
    db_session.commit()

    fastapi_app = client.app
    from app.api.v1.deps import get_current_user
    fastapi_app.dependency_overrides[get_current_user] = lambda: user

    try:
        # Query status=ALL
        res_all = client.get(f"/api/v1/social-comments/ads?social_account_id={acc.id}&status=ALL")
        assert res_all.status_code == 200
        ads_all = res_all.json()
        assert len(ads_all) == 2

        # Query status=ACTIVE
        res_active = client.get(f"/api/v1/social-comments/ads?social_account_id={acc.id}&status=ACTIVE")
        assert res_active.status_code == 200
        ads_active = res_active.json()
        assert len(ads_active) == 1
        assert ads_active[0]["effective_status"] == "ACTIVE"
        assert ads_active[0]["unreplied_comment_count"] == 1

        # Query status=PAUSED
        res_paused = client.get(f"/api/v1/social-comments/ads?social_account_id={acc.id}&status=PAUSED")
        assert res_paused.status_code == 200
        ads_paused = res_paused.json()
        assert len(ads_paused) == 1
        assert ads_paused[0]["effective_status"] == "CAMPAIGN_PAUSED"
    finally:
        fastapi_app.dependency_overrides.clear()

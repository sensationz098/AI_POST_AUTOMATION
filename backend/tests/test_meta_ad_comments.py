import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from app.models.user import User
from app.models.social_account import SocialAccount
from app.models.meta_ad_account import MetaAdAccount
from app.models.meta_ad import MetaAd
from app.models.social_comment import SocialComment
from app.core.security_encryption import encrypt_token
from app.services.meta_service import meta_service

def test_fetch_comments_for_facebook_post_mock():
    comments = meta_service.fetch_comments_for_facebook_post(
        post_id="1001432206614811_1462507462560311",
        access_token="mock_token"
    )
    assert isinstance(comments, list)
    assert len(comments) >= 1
    assert comments[0]["message"] == "Is this class available online?"

@patch("requests.get")
def test_fetch_comments_for_facebook_post_success(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": [
            {
                "id": "1462507462560311_1070990598646589",
                "message": "Interested in enrolling!",
                "created_time": "2026-09-02T06:00:00+00:00",
                "from": {"id": "999888777", "name": "John Doe"}
            }
        ],
        "paging": {}
    }
    mock_get.return_value = mock_resp

    comments = meta_service.fetch_comments_for_facebook_post(
        post_id="1001432206614811_1462507462560311",
        access_token="EAAB12345"
    )
    assert len(comments) == 1
    assert comments[0]["id"] == "1462507462560311_1070990598646589"
    assert comments[0]["message"] == "Interested in enrolling!"

def test_sync_comments_for_meta_ads_end_to_end(db_session):
    # 1. Create User
    user = User(email="ad_comment_user@example.com", full_name="Ad Comment User", hashed_password="pw", is_active=True)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # 2. Create connected Social Account
    sa = SocialAccount(
        user_id=user.id,
        platform="facebook",
        account_id="1001432206614811",
        account_name="Sensationz Page",
        access_token=encrypt_token("EAA_VALID_TOKEN"),
        status="CONNECTED"
    )
    db_session.add(sa)
    db_session.commit()
    db_session.refresh(sa)

    # 3. Create Meta Ad Account
    ad_acct = MetaAdAccount(
        user_id=user.id,
        meta_ad_account_id="act_123456789",
        name="Main Ad Account",
        account_status=1
    )
    db_session.add(ad_acct)
    db_session.commit()

    # 4. Create 2 Meta Ads sharing the same backing facebook_post_id
    ad1 = MetaAd(
        user_id=user.id,
        meta_ad_account_id="act_123456789",
        meta_ad_id="ad_001",
        name="Enroll Today Ad #1",
        campaign_name="Summer Campaign",
        adset_name="Feed Placement",
        facebook_page_id="1001432206614811",
        facebook_post_id="1001432206614811_1462507462560311",
        mapping_status="MAPPED"
    )
    ad2 = MetaAd(
        user_id=user.id,
        meta_ad_account_id="act_123456789",
        meta_ad_id="ad_002",
        name="Enroll Today Ad #2",
        campaign_name="Summer Campaign",
        adset_name="Story Placement",
        facebook_page_id="1001432206614811",
        facebook_post_id="1001432206614811_1462507462560311",
        mapping_status="MAPPED"
    )
    # 5. Create 1 Meta Ad without facebook_post_id (should be skipped gracefully)
    ad_no_post = MetaAd(
        user_id=user.id,
        meta_ad_account_id="act_123456789",
        meta_ad_id="ad_003",
        name="Draft Ad",
        facebook_post_id=None,
        mapping_status="NOT_AVAILABLE"
    )
    db_session.add_all([ad1, ad2, ad_no_post])
    db_session.commit()
    db_session.refresh(ad1)

    # 6. Mock fetch_comments_for_facebook_post
    mock_comments = [
        {
            "id": "c_101",
            "message": "When is the next batch starting?",
            "created_time": "2026-09-02T06:30:00+00:00",
            "from": {"id": "user_201", "name": "Alice"}
        }
    ]

    with patch.object(meta_service, "fetch_comments_for_facebook_post", return_value=mock_comments):
        res = meta_service.sync_comments_for_meta_ads(
            db=db_session,
            user_id=user.id,
            meta_ad_account_id="act_123456789"
        )

    assert res["success"] is True
    assert res["ads_checked"] == 3
    assert res["ads_with_engagement_posts"] == 2
    assert res["ads_skipped_without_post_id"] == 1
    assert res["comments_fetched"] == 1
    assert res["new_comments"] >= 1

    # Verify persisted SocialComment
    db_comment = db_session.query(SocialComment).filter(
        SocialComment.user_id == user.id,
        SocialComment.external_comment_id == "c_101"
    ).first()

    assert db_comment is not None
    assert db_comment.comment_text == "When is the next batch starting?"
    assert db_comment.commenter_name == "Alice"
    assert db_comment.meta_ad_id in [ad1.id, ad2.id]
    assert db_comment.webhook_object == "ad_comment"

def test_sync_meta_ad_comments_api_security(client, db_session):
    # 1. Create User 1 and User 2
    u1 = User(email="u1@example.com", full_name="User One", hashed_password="pw", is_active=True)
    u2 = User(email="u2@example.com", full_name="User Two", hashed_password="pw", is_active=True)
    db_session.add_all([u1, u2])
    db_session.commit()
    db_session.refresh(u1)
    db_session.refresh(u2)

    # 2. Ad Account owned by User 1
    acct_u1 = MetaAdAccount(
        user_id=u1.id,
        meta_ad_account_id="act_owner_u1",
        name="User 1 Ad Account"
    )
    db_session.add(acct_u1)
    db_session.commit()

    # 3. User 2 attempts to sync User 1's ad account -> should return 404
    fastapi_app = client.app
    from app.api.v1.deps import get_current_user
    fastapi_app.dependency_overrides[get_current_user] = lambda: u2

    resp = client.post("/api/v1/meta/ad-accounts/act_owner_u1/comments/sync")
    assert resp.status_code == 404

    # 4. User 1 syncs User 1's ad account -> should succeed
    fastapi_app.dependency_overrides[get_current_user] = lambda: u1
    with patch.object(meta_service, "sync_comments_for_meta_ads", return_value={"success": True, "comments_fetched": 0}):
        resp = client.post("/api/v1/meta/ad-accounts/act_owner_u1/comments/sync")
        assert resp.status_code in (200, 202)
        assert resp.json()["success"] is True

def test_get_social_comments_with_meta_ad_filter(client, db_session):
    u = User(email="meta_ad_filter_u@example.com", full_name="Filter User", hashed_password="pw", is_active=True)
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)

    sa = SocialAccount(
        user_id=u.id,
        platform="facebook",
        account_id="page_999",
        account_name="Filter Page",
        access_token="token_xyz",
        status="CONNECTED"
    )
    db_session.add(sa)
    db_session.commit()
    db_session.refresh(sa)

    ad = MetaAd(
        user_id=u.id,
        meta_ad_account_id="act_filter",
        meta_ad_id="ad_filter_1",
        name="Campaign Ad 1",
        campaign_name="Conversion Campaign",
        mapping_status="MAPPED"
    )
    db_session.add(ad)
    db_session.commit()
    db_session.refresh(ad)

    c1 = SocialComment(
        user_id=u.id,
        social_account_id=sa.id,
        platform="facebook",
        external_comment_id="c_filter_1",
        comment_text="Ad comment text",
        webhook_object="ad_comment",
        meta_ad_id=ad.id
    )
    c2 = SocialComment(
        user_id=u.id,
        social_account_id=sa.id,
        platform="facebook",
        external_comment_id="c_filter_2",
        comment_text="Organic post comment text",
        webhook_object="page",
        meta_ad_id=None
    )
    db_session.add_all([c1, c2])
    db_session.commit()

    fastapi_app = client.app
    from app.api.v1.deps import get_current_user
    fastapi_app.dependency_overrides[get_current_user] = lambda: u

    # Fetch all
    r_all = client.get("/api/v1/social-comments/")
    assert r_all.status_code == 200
    assert len(r_all.json()) == 2

    # Filter by meta_ad_id
    r_filtered = client.get(f"/api/v1/social-comments/?meta_ad_id={ad.id}")
    assert r_filtered.status_code == 200
    data = r_filtered.json()
    assert len(data) == 1
    assert data[0]["external_comment_id"] == "c_filter_1"
    assert data[0]["meta_ad_id"] == ad.id
    assert data[0]["meta_ad"]["name"] == "Campaign Ad 1"
    assert data[0]["meta_ad"]["campaign_name"] == "Conversion Campaign"


def test_get_comments_for_specific_ad_resolution_and_security(client, db_session):
    # 1. Create Owner User and Unauthorized User
    owner = User(email="ad_owner@example.com", full_name="Ad Owner", hashed_password="pw", is_active=True)
    other_user = User(email="other_user@example.com", full_name="Other User", hashed_password="pw", is_active=True)
    db_session.add_all([owner, other_user])
    db_session.commit()
    db_session.refresh(owner)
    db_session.refresh(other_user)

    # 2. Create Meta Ad with large 64-bit external meta_ad_id
    ext_meta_ad_id = "120247633040840010"
    ad = MetaAd(
        id=51,
        user_id=owner.id,
        meta_ad_account_id="act_515151",
        meta_ad_id=ext_meta_ad_id,
        name="Targeted Campaign Ad #51",
        campaign_name="Conversion Booster",
        mapping_status="MAPPED"
    )
    db_session.add(ad)
    db_session.commit()
    db_session.refresh(ad)

    # 3. Create social comments linked to Ad #51
    sa = SocialAccount(user_id=owner.id, platform="facebook", account_id="page_51", account_name="Page 51", access_token="tok")
    db_session.add(sa)
    db_session.commit()
    db_session.refresh(sa)

    comments_to_add = [
        SocialComment(
            user_id=owner.id,
            social_account_id=sa.id,
            platform="facebook",
            external_comment_id=f"c_ad51_{i}",
            comment_text=f"Ad comment #{i}",
            webhook_object="ad_comment",
            meta_ad_id=ad.id
        )
        for i in range(15)
    ]
    db_session.add_all(comments_to_add)
    db_session.commit()

    fastapi_app = client.app
    from app.api.v1.deps import get_current_user
    fastapi_app.dependency_overrides[get_current_user] = lambda: owner

    # A. Access by internal DB ID '51'
    res_id = client.get(f"/api/v1/social-comments/ads/{ad.id}?page=1&limit=10")
    assert res_id.status_code == 200
    body_id = res_id.json()
    assert body_id["ad"]["id"] == 51
    assert body_id["ad"]["name"] == "Targeted Campaign Ad #51"
    assert body_id["total_comments"] == 15
    assert len(body_id["comments"]) == 10
    assert body_id["has_next"] is True

    # B. Access by external string Meta Ad ID '120247633040840010' (must not crash with Postgres integer overflow)
    res_ext = client.get(f"/api/v1/social-comments/ads/{ext_meta_ad_id}?page=1&limit=10")
    assert res_ext.status_code == 200
    body_ext = res_ext.json()
    assert body_ext["ad"]["id"] == 51
    assert body_ext["total_comments"] == 15
    assert len(body_ext["comments"]) == 10

    # C. Page 2 pagination test
    res_p2 = client.get(f"/api/v1/social-comments/ads/{ad.id}?page=2&limit=10")
    assert res_p2.status_code == 200
    body_p2 = res_p2.json()
    assert len(body_p2["comments"]) == 5
    assert body_p2["has_next"] is False

    # D. Tenant Isolation: Other user access should return 404
    fastapi_app.dependency_overrides[get_current_user] = lambda: other_user
    res_unauth = client.get(f"/api/v1/social-comments/ads/{ad.id}")
    assert res_unauth.status_code == 404

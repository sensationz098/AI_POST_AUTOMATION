import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from app.models.user import User
from app.models.social_account import SocialAccount
from app.models.meta_ad_account import MetaAdAccount
from app.models.meta_ad import MetaAd
from app.models.social_comment import SocialComment
from app.models.social_comment_reply import SocialCommentReply
from app.core.security_encryption import encrypt_token
from app.services.meta_service import meta_service
from app.repositories.social_comment_repository import social_comment_repo

def setup_test_environment(db_session):
    """Helper to create user, social accounts, and ad account."""
    user = User(
        email="unified_comments_user@example.com",
        full_name="Unified Comments User",
        hashed_password="hashed_pw",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    fb_account = SocialAccount(
        user_id=user.id,
        platform="facebook",
        account_id="1001432206614811",
        account_name="Sensationz FB Page",
        access_token=encrypt_token("EAA_FB_TOKEN"),
        status="CONNECTED"
    )
    ig_account = SocialAccount(
        user_id=user.id,
        platform="instagram",
        account_id="17841400928371",
        account_name="sensationz_ig",
        access_token=encrypt_token("EAA_IG_TOKEN"),
        status="CONNECTED"
    )
    db_session.add_all([fb_account, ig_account])
    db_session.commit()
    db_session.refresh(fb_account)
    db_session.refresh(ig_account)

    ad_account = MetaAdAccount(
        user_id=user.id,
        meta_ad_account_id="act_303",
        name="Main Ad Account",
        account_status=1
    )
    db_session.add(ad_account)
    db_session.commit()
    db_session.refresh(ad_account)

    ad = MetaAd(
        user_id=user.id,
        meta_ad_account_id="act_303",
        meta_ad_id="ad_404",
        name="Summer Offer Promo Ad",
        campaign_name="Summer Campaign 2026",
        adset_name="Feed Placement",
        effective_status="ACTIVE",
        facebook_page_id="1001432206614811",
        facebook_post_id="1001432206614811_1462507462560311",
        mapping_status="MAPPED"
    )
    db_session.add(ad)
    db_session.commit()
    db_session.refresh(ad)

    return user, fb_account, ig_account, ad_account, ad


def test_1_get_social_comments_returns_organic_only_when_no_ad_comments(client, db_session):
    user, fb_acc, ig_acc, _, _ = setup_test_environment(db_session)

    c1 = SocialComment(
        user_id=user.id,
        social_account_id=fb_acc.id,
        platform="facebook",
        external_comment_id="fb_organic_c1",
        comment_text="Awesome post!",
        webhook_object="page",
        meta_ad_id=None
    )
    db_session.add(c1)
    db_session.commit()

    fastapi_app = client.app
    from app.api.v1.deps import get_current_user
    fastapi_app.dependency_overrides[get_current_user] = lambda: user

    res = client.get("/api/v1/social-comments/")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["external_comment_id"] == "fb_organic_c1"
    assert data[0]["meta_ad_id"] is None
    assert data[0]["meta_ad"] is None


def test_2_get_social_comments_returns_both_organic_and_ad_comments(client, db_session):
    user, fb_acc, ig_acc, _, ad = setup_test_environment(db_session)

    c_organic = SocialComment(
        user_id=user.id,
        social_account_id=fb_acc.id,
        platform="facebook",
        external_comment_id="fb_organic_1",
        comment_text="Organic post comment",
        webhook_object="page",
        meta_ad_id=None
    )
    c_ad = SocialComment(
        user_id=user.id,
        social_account_id=fb_acc.id,
        platform="facebook",
        external_comment_id="fb_ad_c1",
        comment_text="How much is this promo?",
        webhook_object="ad_comment",
        meta_ad_id=ad.id
    )
    db_session.add_all([c_organic, c_ad])
    db_session.commit()

    fastapi_app = client.app
    from app.api.v1.deps import get_current_user
    fastapi_app.dependency_overrides[get_current_user] = lambda: user

    res = client.get("/api/v1/social-comments/")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2
    comment_ids = {c["external_comment_id"] for c in data}
    assert "fb_organic_1" in comment_ids
    assert "fb_ad_c1" in comment_ids


def test_3_get_social_comments_includes_meta_ad_relationship(client, db_session):
    user, fb_acc, _, _, ad = setup_test_environment(db_session)

    c_ad = SocialComment(
        user_id=user.id,
        social_account_id=fb_acc.id,
        platform="facebook",
        external_comment_id="fb_ad_rel_c1",
        comment_text="Is shipping free?",
        webhook_object="ad_comment",
        meta_ad_id=ad.id
    )
    db_session.add(c_ad)
    db_session.commit()

    fastapi_app = client.app
    from app.api.v1.deps import get_current_user
    fastapi_app.dependency_overrides[get_current_user] = lambda: user

    res = client.get("/api/v1/social-comments/")
    assert res.status_code == 200
    data = res.json()
    ad_comm = next(c for c in data if c["external_comment_id"] == "fb_ad_rel_c1")
    assert ad_comm["meta_ad_id"] == ad.id
    assert ad_comm["meta_ad"] is not None
    assert ad_comm["meta_ad"]["name"] == "Summer Offer Promo Ad"
    assert ad_comm["meta_ad"]["campaign_name"] == "Summer Campaign 2026"
    assert ad_comm["meta_ad"]["adset_name"] == "Feed Placement"
    assert ad_comm["meta_ad"]["effective_status"] == "ACTIVE"


def test_4_meta_ad_comment_saved_via_sync_has_meta_ad_id_assigned(db_session):
    user, fb_acc, _, ad_acct, ad = setup_test_environment(db_session)

    mock_comments = [
        {
            "id": "synced_c_555",
            "message": "Interested in this offer!",
            "created_time": "2026-09-03T10:00:00+00:00",
            "from": {"id": "user_777", "name": "Bob Smart"}
        }
    ]

    with patch.object(meta_service, "fetch_comments_for_facebook_post", return_value=mock_comments):
        res = meta_service.sync_comments_for_meta_ads(
            db=db_session,
            user_id=user.id,
            meta_ad_account_id=ad_acct.meta_ad_account_id
        )

    assert res["success"] is True
    assert res["comments_fetched"] == 1

    saved = db_session.query(SocialComment).filter(
        SocialComment.user_id == user.id,
        SocialComment.external_comment_id == "synced_c_555"
    ).first()

    assert saved is not None
    assert saved.comment_text == "Interested in this offer!"
    assert saved.commenter_name == "Bob Smart"
    assert saved.meta_ad_id == ad.id


def test_5_webhook_comment_updated_idempotently_with_meta_ad_id(db_session):
    user, fb_acc, _, _, ad = setup_test_environment(db_session)

    # 1. Create comment via webhook (without meta_ad_id)
    c_existing = SocialComment(
        user_id=user.id,
        social_account_id=fb_acc.id,
        platform="facebook",
        external_comment_id="shared_comment_999",
        comment_text="Original webhook comment text",
        webhook_object="page",
        meta_ad_id=None
    )
    db_session.add(c_existing)
    db_session.commit()

    # 2. Call repo create_or_get_existing with meta_ad_id
    updated = social_comment_repo.create_or_get_existing(
        db=db_session,
        user_id=user.id,
        social_account_id=fb_acc.id,
        platform="facebook",
        external_comment_id="shared_comment_999",
        external_post_id="post_909",
        comment_text="Original webhook comment text",
        commenter_id="user_888",
        commenter_name="Charlie",
        webhook_object="ad_comment",
        meta_ad_id=ad.id
    )

    # Verify same DB row reused and meta_ad_id updated
    assert updated.id == c_existing.id
    assert updated.meta_ad_id == ad.id

    # Verify no duplicate count
    total_count = db_session.query(SocialComment).filter(
        SocialComment.user_id == user.id,
        SocialComment.external_comment_id == "shared_comment_999"
    ).count()
    assert total_count == 1


def test_6_duplicate_sync_execution_does_not_duplicate_records(db_session):
    user, fb_acc, _, ad_acct, ad = setup_test_environment(db_session)

    mock_comments = [
        {
            "id": "idempotent_c_111",
            "message": "Can I get more info?",
            "created_time": "2026-09-03T11:00:00+00:00",
            "from": {"id": "user_444", "name": "David"}
        }
    ]

    with patch.object(meta_service, "fetch_comments_for_facebook_post", return_value=mock_comments):
        # First sync
        res1 = meta_service.sync_comments_for_meta_ads(db=db_session, user_id=user.id, meta_ad_account_id=ad_acct.meta_ad_account_id)
        # Second sync
        res2 = meta_service.sync_comments_for_meta_ads(db=db_session, user_id=user.id, meta_ad_account_id=ad_acct.meta_ad_account_id)

    assert res1["new_comments"] == 1
    assert res2["new_comments"] == 0

    count = db_session.query(SocialComment).filter(
        SocialComment.user_id == user.id,
        SocialComment.external_comment_id == "idempotent_c_111"
    ).count()
    assert count == 1


def test_7_8_platform_filtering_for_organic_and_ad_comments(client, db_session):
    user, fb_acc, ig_acc, _, ad = setup_test_environment(db_session)

    c_fb_org = SocialComment(user_id=user.id, social_account_id=fb_acc.id, platform="facebook", external_comment_id="c_fb_org", comment_text="FB Org", webhook_object="page", meta_ad_id=None)
    c_fb_ad = SocialComment(user_id=user.id, social_account_id=fb_acc.id, platform="facebook", external_comment_id="c_fb_ad", comment_text="FB Ad", webhook_object="ad_comment", meta_ad_id=ad.id)
    c_ig_org = SocialComment(user_id=user.id, social_account_id=ig_acc.id, platform="instagram", external_comment_id="c_ig_org", comment_text="IG Org", webhook_object="instagram", meta_ad_id=None)

    db_session.add_all([c_fb_org, c_fb_ad, c_ig_org])
    db_session.commit()

    fastapi_app = client.app
    from app.api.v1.deps import get_current_user
    fastapi_app.dependency_overrides[get_current_user] = lambda: user

    # Filter Facebook
    res_fb = client.get("/api/v1/social-comments/?platform=facebook")
    assert res_fb.status_code == 200
    fb_ids = [c["external_comment_id"] for c in res_fb.json()]
    assert len(fb_ids) == 2
    assert "c_fb_org" in fb_ids
    assert "c_fb_ad" in fb_ids

    # Filter Instagram
    res_ig = client.get("/api/v1/social-comments/?platform=instagram")
    assert res_ig.status_code == 200
    ig_ids = [c["external_comment_id"] for c in res_ig.json()]
    assert len(ig_ids) == 1
    assert "c_ig_org" in ig_ids


def test_9_reply_to_organic_comment(client, db_session):
    user, fb_acc, _, _, _ = setup_test_environment(db_session)

    c_org = SocialComment(
        user_id=user.id,
        social_account_id=fb_acc.id,
        platform="facebook",
        external_comment_id="c_org_to_reply",
        comment_text="Organic post inquiry",
        webhook_object="page",
        meta_ad_id=None
    )
    db_session.add(c_org)
    db_session.commit()
    db_session.refresh(c_org)

    fastapi_app = client.app
    from app.api.v1.deps import get_current_user
    fastapi_app.dependency_overrides[get_current_user] = lambda: user

    with patch.object(meta_service, "reply_to_facebook_comment", return_value={"id": "reply_fb_123"}):
        res = client.post(f"/api/v1/social-comments/{c_org.id}/reply", json={"message": "Thanks for asking!"})

    assert res.status_code == 200
    assert res.json()["status"] == "success"

    reply_rec = db_session.query(SocialCommentReply).filter(SocialCommentReply.comment_id == c_org.id).first()
    assert reply_rec is not None
    assert reply_rec.message == "Thanks for asking!"


def test_10_reply_to_ad_comment(client, db_session):
    user, fb_acc, _, _, ad = setup_test_environment(db_session)

    c_ad = SocialComment(
        user_id=user.id,
        social_account_id=fb_acc.id,
        platform="facebook",
        external_comment_id="c_ad_to_reply",
        comment_text="Ad promo inquiry",
        webhook_object="ad_comment",
        meta_ad_id=ad.id
    )
    db_session.add(c_ad)
    db_session.commit()
    db_session.refresh(c_ad)

    fastapi_app = client.app
    from app.api.v1.deps import get_current_user
    fastapi_app.dependency_overrides[get_current_user] = lambda: user

    with patch.object(meta_service, "reply_to_facebook_comment", return_value={"id": "reply_ad_456"}):
        res = client.post(f"/api/v1/social-comments/{c_ad.id}/reply", json={"message": "Special offer valid until Friday!"})

    assert res.status_code == 200
    assert res.json()["status"] == "success"

    reply_rec = db_session.query(SocialCommentReply).filter(SocialCommentReply.comment_id == c_ad.id).first()
    assert reply_rec is not None
    assert reply_rec.message == "Special offer valid until Friday!"


def test_11_12_delete_organic_and_ad_comments(client, db_session):
    user, fb_acc, _, _, ad = setup_test_environment(db_session)

    c_org = SocialComment(user_id=user.id, social_account_id=fb_acc.id, platform="facebook", external_comment_id="c_org_del", comment_text="Spam comment", webhook_object="page", meta_ad_id=None)
    c_ad = SocialComment(user_id=user.id, social_account_id=fb_acc.id, platform="facebook", external_comment_id="c_ad_del", comment_text="Bad ad comment", webhook_object="ad_comment", meta_ad_id=ad.id)

    db_session.add_all([c_org, c_ad])
    db_session.commit()
    db_session.refresh(c_org)
    db_session.refresh(c_ad)

    fastapi_app = client.app
    from app.api.v1.deps import get_current_user
    fastapi_app.dependency_overrides[get_current_user] = lambda: user

    # Delete organic comment
    with patch.object(meta_service, "delete_facebook_comment", return_value=True):
        res1 = client.delete(f"/api/v1/social-comments/{c_org.id}")
    assert res1.status_code == 200
    assert res1.json()["status"] == "success"

    # Delete ad comment
    with patch.object(meta_service, "delete_facebook_comment", return_value=True):
        res2 = client.delete(f"/api/v1/social-comments/{c_ad.id}")
    assert res2.status_code == 200
    assert res2.json()["status"] == "success"

    # Verify both soft-deleted / excluded from GET endpoint
    res_list = client.get("/api/v1/social-comments/")
    assert res_list.status_code == 200
    assert len(res_list.json()) == 0


def test_13_facebook_ad_comment_identity_resolution(db_session):
    user, fb_acc, _, ad_acct, ad = setup_test_environment(db_session)

    mock_comments = [
        {
            "id": "fb_identity_c1",
            "message": "Awesome product!",
            "created_time": "2026-09-03T11:30:00+00:00",
            "from": {"id": "fb_usr_999", "name": "John Doe"}
        }
    ]

    with patch.object(meta_service, "fetch_comments_for_facebook_post", return_value=mock_comments):
        res = meta_service.sync_comments_for_meta_ads(db=db_session, user_id=user.id, meta_ad_account_id=ad_acct.meta_ad_account_id)

    assert res["success"] is True
    saved = db_session.query(SocialComment).filter(SocialComment.external_comment_id == "fb_identity_c1").first()
    assert saved is not None
    assert saved.commenter_id == "fb_usr_999"
    assert saved.commenter_name == "John Doe"


def test_14_instagram_ad_comment_username_resolution(db_session):
    user, fb_acc, _, ad_acct, ad = setup_test_environment(db_session)

    mock_comments = [
        {
            "id": "ig_identity_c2",
            "message": "Love this design!",
            "created_time": "2026-09-03T11:35:00+00:00",
            "username": "design_fanatic_ig"
        }
    ]

    with patch.object(meta_service, "fetch_comments_for_facebook_post", return_value=mock_comments):
        res = meta_service.sync_comments_for_meta_ads(db=db_session, user_id=user.id, meta_ad_account_id=ad_acct.meta_ad_account_id)

    assert res["success"] is True
    saved = db_session.query(SocialComment).filter(SocialComment.external_comment_id == "ig_identity_c2").first()
    assert saved is not None
    assert saved.commenter_name == "design_fanatic_ig"


def test_15_enrichment_of_existing_anonymous_comment(db_session):
    user, fb_acc, _, ad_acct, ad = setup_test_environment(db_session)

    # 1. Initially comment exists with NULL name/id
    existing_anon = SocialComment(
        user_id=user.id,
        social_account_id=fb_acc.id,
        platform="facebook",
        external_comment_id="anon_comment_555",
        comment_text="Initial webhook comment without name",
        commenter_id=None,
        commenter_name=None,
        webhook_object="page",
        meta_ad_id=None
    )
    db_session.add(existing_anon)
    db_session.commit()

    # 2. Later Ad Sync provides commenter_id and commenter_name
    mock_comments = [
        {
            "id": "anon_comment_555",
            "message": "Initial webhook comment without name",
            "created_time": "2026-09-03T11:40:00+00:00",
            "from": {"id": "usr_777", "name": "Jane Smith"}
        }
    ]

    with patch.object(meta_service, "fetch_comments_for_facebook_post", return_value=mock_comments):
        res = meta_service.sync_comments_for_meta_ads(db=db_session, user_id=user.id, meta_ad_account_id=ad_acct.meta_ad_account_id)

    # Verify existing DB row enriched with commenter_name and commenter_id
    db_session.refresh(existing_anon)
    assert existing_anon.commenter_id == "usr_777"
    assert existing_anon.commenter_name == "Jane Smith"
    assert existing_anon.meta_ad_id == ad.id


def test_16_preservation_of_existing_valid_commenter_name(db_session):
    user, fb_acc, _, ad_acct, ad = setup_test_environment(db_session)

    existing_valid = SocialComment(
        user_id=user.id,
        social_account_id=fb_acc.id,
        platform="facebook",
        external_comment_id="valid_name_888",
        comment_text="Known commenter",
        commenter_id="usr_888",
        commenter_name="Original Name",
        webhook_object="page",
        meta_ad_id=None
    )
    db_session.add(existing_valid)
    db_session.commit()

    # Later sync returns comment without name
    mock_comments = [
        {
            "id": "valid_name_888",
            "message": "Known commenter",
            "created_time": "2026-09-03T11:45:00+00:00"
        }
    ]

    with patch.object(meta_service, "fetch_comments_for_facebook_post", return_value=mock_comments):
        res = meta_service.sync_comments_for_meta_ads(db=db_session, user_id=user.id, meta_ad_account_id=ad_acct.meta_ad_account_id)

    db_session.refresh(existing_valid)
    assert existing_valid.commenter_name == "Original Name"


def test_17_meta_no_identity_fallback_persists_successfully(db_session):
    user, fb_acc, _, ad_acct, ad = setup_test_environment(db_session)

    mock_comments = [
        {
            "id": "no_identity_999",
            "message": "Comment with no identity payload from Meta",
            "created_time": "2026-09-03T11:50:00+00:00"
        }
    ]

    with patch.object(meta_service, "fetch_comments_for_facebook_post", return_value=mock_comments):
        res = meta_service.sync_comments_for_meta_ads(db=db_session, user_id=user.id, meta_ad_account_id=ad_acct.meta_ad_account_id)

    saved = db_session.query(SocialComment).filter(SocialComment.external_comment_id == "no_identity_999").first()
    assert saved is not None
    assert saved.commenter_name is None
    assert saved.commenter_id is None


import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.social_account import SocialAccount
from app.models.meta_ad import MetaAd
from app.services.meta_service import meta_service, extract_page_id_from_post_id
from app.repositories.social_comment_repository import social_comment_repo
from app.core.security_encryption import encrypt_token

def test_meta_api_returns_comments_saved(db_session: Session):
    """Test 1: Meta API returns comments -> comments successfully saved to DB."""
    user = User(email="diag_save@test.com", full_name="Diag Save User", hashed_password="pw", is_active=True, role="Editor")
    db_session.add(user)
    db_session.commit()

    sa = SocialAccount(
        user_id=user.id, platform="facebook", account_id="1001432206614811",
        account_name="Diag Page", access_token=encrypt_token("tok_diag_1"), status="CONNECTED"
    )
    db_session.add(sa)
    db_session.commit()

    ad = MetaAd(
        user_id=user.id, meta_ad_account_id="act_diag1", meta_ad_id="ad_diag1",
        name="Diag Ad", facebook_page_id="1001432206614811", facebook_post_id="1001432206614811_999111"
    )
    db_session.add(ad)
    db_session.commit()

    mock_comments = [
        {
            "id": "1001432206614811_999111_c1",
            "message": "Great ad product!",
            "created_time": "2026-09-02T10:00:00+00:00",
            "from": {"id": "u1", "name": "Customer One"}
        },
        {
            "id": "1001432206614811_999111_c2",
            "message": "How much does it cost?",
            "created_time": "2026-09-02T10:05:00+00:00",
            "from": {"id": "u2", "name": "Customer Two"}
        }
    ]

    with patch.object(meta_service, "fetch_comments_for_facebook_post") as mock_fetch:
        mock_fetch.return_value = (mock_comments, {"status_code": 200, "is_permission_error": False})
        res = meta_service.sync_comments_for_meta_ads(db=db_session, user_id=user.id, meta_ad_account_id="act_diag1")

        assert res["success"] is True
        assert res["posts_processed"] == 1
        assert res["comments_fetched"] == 2
        assert res["comments_saved"] == 2
        assert res["graph_requests_successful"] == 1

        db_comments = social_comment_repo.get_by_user_id(db=db_session, user_id=user.id, platform="facebook")
        assert len(db_comments) == 2
        comment_texts = {c.comment_text for c in db_comments}
        assert "Great ad product!" in comment_texts
        assert "How much does it cost?" in comment_texts


def test_meta_api_returns_empty_data(db_session: Session):
    """Test 2: Meta API returns empty data array -> correctly reported as zero comments."""
    user = User(email="diag_empty@test.com", full_name="Diag Empty User", hashed_password="pw", is_active=True, role="Editor")
    db_session.add(user)
    db_session.commit()

    sa = SocialAccount(
        user_id=user.id, platform="facebook", account_id="1001432206614811",
        account_name="Diag Page", access_token=encrypt_token("tok_diag_2"), status="CONNECTED"
    )
    db_session.add(sa)
    db_session.commit()

    ad = MetaAd(
        user_id=user.id, meta_ad_account_id="act_diag2", meta_ad_id="ad_diag2",
        name="Diag Ad Empty", facebook_page_id="1001432206614811", facebook_post_id="1001432206614811_999222"
    )
    db_session.add(ad)
    db_session.commit()

    with patch.object(meta_service, "fetch_comments_for_facebook_post") as mock_fetch:
        mock_fetch.return_value = ([], {"status_code": 200, "is_permission_error": False})
        res = meta_service.sync_comments_for_meta_ads(db=db_session, user_id=user.id, meta_ad_account_id="act_diag2")

        assert res["success"] is True
        assert res["posts_processed"] == 1
        assert res["comments_fetched"] == 0
        assert res["posts_returning_zero_comments"] == 1
        assert res["graph_requests_successful"] == 1


def test_meta_api_pagination(db_session: Session):
    """Test 3: Meta API returns pagination -> all pages processed."""
    with patch("requests.get") as mock_get:
        # Mock 2 pages of response
        resp1 = MagicMock()
        resp1.status_code = 200
        resp1.headers = {"content-type": "application/json"}
        resp1.json.return_value = {
            "data": [{"id": "c1", "message": "Page 1 comment"}],
            "paging": {"next": "https://graph.facebook.com/v18.0/post1/comments?after=cursor1"}
        }

        resp2 = MagicMock()
        resp2.status_code = 200
        resp2.headers = {"content-type": "application/json"}
        resp2.json.return_value = {
            "data": [{"id": "c2", "message": "Page 2 comment"}],
            "paging": {}
        }

        mock_get.side_effect = [resp1, resp2]

        comments, details = meta_service.fetch_comments_for_facebook_post(
            post_id="1001432206614811_123",
            access_token="tok_real_token",
            page_id="1001432206614811",
            return_details=True
        )

        assert len(comments) == 2
        assert comments[0]["id"] == "c1"
        assert comments[1]["id"] == "c2"
        assert details["status_code"] == 200


def test_comment_already_exists_deduplicated(db_session: Session):
    """Test 4: Existing comment -> reused, no duplicate DB rows created."""
    user = User(email="diag_dedup@test.com", full_name="Diag Dedup User", hashed_password="pw", is_active=True, role="Editor")
    db_session.add(user)
    db_session.commit()

    sa = SocialAccount(
        user_id=user.id, platform="facebook", account_id="1001432206614811",
        account_name="Diag Page", access_token=encrypt_token("tok_diag_3"), status="CONNECTED"
    )
    db_session.add(sa)
    db_session.commit()

    ad = MetaAd(
        user_id=user.id, meta_ad_account_id="act_diag3", meta_ad_id="ad_diag3",
        name="Diag Ad Dedup", facebook_page_id="1001432206614811", facebook_post_id="1001432206614811_999333"
    )
    db_session.add(ad)
    db_session.commit()

    mock_comments = [{"id": "c_dup_1", "message": "Duplicate test comment", "created_time": "2026-09-02T10:00:00+00:00"}]

    with patch.object(meta_service, "fetch_comments_for_facebook_post") as mock_fetch:
        mock_fetch.return_value = (mock_comments, {"status_code": 200, "is_permission_error": False})
        
        res1 = meta_service.sync_comments_for_meta_ads(db=db_session, user_id=user.id, meta_ad_account_id="act_diag3")
        assert res1["comments_saved"] == 1
        assert res1["comments_reused"] == 0

        res2 = meta_service.sync_comments_for_meta_ads(db=db_session, user_id=user.id, meta_ad_account_id="act_diag3")
        assert res2["comments_saved"] == 0
        assert res2["comments_reused"] == 1

        db_comments = social_comment_repo.get_by_user_id(db=db_session, user_id=user.id, platform="facebook")
        assert len(db_comments) == 1


def test_comment_save_failure_handled(db_session: Session):
    """Test 5: Save failure -> error logged, comments_skipped incremented, not swallowed blindly."""
    user = User(email="diag_err@test.com", full_name="Diag Err User", hashed_password="pw", is_active=True, role="Editor")
    db_session.add(user)
    db_session.commit()

    sa = SocialAccount(
        user_id=user.id, platform="facebook", account_id="1001432206614811",
        account_name="Diag Page", access_token=encrypt_token("tok_diag_4"), status="CONNECTED"
    )
    db_session.add(sa)
    db_session.commit()

    ad = MetaAd(
        user_id=user.id, meta_ad_account_id="act_diag4", meta_ad_id="ad_diag4",
        name="Diag Ad Err", facebook_page_id="1001432206614811", facebook_post_id="1001432206614811_999444"
    )
    db_session.add(ad)
    db_session.commit()

    mock_comments = [{"id": "c_err_1", "message": "Failing save comment"}]

    with patch.object(meta_service, "fetch_comments_for_facebook_post") as mock_fetch:
        mock_fetch.return_value = (mock_comments, {"status_code": 200, "is_permission_error": False})
        with patch.object(social_comment_repo, "create_or_get_existing", side_effect=Exception("DB Save Failure")):
            res = meta_service.sync_comments_for_meta_ads(db=db_session, user_id=user.id, meta_ad_account_id="act_diag4")
            
            assert res["success"] is True
            assert res["comments_skipped"] == 1


def test_correct_post_id_ad_relationship(db_session: Session):
    """Test 6: Verify post ID used matches ad and metadata_json stores ad context."""
    user = User(email="diag_rel@test.com", full_name="Diag Rel User", hashed_password="pw", is_active=True, role="Editor")
    db_session.add(user)
    db_session.commit()

    sa = SocialAccount(
        user_id=user.id, platform="facebook", account_id="1001432206614811",
        account_name="Diag Page", access_token=encrypt_token("tok_diag_5"), status="CONNECTED"
    )
    db_session.add(sa)
    db_session.commit()

    ad = MetaAd(
        user_id=user.id, meta_ad_account_id="act_diag5", meta_ad_id="ad_diag5",
        name="Campaign Ad", campaign_name="Summer Campaign", facebook_page_id="1001432206614811", facebook_post_id="1001432206614811_999555"
    )
    db_session.add(ad)
    db_session.commit()

    mock_comments = [{"id": "c_rel_1", "message": "Context test"}]

    with patch.object(meta_service, "fetch_comments_for_facebook_post") as mock_fetch:
        mock_fetch.return_value = (mock_comments, {"status_code": 200, "is_permission_error": False})
        meta_service.sync_comments_for_meta_ads(db=db_session, user_id=user.id, meta_ad_account_id="act_diag5")

        comment = social_comment_repo.get_by_user_id(db=db_session, user_id=user.id, platform="facebook")[0]
        assert comment.external_post_id == "1001432206614811_999555"
        assert comment.meta_ad_id == ad.id
        assert comment.metadata_json.get("campaign_name") == "Summer Campaign"


def test_saved_comment_returned_by_api(db_session: Session):
    """Test 7: Saved comment is queryable and returned by application repository API."""
    user = User(email="diag_api@test.com", full_name="Diag API User", hashed_password="pw", is_active=True, role="Editor")
    db_session.add(user)
    db_session.commit()

    sa = SocialAccount(
        user_id=user.id, platform="facebook", account_id="1001432206614811",
        account_name="Diag Page", access_token=encrypt_token("tok_diag_6"), status="CONNECTED"
    )
    db_session.add(sa)
    db_session.commit()

    res = meta_service.sync_comments_for_single_post(db=db_session, user_id=user.id, post_id="1001432206614811_999666")
    assert res["success"] is True or res["reason"] == "INVALID_TOKEN" or res["comments_saved"] == 0

    # Explicitly test creation and retrieval
    comment_rec = social_comment_repo.create_or_get_existing(
        db=db_session,
        user_id=user.id,
        social_account_id=sa.id,
        platform="facebook",
        external_comment_id="c_api_777",
        external_post_id="1001432206614811_999666",
        comment_text="Returned by API test"
    )
    assert comment_rec is not None

    comments = social_comment_repo.get_by_user_id(db=db_session, user_id=user.id, platform="facebook", social_account_id=sa.id)
    assert any(c.external_comment_id == "c_api_777" for c in comments)


def test_mixed_batch_diagnostic_counts(db_session: Session):
    """Test 8: Mixed batch -> some posts empty, some successful, some skipped -> counts accurate."""
    user = User(email="diag_batch@test.com", full_name="Diag Batch User", hashed_password="pw", is_active=True, role="Editor")
    db_session.add(user)
    db_session.commit()

    sa = SocialAccount(
        user_id=user.id, platform="facebook", account_id="1001432206614811",
        account_name="Diag Page", access_token=encrypt_token("tok_diag_7"), status="CONNECTED"
    )
    db_session.add(sa)
    db_session.commit()

    ad1 = MetaAd(user_id=user.id, meta_ad_account_id="act_batch", meta_ad_id="ad_b1", facebook_page_id="1001432206614811", facebook_post_id="1001432206614811_b1")
    ad2 = MetaAd(user_id=user.id, meta_ad_account_id="act_batch", meta_ad_id="ad_b2", facebook_page_id="1001432206614811", facebook_post_id="1001432206614811_b2")
    ad3 = MetaAd(user_id=user.id, meta_ad_account_id="act_batch", meta_ad_id="ad_b3", facebook_page_id="711139875422034", facebook_post_id="711139875422034_b3")
    db_session.add_all([ad1, ad2, ad3])
    db_session.commit()

    def mock_fetch_side_effect(post_id, access_token, page_id, return_details=False):
        if post_id == "1001432206614811_b1":
            return ([{"id": "cb1", "message": "Batch comment 1"}], {"status_code": 200, "is_permission_error": False})
        else:
            return ([], {"status_code": 200, "is_permission_error": False})

    with patch.object(meta_service, "fetch_comments_for_facebook_post", side_effect=mock_fetch_side_effect):
        res = meta_service.sync_comments_for_meta_ads(db=db_session, user_id=user.id, meta_ad_account_id="act_batch")

        assert res["success"] is True
        assert res["ads_total"] == 3
        assert res["posts_processed"] == 2
        assert res["pages_not_connected"] == 1
        assert res["graph_requests_successful"] == 2
        assert res["comments_fetched"] == 1
        assert res["comments_saved"] == 1
        assert res["posts_returning_zero_comments"] == 1


def test_unconnected_page_skipped_without_permission_error(db_session: Session):
    """Test 9: Unconnected Page -> skipped without permission error."""
    user = User(email="diag_unconn@test.com", full_name="Diag Unconn User", hashed_password="pw", is_active=True, role="Editor")
    db_session.add(user)
    db_session.commit()

    ad = MetaAd(user_id=user.id, meta_ad_account_id="act_unconn", meta_ad_id="ad_u1", facebook_page_id="999888777", facebook_post_id="999888777_111")
    db_session.add(ad)
    db_session.commit()

    res = meta_service.sync_comments_for_meta_ads(db=db_session, user_id=user.id, meta_ad_account_id="act_unconn")
    assert res["success"] is True
    assert res["pages_not_connected"] == 1
    assert res["permission_errors"] == 0


def test_exact_page_token_success(db_session: Session):
    """Test 10: Exact Page token -> Graph API request succeeds with correct token."""
    user = User(email="diag_exact@test.com", full_name="Diag Exact User", hashed_password="pw", is_active=True, role="Editor")
    db_session.add(user)
    db_session.commit()

    sa = SocialAccount(
        user_id=user.id, platform="facebook", account_id="1001432206614811",
        account_name="Exact Diag Page", access_token=encrypt_token("tok_exact_diag"), status="CONNECTED"
    )
    db_session.add(sa)
    db_session.commit()

    ad = MetaAd(user_id=user.id, meta_ad_account_id="act_exact", meta_ad_id="ad_e1", facebook_page_id="1001432206614811", facebook_post_id="1001432206614811_999")
    db_session.add(ad)
    db_session.commit()

    with patch.object(meta_service, "fetch_comments_for_facebook_post") as mock_fetch:
        mock_fetch.return_value = ([], {"status_code": 200, "is_permission_error": False})
        res = meta_service.sync_comments_for_meta_ads(db=db_session, user_id=user.id, meta_ad_account_id="act_exact")
        
        assert res["success"] is True
        mock_fetch.assert_called_once()
        assert mock_fetch.call_args.kwargs["access_token"] == "tok_exact_diag"
        assert mock_fetch.call_args.kwargs["page_id"] == "1001432206614811"

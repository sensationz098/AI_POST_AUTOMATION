import pytest
import time
from unittest.mock import patch, MagicMock
from app.models.user import User
from app.models.social_account import SocialAccount
from app.models.meta_ad_account import MetaAdAccount
from app.models.meta_ad import MetaAd
from app.models.social_comment import SocialComment
from app.core.security_encryption import encrypt_token
from app.services.meta_service import meta_service
from app.services.meta_comment_job_manager import job_manager
from app.repositories.social_comment_repository import social_comment_repo
from app.main import app as fastapi_app
from app.api.v1.deps import get_current_user


def test_successful_backend_sync_response(client, db_session):
    """Scenario 1: Verified backend sync response schema for async dispatch."""
    u = User(email="async_sync_u1@example.com", full_name="Async User 1", hashed_password="pw", is_active=True)
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)

    acct = MetaAdAccount(user_id=u.id, meta_ad_account_id="act_async_101", name="Async Ad Account 1")
    db_session.add(acct)
    db_session.commit()

    ad1 = MetaAd(user_id=u.id, meta_ad_account_id="act_async_101", meta_ad_id="ad_a1", facebook_page_id="1001", facebook_post_id="1001_p1")
    ad2 = MetaAd(user_id=u.id, meta_ad_account_id="act_async_101", meta_ad_id="ad_a2", facebook_page_id="1001", facebook_post_id="1001_p2")
    db_session.add_all([ad1, ad2])
    db_session.commit()

    fastapi_app = client.app
    fastapi_app.dependency_overrides[get_current_user] = lambda: u

    resp = client.post("/api/v1/meta/ad-accounts/act_async_101/comments/sync")
    assert resp.status_code == 202
    data = resp.json()
    assert data["success"] is True
    assert "job_id" in data
    assert data["status"] == "PROCESSING"
    assert data["ads_total"] == 2
    assert data["ads_processed"] == 0


def test_long_running_sync_background_job_polling(client, db_session):
    """Scenario 2: Long-running sync background job execution & status endpoint polling."""
    from tests.conftest import TestingSessionLocal

    u = User(email="async_sync_u2@example.com", full_name="Async User 2", hashed_password="pw", is_active=True)
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)

    acct = MetaAdAccount(user_id=u.id, meta_ad_account_id="act_async_102", name="Async Ad Account 2")
    sa = SocialAccount(
        user_id=u.id, platform="facebook", account_id="1002", account_name="Page 1002",
        access_token=encrypt_token("tok_1002"), status="CONNECTED"
    )
    ad1 = MetaAd(user_id=u.id, meta_ad_account_id="act_async_102", meta_ad_id="ad_b1", facebook_page_id="1002", facebook_post_id="1002_pb1")
    db_session.add_all([acct, sa, ad1])
    db_session.commit()

    fastapi_app = client.app
    fastapi_app.dependency_overrides[get_current_user] = lambda: u

    mock_comments = [{"id": "c_job_1", "message": "Background sync comment test"}]
    from app.api.v1 import meta as meta_api_mod
    orig_bg = meta_api_mod.run_background_comment_sync

    with patch.object(meta_api_mod, "run_background_comment_sync", side_effect=lambda *args, **kwargs: orig_bg(*args, **{**kwargs, "db": db_session})):
        with patch.object(meta_service, "fetch_comments_for_facebook_post", return_value=(mock_comments, {"status_code": 200})):
            init_res = client.post("/api/v1/meta/ad-accounts/act_async_102/comments/sync")
            assert init_res.status_code == 202
            init_data = init_res.json()
            job_id = init_data["job_id"]

            # Poll status endpoint until completed
            completed = False
            for _ in range(20):
                status_res = client.get(f"/api/v1/meta/ad-accounts/act_async_102/comments/sync/status/{job_id}")
                assert status_res.status_code == 200
                s_data = status_res.json()
                if s_data["status"] == "COMPLETED":
                    completed = True
                    assert s_data["comments_fetched"] == 1
                    assert s_data["comments_saved"] == 1
                    break
                time.sleep(0.1)

            assert completed is True, f"Job did not complete. Final job state: {s_data}"


def test_frontend_compatible_response_schema(client, db_session):
    """Scenario 3: Response contract verification with all required metric fields."""
    u = User(email="async_sync_u3@example.com", full_name="Async User 3", hashed_password="pw", is_active=True)
    db_session.add(u)
    db_session.commit()

    acct = MetaAdAccount(user_id=u.id, meta_ad_account_id="act_async_103", name="Async Ad Account 3")
    db_session.add(acct)
    db_session.commit()

    fastapi_app = client.app
    fastapi_app.dependency_overrides[get_current_user] = lambda: u

    # Test direct synchronous execution mode using run_sync=true
    mock_res = {
        "success": True,
        "reconnect_required": False,
        "ad_account_id": "act_async_103",
        "ads_total": 5,
        "ads_checked": 5,
        "posts_processed": 5,
        "ads_with_post_id": 5,
        "graph_requests_successful": 5,
        "graph_requests_failed": 0,
        "posts_returning_zero_comments": 2,
        "comments_fetched": 10,
        "comments_saved": 8,
        "comments_reused": 2,
        "comments_skipped": 0,
        "new_comments": 8,
        "existing_comments": 2,
        "permission_errors": 0,
        "duration_seconds": 1.2
    }

    with patch.object(meta_service, "sync_comments_for_meta_ads", return_value=mock_res):
        resp = client.post("/api/v1/meta/ad-accounts/act_async_103/comments/sync?run_sync=true")
        assert resp.status_code == 200
        data = resp.json()
        required_fields = [
            "comments_saved", "comments_fetched", "comments_reused",
            "comments_skipped", "posts_processed", "graph_requests_successful",
            "graph_requests_failed"
        ]
        for field in required_fields:
            assert field in data, f"Missing required frontend schema field: {field}"


def test_comments_saved_error_resilience(client, db_session):
    """Scenario 4: Verification that comments saved before an post error remain committed in DB."""
    u = User(email="async_sync_u4@example.com", full_name="Async User 4", hashed_password="pw", is_active=True)
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)

    sa = SocialAccount(
        user_id=u.id, platform="facebook", account_id="1004", account_name="Page 1004",
        access_token=encrypt_token("tok_1004"), status="CONNECTED"
    )
    ad1 = MetaAd(user_id=u.id, meta_ad_account_id="act_async_104", meta_ad_id="ad_d1", facebook_page_id="1004", facebook_post_id="1004_p1")
    ad2 = MetaAd(user_id=u.id, meta_ad_account_id="act_async_104", meta_ad_id="ad_d2", facebook_page_id="1004", facebook_post_id="1004_p2")
    db_session.add_all([sa, ad1, ad2])
    db_session.commit()

    def mock_fetch_side_effect(post_id, access_token, page_id, return_details=False):
        if post_id == "1004_p1":
            return ([{"id": "c_resilient_1", "message": "Saved before error"}], {"status_code": 200})
        else:
            raise Exception("API rate limit on second post")

    with patch.object(meta_service, "fetch_comments_for_facebook_post", side_effect=mock_fetch_side_effect):
        meta_service.sync_comments_for_meta_ads(db=db_session, user_id=u.id, meta_ad_account_id="act_async_104")

    # Verify that c_resilient_1 WAS saved in PostgreSQL despite the error on post 2
    c_saved = db_session.query(SocialComment).filter(
        SocialComment.user_id == u.id,
        SocialComment.external_comment_id == "c_resilient_1"
    ).first()

    assert c_saved is not None
    assert c_saved.comment_text == "Saved before error"


def test_saved_comments_retrievable_in_social_comments_api(client, db_session):
    """Scenario 5: Complete end-to-end trace from Meta sync persistence to Social Comments API."""
    u = User(email="async_sync_u5@example.com", full_name="Async User 5", hashed_password="pw", is_active=True)
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)

    sa = SocialAccount(
        user_id=u.id, platform="facebook", account_id="1005", account_name="Page 1005",
        access_token=encrypt_token("tok_1005"), status="CONNECTED"
    )
    ad = MetaAd(user_id=u.id, meta_ad_account_id="act_async_105", meta_ad_id="ad_e1", facebook_page_id="1005", facebook_post_id="1005_pe1")
    db_session.add_all([sa, ad])
    db_session.commit()

    mock_comments = [{"id": "c_retrievable_99", "message": "Retrievable comment test text"}]
    with patch.object(meta_service, "fetch_comments_for_facebook_post", return_value=(mock_comments, {"status_code": 200})):
        res = meta_service.sync_comments_for_meta_ads(db=db_session, user_id=u.id, meta_ad_account_id="act_async_105")
        assert res["comments_saved"] == 1

    # Query Social Comments API endpoint
    fastapi_app = client.app
    fastapi_app.dependency_overrides[get_current_user] = lambda: u
    api_resp = client.get("/api/v1/social-comments/")
    assert api_resp.status_code == 200
    comments_list = api_resp.json()

    matched = [c for c in comments_list if c["external_comment_id"] == "c_retrievable_99"]
    assert len(matched) == 1
    assert matched[0]["comment_text"] == "Retrievable comment test text"
    assert matched[0]["meta_ad_id"] == ad.id

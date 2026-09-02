import pytest
import time
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.models.user import User
from app.models.social_account import SocialAccount
from app.models.meta_ad_account import MetaAdAccount
from app.models.meta_ad import MetaAd
from app.core.security_encryption import encrypt_token
from app.services.meta_service import meta_service
from app.api.v1.deps import get_current_user
from app.main import app as fastapi_app


def setup_test_ads_fixture(db_session: Session):
    """
    Helper fixture creating:
    - 1 User
    - 1 Connected Facebook SocialAccount (Page ID: 1001432206614811)
    - 1 MetaAdAccount ("act_status_101")
    - 10 MetaAd records total:
        - 3 ACTIVE ads
        - 4 PAUSED ads
        - 2 ADSET_PAUSED ads
        - 1 CAMPAIGN_PAUSED ad
    """
    user = User(
        email="status_filter_user@test.com",
        full_name="Status Filter User",
        hashed_password="hashed_pw_123",
        is_active=True,
        role="Editor"
    )
    db_session.add(user)
    db_session.commit()

    sa = SocialAccount(
        user_id=user.id,
        platform="facebook",
        account_id="1001432206614811",
        account_name="Matching Page",
        access_token=encrypt_token("page_token_valid_123"),
        status="CONNECTED"
    )
    db_session.add(sa)

    ad_acct = MetaAdAccount(
        user_id=user.id,
        meta_ad_account_id="act_status_101",
        name="Status Test Account",
        account_status=1,
        currency="USD"
    )
    db_session.add(ad_acct)
    db_session.commit()

    ads = [
        # 3 ACTIVE ads
        MetaAd(user_id=user.id, meta_ad_account_id="act_status_101", meta_ad_id="ad_act_1", name="Active 1", effective_status="ACTIVE", facebook_page_id="1001432206614811", facebook_post_id="1001432206614811_post1"),
        MetaAd(user_id=user.id, meta_ad_account_id="act_status_101", meta_ad_id="ad_act_2", name="Active 2", effective_status="ACTIVE", facebook_page_id="1001432206614811", facebook_post_id="1001432206614811_post2"),
        MetaAd(user_id=user.id, meta_ad_account_id="act_status_101", meta_ad_id="ad_act_3", name="Active 3", effective_status="ACTIVE", facebook_page_id="1001432206614811", facebook_post_id="1001432206614811_post3"),
        # 4 PAUSED ads
        MetaAd(user_id=user.id, meta_ad_account_id="act_status_101", meta_ad_id="ad_paused_1", name="Paused 1", effective_status="PAUSED", facebook_page_id="1001432206614811", facebook_post_id="1001432206614811_post4"),
        MetaAd(user_id=user.id, meta_ad_account_id="act_status_101", meta_ad_id="ad_paused_2", name="Paused 2", effective_status="PAUSED", facebook_page_id="1001432206614811", facebook_post_id="1001432206614811_post5"),
        MetaAd(user_id=user.id, meta_ad_account_id="act_status_101", meta_ad_id="ad_paused_3", name="Paused 3", effective_status="PAUSED", facebook_page_id="1001432206614811", facebook_post_id="1001432206614811_post6"),
        MetaAd(user_id=user.id, meta_ad_account_id="act_status_101", meta_ad_id="ad_paused_4", name="Paused 4", effective_status="PAUSED", facebook_page_id="1001432206614811", facebook_post_id="1001432206614811_post7"),
        # 2 ADSET_PAUSED ads
        MetaAd(user_id=user.id, meta_ad_account_id="act_status_101", meta_ad_id="ad_adset_paused_1", name="Adset Paused 1", effective_status="ADSET_PAUSED", facebook_page_id="1001432206614811", facebook_post_id="1001432206614811_post8"),
        MetaAd(user_id=user.id, meta_ad_account_id="act_status_101", meta_ad_id="ad_adset_paused_2", name="Adset Paused 2", effective_status="ADSET_PAUSED", facebook_page_id="1001432206614811", facebook_post_id="1001432206614811_post9"),
        # 1 CAMPAIGN_PAUSED ad
        MetaAd(user_id=user.id, meta_ad_account_id="act_status_101", meta_ad_id="ad_camp_paused_1", name="Campaign Paused 1", effective_status="CAMPAIGN_PAUSED", facebook_page_id="1001432206614811", facebook_post_id="1001432206614811_post10"),
    ]
    db_session.add_all(ads)
    db_session.commit()

    return user, ad_acct, sa, ads


def test_1_default_active_filter_processes_only_active_ads(db_session: Session):
    """
    TEST 1: Given 10 ads total (3 ACTIVE, 7 non-active),
    verify default status_filter="ACTIVE" processes ONLY the 3 ACTIVE ads.
    """
    user, ad_acct, sa, ads = setup_test_ads_fixture(db_session)

    mock_comments = [{"id": "c_act_1", "message": "Active ad comment"}]

    with patch.object(meta_service, "fetch_comments_for_facebook_post", return_value=(mock_comments, {"status_code": 200})) as mock_fetch:
        res = meta_service.sync_comments_for_meta_ads(
            db=db_session,
            user_id=user.id,
            meta_ad_account_id="act_status_101",
            status_filter="ACTIVE"
        )

        assert res["success"] is True
        assert res["ads_total"] == 10
        assert res["ads_matching_filter"] == 3
        assert res["ads_processed"] == 3
        assert res["posts_processed"] == 3
        assert res["status_filter"] == "ACTIVE"

        # Verify fetch_comments_for_facebook_post called exactly 3 times (once per ACTIVE post)
        assert mock_fetch.call_count == 3
        called_post_ids = [call_args.kwargs.get("post_id") or call_args[0][0] for call_args in mock_fetch.call_args_list]
        assert set(called_post_ids) == {
            "1001432206614811_post1",
            "1001432206614811_post2",
            "1001432206614811_post3"
        }


def test_2_no_graph_requests_for_non_active_ads(db_session: Session):
    """
    TEST 2: Verify that PAUSED, ADSET_PAUSED, CAMPAIGN_PAUSED ads
    do NOT trigger fetch_comments_for_facebook_post() when filter is ACTIVE.
    """
    user, ad_acct, sa, ads = setup_test_ads_fixture(db_session)

    with patch.object(meta_service, "fetch_comments_for_facebook_post") as mock_fetch:
        res = meta_service.sync_comments_for_meta_ads(
            db=db_session,
            user_id=user.id,
            meta_ad_account_id="act_status_101",
            status_filter="ACTIVE"
        )

        non_active_post_ids = {
            "1001432206614811_post4",
            "1001432206614811_post5",
            "1001432206614811_post6",
            "1001432206614811_post7",
            "1001432206614811_post8",
            "1001432206614811_post9",
            "1001432206614811_post10"
        }

        called_post_ids = {call_args.kwargs.get("post_id") or call_args[0][0] for call_args in mock_fetch.call_args_list}
        assert called_post_ids.isdisjoint(non_active_post_ids), "Non-active post IDs were triggered!"


def test_3_all_ads_mode_processes_all_ads(db_session: Session):
    """
    TEST 3: Verify status_filter="ALL" (or None) processes all 10 ads regardless of status.
    """
    user, ad_acct, sa, ads = setup_test_ads_fixture(db_session)

    mock_comments = [{"id": "c_all_1", "message": "Comment"}]

    with patch.object(meta_service, "fetch_comments_for_facebook_post", return_value=(mock_comments, {"status_code": 200})) as mock_fetch:
        res = meta_service.sync_comments_for_meta_ads(
            db=db_session,
            user_id=user.id,
            meta_ad_account_id="act_status_101",
            status_filter="ALL"
        )

        assert res["success"] is True
        assert res["ads_total"] == 10
        assert res["ads_matching_filter"] == 10
        assert res["ads_processed"] == 10
        assert res["posts_processed"] == 10
        assert res["status_filter"] == "ALL"
        assert mock_fetch.call_count == 10


def test_4_metrics_correctness(db_session: Session):
    """
    TEST 4: Verify metrics (ads_total, ads_matching_filter, ads_processed, status_filter).
    """
    user, ad_acct, sa, ads = setup_test_ads_fixture(db_session)

    res = meta_service.sync_comments_for_meta_ads(
        db=db_session,
        user_id=user.id,
        meta_ad_account_id="act_status_101",
        status_filter="ACTIVE"
    )

    assert res["ads_total"] == 10
    assert res["ads_matching_filter"] == 3
    assert res["ads_processed"] == 3
    assert res["status_filter"] == "ACTIVE"


def test_5_async_job_filter_propagation(client, db_session: Session):
    """
    TEST 5: Verify status_filter propagates through:
    API Endpoint -> Job Manager -> Background Task -> Service.
    """
    user, ad_acct, sa, ads = setup_test_ads_fixture(db_session)
    fastapi_app.dependency_overrides[get_current_user] = lambda: user

    from app.api.v1 import meta as meta_api_mod
    orig_bg = meta_api_mod.run_background_comment_sync

    mock_comments = [{"id": "c_async_act_1", "message": "Async active comment"}]

    with patch.object(meta_api_mod, "run_background_comment_sync", side_effect=lambda *args, **kwargs: orig_bg(*args, **{**kwargs, "db": db_session})):
        with patch.object(meta_service, "fetch_comments_for_facebook_post", return_value=(mock_comments, {"status_code": 200})):
            # 1. API Call with default status (or ?status=ACTIVE)
            res = client.post("/api/v1/meta/ad-accounts/act_status_101/comments/sync?status=ACTIVE")
            assert res.status_code == 202
            data = res.json()
            assert data["status_filter"] == "ACTIVE"
            assert data["ads_total"] == 10
            assert data["ads_matching_filter"] == 3
            job_id = data["job_id"]

            # Poll status until completed
            completed = False
            for _ in range(20):
                status_res = client.get(f"/api/v1/meta/ad-accounts/act_status_101/comments/sync/status/{job_id}")
                assert status_res.status_code == 200
                s_data = status_res.json()
                if s_data["status"] == "COMPLETED":
                    completed = True
                    assert s_data["status_filter"] == "ACTIVE"
                    assert s_data["ads_matching_filter"] == 3
                    assert s_data["comments_fetched"] == 3
                    break
                time.sleep(0.1)

            assert completed is True, f"Job failed to complete. Final status: {s_data}"


def test_6_strict_page_token_preserved_with_status_filter(db_session: Session):
    """
    TEST 6: Verify strict Page token matching rules remain completely intact when status_filter is active.
    - Page ID extracted from post ID
    - Match exact SocialAccount
    - No cross-page token fallback
    """
    user = User(email="strict_token_test@test.com", full_name="Strict User", hashed_password="pw", is_active=True, role="Editor")
    db_session.add(user)
    db_session.commit()

    # Unconnected page post
    ad_unconnected = MetaAd(
        user_id=user.id,
        meta_ad_account_id="act_strict_1",
        meta_ad_id="ad_unconn",
        name="Unconnected Ad",
        effective_status="ACTIVE",
        facebook_page_id="999888777666",
        facebook_post_id="999888777666_post123"
    )
    db_session.add(ad_unconnected)
    db_session.commit()

    with patch.object(meta_service, "fetch_comments_for_facebook_post") as mock_fetch:
        res = meta_service.sync_comments_for_meta_ads(
            db=db_session,
            user_id=user.id,
            meta_ad_account_id="act_strict_1",
            status_filter="ACTIVE"
        )

        assert res["success"] is True
        assert res["pages_not_connected"] == 1
        # Crucial: fetch_comments_for_facebook_post must NOT be called for unconnected page
        mock_fetch.assert_not_called()

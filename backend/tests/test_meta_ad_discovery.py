import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.social_account import SocialAccount
from app.models.meta_ad_account import MetaAdAccount
from app.models.meta_ad import MetaAd
from app.services.meta_service import meta_service
from app.repositories.meta_ad_account_repository import meta_ad_account_repo
from app.repositories.meta_ad_repository import meta_ad_repo
from app.core.security_encryption import encrypt_token
from app.api.v1.deps import get_current_user


@pytest.fixture
def ad_test_user(db_session: Session):
    user = User(
        email="ad_disc_user1@example.com",
        full_name="Ad Discovery User 1",
        hashed_password="hashed_pass_123",
        role="Editor",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def ad_test_user_2(db_session: Session):
    user = User(
        email="ad_disc_user2@example.com",
        full_name="Ad Discovery User 2",
        hashed_password="hashed_pass_456",
        role="Editor",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def user1_social_account(db_session: Session, ad_test_user: User):
    account = SocialAccount(
        user_id=ad_test_user.id,
        platform="facebook",
        account_id="109823471029481",
        account_name="User 1 Page",
        access_token=encrypt_token("EAABwz1XkREYBAIJlLUXdAZBfq_user1_token"),
        token_type="user_access_token",
        status="CONNECTED",
        metadata_json={
            "ads_read_granted": True,
            "granted_scopes": ["pages_show_list", "ads_read"],
            "user_access_token": encrypt_token("EAABwz1XkREYBAIJlLUXdAZBfq_user1_token")
        }
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


@pytest.fixture
def user1_ad_account(db_session: Session, ad_test_user: User):
    return meta_ad_account_repo.upsert(db_session, ad_test_user.id, {
        "id": "act_100200300",
        "name": "User 1 Primary Ad Account",
        "account_status": 1,
        "currency": "USD",
        "timezone_name": "America/New_York"
    })


@pytest.fixture
def user2_ad_account(db_session: Session, ad_test_user_2: User):
    return meta_ad_account_repo.upsert(db_session, ad_test_user_2.id, {
        "id": "act_999888777",
        "name": "User 2 Private Ad Account",
        "account_status": 1,
        "currency": "EUR",
        "timezone_name": "Europe/London"
    })


# 1. Ads sync requires authentication
def test_ads_sync_requires_authentication(client: TestClient):
    res = client.post("/api/v1/meta/ad-accounts/act_100200300/ads/sync")
    assert res.status_code == 401


# 2. User A cannot sync User B's Ad Account (Tenant Isolation)
def test_user_cannot_sync_another_users_ad_account(
    client: TestClient,
    db_session: Session,
    ad_test_user: User,
    user2_ad_account: MetaAdAccount
):
    from app.main import app
    app.dependency_overrides[get_current_user] = lambda: ad_test_user
    try:
        res = client.post(f"/api/v1/meta/ad-accounts/{user2_ad_account.meta_ad_account_id}/ads/sync")
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower() or "denied" in res.json()["detail"].lower()
    finally:
        if get_current_user in app.dependency_overrides:
            del app.dependency_overrides[get_current_user]


# 3. User A cannot read User B's Ads (Tenant Isolation)
def test_user_cannot_read_another_users_ads(
    client: TestClient,
    db_session: Session,
    ad_test_user: User,
    user2_ad_account: MetaAdAccount
):
    from app.main import app
    app.dependency_overrides[get_current_user] = lambda: ad_test_user
    try:
        res = client.get(f"/api/v1/meta/ad-accounts/{user2_ad_account.meta_ad_account_id}/ads")
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower() or "denied" in res.json()["detail"].lower()
    finally:
        if get_current_user in app.dependency_overrides:
            del app.dependency_overrides[get_current_user]


# 4. Ads sync requires ads_read permission
def test_ads_sync_requires_ads_read_permission(
    client: TestClient,
    db_session: Session,
    ad_test_user: User,
    user1_ad_account: MetaAdAccount
):
    from app.main import app
    # Social account without ads_read
    no_ads_account = SocialAccount(
        user_id=ad_test_user.id,
        platform="facebook",
        account_id="109823471029482",
        account_name="No Ads Scope Page",
        access_token=encrypt_token("EAABwz1XkREYBAIJlLUXdAZBfq_no_ads"),
        token_type="user_access_token",
        status="CONNECTED",
        metadata_json={
            "ads_read_granted": False,
            "granted_scopes": ["pages_show_list"],
            "user_access_token": encrypt_token("EAABwz1XkREYBAIJlLUXdAZBfq_no_ads")
        }
    )
    db_session.add(no_ads_account)
    db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: ad_test_user
    try:
        res = client.post(f"/api/v1/meta/ad-accounts/{user1_ad_account.meta_ad_account_id}/ads/sync")
        assert res.status_code == 400
        assert "ads_read" in res.json()["detail"].lower() or "permission" in res.json()["detail"].lower()
    finally:
        if get_current_user in app.dependency_overrides:
            del app.dependency_overrides[get_current_user]


# 5. Fetch Ads constructs Graph API request correctly
def test_fetch_ads_constructs_graph_api_request():
    with patch("requests.get") as mock_get:
        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_res.json.return_value = {
            "data": [
                {
                    "id": "12020582928371",
                    "name": "Test Promo Ad",
                    "effective_status": "ACTIVE",
                    "creative": {
                        "id": "12020582928999",
                        "effective_object_story_id": "109823471029481_12020582928371"
                    }
                }
            ],
            "paging": {}
        }
        mock_get.return_value = mock_res

        ads = meta_service.fetch_ads_for_ad_account("EAABwz1XkREYBAIJlLUXdAZBfq_token", "act_100200300")
        assert len(ads) == 1
        assert ads[0]["id"] == "12020582928371"

        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert "act_100200300/ads" in args[0]
        assert "creative" in kwargs["params"]["fields"]


# 6. Pagination & cursor deduplication
def test_fetch_ads_pagination_and_cursor_deduplication():
    with patch("requests.get") as mock_get:
        page1 = MagicMock()
        page1.status_code = 200
        page1.json.return_value = {
            "data": [{"id": "ad_1", "name": "Ad 1"}],
            "paging": {
                "cursors": {"after": "cursor_ad_2"},
                "next": "https://graph.facebook.com/v19.0/act_100200300/ads?after=cursor_ad_2"
            }
        }

        page2 = MagicMock()
        page2.status_code = 200
        page2.json.return_value = {
            "data": [{"id": "ad_2", "name": "Ad 2"}],
            "paging": {
                "cursors": {"after": "cursor_ad_2"},  # Duplicate cursor
                "next": "https://graph.facebook.com/v19.0/act_100200300/ads?after=cursor_ad_2"
            }
        }

        mock_get.side_effect = [page1, page2]

        ads = meta_service.fetch_ads_for_ad_account("EAABwz1XkREYBAIJlLUXdAZBfq_token", "act_100200300")
        assert len(ads) == 2
        assert mock_get.call_count == 2


# 7. Ad Sync is idempotent and updates existing records
def test_ad_sync_is_idempotent(db_session: Session, ad_test_user: User, user1_ad_account: MetaAdAccount):
    ad_data = {
        "id": "12020582928371",
        "name": "Summer Ad Initial",
        "campaign": {"id": "c1", "name": "Camp 1"},
        "adset": {"id": "s1", "name": "Set 1"},
        "effective_status": "ACTIVE"
    }

    mapped_info = {
        "creative_id": "cr1",
        "facebook_page_id": "109823471029481",
        "facebook_post_id": "109823471029481_12020582928371",
        "engagement_object_type": "FACEBOOK_POST",
        "engagement_object_id": "109823471029481_12020582928371",
        "mapping_status": "MAPPED"
    }

    # First sync
    rec1 = meta_ad_repo.upsert(db_session, ad_test_user.id, user1_ad_account.meta_ad_account_id, ad_data, mapped_info)
    assert rec1.id is not None
    assert rec1.name == "Summer Ad Initial"

    # Second sync with updated name & status
    ad_data_updated = dict(ad_data)
    ad_data_updated["name"] = "Summer Ad Updated"
    ad_data_updated["effective_status"] = "PAUSED"

    rec2 = meta_ad_repo.upsert(db_session, ad_test_user.id, user1_ad_account.meta_ad_account_id, ad_data_updated, mapped_info)
    assert rec2.id == rec1.id
    assert rec2.name == "Summer Ad Updated"
    assert rec2.effective_status == "PAUSED"

    # Verify no duplicates in database
    ads_in_db = meta_ad_repo.get_by_ad_account(db_session, ad_test_user.id, user1_ad_account.meta_ad_account_id)
    assert len(ads_in_db) == 1


# 8. Engagement mapping: Facebook Post ID extraction
def test_extract_engagement_mapping_facebook_post():
    ad_payload = {
        "id": "ad_fb_1",
        "creative": {
            "id": "cr_fb_1",
            "effective_object_story_id": "109823471029481_12020582928371",
            "object_story_spec": {
                "page_id": "109823471029481"
            }
        }
    }

    mapping = meta_service.extract_engagement_mapping(ad_payload)
    assert mapping["creative_id"] == "cr_fb_1"
    assert mapping["facebook_page_id"] == "109823471029481"
    assert mapping["facebook_post_id"] == "109823471029481_12020582928371"
    assert mapping["engagement_object_type"] == "FACEBOOK_POST"
    assert mapping["engagement_object_id"] == "109823471029481_12020582928371"
    assert mapping["mapping_status"] == "MAPPED"


# 9. Engagement mapping: Instagram Media ID extraction
def test_extract_engagement_mapping_instagram_media():
    ad_payload = {
        "id": "ad_ig_1",
        "creative": {
            "id": "cr_ig_1",
            "object_story_spec": {
                "instagram_actor_id": "17841400928371",
                "video_data": {
                    "instagram_media_id": "17841400928999"
                }
            }
        }
    }

    mapping = meta_service.extract_engagement_mapping(ad_payload)
    assert mapping["creative_id"] == "cr_ig_1"
    assert mapping["instagram_account_id"] == "17841400928371"
    assert mapping["instagram_media_id"] == "17841400928999"
    assert mapping["engagement_object_type"] == "INSTAGRAM_MEDIA"
    assert mapping["engagement_object_id"] == "17841400928999"
    assert mapping["mapping_status"] == "MAPPED"


# 10. Engagement mapping: Both Facebook and Instagram
def test_extract_engagement_mapping_both_facebook_and_instagram():
    ad_payload = {
        "id": "ad_both_1",
        "creative": {
            "id": "cr_both_1",
            "effective_object_story_id": "109823471029481_12020582928371",
            "object_story_spec": {
                "page_id": "109823471029481",
                "instagram_actor_id": "17841400928371",
                "photo_data": {
                    "instagram_media_id": "17841400928999"
                }
            }
        }
    }

    mapping = meta_service.extract_engagement_mapping(ad_payload)
    assert mapping["creative_id"] == "cr_both_1"
    assert mapping["facebook_post_id"] == "109823471029481_12020582928371"
    assert mapping["instagram_media_id"] == "17841400928999"
    assert mapping["engagement_object_type"] == "BOTH"
    assert mapping["mapping_status"] == "MAPPED"


# 11. Engagement mapping: No engagement object
def test_extract_engagement_mapping_no_engagement_object():
    ad_payload = {
        "id": "ad_empty_1",
        "creative": {}
    }

    mapping = meta_service.extract_engagement_mapping(ad_payload)
    assert mapping["creative_id"] is None
    assert mapping["facebook_post_id"] is None
    assert mapping["instagram_media_id"] is None
    assert mapping["engagement_object_type"] == "UNKNOWN"
    assert mapping["mapping_status"] == "NOT_AVAILABLE"


# 12. Engagement mapping: Partial mapping
def test_extract_engagement_mapping_partial():
    ad_payload = {
        "id": "ad_part_1",
        "creative": {
            "id": "cr_part_1",
            "object_story_spec": {
                "page_id": "109823471029481"
            }
        }
    }

    mapping = meta_service.extract_engagement_mapping(ad_payload)
    assert mapping["creative_id"] == "cr_part_1"
    assert mapping["facebook_page_id"] == "109823471029481"
    assert mapping["facebook_post_id"] is None
    assert mapping["engagement_object_type"] == "UNKNOWN"
    assert mapping["mapping_status"] == "PARTIALLY_MAPPED"


# 13. No sensitive tokens in API responses
def test_no_sensitive_tokens_in_ad_sync_and_get_responses(
    client: TestClient,
    db_session: Session,
    ad_test_user: User,
    user1_social_account: SocialAccount,
    user1_ad_account: MetaAdAccount
):
    from app.main import app
    app.dependency_overrides[get_current_user] = lambda: ad_test_user

    mock_ads = [
        {
            "id": "12020582928371",
            "name": "Security Check Ad",
            "effective_status": "ACTIVE",
            "creative": {
                "id": "12020582928999",
                "effective_object_story_id": "109823471029481_12020582928371"
            }
        }
    ]

    with patch.object(meta_service, "fetch_ads_for_ad_account", return_value=mock_ads):
        try:
            res_sync = client.post(f"/api/v1/meta/ad-accounts/{user1_ad_account.meta_ad_account_id}/ads/sync")
            assert res_sync.status_code == 200

            res_get = client.get(f"/api/v1/meta/ad-accounts/{user1_ad_account.meta_ad_account_id}/ads")
            assert res_get.status_code == 200

            sync_json = str(res_sync.json())
            get_json = str(res_get.json())

            assert "EAABwz1XkREYBAIJlLUXdAZBfq" not in sync_json
            assert "user_access_token" not in sync_json
            assert "EAABwz1XkREYBAIJlLUXdAZBfq" not in get_json
            assert "user_access_token" not in get_json
        finally:
            if get_current_user in app.dependency_overrides:
                del app.dependency_overrides[get_current_user]


# 14. Ads fetch requests nested creative fields inline
def test_fetch_ads_nested_creative_fields():
    with patch("requests.get") as mock_get:
        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_res.json.return_value = {
            "data": [
                {
                    "id": "12020582928371",
                    "name": "Nested Creative Ad",
                    "creative": {
                        "id": "cr_123",
                        "name": "Creative 123",
                        "effective_object_story_id": "109823471029481_12020582928371"
                    }
                }
            ],
            "paging": {}
        }
        mock_get.return_value = mock_res

        ads = meta_service.fetch_ads_for_ad_account("EAABwz1XkREYBAIJlLUXdAZBfq_token", "act_100200300")
        assert len(ads) == 1

        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        requested_fields = kwargs["params"]["fields"]

        assert "creative{" in requested_fields
        assert "effective_object_story_id" in requested_fields
        assert "object_story_spec" in requested_fields
        assert "asset_feed_spec" in requested_fields


# 15. Fetch Creative separately requests lightweight creative fields (no asset_feed_spec)
def test_fetch_creative_separately_lightweight_fields():
    with patch("requests.get") as mock_get:
        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_res.json.return_value = {
            "id": "cr_123",
            "name": "Standalone Creative",
            "effective_object_story_id": "109823471029481_999888777",
            "object_story_spec": {"page_id": "109823471029481"}
        }
        mock_get.return_value = mock_res

        creative_data = meta_service.fetch_creative("EAABwz1XkREYBAIJlLUXdAZBfq_token", "cr_123")
        assert creative_data is not None
        assert creative_data["id"] == "cr_123"

        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert "cr_123" in args[0]
        requested_fields = kwargs["params"]["fields"]
        assert "effective_object_story_id" in requested_fields
        assert "object_story_spec" in requested_fields
        assert "asset_feed_spec" not in requested_fields


# 16. Instagram Actor ID alone results in PARTIALLY_MAPPED (not MAPPED)
def test_instagram_actor_alone_is_partially_mapped():
    ad_data = {"id": "ad_ig_actor", "creative": {"id": "cr_ig_actor"}}
    creative_data = {
        "id": "cr_ig_actor",
        "object_story_spec": {
            "instagram_actor_id": "17841400928371"
            # No instagram_media_id, no video_data, no photo_data!
        }
    }

    mapping = meta_service.extract_engagement_mapping(ad_data, creative_data=creative_data)
    assert mapping["creative_id"] == "cr_ig_actor"
    assert mapping["instagram_account_id"] == "17841400928371"
    assert mapping["instagram_media_id"] is None
    assert mapping["mapping_status"] == "PARTIALLY_MAPPED"
    assert mapping["mapping_status"] != "MAPPED"


# 17. Single creative fetch failure does not abort full ad sync
def test_single_creative_failure_does_not_abort_ad_sync(
    client: TestClient,
    db_session: Session,
    ad_test_user: User,
    user1_social_account: SocialAccount,
    user1_ad_account: MetaAdAccount
):
    from app.main import app
    app.dependency_overrides[get_current_user] = lambda: ad_test_user

    mock_ads = [
        {"id": "ad_1", "name": "Ad 1", "creative": {"id": "cr_1"}},
        {"id": "ad_2", "name": "Ad 2", "creative": {"id": "cr_2"}}
    ]

    def mock_fetch_creative(token, c_id):
        if c_id == "cr_1":
            return {"id": "cr_1", "effective_object_story_id": "109823471029481_1111"}
        # cr_2 fails!
        return None

    with patch.object(meta_service, "fetch_ads_for_ad_account", return_value=mock_ads), \
         patch.object(meta_service, "fetch_creative", side_effect=mock_fetch_creative):
        try:
            res = client.post(f"/api/v1/meta/ad-accounts/{user1_ad_account.meta_ad_account_id}/ads/sync")
            assert res.status_code == 200
            data = res.json()

            assert data["success"] is True
            assert data["synced_count"] == 2
            assert data["mapped_count"] == 1
            assert data["unmapped_count"] == 1

            ads = data["ads"]
            ad1_rec = next(a for a in ads if a["meta_ad_id"] == "ad_1")
            ad2_rec = next(a for a in ads if a["meta_ad_id"] == "ad_2")

            assert ad1_rec["mapping_status"] == "MAPPED"
            assert ad2_rec["mapping_status"] == "ERROR"
        finally:
            if get_current_user in app.dependency_overrides:
                del app.dependency_overrides[get_current_user]


# 18. Main Ads request failure cleanly fails the sync
def test_main_ads_request_failure_fails_sync(
    client: TestClient,
    db_session: Session,
    ad_test_user: User,
    user1_social_account: SocialAccount,
    user1_ad_account: MetaAdAccount
):
    from app.main import app
    app.dependency_overrides[get_current_user] = lambda: ad_test_user

    with patch.object(meta_service, "fetch_ads_for_ad_account", side_effect=Exception("Meta Graph API error (code 1): Please reduce data")):
        try:
            res = client.post(f"/api/v1/meta/ad-accounts/{user1_ad_account.meta_ad_account_id}/ads/sync")
            assert res.status_code == 400
            assert "reduce data" in res.json()["detail"].lower() or "meta api error" in res.json()["detail"].lower()
        finally:
            if get_current_user in app.dependency_overrides:
                del app.dependency_overrides[get_current_user]


# 19. Creative Deduplication & Batch Enrichment Test
def test_creative_deduplication_and_batch_enrichment(
    client: TestClient,
    db_session: Session,
    ad_test_user: User,
    user1_social_account: SocialAccount,
    user1_ad_account: MetaAdAccount
):
    from app.main import app
    app.dependency_overrides[get_current_user] = lambda: ad_test_user

    # 10 Ads sharing 2 unique creatives (cr_1 and cr_2)
    mock_ads = [
        {"id": f"ad_{i}", "name": f"Ad {i}", "creative": {"id": "cr_1" if i % 2 == 0 else "cr_2"}}
        for i in range(10)
    ]

    mock_creative_cache = {
        "cr_1": {"id": "cr_1", "effective_object_story_id": "109823471029481_1111"},
        "cr_2": {"id": "cr_2", "effective_object_story_id": "109823471029481_2222"}
    }

    with patch.object(meta_service, "fetch_ads_for_ad_account", return_value=mock_ads), \
         patch.object(meta_service, "fetch_creatives_batch", return_value=mock_creative_cache) as mock_batch:
        try:
            res = client.post(f"/api/v1/meta/ad-accounts/{user1_ad_account.meta_ad_account_id}/ads/sync")
            assert res.status_code == 200
            data = res.json()

            assert data["success"] is True
            assert data["ads_fetched"] == 10
            assert data["ads_synced"] == 10
            assert data["unique_creatives"] == 2
            assert data["creatives_enriched"] == 2
            assert data["creative_fetch_failures"] == 0

            mapping_summary = data["mapping_summary"]
            assert mapping_summary["mapped"] == 10
            assert mapping_summary["error"] == 0

            # Verify batch fetcher was called once with deduplicated creative IDs
            mock_batch.assert_called_once()
            args, kwargs = mock_batch.call_args
            passed_ids = args[1]
            assert set(passed_ids) == {"cr_1", "cr_2"}
            assert len(passed_ids) == 2
        finally:
            if get_current_user in app.dependency_overrides:
                del app.dependency_overrides[get_current_user]


# 20. Bulk DB persistence idempotency test
def test_bulk_db_persistence_idempotency(db_session: Session, ad_test_user: User):
    from app.repositories.meta_ad_repository import meta_ad_repo

    mock_ads = [
        {"id": f"ad_idempotent_{i}", "name": f"Ad {i}", "creative": {"id": "cr_100"}}
        for i in range(5)
    ]
    mappings_map = {
        f"ad_idempotent_{i}": {"creative_id": "cr_100", "mapping_status": "NOT_AVAILABLE"}
        for i in range(5)
    }

    # First sync
    res1 = meta_ad_repo.sync_ads_for_user(db_session, ad_test_user.id, "act_100200300", mock_ads, mappings_map)
    assert len(res1) == 5

    # Second sync (same ads)
    res2 = meta_ad_repo.sync_ads_for_user(db_session, ad_test_user.id, "act_100200300", mock_ads, mappings_map)
    assert len(res2) == 5

    # Check total records in DB for this account & user (must still be 5, no duplicates)
    all_db_ads = meta_ad_repo.get_by_ad_account(db_session, ad_test_user.id, "act_100200300")
    assert len(all_db_ads) == 5


# 21. Inline creative data prevents fallback API calls
def test_inline_creative_prevents_fallback_api_call():
    inline_ads = [
        {
            "id": f"inline_ad_{i}",
            "name": f"Inline Ad {i}",
            "creative": {
                "id": f"inline_cr_{i}",
                "effective_object_story_id": f"109823471029481_{i}"
            }
        }
        for i in range(5)
    ]

    with patch.object(meta_service, "fetch_creatives_batch") as mock_batch:
        result = meta_service.process_creative_enrichment("token", inline_ads)
        metrics = result["metrics"]

        assert metrics["ads_fetched"] == 5
        assert metrics["inline_creatives_resolved"] == 5
        assert metrics["creatives_requiring_fallback"] == 0
        assert metrics["creative_cache_hits"] == 0
        mock_batch.assert_not_called()


# 22. Hybrid inline resolution with fallback for missing creative data
def test_mixed_inline_and_fallback_creatives():
    mixed_ads = [
        # 3 ads with inline creative data
        {"id": "ad_in_1", "creative": {"id": "cr_in_1", "effective_object_story_id": "109823471029481_101"}},
        {"id": "ad_in_2", "creative": {"id": "cr_in_2", "effective_object_story_id": "109823471029481_102"}},
        {"id": "ad_in_3", "creative": {"id": "cr_in_3", "effective_object_story_id": "109823471029481_103"}},
        # 2 ads missing inline data (only basic id)
        {"id": "ad_missing_1", "creative": {"id": "cr_miss_1"}},
        {"id": "ad_missing_2", "creative": {"id": "cr_miss_2"}}
    ]

    fallback_return = {
        "cr_miss_1": {"id": "cr_miss_1", "effective_object_story_id": "109823471029481_201"},
        "cr_miss_2": {"id": "cr_miss_2", "effective_object_story_id": "109823471029481_202"}
    }

    with patch.object(meta_service, "fetch_creatives_batch", return_value=fallback_return) as mock_batch:
        result = meta_service.process_creative_enrichment("token", mixed_ads)
        metrics = result["metrics"]

        assert metrics["ads_fetched"] == 5
        assert metrics["inline_creatives_resolved"] == 3
        assert metrics["creatives_requiring_fallback"] == 2
        assert metrics["fallback_creatives_enriched"] == 2

        mock_batch.assert_called_once()
        args, kwargs = mock_batch.call_args
        requested_ids = args[1]
        assert set(requested_ids) == {"cr_miss_1", "cr_miss_2"}


# 23. DB Cache Hit prevents API fallback for existing mapped ads
def test_db_creative_cache_hit_prevents_api_fallback(db_session: Session, ad_test_user: User):
    # Create existing mapped DB record
    ad_data = {"id": "ad_db_1", "name": "DB Cached Ad", "creative": {"id": "cr_db_1"}}
    mapped_info = {
        "creative_id": "cr_db_1",
        "facebook_page_id": "109823471029481",
        "facebook_post_id": "109823471029481_9999",
        "engagement_object_type": "FACEBOOK_POST",
        "engagement_object_id": "109823471029481_9999",
        "mapping_status": "MAPPED"
    }
    meta_ad_repo.upsert(db_session, ad_test_user.id, "act_100200300", ad_data, mapped_info)

    existing_ads = meta_ad_repo.get_by_ad_account(db_session, ad_test_user.id, "act_100200300")

    # Incoming ad has missing inline data (only id)
    new_incoming_ads = [{"id": "ad_db_1", "name": "DB Cached Ad", "creative": {"id": "cr_db_1"}}]

    with patch.object(meta_service, "fetch_creatives_batch") as mock_batch:
        result = meta_service.process_creative_enrichment("token", new_incoming_ads, existing_ads=existing_ads)
        metrics = result["metrics"]

        assert metrics["ads_fetched"] == 1
        assert metrics["inline_creatives_resolved"] == 0
        assert metrics["creative_cache_hits"] == 1
        assert metrics["creatives_requiring_fallback"] == 0
        mock_batch.assert_not_called()


# 24. Observability metrics returned in sync API response
def test_observability_metrics_in_sync_response(
    client: TestClient,
    db_session: Session,
    ad_test_user: User,
    user1_social_account: SocialAccount,
    user1_ad_account: MetaAdAccount
):
    from app.main import app
    app.dependency_overrides[get_current_user] = lambda: ad_test_user

    mock_ads = [
        {
            "id": "ad_obs_1",
            "name": "Obs Ad 1",
            "creative": {
                "id": "cr_obs_1",
                "effective_object_story_id": "109823471029481_8888"
            }
        }
    ]

    with patch.object(meta_service, "fetch_ads_for_ad_account", return_value=mock_ads):
        try:
            res = client.post(f"/api/v1/meta/ad-accounts/{user1_ad_account.meta_ad_account_id}/ads/sync")
            assert res.status_code == 200
            data = res.json()

            assert data["success"] is True
            assert data["ads_fetched"] == 1
            assert data["inline_creatives_resolved"] == 1
            assert data["creatives_requiring_fallback"] == 0
            assert data["creative_cache_hits"] == 0
        finally:
            if get_current_user in app.dependency_overrides:
                del app.dependency_overrides[get_current_user]



import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.social_account import SocialAccount
from app.models.meta_ad_account import MetaAdAccount
from app.services.meta_service import meta_service
from app.repositories.meta_ad_account_repository import meta_ad_account_repo
from app.core.security_encryption import encrypt_token
from app.api.v1.deps import get_current_user


# Mock dependencies for authenticated test user
@pytest.fixture
def test_user(db_session: Session):
    user = User(
        email="ads_user@example.com",
        full_name="Ads Test User",
        hashed_password="hashed_pass_123",
        role="Editor",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_user_2(db_session: Session):
    user = User(
        email="other_user@example.com",
        full_name="Other Test User",
        hashed_password="hashed_pass_456",
        role="Editor",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def connected_account_with_ads(db_session: Session, test_user: User):
    account = SocialAccount(
        user_id=test_user.id,
        platform="facebook",
        account_id="109823471029481",
        account_name="Test FB Page",
        access_token=encrypt_token("EAABwz1XkREYBAIJlLUXdAZBfq_user_token"),
        token_type="user_access_token",
        status="CONNECTED",
        metadata_json={
            "ads_read_granted": True,
            "granted_scopes": ["pages_show_list", "ads_read"],
            "user_access_token": encrypt_token("EAABwz1XkREYBAIJlLUXdAZBfq_user_token")
        }
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


@pytest.fixture
def connected_account_without_ads(db_session: Session, test_user: User):
    account = SocialAccount(
        user_id=test_user.id,
        platform="facebook",
        account_id="109823471029482",
        account_name="Test FB Page No Ads",
        access_token=encrypt_token("EAABwz1XkREYBAIJlLUXdAZBfq_no_ads_token"),
        token_type="user_access_token",
        status="CONNECTED",
        metadata_json={
            "ads_read_granted": False,
            "granted_scopes": ["pages_show_list"],
            "user_access_token": encrypt_token("EAABwz1XkREYBAIJlLUXdAZBfq_no_ads_token")
        }
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


# 1. Test fetch_ad_accounts constructs Meta Graph API request correctly
def test_fetch_ad_accounts_constructs_graph_api_request():
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "id": "act_109823471029",
                    "name": "Primary Ad Account",
                    "account_status": 1,
                    "currency": "USD",
                    "timezone_name": "America/Los_Angeles"
                }
            ],
            "paging": {}
        }
        mock_get.return_value = mock_response

        res = meta_service.fetch_ad_accounts("EAABwz1XkREYBAIJlLUXdAZBfq_test_token")

        assert len(res) == 1
        assert res[0]["id"] == "act_109823471029"
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert "me/adaccounts" in args[0]
        assert kwargs["params"]["fields"] == "id,name,account_status,currency,timezone_name"


# 2. Test multi-page cursor pagination handling and deduplication
def test_fetch_ad_accounts_pagination_and_cursor_deduplication():
    with patch("requests.get") as mock_get:
        page1 = MagicMock()
        page1.status_code = 200
        page1.json.return_value = {
            "data": [{"id": "act_1", "name": "Ad Account 1", "account_status": 1}],
            "paging": {
                "cursors": {"after": "cursor_page_2"},
                "next": "https://graph.facebook.com/v19.0/me/adaccounts?after=cursor_page_2"
            }
        }

        page2 = MagicMock()
        page2.status_code = 200
        page2.json.return_value = {
            "data": [{"id": "act_2", "name": "Ad Account 2", "account_status": 1}],
            "paging": {
                "cursors": {"after": "cursor_page_2"},  # Duplicate cursor -> should break pagination
                "next": "https://graph.facebook.com/v19.0/me/adaccounts?after=cursor_page_2"
            }
        }

        mock_get.side_effect = [page1, page2]

        res = meta_service.fetch_ad_accounts("EAABwz1XkREYBAIJlLUXdAZBfq_test_token")

        assert len(res) == 2
        assert res[0]["id"] == "act_1"
        assert res[1]["id"] == "act_2"
        # Must halt after page 2 due to duplicate cursor protection
        assert mock_get.call_count == 2


# 3. Test sync_meta_ad_accounts endpoint blocks when ads_read permission is missing
def test_sync_ad_accounts_fails_if_ads_read_missing(client: TestClient, db_session: Session, test_user: User, connected_account_without_ads: SocialAccount):
    from app.main import app
    app.dependency_overrides[get_current_user] = lambda: test_user

    try:
        res = client.post("/api/v1/meta/ad-accounts/sync")
        assert res.status_code == 400
        assert "ads_read" in res.json()["detail"].lower() or "permission" in res.json()["detail"].lower()
    finally:
        if get_current_user in app.dependency_overrides:
            del app.dependency_overrides[get_current_user]


# 4. Test sync_meta_ad_accounts endpoint succeeds when ads_read permission is granted
def test_sync_ad_accounts_success(client: TestClient, db_session: Session, test_user: User, connected_account_with_ads: SocialAccount):
    from app.main import app
    app.dependency_overrides[get_current_user] = lambda: test_user

    mock_ad_data = [
        {
            "id": "act_100200300",
            "name": "Growth Ad Account",
            "account_status": 1,
            "currency": "USD",
            "timezone_name": "UTC"
        }
    ]

    with patch.object(meta_service, "fetch_ad_accounts", return_value=mock_ad_data):
        try:
            res = client.post("/api/v1/meta/ad-accounts/sync")
            assert res.status_code == 200
            data = res.json()
            assert data["success"] is True
            assert data["synced_count"] == 1
            assert data["accounts"][0]["meta_ad_account_id"] == "act_100200300"
            assert data["accounts"][0]["status_label"] == "ACTIVE"
        finally:
            if get_current_user in app.dependency_overrides:
                del app.dependency_overrides[get_current_user]


# 5. Test database upsert updates existing ad account and does not duplicate
def test_repository_upsert_behavior(db_session: Session, test_user: User):
    ad1 = {
        "id": "act_555666",
        "name": "Initial Name",
        "account_status": 1,
        "currency": "USD",
        "timezone_name": "America/New_York"
    }

    acc1 = meta_ad_account_repo.upsert(db_session, test_user.id, ad1)
    assert acc1.id is not None
    assert acc1.name == "Initial Name"
    assert acc1.account_status == 1

    # Upsert again with updated name & status
    ad1_updated = {
        "id": "act_555666",
        "name": "Updated Name",
        "account_status": 2,
        "currency": "USD",
        "timezone_name": "America/New_York"
    }

    acc1_updated = meta_ad_account_repo.upsert(db_session, test_user.id, ad1_updated)
    assert acc1_updated.id == acc1.id
    assert acc1_updated.name == "Updated Name"
    assert acc1_updated.account_status == 2

    # Verify total count in DB for user is still 1
    stored = meta_ad_account_repo.get_by_user(db_session, test_user.id)
    assert len(stored) == 1


# 6. Test strict tenant user isolation for GET /meta/ad-accounts
def test_get_ad_accounts_tenant_isolation(client: TestClient, db_session: Session, test_user: User, test_user_2: User):
    from app.main import app

    # Add Ad Account for User 1
    meta_ad_account_repo.upsert(db_session, test_user.id, {
        "id": "act_user_1",
        "name": "User 1 Account",
        "account_status": 1
    })

    # Add Ad Account for User 2
    meta_ad_account_repo.upsert(db_session, test_user_2.id, {
        "id": "act_user_2",
        "name": "User 2 Account",
        "account_status": 1
    })

    # Fetch as User 1
    app.dependency_overrides[get_current_user] = lambda: test_user
    try:
        res1 = client.get("/api/v1/meta/ad-accounts")
        assert res1.status_code == 200
        data1 = res1.json()
        assert len(data1) == 1
        assert data1[0]["meta_ad_account_id"] == "act_user_1"
    finally:
        if get_current_user in app.dependency_overrides:
            del app.dependency_overrides[get_current_user]

    # Fetch as User 2
    app.dependency_overrides[get_current_user] = lambda: test_user_2
    try:
        res2 = client.get("/api/v1/meta/ad-accounts")
        assert res2.status_code == 200
        data2 = res2.json()
        assert len(data2) == 1
        assert data2[0]["meta_ad_account_id"] == "act_user_2"
    finally:
        if get_current_user in app.dependency_overrides:
            del app.dependency_overrides[get_current_user]


# 7. Test no sensitive access tokens exposed in API response
def test_no_sensitive_tokens_in_response(client: TestClient, db_session: Session, test_user: User, connected_account_with_ads: SocialAccount):
    from app.main import app
    app.dependency_overrides[get_current_user] = lambda: test_user

    mock_ad_data = [
        {
            "id": "act_777888",
            "name": "Security Check Account",
            "account_status": 1,
            "currency": "EUR"
        }
    ]

    with patch.object(meta_service, "fetch_ad_accounts", return_value=mock_ad_data):
        try:
            res_sync = client.post("/api/v1/meta/ad-accounts/sync")
            res_get = client.get("/api/v1/meta/ad-accounts")

            sync_str = str(res_sync.json())
            get_str = str(res_get.json())

            assert "EAABwz1XkREYBAIJlLUXdAZBfq" not in sync_str
            assert "user_access_token" not in sync_str
            assert "EAABwz1XkREYBAIJlLUXdAZBfq" not in get_str
            assert "user_access_token" not in get_str
        finally:
            if get_current_user in app.dependency_overrides:
                del app.dependency_overrides[get_current_user]

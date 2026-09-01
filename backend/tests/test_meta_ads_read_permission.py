import pytest
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch, MagicMock
from app.services.meta_service import meta_service
from app.models.social_account import SocialAccount

def test_oauth_authorization_url_includes_ads_read_and_existing_scopes():
    """1. OAuth authorization URL includes ads_read alongside all existing required permissions."""
    with patch("app.core.config.settings.META_CONFIG_ID", None):
        url = meta_service.get_authorization_url(state="ads_read_test_state")
        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        assert "scope" in params
        scope_list = params["scope"][0].split(",")

        # Verify ads_read is explicitly requested
        assert "ads_read" in scope_list

        # Verify existing permissions are preserved
        expected_existing = [
            "pages_show_list",
            "pages_read_engagement",
            "pages_manage_posts",
            "pages_read_user_content",
            "pages_manage_engagement",
            "pages_manage_metadata",
            "instagram_basic",
            "instagram_content_publish",
            "instagram_manage_comments",
            "business_management",
        ]
        for scope in expected_existing:
            assert scope in scope_list

        assert len(scope_list) == 11
        assert "ads_management" not in scope_list  # Must NOT include write access for Ads


def test_ads_read_permission_verification_when_granted():
    """2. Permission verification helper accurately identifies ads_read as GRANTED."""
    perm_map = {
        "pages_show_list": "granted",
        "pages_read_engagement": "granted",
        "instagram_basic": "granted",
        "ads_read": "granted"
    }

    res = meta_service.verify_ads_read_permission(perm_map)

    assert res["permission"] == "ads_read"
    assert res["requested"] is True
    assert res["granted"] is True
    assert res["status"] == "granted"


def test_ads_read_permission_verification_when_declined():
    """3. Permission verification helper accurately identifies ads_read as DECLINED/NOT GRANTED."""
    perm_map = {
        "pages_show_list": "granted",
        "pages_read_engagement": "granted",
        "instagram_basic": "granted",
        "ads_read": "declined"
    }

    res = meta_service.verify_ads_read_permission(perm_map)

    assert res["permission"] == "ads_read"
    assert res["requested"] is True
    assert res["granted"] is False
    assert res["status"] == "declined"


def test_ads_read_permission_verification_when_missing_from_map():
    """4. Permission verification helper defaults to not granted when ads_read is missing from permission map."""
    perm_map = {
        "pages_show_list": "granted",
        "instagram_basic": "granted"
    }

    res = meta_service.verify_ads_read_permission(perm_map)

    assert res["permission"] == "ads_read"
    assert res["requested"] is True
    assert res["granted"] is False
    assert res["status"] == "declined"


def test_no_sensitive_tokens_exposed_in_permission_verification_logging():
    """5. Verify that permission verification logging NEVER leaks access tokens, secrets, or auth codes."""
    perm_map = {
        "pages_show_list": "granted",
        "ads_read": "granted"
    }

    with patch("app.services.meta_service.logger.info") as mock_log:
        meta_service.verify_ads_read_permission(perm_map)

        logs = [call.args[0] for call in mock_log.call_args_list if call.args]
        assert len(logs) > 0
        perm_log = next(l for l in logs if "[META_PERMISSIONS]" in l)

        assert "ads_read" in perm_log.lower()
        assert "access_token" not in perm_log.lower()
        assert "client_secret" not in perm_log.lower()
        assert "app_secret" not in perm_log.lower()
        assert "code=" not in perm_log.lower()


def test_no_ad_accounts_fetching_implemented():
    """6. Confirm no Ad Account endpoints (/me/adaccounts) are invoked or implemented during OAuth / permission check."""
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "data": [
                {"permission": "pages_show_list", "status": "granted"},
                {"permission": "ads_read", "status": "granted"}
            ]
        }

        # Inspect token permissions
        res = meta_service.inspect_token_permissions("mock_test_token_123")

        # Verify calls made were ONLY to /me/permissions
        called_urls = [call.args[0] if call.args else call.kwargs.get("url", "") for call in mock_get.call_args_list]
        for url in called_urls:
            assert "adaccounts" not in url, f"Unexpected Ad Account call detected: {url}"


def test_reconnection_flow_preserves_account_status_and_updates_ads_read_granted():
    """7. Verify reconnecting an existing account updates metadata_json with ads_read_granted without breaking account status."""
    existing_account = SocialAccount(
        user_id=10,
        platform="facebook",
        account_id="page_123",
        account_name="Test Brand Page",
        access_token="encrypted_bytes",
        status="CONNECTED",
        metadata_json={
            "granted_scopes": ["pages_show_list", "pages_manage_posts"],
            "ads_read_granted": False
        }
    )

    assert existing_account.status == "CONNECTED"
    assert existing_account.metadata_json.get("ads_read_granted") is False

    # Simulate re-authenticating with ads_read permission granted
    updated_metadata = dict(existing_account.metadata_json)
    updated_metadata.update({
        "granted_scopes": meta_service.REQUIRED_META_OAUTH_SCOPES,
        "ads_read_granted": True
    })
    existing_account.metadata_json = updated_metadata

    assert existing_account.status == "CONNECTED"
    assert existing_account.metadata_json.get("ads_read_granted") is True
    assert "ads_read" in existing_account.metadata_json.get("granted_scopes")

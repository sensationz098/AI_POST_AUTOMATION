import pytest
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch, MagicMock
from app.services.meta_service import meta_service
from app.models.social_account import SocialAccount

def test_meta_oauth_authorization_url_contains_all_scopes():
    """Verify Meta OAuth authorization URL contains all existing and new comment scopes."""
    with patch("app.core.config.settings.META_CONFIG_ID", None):
        url = meta_service.get_authorization_url(state="test_state_token_123")
        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        assert "scope" in params
        scope_str = params["scope"][0]
        scopes = scope_str.split(",")

    # 1. Existing publishing permissions preserved
    existing_scopes = [
        "pages_show_list",
        "pages_read_engagement",
        "pages_manage_posts",
        "instagram_basic",
        "instagram_content_publish",
        "business_management"
    ]
    for s in existing_scopes:
        assert s in scopes, f"Existing scope '{s}' missing from OAuth URL"

    # 2. New comment automation permissions present
    new_comment_scopes = [
        "instagram_manage_comments",
        "pages_read_user_content",
        "pages_manage_engagement",
        "pages_manage_metadata"
    ]
    for s in new_comment_scopes:
        assert s in scopes, f"New comment scope '{s}' missing from OAuth URL"

    # Total expected scope count
    assert len(scopes) == 10

def test_oauth_authorization_url_logging_does_not_leak_secrets():
    """Verify OAuth authorization URL generation logs scope names but NEVER logs secrets or tokens."""
    with patch("app.services.meta_service.logger.info") as mock_log_info:
        meta_service.get_authorization_url(state="secure_state_456")

        logs = [call.args[0] for call in mock_log_info.call_args_list]
        assert len(logs) > 0
        oauth_log = next(log for log in logs if "[META_OAUTH]" in log)

        # Confirm scope names logged
        assert "instagram_manage_comments" in oauth_log
        assert "pages_read_user_content" in oauth_log

        # Confirm sensitive fields are NOT in log
        assert "access_token" not in oauth_log.lower()
        assert "client_secret" not in oauth_log.lower()
        assert "app_secret" not in oauth_log.lower()

def test_existing_accounts_reconnection_identification():
    """Verify existing connected accounts prior to scope update are marked as requiring reconnection safely."""
    # Existing legacy account with empty metadata
    legacy_account = SocialAccount(
        user_id=1,
        platform="facebook",
        account_id="123456",
        account_name="Legacy FB Page",
        access_token="encrypted_token_bytes",
        status="CONNECTED",
        metadata_json={}
    )

    assert legacy_account.requires_reconnection_for_comment_automation is True
    assert legacy_account.status == "CONNECTED"  # Connection status is NOT invalidated or broken

    # Account connected after scope expansion
    updated_account = SocialAccount(
        user_id=1,
        platform="instagram",
        account_id="789012",
        account_name="@new_ig_brand",
        access_token="encrypted_token_bytes",
        status="CONNECTED",
        metadata_json={
            "granted_scopes": meta_service.REQUIRED_META_OAUTH_SCOPES,
            "comment_automation_ready": True
        }
    )

    assert updated_account.requires_reconnection_for_comment_automation is False
    assert updated_account.status == "CONNECTED"

def test_check_comment_automation_reconnection_needed_helper():
    """Verify service helper accurately identifies missing scopes for existing vs upgraded metadata."""
    legacy_meta = {}
    legacy_res = meta_service.check_comment_automation_reconnection_needed(legacy_meta)
    assert legacy_res["reconnection_required"] is True
    assert legacy_res["comment_automation_ready"] is False
    assert len(legacy_res["missing_scopes"]) == 4

    upgraded_meta = {
        "granted_scopes": meta_service.REQUIRED_META_OAUTH_SCOPES,
        "comment_automation_ready": True
    }
    upgraded_res = meta_service.check_comment_automation_reconnection_needed(upgraded_meta)
    assert upgraded_res["reconnection_required"] is False
    assert upgraded_res["comment_automation_ready"] is True
    assert len(upgraded_res["missing_scopes"]) == 0

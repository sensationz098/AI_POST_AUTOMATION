import pytest
import logging
from unittest.mock import patch, MagicMock
from app.services.meta_service import meta_service
from app.models.meta_ad import MetaAd
from app.models.social_account import SocialAccount
from app.repositories.social_account_repository import social_account_repo

def test_meta_oauth_scopes_include_pages_read_user_content():
    """Verify that pages_read_user_content is included in REQUIRED_META_OAUTH_SCOPES."""
    assert "pages_read_user_content" in meta_service.REQUIRED_META_OAUTH_SCOPES
    assert "pages_show_list" in meta_service.REQUIRED_META_OAUTH_SCOPES
    assert "pages_read_engagement" in meta_service.REQUIRED_META_OAUTH_SCOPES
    assert "pages_manage_posts" in meta_service.REQUIRED_META_OAUTH_SCOPES
    assert "pages_manage_engagement" in meta_service.REQUIRED_META_OAUTH_SCOPES
    assert "ads_read" in meta_service.REQUIRED_META_OAUTH_SCOPES


def test_get_authorization_url_includes_pages_read_user_content():
    """Verify the generated Meta OAuth authorization URL explicitly contains pages_read_user_content in scope query param."""
    auth_url = meta_service.get_authorization_url(state="test_state_123")
    assert "pages_read_user_content" in auth_url
    assert "response_type=code" in auth_url
    assert "state=test_state_123" in auth_url


def test_fetch_comments_handles_permission_error_code_10(caplog):
    """Verify fetch_comments_for_facebook_post detects permission error code 10 correctly."""
    mock_error_resp = MagicMock()
    mock_error_resp.status_code = 400
    mock_error_resp.headers = {"content-type": "application/json"}
    mock_error_resp.json.return_value = {
        "error": {
            "message": "(#10) This endpoint requires the 'pages_read_user_content' permission or the 'Page Public Content Access' feature.",
            "type": "OAuthException",
            "code": 10,
            "fbtrace_id": "A1B2C3D4E5"
        }
    }

    SECRET_TOKEN = "EAAB123456789SECRETTOKEN_DO_NOT_LOG"

    with patch("requests.get", return_value=mock_error_resp):
        with caplog.at_level(logging.WARNING):
            comments, details = meta_service.fetch_comments_for_facebook_post(
                post_id="post_123_456",
                access_token=SECRET_TOKEN,
                page_id="page_789",
                return_details=True
            )

    assert comments == []
    assert details["is_permission_error"] is True
    assert details["missing_permission"] == "pages_read_user_content"
    assert details["error_code"] == 10
    assert details["status_code"] == 400

    # Ensure secret token value is NEVER logged in caplog
    log_text = caplog.text
    assert SECRET_TOKEN not in log_text
    assert "PERMISSION ERROR for post=post_123_456" in log_text


def test_sync_comments_for_meta_ads_returns_structured_permission_error(caplog):
    """Verify sync_comments_for_meta_ads returns structured error payload with reconnect_required when Meta permission fails."""
    mock_db = MagicMock()

    # Mock ad record
    mock_ad = MagicMock(spec=MetaAd)
    mock_ad.id = 1
    mock_ad.meta_ad_id = "ad_1001"
    mock_ad.name = "Campaign Ad 1"
    mock_ad.campaign_id = "camp_1"
    mock_ad.campaign_name = "Campaign 1"
    mock_ad.adset_id = "adset_1"
    mock_ad.adset_name = "AdSet 1"
    mock_ad.creative_id = "creative_1"
    mock_ad.facebook_page_id = "711139875422034"
    mock_ad.facebook_post_id = "711139875422034_122142588518963628"

    mock_db.query().filter().all.side_effect = [
        [mock_ad],  # Ads query
        [          # SocialAccount query
            MagicMock(
                spec=SocialAccount,
                id=42,
                platform="facebook",
                account_id="711139875422034",
                token_type="page_access_token",
                access_token="encrypted_page_access_token_xyz"
            )
        ]
    ]

    mock_error_resp = MagicMock()
    mock_error_resp.status_code = 400
    mock_error_resp.headers = {"content-type": "application/json"}
    mock_error_resp.json.return_value = {
        "error": {
            "message": "(#10) This endpoint requires the 'pages_read_user_content' permission or the 'Page Public Content Access' feature.",
            "type": "OAuthException",
            "code": 10
        }
    }

    RAW_PAGE_TOKEN = "EAAG987654321_PAGE_TOKEN_SECRET"

    with patch("app.services.meta_service.decrypt_token", return_value=RAW_PAGE_TOKEN), \
         patch("requests.get", return_value=mock_error_resp):
        with caplog.at_level(logging.INFO):
            result = meta_service.sync_comments_for_meta_ads(
                db=mock_db,
                user_id=1,
                meta_ad_account_id="act_123456"
            )

    assert result["success"] is False
    assert result["reconnect_required"] is True
    assert "pages_read_user_content" in result["reason"]
    assert result["error_type"] == "META_PERMISSION_ERROR"
    assert result["missing_permission"] == "pages_read_user_content"
    assert result["requires_app_review"] is True
    assert result["ads_failed"] == 1
    assert result["permission_errors"] == 1

    # Verify no raw token logged
    assert RAW_PAGE_TOKEN not in caplog.text


def test_evaluate_social_account_token_health_missing_permission():
    """Verify evaluate_social_account_token_health flags reconnect_required when pages_read_user_content is missing."""
    mock_acc = MagicMock(spec=SocialAccount)
    mock_acc.id = 10
    mock_acc.platform = "facebook"
    mock_acc.account_id = "711139875422034"
    mock_acc.account_name = "Test Brand Page"
    mock_acc.token_type = "page_access_token"
    mock_acc.status = "CONNECTED"
    mock_acc.access_token = "mock_encrypted_tok"
    mock_acc.created_at = None
    mock_acc.updated_at = None
    mock_acc.metadata_json = {
        "granted_scopes": ["pages_show_list", "pages_read_engagement"]  # Missing pages_read_user_content
    }

    with patch("app.services.meta_service.decrypt_token", return_value="mock_decrypted"), \
         patch.object(meta_service, "debug_token", return_value={"scopes": ["pages_show_list", "pages_read_engagement"]}):
        health = meta_service.evaluate_social_account_token_health(mock_acc)

    assert health["reconnect_required"] is True
    assert health["scope_checks"]["pages_read_user_content"] is False
    assert health["scope_checks"]["pages_read_engagement"] is True


def test_evaluate_social_account_token_health_with_all_permissions():
    """Verify evaluate_social_account_token_health returns reconnect_required=False when pages_read_user_content is present."""
    mock_acc = MagicMock(spec=SocialAccount)
    mock_acc.id = 11
    mock_acc.platform = "facebook"
    mock_acc.account_id = "711139875422034"
    mock_acc.account_name = "Test Brand Page"
    mock_acc.token_type = "page_access_token"
    mock_acc.status = "CONNECTED"
    mock_acc.access_token = "mock_encrypted_tok"
    mock_acc.created_at = None
    mock_acc.updated_at = None
    mock_acc.metadata_json = {
        "granted_scopes": ["pages_show_list", "pages_read_engagement", "pages_read_user_content", "pages_manage_engagement"]
    }

    with patch("app.services.meta_service.decrypt_token", return_value="mock_decrypted"), \
         patch.object(meta_service, "debug_token", return_value={"scopes": ["pages_show_list", "pages_read_engagement", "pages_read_user_content", "pages_manage_engagement"]}):
        health = meta_service.evaluate_social_account_token_health(mock_acc)

    assert health["reconnect_required"] is False
    assert health["scope_checks"]["pages_read_user_content"] is True


def test_reconnect_updates_existing_social_account_token():
    """Verify social_account_repo.create_or_update updates an existing SocialAccount row instead of duplicating it."""
    mock_db = MagicMock()
    existing_acc = MagicMock(spec=SocialAccount)
    existing_acc.id = 101
    existing_acc.account_id = "711139875422034"
    existing_acc.platform = "facebook"
    existing_acc.access_token = "old_encrypted_token"
    existing_acc.metadata_json = {"granted_scopes": ["pages_show_list"]}

    with patch.object(social_account_repo, "get_by_account_id", return_value=existing_acc), \
         patch("app.repositories.social_account_repository.encrypt_token", return_value="new_encrypted_token"):
        updated = social_account_repo.create_or_update(
            db=mock_db,
            user_id=1,
            platform="facebook",
            account_id="711139875422034",
            account_name="Updated Page Name",
            access_token="new_raw_token_abc",
            metadata_json={"granted_scopes": ["pages_read_user_content"]}
        )

    assert updated.id == 101
    assert updated.access_token == "new_encrypted_token"
    assert updated.account_name == "Updated Page Name"
    mock_db.add.assert_not_called()  # Proves existing record was updated, not newly added!
    mock_db.commit.assert_called_once()

import pytest
import json
import hmac
import hashlib
from unittest.mock import patch, MagicMock
from app.services.meta_service import meta_service
from app.models.social_account import SocialAccount
from app.repositories.social_account_repository import social_account_repo
from app.core.security_encryption import encrypt_token
from app.core.config import settings

def test_successful_facebook_page_webhook_subscription_calls_correct_endpoint():
    """Verify subscribe_page_to_webhook calls POST /{page_id}/subscribed_apps with subscribed_fields=feed."""
    page_id = "109823471099"
    token = "EAAB12345secret_page_token"
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"success": True}

    with patch("requests.post", return_value=mock_resp) as mock_post:
        res = meta_service.subscribe_page_to_webhook(page_id, token)

        assert mock_post.called
        call_url, call_kwargs = mock_post.call_args
        assert f"/{page_id}/subscribed_apps" in call_url[0]
        assert call_kwargs["params"]["subscribed_fields"] == "feed"
        assert res["subscription_status"] == "subscribed"
        assert res["subscribed_fields"] == ["feed"]

def test_instagram_webhook_registration_does_not_make_unsupported_http_request():
    """Verify subscribe_instagram_account_to_webhook registers App-level webhook without making unsupported HTTP calls."""
    ig_id = "17841400928399"
    token = "EAAB12345secret_page_token"

    with patch("requests.post") as mock_post:
        res = meta_service.subscribe_instagram_account_to_webhook(ig_id, token)

        # Unsupported HTTP request to /{ig_id}/subscribed_apps must NOT be made
        assert not mock_post.called
        assert res["subscription_status"] == "subscribed"
        assert res["subscribed_fields"] == ["comments"]

def test_facebook_subscription_uses_only_feed():
    """Verify Facebook subscription ONLY requests the 'feed' field."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"success": True}

    with patch("requests.post", return_value=mock_resp) as mock_post:
        meta_service.subscribe_page_to_webhook("12345", "EAABtoken")
        params = mock_post.call_args[1]["params"]
        assert params["subscribed_fields"] == "feed"
        assert "comments" not in params["subscribed_fields"]

def test_tokens_never_appear_in_logs_or_errors():
    """Verify raw access tokens never leak into error message results."""
    secret_token = "EAAB_VERY_SECRET_PAGE_ACCESS_TOKEN_9999"
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.json.return_value = {"error": {"message": "Invalid page access token", "code": 190}}

    with patch("requests.post", return_value=mock_resp):
        res_fb = meta_service.subscribe_page_to_webhook("12345", secret_token)
        res_ig = meta_service.subscribe_instagram_account_to_webhook("67890", secret_token)

        assert secret_token not in str(res_fb)
        assert secret_token not in str(res_ig)

def test_readiness_accurately_represents_instagram_and_facebook_webhook_configuration():
    """Verify readiness logic evaluates webhook status accurately for Facebook and Instagram accounts."""
    secret_token = "EAAB_VERY_SECRET_TOKEN_888"
    fb_acc = SocialAccount(
        id=20,
        user_id=1,
        platform="facebook",
        account_id="109823471099",
        account_name="Test Page",
        access_token=encrypt_token(secret_token),
        status="CONNECTED",
        metadata_json={"comment_automation": {"facebook_webhook_subscription": {"status": "subscribed"}}}
    )
    ig_acc = SocialAccount(
        id=21,
        user_id=1,
        platform="instagram",
        account_id="17841400928399",
        account_name="@ig_test",
        access_token=encrypt_token(secret_token),
        status="CONNECTED",
        metadata_json={
            "instagram_account_id": "17841400928399",
            "comment_automation": {"instagram_webhook_subscription": {"status": "subscribed"}}
        }
    )

    with patch.object(meta_service, "inspect_token_permissions", return_value={"status": "success", "permissions": {s: "granted" for s in meta_service.REQUIRED_META_OAUTH_SCOPES}}):
        r_fb = meta_service.evaluate_account_comment_automation_readiness(fb_acc, secret_token)
        r_ig = meta_service.evaluate_account_comment_automation_readiness(ig_acc, secret_token)

        assert secret_token not in str(r_fb)
        assert secret_token not in str(r_ig)
        assert r_fb["page_webhook_subscribed"] is True
        assert r_ig["instagram_webhook_subscribed"] is True
        assert r_fb["comment_automation_ready"] is False
        assert r_ig["comment_automation_ready"] is False

def test_existing_metadata_fields_are_preserved(db_session):
    """Verify social_account_repo.create_or_update preserves existing metadata_json keys."""
    user_id = 99
    page_id = "page_999"

    social_account_repo.create_or_update(
        db=db_session,
        user_id=user_id,
        platform="facebook",
        account_id=page_id,
        account_name="Initial Page",
        access_token="token_v1",
        metadata_json={"existing_custom_setting": "keep_this_value"}
    )

    social_account_repo.create_or_update(
        db=db_session,
        user_id=user_id,
        platform="facebook",
        account_id=page_id,
        account_name="Initial Page Updated",
        access_token="token_v2",
        metadata_json={"comment_automation": {"facebook_webhook_subscription": {"status": "subscribed"}}}
    )

    updated_acc = social_account_repo.get_by_account_id(db_session, user_id, "facebook", page_id)
    assert updated_acc.metadata_json["existing_custom_setting"] == "keep_this_value"
    assert updated_acc.metadata_json["comment_automation"]["facebook_webhook_subscription"]["status"] == "subscribed"

def test_oauth_flow_completes_and_connects_both_fb_and_ig(client, db_session):
    """Verify OAuth callback connects both FB Page and IG Account cleanly."""
    with patch.object(meta_service, "exchange_code_for_user_token", return_value="short_tok"), \
         patch.object(meta_service, "get_long_lived_user_token", return_value="long_tok"), \
         patch.object(meta_service, "fetch_user_pages_and_instagram_accounts", return_value={
             "facebook_pages": [{"account_id": "page_123", "account_name": "Test FB Page", "access_token": "page_tok", "logo_url": None}],
             "instagram_accounts": [{"account_id": "ig_456", "account_name": "Test IG Account", "access_token": "page_tok", "logo_url": None}]
         }), \
         patch.object(meta_service, "subscribe_page_to_webhook", return_value={"page_id": "page_123", "subscription_status": "subscribed", "reason": None}), \
         patch("app.api.v1.meta.pop_oauth_state", return_value=1):

        res = client.get("/api/v1/meta/oauth/callback?code=valid_code&state=valid_state", follow_redirects=False)
        assert res.status_code == 307
        assert "connected=true" in res.headers["location"]

        acc_fb = social_account_repo.get_by_account_id(db_session, 1, "facebook", "page_123")
        acc_ig = social_account_repo.get_by_account_id(db_session, 1, "instagram", "ig_456")

        assert acc_fb is not None and acc_fb.status == "CONNECTED"
        assert acc_ig is not None and acc_ig.status == "CONNECTED"
        assert acc_fb.metadata_json["comment_automation"]["facebook_webhook_subscription"]["status"] == "subscribed"
        assert acc_ig.metadata_json["comment_automation"]["instagram_webhook_subscription"]["status"] == "subscribed"

def test_missing_account_ids_and_tokens_handled_safely():
    """Verify missing page/IG ID or token returns failure status without raising exception."""
    res1 = meta_service.subscribe_page_to_webhook("", "token")
    res2 = meta_service.subscribe_instagram_account_to_webhook("", "token")

    assert res1["subscription_status"] == "failed"
    assert res2["subscription_status"] == "failed"

def test_webhook_post_recognizes_page_object_with_event_type(client):
    """Verify webhook POST receiver validates HMAC signature and logs page object type and field changes."""
    payload = json.dumps({
        "object": "page",
        "entry": [{"id": "page_123", "time": 1700000000, "changes": [{"field": "feed", "value": {"item": "status"}}]}]
    }).encode("utf-8")
    secret = (settings.META_APP_SECRET or "test_secret").encode("utf-8")
    expected_hash = hmac.new(secret, payload, hashlib.sha256).hexdigest()
    headers = {"X-Hub-Signature-256": f"sha256={expected_hash}"}

    res = client.post("/api/v1/webhooks/meta", data=payload, headers=headers)
    assert res.status_code == 200
    assert res.json() == {"status": "success"}

def test_webhook_post_recognizes_instagram_object_with_event_type(client):
    """Verify webhook POST receiver validates HMAC signature and logs instagram object type and comments change."""
    payload = json.dumps({
        "object": "instagram",
        "entry": [{"id": "ig_456", "time": 1700000000, "changes": [{"field": "comments", "value": {"id": "c_1"}}]}]
    }).encode("utf-8")
    secret = (settings.META_APP_SECRET or "test_secret").encode("utf-8")
    expected_hash = hmac.new(secret, payload, hashlib.sha256).hexdigest()
    headers = {"X-Hub-Signature-256": f"sha256={expected_hash}"}

    res = client.post("/api/v1/webhooks/meta", data=payload, headers=headers)
    assert res.status_code == 200
    assert res.json() == {"status": "success"}

def test_invalid_webhook_signatures_rejected(client):
    """Verify POST webhooks with invalid signature header are rejected with 403 Forbidden."""
    payload = json.dumps({"object": "page", "entry": []}).encode("utf-8")
    headers = {"X-Hub-Signature-256": "sha256=invalid_hash_value"}

    res = client.post("/api/v1/webhooks/meta", data=payload, headers=headers)
    assert res.status_code == 403

def test_facebook_publishing_unaffected(db_session):
    """Verify Facebook publishing logic operates normally."""
    from app.services.publisher_service import FacebookPublisher
    
    acc = social_account_repo.create_or_update(
        db=db_session,
        user_id=1,
        platform="facebook",
        account_id="fb_pub_page",
        account_name="Publish Page",
        access_token="page_pub_token"
    )

    with patch.object(meta_service, "publish_to_facebook_page", return_value={"id": "fb_post_10099"}) as mock_pub:
        publisher = FacebookPublisher()
        post_id = publisher.publish(account=acc, caption="Test FB post", public_media_url=None, is_video=False)
        assert post_id == "fb_post_10099"
        assert mock_pub.called

def test_instagram_publishing_unaffected(db_session):
    """Verify Instagram publishing logic operates normally."""
    from app.services.publisher_service import InstagramPublisher
    
    acc = social_account_repo.create_or_update(
        db=db_session,
        user_id=1,
        platform="instagram",
        account_id="17841400928399",
        account_name="@ig_pub_account",
        access_token="page_pub_token"
    )

    with patch.object(meta_service, "publish_to_instagram_business", return_value={"id": "ig_media_554433"}) as mock_pub:
        publisher = InstagramPublisher()
        post_id = publisher.publish(account=acc, caption="Test IG post", public_media_url="https://res.cloudinary.com/demo/image/upload/sample.jpg", is_video=False)
        assert post_id == "ig_media_554433"
        assert mock_pub.called

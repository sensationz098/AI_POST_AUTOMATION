import pytest
from unittest.mock import patch, MagicMock
from app.services.meta_service import meta_service
from app.models.social_account import SocialAccount
from app.core.security_encryption import encrypt_token

def test_all_granted_permissions_produce_correct_readiness():
    """Verify when all permissions are granted, capability readiness fields are True but comment_automation_ready remains False."""
    all_granted = {scope: "granted" for scope in meta_service.REQUIRED_META_OAUTH_SCOPES}

    account = SocialAccount(
        id=10,
        user_id=1,
        platform="facebook",
        account_id="109823471099",
        account_name="Test Page",
        access_token=encrypt_token("EAAB12345secret"),
        status="CONNECTED",
        metadata_json={"custom_setting": "keep_me"}
    )

    with patch.object(meta_service, "inspect_token_permissions", return_value={"status": "success", "permissions": all_granted}):
        res = meta_service.evaluate_account_comment_automation_readiness(account, "EAAB12345secret")

    assert res["requires_reconnection"] is False
    assert res["oauth_permissions_ready"] is True
    assert res["comment_read_ready"] is True
    assert res["comment_reply_ready"] is True
    assert res["webhook_prerequisites_ready"] is True
    assert res["webhook_configured"] is False
    # CRITICAL: Must remain False because webhook engine is not yet implemented
    assert res["comment_automation_ready"] is False
    assert res["missing_permissions"] == []

def test_missing_instagram_manage_comments_requires_reconnection():
    """Verify missing instagram_manage_comments marks Instagram account as requiring reconnection."""
    perm_map = {scope: "granted" for scope in meta_service.REQUIRED_META_OAUTH_SCOPES}
    perm_map["instagram_manage_comments"] = "declined"

    account = SocialAccount(
        id=11,
        user_id=1,
        platform="instagram",
        account_id="17841400928399",
        account_name="@test_ig",
        access_token=encrypt_token("EAAB12345secret"),
        status="CONNECTED"
    )

    with patch.object(meta_service, "inspect_token_permissions", return_value={"status": "success", "permissions": perm_map}):
        res = meta_service.evaluate_account_comment_automation_readiness(account, "EAAB12345secret")

    assert res["requires_reconnection"] is True
    assert res["oauth_permissions_ready"] is False
    assert "instagram_manage_comments" in res["missing_permissions"]
    assert res["comment_reply_ready"] is False
    assert res["comment_automation_ready"] is False
    assert account.status == "CONNECTED"  # Connection status remains intact

def test_missing_pages_read_user_content_disables_fb_comment_reading():
    """Verify missing pages_read_user_content sets comment_read_ready to False for Facebook Page."""
    perm_map = {scope: "granted" for scope in meta_service.REQUIRED_META_OAUTH_SCOPES}
    perm_map["pages_read_user_content"] = "declined"

    account = SocialAccount(
        id=12,
        user_id=1,
        platform="facebook",
        account_id="109823471099",
        account_name="FB Page",
        access_token=encrypt_token("EAAB12345secret"),
        status="CONNECTED"
    )

    with patch.object(meta_service, "inspect_token_permissions", return_value={"status": "success", "permissions": perm_map}):
        res = meta_service.evaluate_account_comment_automation_readiness(account, "EAAB12345secret")

    assert res["comment_read_ready"] is False
    assert "pages_read_user_content" in res["missing_permissions"]

def test_missing_pages_manage_engagement_disables_fb_comment_replies():
    """Verify missing pages_manage_engagement sets comment_reply_ready to False for Facebook Page."""
    perm_map = {scope: "granted" for scope in meta_service.REQUIRED_META_OAUTH_SCOPES}
    perm_map["pages_manage_engagement"] = "declined"

    account = SocialAccount(
        id=13,
        user_id=1,
        platform="facebook",
        account_id="109823471099",
        account_name="FB Page",
        access_token=encrypt_token("EAAB12345secret"),
        status="CONNECTED"
    )

    with patch.object(meta_service, "inspect_token_permissions", return_value={"status": "success", "permissions": perm_map}):
        res = meta_service.evaluate_account_comment_automation_readiness(account, "EAAB12345secret")

    assert res["comment_reply_ready"] is False
    assert "pages_manage_engagement" in res["missing_permissions"]

def test_missing_pages_manage_metadata_disables_fb_webhook_prerequisites():
    """Verify missing pages_manage_metadata sets webhook_prerequisites_ready to False."""
    perm_map = {scope: "granted" for scope in meta_service.REQUIRED_META_OAUTH_SCOPES}
    perm_map["pages_manage_metadata"] = "declined"

    account = SocialAccount(
        id=14,
        user_id=1,
        platform="facebook",
        account_id="109823471099",
        account_name="FB Page",
        access_token=encrypt_token("EAAB12345secret"),
        status="CONNECTED"
    )

    with patch.object(meta_service, "inspect_token_permissions", return_value={"status": "success", "permissions": perm_map}):
        res = meta_service.evaluate_account_comment_automation_readiness(account, "EAAB12345secret")

    assert res["webhook_prerequisites_ready"] is False
    assert "pages_manage_metadata" in res["missing_permissions"]

def test_unlinked_instagram_account_is_not_ready():
    """Verify an Instagram account without a linked Instagram Professional account ID is marked as not ready."""
    perm_map = {scope: "granted" for scope in meta_service.REQUIRED_META_OAUTH_SCOPES}

    account = SocialAccount(
        id=15,
        user_id=1,
        platform="instagram",
        account_id="",  # Empty linked IG account ID
        account_name="@unlinked_ig",
        access_token=encrypt_token("EAAB12345secret"),
        status="CONNECTED"
    )

    with patch.object(meta_service, "inspect_token_permissions", return_value={"status": "success", "permissions": perm_map}):
        res = meta_service.evaluate_account_comment_automation_readiness(account, "EAAB12345secret")

    assert res["requires_reconnection"] is True
    assert "instagram_account_not_linked" in res["missing_permissions"]
    assert res["comment_read_ready"] is False
    assert res["comment_reply_ready"] is False

def test_tokens_and_secrets_never_appear_in_readiness_response():
    """Verify readiness output contains zero raw tokens, encrypted strings, or app secrets."""
    secret_token = "EAAB12345VERYSECRETTOKEN999"
    account = SocialAccount(
        id=16,
        user_id=1,
        platform="facebook",
        account_id="109823471099",
        account_name="FB Page",
        access_token=encrypt_token(secret_token),
        status="CONNECTED"
    )

    with patch.object(meta_service, "inspect_token_permissions", return_value={"status": "success", "permissions": {s: "granted" for s in meta_service.REQUIRED_META_OAUTH_SCOPES}}):
        res = meta_service.evaluate_account_comment_automation_readiness(account, secret_token)

    res_str = str(res)
    assert secret_token not in res_str
    assert "enc_gAAAAA" not in res_str
    assert "access_token" not in res

def test_readiness_api_endpoint_user_isolation(client, db_session):
    """Verify authenticated users can ONLY query their own connected accounts readiness (IDOR protection)."""
    import uuid
    # Register & Login User A
    email_a = f"readiness_userA_{uuid.uuid4().hex[:8]}@test.com"
    client.post("/api/v1/auth/register", json={"email": email_a, "password": "Password123!", "full_name": "User A"})
    token_a = client.post("/api/v1/auth/login", json={"email": email_a, "password": "Password123!"}).json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Register & Login User B
    email_b = f"readiness_userB_{uuid.uuid4().hex[:8]}@test.com"
    client.post("/api/v1/auth/register", json={"email": email_b, "password": "Password123!", "full_name": "User B"})
    token_b = client.post("/api/v1/auth/login", json={"email": email_b, "password": "Password123!"}).json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Get User B model record ID
    from app.repositories.user_repository import user_repo
    user_b = user_repo.get_by_email(db_session, email_b)

    # Create social account belonging to User B
    sec_account = SocialAccount(
        user_id=user_b.id,
        platform="facebook",
        account_id="999888777",
        account_name="User B Page",
        access_token=encrypt_token("EAABsecret_sec"),
        status="CONNECTED"
    )
    db_session.add(sec_account)
    db_session.commit()

    with patch.object(meta_service, "inspect_token_permissions", return_value={"status": "success", "permissions": {s: "granted" for s in meta_service.REQUIRED_META_OAUTH_SCOPES}}):
        # User A requests comment automation readiness
        response = client.get("/api/v1/social-accounts/comment-automation/readiness", headers=headers_a)
        assert response.status_code == 200
        data = response.json()
        account_ids = [a["social_account_id"] for a in data["accounts"]]

        # Verify User B's account is NOT returned to User A
        assert sec_account.id not in account_ids

import hmac
import hashlib
import pytest
from unittest.mock import patch
from app.core.config import settings

def test_webhook_route_registration_not_404(client):
    """Verify GET /api/v1/webhooks/meta is registered and does not return 404 Not Found."""
    with patch.object(settings, "META_WEBHOOK_VERIFY_TOKEN", "valid_verify_token_123"):
        res = client.get("/api/v1/webhooks/meta")
        assert res.status_code != 404

def test_valid_get_webhook_verification(client):
    """Verify GET webhook verification returns HTTP 200 plain text matching hub.challenge exactly."""
    verify_token = "my_secret_webhook_verify_token_2026"
    challenge_val = "123456789_challenge_test"

    with patch.object(settings, "META_WEBHOOK_VERIFY_TOKEN", verify_token):
        res = client.get(
            f"/api/v1/webhooks/meta?hub.mode=subscribe&hub.verify_token={verify_token}&hub.challenge={challenge_val}"
        )

        assert res.status_code == 200
        assert res.text == challenge_val
        assert "application/json" not in res.headers.get("content-type", "").lower()
        assert "text/plain" in res.headers.get("content-type", "").lower()

def test_invalid_verification_token_rejected(client):
    """Verify GET webhook request with invalid verify token returns HTTP 403 Forbidden."""
    with patch.object(settings, "META_WEBHOOK_VERIFY_TOKEN", "correct_token_999"):
        res = client.get(
            "/api/v1/webhooks/meta?hub.mode=subscribe&hub.verify_token=WRONG_TOKEN&hub.challenge=999"
        )
        assert res.status_code == 403

def test_missing_verification_parameters_rejected(client):
    """Verify GET webhook request with missing mode or token returns HTTP 403 Forbidden."""
    with patch.object(settings, "META_WEBHOOK_VERIFY_TOKEN", "correct_token_999"):
        res = client.get("/api/v1/webhooks/meta?hub.challenge=999")
        assert res.status_code == 403

def test_post_valid_signature_returns_200(client):
    """Verify POST webhook event payload with valid X-Hub-Signature-256 returns HTTP 200."""
    app_secret = "meta_app_secret_test_32_chars_long"
    payload = '{"object": "page", "entry": [{"id": "1001", "time": 1700000000}]}'
    payload_bytes = payload.encode("utf-8")

    expected_hash = hmac.new(app_secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    valid_sig_header = f"sha256={expected_hash}"

    with patch.object(settings, "META_APP_SECRET", app_secret):
        res = client.post(
            "/api/v1/webhooks/meta",
            content=payload_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": valid_sig_header
            }
        )
        assert res.status_code == 200
        assert res.json()["status"] == "success"

def test_post_invalid_signature_rejected(client):
    """Verify POST webhook event payload with invalid HMAC signature returns HTTP 403."""
    app_secret = "meta_app_secret_test_32_chars_long"
    payload_bytes = b'{"object": "page", "entry": []}'

    with patch.object(settings, "META_APP_SECRET", app_secret):
        res = client.post(
            "/api/v1/webhooks/meta",
            content=payload_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": "sha256=invalid_fake_hmac_hash_value"
            }
        )
        assert res.status_code == 403

def test_post_missing_signature_rejected(client):
    """Verify POST webhook event payload with missing signature header returns HTTP 403."""
    app_secret = "meta_app_secret_test_32_chars_long"
    payload_bytes = b'{"object": "page", "entry": []}'

    with patch.object(settings, "META_APP_SECRET", app_secret):
        res = client.post(
            "/api/v1/webhooks/meta",
            content=payload_bytes,
            headers={"Content-Type": "application/json"}
        )
        assert res.status_code == 403

def test_security_secrets_never_exposed_in_responses_or_logs(client):
    """Verify META_WEBHOOK_VERIFY_TOKEN and META_APP_SECRET never appear in HTTP responses or logs."""
    verify_token = "TOP_SECRET_VERIFY_TOKEN_XYZ_99"
    app_secret = "TOP_SECRET_APP_SECRET_ABC_88"

    with patch.object(settings, "META_WEBHOOK_VERIFY_TOKEN", verify_token), \
         patch.object(settings, "META_APP_SECRET", app_secret):
        
        # Test failed verification response
        get_res = client.get("/api/v1/webhooks/meta?hub.mode=subscribe&hub.verify_token=bad")
        assert verify_token not in get_res.text
        assert app_secret not in get_res.text

        # Test failed post signature response
        post_res = client.post(
            "/api/v1/webhooks/meta",
            content=b'{"object":"page"}',
            headers={"X-Hub-Signature-256": "sha256=bad"}
        )
        assert verify_token not in post_res.text
        assert app_secret not in post_res.text

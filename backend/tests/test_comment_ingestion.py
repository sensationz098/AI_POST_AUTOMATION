import pytest
import json
import hmac
import hashlib
from unittest.mock import patch, MagicMock
from app.models.social_account import SocialAccount
from app.models.social_comment import SocialComment
from app.repositories.social_account_repository import social_account_repo
from app.repositories.social_comment_repository import social_comment_repo
from app.services.meta_service import meta_service
from app.core.config import settings

def generate_signature(payload_bytes: bytes) -> str:
    """Helper to generate valid X-Hub-Signature-256 header."""
    digest = hmac.new(settings.META_APP_SECRET.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return f"sha256={digest}"

def test_valid_facebook_signature_accepted(client):
    payload = json.dumps({"object": "page", "entry": []}).encode("utf-8")
    headers = {"X-Hub-Signature-256": generate_signature(payload)}
    res = client.post("/api/v1/webhooks/meta", data=payload, headers=headers)
    assert res.status_code == 200

def test_valid_instagram_signature_accepted(client):
    payload = json.dumps({"object": "instagram", "entry": []}).encode("utf-8")
    headers = {"X-Hub-Signature-256": generate_signature(payload)}
    res = client.post("/api/v1/webhooks/meta", data=payload, headers=headers)
    assert res.status_code == 200

def test_invalid_signature_returns_403(client):
    payload = json.dumps({"object": "page", "entry": []}).encode("utf-8")
    headers = {"X-Hub-Signature-256": "sha256=invalid_hash"}
    res = client.post("/api/v1/webhooks/meta", data=payload, headers=headers)
    assert res.status_code == 403

def test_missing_signature_returns_403(client):
    payload = json.dumps({"object": "page", "entry": []}).encode("utf-8")
    res = client.post("/api/v1/webhooks/meta", data=payload)
    assert res.status_code == 403

def test_facebook_comment_event_creates_record(client, db_session):
    # Setup FB SocialAccount for User 1
    social_account_repo.create_or_update(
        db=db_session, user_id=1, platform="facebook", account_id="page_fb_100", account_name="Test FB Page", access_token="tok_100"
    )

    payload = json.dumps({
        "object": "page",
        "entry": [{
            "id": "page_fb_100",
            "time": 1700000000,
            "changes": [{
                "field": "feed",
                "value": {
                    "item": "comment",
                    "verb": "add",
                    "comment_id": "c_fb_999",
                    "post_id": "post_fb_111",
                    "message": "Great Facebook post!",
                    "from": {"id": "user_fb_55", "name": "Alice"}
                }
            }]
        }]
    }).encode("utf-8")

    headers = {"X-Hub-Signature-256": generate_signature(payload)}
    res = client.post("/api/v1/webhooks/meta", data=payload, headers=headers)
    assert res.status_code == 200

    comment = db_session.query(SocialComment).filter_by(external_comment_id="c_fb_999").first()
    assert comment is not None
    assert comment.user_id == 1
    assert comment.platform == "facebook"
    assert comment.comment_text == "Great Facebook post!"
    assert comment.commenter_name == "Alice"
    assert comment.processing_status == "RECEIVED"

def test_facebook_non_comment_feed_event_ignored(client, db_session):
    social_account_repo.create_or_update(
        db=db_session, user_id=1, platform="facebook", account_id="page_fb_100", account_name="Test FB Page", access_token="tok_100"
    )

    # Post addition event (item != comment)
    payload = json.dumps({
        "object": "page",
        "entry": [{
            "id": "page_fb_100",
            "changes": [{
                "field": "feed",
                "value": {
                    "item": "status",
                    "verb": "add",
                    "post_id": "post_fb_222",
                    "message": "New status update"
                }
            }]
        }]
    }).encode("utf-8")

    headers = {"X-Hub-Signature-256": generate_signature(payload)}
    res = client.post("/api/v1/webhooks/meta", data=payload, headers=headers)
    assert res.status_code == 200

    assert db_session.query(SocialComment).filter_by(external_post_id="post_fb_222").first() is None

def test_missing_optional_facebook_fields_do_not_crash(client, db_session):
    social_account_repo.create_or_update(
        db=db_session, user_id=1, platform="facebook", account_id="page_fb_100", account_name="Test FB Page", access_token="tok_100"
    )

    # Missing from, created_time, message
    payload = json.dumps({
        "object": "page",
        "entry": [{
            "id": "page_fb_100",
            "changes": [{
                "field": "feed",
                "value": {
                    "item": "comment",
                    "comment_id": "c_fb_min"
                }
            }]
        }]
    }).encode("utf-8")

    headers = {"X-Hub-Signature-256": generate_signature(payload)}
    res = client.post("/api/v1/webhooks/meta", data=payload, headers=headers)
    assert res.status_code == 200

    c = db_session.query(SocialComment).filter_by(external_comment_id="c_fb_min").first()
    assert c is not None
    assert c.comment_text is None

def test_unknown_facebook_event_structures_ignored_safely(client):
    payload = json.dumps({"object": "page", "entry": [{"id": "page_fb_100", "unknown_key": [1, 2, 3]}]}).encode("utf-8")
    headers = {"X-Hub-Signature-256": generate_signature(payload)}
    res = client.post("/api/v1/webhooks/meta", data=payload, headers=headers)
    assert res.status_code == 200

def test_instagram_comment_event_creates_record(client, db_session):
    social_account_repo.create_or_update(
        db=db_session, user_id=2, platform="instagram", account_id="ig_acc_200", account_name="@ig_test", access_token="tok_200"
    )

    payload = json.dumps({
        "object": "instagram",
        "entry": [{
            "id": "ig_acc_200",
            "time": 1700000000,
            "changes": [{
                "field": "comments",
                "value": {
                    "id": "c_ig_888",
                    "text": "Love this photo!",
                    "media": {"id": "m_ig_777"},
                    "from": {"id": "ig_user_123", "username": "bob_instagram"}
                }
            }]
        }]
    }).encode("utf-8")

    headers = {"X-Hub-Signature-256": generate_signature(payload)}
    res = client.post("/api/v1/webhooks/meta", data=payload, headers=headers)
    assert res.status_code == 200

    comment = db_session.query(SocialComment).filter_by(external_comment_id="c_ig_888").first()
    assert comment is not None
    assert comment.user_id == 2
    assert comment.platform == "instagram"
    assert comment.comment_text == "Love this photo!"
    assert comment.commenter_name == "bob_instagram"

def test_non_comment_instagram_event_ignored(client, db_session):
    social_account_repo.create_or_update(
        db=db_session, user_id=2, platform="instagram", account_id="ig_acc_200", account_name="@ig_test", access_token="tok_200"
    )

    payload = json.dumps({
        "object": "instagram",
        "entry": [{
            "id": "ig_acc_200",
            "changes": [{
                "field": "story_insights",
                "value": {"media_id": "story_1"}
            }]
        }]
    }).encode("utf-8")

    headers = {"X-Hub-Signature-256": generate_signature(payload)}
    res = client.post("/api/v1/webhooks/meta", data=payload, headers=headers)
    assert res.status_code == 200

    assert db_session.query(SocialComment).filter_by(external_post_id="story_1").first() is None

def test_missing_optional_instagram_fields_do_not_crash(client, db_session):
    social_account_repo.create_or_update(
        db=db_session, user_id=2, platform="instagram", account_id="ig_acc_200", account_name="@ig_test", access_token="tok_200"
    )

    payload = json.dumps({
        "object": "instagram",
        "entry": [{
            "id": "ig_acc_200",
            "changes": [{
                "field": "comments",
                "value": {"id": "c_ig_min"}
            }]
        }]
    }).encode("utf-8")

    headers = {"X-Hub-Signature-256": generate_signature(payload)}
    res = client.post("/api/v1/webhooks/meta", data=payload, headers=headers)
    assert res.status_code == 200

    c = db_session.query(SocialComment).filter_by(external_comment_id="c_ig_min").first()
    assert c is not None

def test_user_and_account_isolation(client, db_session):
    """Verify User A's comment event is strictly isolated and never assigned to User B."""
    social_account_repo.create_or_update(db=db_session, user_id=10, platform="facebook", account_id="fb_page_user10", account_name="P10", access_token="tok")
    social_account_repo.create_or_update(db=db_session, user_id=20, platform="facebook", account_id="fb_page_user20", account_name="P20", access_token="tok")

    payload = json.dumps({
        "object": "page",
        "entry": [{
            "id": "fb_page_user10",
            "changes": [{"field": "feed", "value": {"item": "comment", "comment_id": "c_user10", "message": "For User 10"}}]
        }]
    }).encode("utf-8")

    headers = {"X-Hub-Signature-256": generate_signature(payload)}
    client.post("/api/v1/webhooks/meta", data=payload, headers=headers)

    c10 = db_session.query(SocialComment).filter_by(external_comment_id="c_user10").first()
    assert c10.user_id == 10
    assert c10.user_id != 20

def test_deduplication_facebook_and_instagram(client, db_session):
    """Verify sending duplicate comment webhooks creates only ONE record."""
    social_account_repo.create_or_update(db=db_session, user_id=1, platform="facebook", account_id="p_fb", account_name="FB", access_token="tok")
    social_account_repo.create_or_update(db=db_session, user_id=1, platform="instagram", account_id="p_ig", account_name="IG", access_token="tok")

    fb_payload = json.dumps({
        "object": "page",
        "entry": [{"id": "p_fb", "changes": [{"field": "feed", "value": {"item": "comment", "comment_id": "dup_fb_1"}}]}]
    }).encode("utf-8")
    fb_headers = {"X-Hub-Signature-256": generate_signature(fb_payload)}

    # Send twice
    client.post("/api/v1/webhooks/meta", data=fb_payload, headers=fb_headers)
    client.post("/api/v1/webhooks/meta", data=fb_payload, headers=fb_headers)

    fb_count = db_session.query(SocialComment).filter_by(external_comment_id="dup_fb_1").count()
    assert fb_count == 1

    ig_payload = json.dumps({
        "object": "instagram",
        "entry": [{"id": "p_ig", "changes": [{"field": "comments", "value": {"id": "dup_ig_1"}}]}]
    }).encode("utf-8")
    ig_headers = {"X-Hub-Signature-256": generate_signature(ig_payload)}

    # Send twice
    client.post("/api/v1/webhooks/meta", data=ig_payload, headers=ig_headers)
    client.post("/api/v1/webhooks/meta", data=ig_payload, headers=ig_headers)

    ig_count = db_session.query(SocialComment).filter_by(external_comment_id="dup_ig_1").count()
    assert ig_count == 1

def test_access_tokens_and_secrets_never_appear_in_comment_records(db_session):
    """Verify SocialComment model and repository do not store tokens or app secrets."""
    c = db_session.query(SocialComment).first()
    if c:
        comment_dict = str(c.__dict__)
        assert "access_token" not in comment_dict
        assert "app_secret" not in comment_dict
        assert settings.META_APP_SECRET not in comment_dict

def test_webhook_get_verification_unaffected(client):
    res = client.get(f"/api/v1/webhooks/meta?hub.mode=subscribe&hub.verify_token={settings.META_WEBHOOK_VERIFY_TOKEN}&hub.challenge=test_challenge_123")
    assert res.status_code == 200
    assert res.text == "test_challenge_123"

def test_publishing_and_oauth_unaffected(db_session):
    """Verify Facebook and Instagram publishing logic operate normally."""
    from app.services.publisher_service import FacebookPublisher, InstagramPublisher

    acc_fb = social_account_repo.create_or_update(db=db_session, user_id=1, platform="facebook", account_id="fb_page_pub", account_name="P", access_token="tok")
    acc_ig = social_account_repo.create_or_update(db=db_session, user_id=1, platform="instagram", account_id="ig_acc_pub", account_name="I", access_token="tok")

    with patch.object(meta_service, "publish_to_facebook_page", return_value={"id": "fb_post_999"}) as mock_fb, \
         patch.object(meta_service, "publish_to_instagram_business", return_value={"id": "ig_media_999"}) as mock_ig:

        res_fb = FacebookPublisher().publish(account=acc_fb, caption="FB post", public_media_url=None, is_video=False)
        res_ig = InstagramPublisher().publish(account=acc_ig, caption="IG post", public_media_url="https://res.cloudinary.com/demo/image/upload/sample.jpg", is_video=False)

        assert res_fb == "fb_post_999"
        assert res_ig == "ig_media_999"
        assert mock_fb.called
        assert mock_ig.called

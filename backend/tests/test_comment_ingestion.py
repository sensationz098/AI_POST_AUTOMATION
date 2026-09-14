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
    secret = (settings.META_APP_SECRET or "test_secret").encode("utf-8")
    digest = hmac.new(secret, payload_bytes, hashlib.sha256).hexdigest()
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
    token = settings.META_WEBHOOK_VERIFY_TOKEN or "test_verify_token"
    res = client.get(f"/api/v1/webhooks/meta?hub.mode=subscribe&hub.verify_token={token}&hub.challenge=test_challenge_123")
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

def test_instagram_comment_webhook_normalizes_parent_id_matching_media_id(client, db_session):
    """
    Verify that when Instagram webhook sends parent_id matching the media_id (top-level comment),
    parent_comment_id is normalized to None.
    """
    social_account_repo.create_or_update(
        db=db_session, user_id=3, platform="instagram", account_id="17841443294223730", account_name="@ig_prod", access_token="tok_300"
    )

    payload = json.dumps({
        "object": "instagram",
        "entry": [{
            "id": "17841443294223730",
            "time": 1700000000,
            "changes": [{
                "field": "comments",
                "value": {
                    "id": "17967710256188117",
                    "text": "Hey",
                    "media": {"id": "17902645869579015"},
                    "parent_id": "17902645869579015",  # Meta sends media ID as parent_id for top-level comments
                    "from": {"id": "ig_user_777", "username": "soubhagyavashishtha"}
                }
            }]
        }]
    }).encode("utf-8")

    headers = {"X-Hub-Signature-256": generate_signature(payload)}
    res = client.post("/api/v1/webhooks/meta", data=payload, headers=headers)
    assert res.status_code == 200

    comment = db_session.query(SocialComment).filter_by(external_comment_id="17967710256188117").first()
    assert comment is not None
    assert comment.user_id == 3
    assert comment.external_post_id == "17902645869579015"
    assert comment.parent_comment_id is None
    assert comment.comment_text == "Hey"

def test_duplicate_social_account_resolves_most_recent_active_owner(db_session):
    """
    Test A: Verify that when duplicate SocialAccount records exist with the same (platform, account_id),
    global webhook resolution (user_id=None) deterministically selects the CONNECTED record
    with the most recent updated_at and highest id tie-breaker.
    """
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)

    # Older account for user 1 (e.g. created 7 days ago)
    acc1 = SocialAccount(
        user_id=1,
        platform="instagram",
        account_id="ig_shared_123",
        account_name="@user1_ig",
        access_token="tok_1",
        status="CONNECTED",
        created_at=now - timedelta(days=7),
        updated_at=now - timedelta(days=7)
    )
    # Newer account for user 2 (e.g. created today)
    acc2 = SocialAccount(
        user_id=2,
        platform="instagram",
        account_id="ig_shared_123",
        account_name="@user2_ig",
        access_token="tok_2",
        status="CONNECTED",
        created_at=now,
        updated_at=now
    )
    db_session.add_all([acc1, acc2])
    db_session.commit()

    resolved = social_account_repo.get_by_account_id(db_session, user_id=None, platform="instagram", account_id="ig_shared_123")
    assert resolved is not None
    assert resolved.id == acc2.id
    assert resolved.user_id == 2


def test_connected_account_beats_disconnected_newer_account(db_session):
    """
    Test B: Verify status priority: a CONNECTED older account beats a DISCONNECTED/REVOKED newer account.
    """
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)

    acc_connected_old = SocialAccount(
        user_id=1,
        platform="facebook",
        account_id="fb_shared_456",
        account_name="Active Page",
        access_token="tok_conn",
        status="CONNECTED",
        created_at=now - timedelta(days=5),
        updated_at=now - timedelta(days=5)
    )
    acc_revoked_new = SocialAccount(
        user_id=2,
        platform="facebook",
        account_id="fb_shared_456",
        account_name="Revoked Page",
        access_token="tok_rev",
        status="REVOKED",
        created_at=now,
        updated_at=now
    )
    db_session.add_all([acc_connected_old, acc_revoked_new])
    db_session.commit()

    resolved = social_account_repo.get_by_account_id(db_session, user_id=None, platform="facebook", account_id="fb_shared_456")
    assert resolved is not None
    assert resolved.id == acc_connected_old.id
    assert resolved.user_id == 1
    assert resolved.status == "CONNECTED"


def test_webhook_comment_uses_resolved_account_tenant(client, db_session):
    """
    Test C: Verify incoming webhook assigns SocialComment.user_id and social_account_id
    matching the resolved authoritative SocialAccount.
    """
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)

    acc1 = SocialAccount(
        user_id=1, platform="instagram", account_id="ig_tenant_789", account_name="@ig_old",
        access_token="tok1", status="CONNECTED", created_at=now - timedelta(days=2), updated_at=now - timedelta(days=2)
    )
    acc2 = SocialAccount(
        user_id=2, platform="instagram", account_id="ig_tenant_789", account_name="@ig_new",
        access_token="tok2", status="CONNECTED", created_at=now, updated_at=now
    )
    db_session.add_all([acc1, acc2])
    db_session.commit()

    payload = json.dumps({
        "object": "instagram",
        "entry": [{
            "id": "ig_tenant_789",
            "time": 1700000000,
            "changes": [{
                "field": "comments",
                "value": {
                    "id": "c_tenant_test_1",
                    "text": "Tenant isolation check",
                    "media": {"id": "media_789"},
                    "from": {"id": "u_99", "username": "commenter_99"}
                }
            }]
        }]
    }).encode("utf-8")

    headers = {"X-Hub-Signature-256": generate_signature(payload)}
    res = client.post("/api/v1/webhooks/meta", data=payload, headers=headers)
    assert res.status_code == 200

    comment = db_session.query(SocialComment).filter_by(external_comment_id="c_tenant_test_1").first()
    assert comment is not None
    assert comment.user_id == acc2.user_id
    assert comment.user_id == 2
    assert comment.social_account_id == acc2.id


def test_webhook_comment_visible_in_resolved_users_inbox(client, db_session):
    """
    Test D: Verify that after webhook ingestion, SocialCommentRepository.get_by_user_id()
    for the resolved user returns the comment.
    """
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)

    acc = SocialAccount(
        user_id=2, platform="instagram", account_id="ig_inbox_test", account_name="@inbox_ig",
        access_token="tok", status="CONNECTED", created_at=now, updated_at=now
    )
    db_session.add(acc)
    db_session.commit()

    payload = json.dumps({
        "object": "instagram",
        "entry": [{
            "id": "ig_inbox_test",
            "changes": [{
                "field": "comments",
                "value": {
                    "id": "c_inbox_visible",
                    "text": "Hello Inbox",
                    "media": {"id": "m_inbox_1"}
                }
            }]
        }]
    }).encode("utf-8")

    headers = {"X-Hub-Signature-256": generate_signature(payload)}
    res = client.post("/api/v1/webhooks/meta", data=payload, headers=headers)
    assert res.status_code == 200

    user2_comments = social_comment_repo.get_by_user_id(db=db_session, user_id=2)
    ext_ids = [c.external_comment_id for c in user2_comments]
    assert "c_inbox_visible" in ext_ids


def test_webhook_comment_isolated_from_other_users(client, db_session):
    """
    Test E: Verify that other users' inboxes (e.g. user_id=1) do NOT receive or view
    comments belonging to user_id=2.
    """
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)

    acc = SocialAccount(
        user_id=2, platform="instagram", account_id="ig_isolated_acc", account_name="@isolated_ig",
        access_token="tok", status="CONNECTED", created_at=now, updated_at=now
    )
    db_session.add(acc)
    db_session.commit()

    payload = json.dumps({
        "object": "instagram",
        "entry": [{
            "id": "ig_isolated_acc",
            "changes": [{
                "field": "comments",
                "value": {
                    "id": "c_isolated_1",
                    "text": "Secret Comment",
                    "media": {"id": "m_iso_1"}
                }
            }]
        }]
    }).encode("utf-8")

    headers = {"X-Hub-Signature-256": generate_signature(payload)}
    res = client.post("/api/v1/webhooks/meta", data=payload, headers=headers)
    assert res.status_code == 200

    user1_comments = social_comment_repo.get_by_user_id(db=db_session, user_id=1)
    ext_ids_1 = [c.external_comment_id for c in user1_comments]
    assert "c_isolated_1" not in ext_ids_1

    user2_comments = social_comment_repo.get_by_user_id(db=db_session, user_id=2)
    ext_ids_2 = [c.external_comment_id for c in user2_comments]
    assert "c_isolated_1" in ext_ids_2


def test_existing_comment_ownership_reconciliation_is_safe(db_session):
    """
    Test F: Verify that existing comment ownership reconciliation only updates ownership
    when the target SocialAccount is proven to be the authoritative active account for the exact same
    (platform, external account_id) relationship, and does NOT allow arbitrary cross-tenant theft.
    """
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)

    # 1. Authoritative account for Page A
    acc_a1 = SocialAccount(
        user_id=1, platform="facebook", account_id="page_reconcile_A", account_name="Page A Old",
        access_token="tok", status="CONNECTED", created_at=now - timedelta(days=2), updated_at=now - timedelta(days=2)
    )
    acc_a2 = SocialAccount(
        user_id=2, platform="facebook", account_id="page_reconcile_A", account_name="Page A New",
        access_token="tok", status="CONNECTED", created_at=now, updated_at=now
    )
    # Unrelated account for Page B
    acc_b = SocialAccount(
        user_id=3, platform="facebook", account_id="page_reconcile_B", account_name="Page B",
        access_token="tok", status="CONNECTED", created_at=now, updated_at=now
    )
    db_session.add_all([acc_a1, acc_a2, acc_b])
    db_session.commit()

    # Create existing comment under old acc_a1
    comment = social_comment_repo.create_or_get_existing(
        db=db_session,
        user_id=acc_a1.user_id,
        social_account_id=acc_a1.id,
        platform="facebook",
        external_comment_id="c_recon_test_1",
        comment_text="Reconcile Me"
    )
    assert comment.user_id == 1
    assert comment.social_account_id == acc_a1.id

    # Re-ingest with authoritative acc_a2 -> Should safely reconcile to user 2
    comment_recon = social_comment_repo.create_or_get_existing(
        db=db_session,
        user_id=acc_a2.user_id,
        social_account_id=acc_a2.id,
        platform="facebook",
        external_comment_id="c_recon_test_1"
    )
    assert comment_recon.user_id == 2
    assert comment_recon.social_account_id == acc_a2.id

    # Attempt to reconcile with unrelated Page B account (acc_b) -> Should NOT steal ownership
    comment_blocked = social_comment_repo.create_or_get_existing(
        db=db_session,
        user_id=acc_b.user_id,
        social_account_id=acc_b.id,
        platform="facebook",
        external_comment_id="c_recon_test_1"
    )
    assert comment_blocked.user_id == 2
    assert comment_blocked.social_account_id == acc_a2.id


def test_instagram_and_facebook_global_account_resolution(db_session):
    """
    Test G: Verify both Facebook and Instagram platforms use deterministic global resolution.
    """
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)

    # Facebook
    fb1 = SocialAccount(user_id=1, platform="facebook", account_id="fb_global_1", account_name="FB1", access_token="t", status="CONNECTED", created_at=now - timedelta(days=1), updated_at=now - timedelta(days=1))
    fb2 = SocialAccount(user_id=2, platform="facebook", account_id="fb_global_1", account_name="FB2", access_token="t", status="CONNECTED", created_at=now, updated_at=now)

    # Instagram
    ig1 = SocialAccount(user_id=1, platform="instagram", account_id="ig_global_1", account_name="IG1", access_token="t", status="CONNECTED", created_at=now - timedelta(days=1), updated_at=now - timedelta(days=1))
    ig2 = SocialAccount(user_id=2, platform="instagram", account_id="ig_global_1", account_name="IG2", access_token="t", status="CONNECTED", created_at=now, updated_at=now)

    db_session.add_all([fb1, fb2, ig1, ig2])
    db_session.commit()

    fb_res = social_account_repo.get_by_account_id(db_session, user_id=None, platform="facebook", account_id="fb_global_1")
    ig_res = social_account_repo.get_by_account_id(db_session, user_id=None, platform="instagram", account_id="ig_global_1")

    assert fb_res.id == fb2.id
    assert fb_res.user_id == 2
    assert ig_res.id == ig2.id
    assert ig_res.user_id == 2


def test_instagram_metadata_fallback_uses_authoritative_account(client, db_session):
    """
    Test H: Verify fallback resolution via metadata_json uses deterministic ordering (CONNECTED + most recent).
    """
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)

    # Older account with linked IG ID in metadata_json
    acc1 = SocialAccount(
        user_id=1,
        platform="instagram",
        account_id="ig_meta_old_id",
        account_name="@ig_meta_1",
        access_token="tok1",
        status="CONNECTED",
        metadata_json={"instagram_business_account": {"id": "ig_meta_target_999"}},
        created_at=now - timedelta(days=3),
        updated_at=now - timedelta(days=3)
    )
    # Newer account with linked IG ID in metadata_json
    acc2 = SocialAccount(
        user_id=2,
        platform="instagram",
        account_id="ig_meta_new_id",
        account_name="@ig_meta_2",
        access_token="tok2",
        status="CONNECTED",
        metadata_json={"instagram_business_account": {"id": "ig_meta_target_999"}},
        created_at=now,
        updated_at=now
    )
    db_session.add_all([acc1, acc2])
    db_session.commit()

    payload = json.dumps({
        "object": "instagram",
        "entry": [{
            "id": "ig_meta_target_999",
            "changes": [{
                "field": "comments",
                "value": {
                    "id": "c_fallback_test_1",
                    "text": "Fallback resolution comment"
                }
            }]
        }]
    }).encode("utf-8")

    headers = {"X-Hub-Signature-256": generate_signature(payload)}
    res = client.post("/api/v1/webhooks/meta", data=payload, headers=headers)
    assert res.status_code == 200

    comment = db_session.query(SocialComment).filter_by(external_comment_id="c_fallback_test_1").first()
    assert comment is not None
    assert comment.user_id == 2
    assert comment.social_account_id == acc2.id


def test_resolution_logging(client, db_session, caplog):
    """
    Test I: Verify the structured [META_WEBHOOK_ACCOUNT_RESOLVED] log is emitted
    with platform, external account ID, social account ID, user ID, brand ID, and account name.
    """
    import logging
    social_account_repo.create_or_update(
        db=db_session, user_id=5, platform="instagram", account_id="ig_log_acc_5", account_name="@log_test", access_token="tok"
    )

    payload = json.dumps({
        "object": "instagram",
        "entry": [{
            "id": "ig_log_acc_5",
            "changes": [{
                "field": "comments",
                "value": {"id": "c_log_1", "text": "Log test"}
            }]
        }]
    }).encode("utf-8")

    headers = {"X-Hub-Signature-256": generate_signature(payload)}
    with caplog.at_level(logging.INFO):
        res = client.post("/api/v1/webhooks/meta", data=payload, headers=headers)
        assert res.status_code == 200
        assert "[META_WEBHOOK_ACCOUNT_RESOLVED]" in caplog.text
        assert "platform=instagram" in caplog.text
        assert "external_account_id=ig_log_acc_5" in caplog.text
        assert "user_id=5" in caplog.text
        assert "account_name=@log_test" in caplog.text


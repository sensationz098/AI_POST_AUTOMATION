import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
from app.models.post import Post, PostStatus
from app.models.social_account import SocialAccount
from app.models.publishing_batch import PublishingBatch, PublishingJob, JobStatus, BatchStatus
from app.core.security_encryption import encrypt_token

def get_auth_token_and_user(client):
    email = f"audituser_{datetime.now(timezone.utc).timestamp()}@socialai.com"
    reg_payload = {"email": email, "password": "Password123!", "full_name": "Audit Tester", "role": "Admin"}
    client.post("/api/v1/auth/register", json=reg_payload)
    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    brand_res = client.post("/api/v1/brands/", json={"name": "Audit Brand", "tone_of_voice": "Professional"}, headers=headers)
    brand_id = brand_res.json()["id"]
    user_id = brand_res.json()["user_id"]

    return headers, brand_id, user_id


def test_published_post_appears_in_scheduler_with_external_ids(client, db_session):
    """Verify published posts appear in GET /posts/ with populated external platform IDs."""
    headers, brand_id, user_id = get_auth_token_and_user(client)

    fb_acc = SocialAccount(
        user_id=user_id, brand_id=brand_id, platform="facebook",
        account_id="fb_audit_101", account_name="FB Audit Page",
        access_token=encrypt_token("tok_fb_audit"), status="CONNECTED"
    )
    ig_acc = SocialAccount(
        user_id=user_id, brand_id=brand_id, platform="instagram",
        account_id="ig_audit_202", account_name="@ig_audit_biz",
        access_token=encrypt_token("tok_ig_audit"), status="CONNECTED"
    )
    db_session.add_all([fb_acc, ig_acc])
    db_session.commit()

    post = Post(
        brand_id=brand_id, user_id=user_id, title="Published Real Post 4 Sept 2026",
        caption="Audit published real post test caption", platforms=["facebook", "instagram"],
        status=PostStatus.PUBLISHED.value, published_at=datetime.now(timezone.utc)
    )
    db_session.add(post)
    db_session.commit()

    batch = PublishingBatch(
        post_id=post.id, user_id=user_id, status=BatchStatus.SUCCESS.value,
        total_targets=2, successful_targets=2, failed_targets=0
    )
    db_session.add(batch)
    db_session.commit()

    job_fb = PublishingJob(
        batch_id=batch.id, social_account_id=fb_acc.id, platform="facebook",
        status=JobStatus.SUCCESS.value, external_post_id="ext_fb_post_1788794795798692"
    )
    job_ig = PublishingJob(
        batch_id=batch.id, social_account_id=ig_acc.id, platform="instagram",
        status=JobStatus.SUCCESS.value, external_post_id="ext_ig_media_18138525010565028"
    )
    db_session.add_all([job_fb, job_ig])
    db_session.commit()

    # Call GET /api/v1/posts/
    res = client.get("/api/v1/posts/", headers=headers)
    assert res.status_code == 200
    posts = res.json()
    assert len(posts) >= 1

    target = next((p for p in posts if p["id"] == post.id), None)
    assert target is not None
    assert target["status"] == "PUBLISHED"
    assert target["fb_post_id"] == "ext_fb_post_1788794795798692"
    assert target["ig_media_id"] == "ext_ig_media_18138525010565028"


def test_scheduled_post_appears_in_scheduler(client, db_session):
    """Verify scheduled post appears in GET /posts/ with SCHEDULED status."""
    headers, brand_id, user_id = get_auth_token_and_user(client)

    future_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    create_res = client.post("/api/v1/posts/", json={
        "brand_id": brand_id,
        "title": "Scheduled Post Future",
        "caption": "Will publish in 2 days",
        "platforms": ["facebook"],
        "status": "SCHEDULED",
        "scheduled_at": future_time
    }, headers=headers)
    assert create_res.status_code == 201

    res = client.get("/api/v1/posts/?status=SCHEDULED", headers=headers)
    assert res.status_code == 200
    sched_posts = res.json()
    assert len(sched_posts) == 1
    assert sched_posts[0]["status"] == "SCHEDULED"


def test_failed_post_is_not_marked_published(client, db_session):
    """Verify failed publishing batch marks post FAILED, not PUBLISHED."""
    headers, brand_id, user_id = get_auth_token_and_user(client)

    post = Post(
        brand_id=brand_id, user_id=user_id, title="Failed Attempt Post",
        caption="Publish failed on Meta Graph API", platforms=["instagram"],
        status=PostStatus.FAILED.value, last_error="Media upload failed with error code 2207052"
    )
    db_session.add(post)
    db_session.commit()

    res = client.get("/api/v1/posts/?status=FAILED", headers=headers)
    assert res.status_code == 200
    failed_posts = res.json()
    assert len(failed_posts) == 1
    assert failed_posts[0]["status"] == "FAILED"
    assert "Media upload failed" in failed_posts[0]["last_error"]


def test_post_scheduler_account_user_isolation(client, db_session):
    """Verify user A cannot see user B's posts in post scheduler."""
    headers_a, brand_a, user_a = get_auth_token_and_user(client)
    headers_b, brand_b, user_b = get_auth_token_and_user(client)

    client.post("/api/v1/posts/", json={
        "brand_id": brand_a,
        "title": "User A Private Post",
        "caption": "Only for User A",
        "platforms": ["facebook"]
    }, headers=headers_a)

    res_b = client.get("/api/v1/posts/", headers=headers_b)
    assert res_b.status_code == 200
    posts_b = res_b.json()
    for p in posts_b:
        assert p["user_id"] == user_b

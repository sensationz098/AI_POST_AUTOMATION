import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
from app.models.post import Post, PostStatus
from app.models.social_account import SocialAccount
from app.models.publishing_batch import PublishingBatch, PublishingJob, JobStatus, BatchStatus
from app.models.external_post_context import ExternalPostContext
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
    """Verify published posts appear in GET /posts/ with populated external platform IDs & URLs."""
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

    res = client.get("/api/v1/posts/", headers=headers)
    assert res.status_code == 200
    posts = res.json()

    target = next((p for p in posts if p["id"] == post.id), None)
    assert target is not None
    assert target["status"] == "PUBLISHED"
    assert target["fb_post_id"] == "ext_fb_post_1788794795798692"
    assert target["ig_media_id"] == "ext_ig_media_18138525010565028"
    assert target["fb_post_url"] == "https://www.facebook.com/ext_fb_post_1788794795798692"
    assert target["ig_media_url"] == "https://www.instagram.com/p/ext_ig_media_18138525010565028"


def test_published_facebook_only_post_view_url(client, db_session):
    """Test A: Published Facebook-only post exposes Facebook URL and null Instagram URL."""
    headers, brand_id, user_id = get_auth_token_and_user(client)

    post = Post(
        brand_id=brand_id, user_id=user_id, title="Facebook Only Post",
        caption="FB only caption", platforms=["facebook"],
        status=PostStatus.PUBLISHED.value, fb_post_id="fb_only_998877"
    )
    db_session.add(post)
    db_session.commit()

    res = client.get("/api/v1/posts/", headers=headers)
    assert res.status_code == 200
    target = next(p for p in res.json() if p["id"] == post.id)

    assert target["fb_post_id"] == "fb_only_998877"
    assert target["fb_post_url"] == "https://www.facebook.com/fb_only_998877"
    assert target["ig_media_id"] is None
    assert target["ig_media_url"] is None


def test_published_instagram_only_post_view_url(client, db_session):
    """Test B: Published Instagram-only post exposes Instagram URL and null Facebook URL."""
    headers, brand_id, user_id = get_auth_token_and_user(client)

    post = Post(
        brand_id=brand_id, user_id=user_id, title="Instagram Only Post",
        caption="IG only caption", platforms=["instagram"],
        status=PostStatus.PUBLISHED.value, ig_media_id="ig_only_112233"
    )
    db_session.add(post)
    db_session.commit()

    res = client.get("/api/v1/posts/", headers=headers)
    assert res.status_code == 200
    target = next(p for p in res.json() if p["id"] == post.id)

    assert target["ig_media_id"] == "ig_only_112233"
    assert target["ig_media_url"] == "https://www.instagram.com/p/ig_only_112233"
    assert target["fb_post_id"] is None
    assert target["fb_post_url"] is None


def test_partial_failure_platform_view_urls(client, db_session):
    """Test D: Facebook succeeded + Instagram failed exposes only Facebook option."""
    headers, brand_id, user_id = get_auth_token_and_user(client)

    fb_acc = SocialAccount(
        user_id=user_id, brand_id=brand_id, platform="facebook",
        account_id="fb_part_1", account_name="FB Page",
        access_token=encrypt_token("tok_fb"), status="CONNECTED"
    )
    ig_acc = SocialAccount(
        user_id=user_id, brand_id=brand_id, platform="instagram",
        account_id="ig_part_2", account_name="@ig_page",
        access_token=encrypt_token("tok_ig"), status="CONNECTED"
    )
    db_session.add_all([fb_acc, ig_acc])
    db_session.commit()

    post = Post(
        brand_id=brand_id, user_id=user_id, title="Partial Fail Post",
        caption="FB success, IG fail", platforms=["facebook", "instagram"],
        status=PostStatus.FAILED.value
    )
    db_session.add(post)
    db_session.commit()

    batch = PublishingBatch(
        post_id=post.id, user_id=user_id, status=BatchStatus.PARTIAL_SUCCESS.value,
        total_targets=2, successful_targets=1, failed_targets=1
    )
    db_session.add(batch)
    db_session.commit()

    job_fb = PublishingJob(
        batch_id=batch.id, social_account_id=fb_acc.id, platform="facebook",
        status=JobStatus.SUCCESS.value, external_post_id="fb_partial_succ_123"
    )
    job_ig = PublishingJob(
        batch_id=batch.id, social_account_id=ig_acc.id, platform="instagram",
        status=JobStatus.FAILED.value, error_message="Media container creation failed"
    )
    db_session.add_all([job_fb, job_ig])
    db_session.commit()

    res = client.get("/api/v1/posts/", headers=headers)
    assert res.status_code == 200
    target = next(p for p in res.json() if p["id"] == post.id)

    # FB succeeded -> URL present
    assert target["fb_post_id"] == "fb_partial_succ_123"
    assert target["fb_post_url"] == "https://www.facebook.com/fb_partial_succ_123"
    # IG failed -> URL null
    assert target["ig_media_id"] is None
    assert target["ig_media_url"] is None


def test_canonical_permalink_resolution_from_context(client, db_session):
    """Verify permalink stored in ExternalPostContext overrides generic URL construction."""
    headers, brand_id, user_id = get_auth_token_and_user(client)

    post = Post(
        brand_id=brand_id, user_id=user_id, title="Canonical Reel Post",
        caption="Reel caption", platforms=["instagram"],
        status=PostStatus.PUBLISHED.value, ig_media_id="ig_reel_8877"
    )
    db_session.add(post)
    db_session.commit()

    ctx = ExternalPostContext(
        external_post_id="ig_reel_8877",
        social_account_id=1,
        platform="instagram",
        permalink="https://www.instagram.com/reel/Dc29nviDbdd/"
    )
    db_session.add(ctx)
    db_session.commit()

    res = client.get("/api/v1/posts/", headers=headers)
    assert res.status_code == 200
    target = next(p for p in res.json() if p["id"] == post.id)

    assert target["ig_media_url"] == "https://www.instagram.com/reel/Dc29nviDbdd/"


def test_draft_scheduled_failed_post_urls_null(client, db_session):
    """Test E & F: Draft, scheduled, and un-published failed posts return null URLs."""
    headers, brand_id, user_id = get_auth_token_and_user(client)

    future_time = datetime.now(timezone.utc) + timedelta(days=2)
    draft = Post(brand_id=brand_id, user_id=user_id, title="Draft Post", caption="Draft", platforms=["facebook"], status="DRAFT")
    sched = Post(brand_id=brand_id, user_id=user_id, title="Sched Post", caption="Sched", platforms=["facebook"], status="SCHEDULED", scheduled_at=future_time)
    failed = Post(brand_id=brand_id, user_id=user_id, title="Fail Post", caption="Fail", platforms=["facebook"], status="FAILED")
    db_session.add_all([draft, sched, failed])
    db_session.commit()

    res = client.get("/api/v1/posts/", headers=headers)
    assert res.status_code == 200
    posts = res.json()

    for p in posts:
        if p["id"] in [draft.id, sched.id, failed.id]:
            assert p["fb_post_url"] is None
            assert p["ig_media_url"] is None


def test_post_scheduler_account_user_isolation(client, db_session):
    """Test H: Verify user A cannot see or obtain user B's post URLs."""
    headers_a, brand_a, user_a = get_auth_token_and_user(client)
    headers_b, brand_b, user_b = get_auth_token_and_user(client)

    post_a = Post(
        brand_id=brand_a, user_id=user_a, title="User A Post",
        caption="Secret A", platforms=["facebook"], status="PUBLISHED",
        fb_post_id="secret_a_123"
    )
    db_session.add(post_a)
    db_session.commit()

    res_b = client.get("/api/v1/posts/", headers=headers_b)
    assert res_b.status_code == 200
    posts_b = res_b.json()
    assert not any(p["id"] == post_a.id for p in posts_b)

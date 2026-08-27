import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from app.models.post import Post, PostStatus
from app.models.social_account import SocialAccount
from app.models.publishing_batch import PublishingBatch, PublishingJob, JobStatus, BatchStatus
from app.core.security_encryption import encrypt_token
from app.services.post_service import post_service

def get_auth_token_and_user(client):
    email = f"deleteuser_{datetime.utcnow().timestamp()}@socialai.com"
    reg_payload = {"email": email, "password": "Password123!", "full_name": "Deletion Tester", "role": "Admin"}
    client.post("/api/v1/auth/register", json=reg_payload)
    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    brand_res = client.post("/api/v1/brands/", json={"name": "Delete Brand", "tone_of_voice": "Friendly"}, headers=headers)
    brand_id = brand_res.json()["id"]
    user_id = brand_res.json()["user_id"]

    return headers, brand_id, user_id

def test_owner_can_delete_draft(client, db_session):
    headers, brand_id, user_id = get_auth_token_and_user(client)

    post_res = client.post("/api/v1/posts/", json={
        "brand_id": brand_id,
        "title": "Draft Post to Delete",
        "caption": "Testing draft deletion",
        "platforms": ["facebook"]
    }, headers=headers)
    assert post_res.status_code == 201
    post_id = post_res.json()["id"]

    # Delete draft post
    del_res = client.delete(f"/api/v1/posts/{post_id}", headers=headers)
    assert del_res.status_code == 200
    res_data = del_res.json()
    assert res_data["success"] is True
    assert res_data["post_id"] == post_id

    # Verify post is removed from database
    db_post = db_session.query(Post).filter(Post.id == post_id).first()
    assert db_post is None

def test_non_owner_cannot_delete_other_user_post(client, db_session):
    headers1, brand_id1, user_id1 = get_auth_token_and_user(client)
    headers2, brand_id2, user_id2 = get_auth_token_and_user(client)

    # User 1 creates post
    post_res = client.post("/api/v1/posts/", json={
        "brand_id": brand_id1,
        "title": "User 1 Private Post",
        "caption": "Do not touch",
        "platforms": ["facebook"]
    }, headers=headers1)
    post_id = post_res.json()["id"]

    # User 2 attempts to delete User 1's post
    del_res = client.delete(f"/api/v1/posts/{post_id}", headers=headers2)
    assert del_res.status_code == 404

    # Verify post remains in database
    db_post = db_session.query(Post).filter(Post.id == post_id).first()
    assert db_post is not None
    assert db_post.user_id == user_id1

def test_delete_published_facebook_post(client, db_session):
    headers, brand_id, user_id = get_auth_token_and_user(client)

    # Create connected Facebook account
    soc_acc = SocialAccount(
        user_id=user_id,
        brand_id=brand_id,
        platform="facebook",
        account_id="fb_acc_1001",
        account_name="Facebook Brand Page",
        access_token=encrypt_token("fb_secret_token_123"),
        status="CONNECTED"
    )
    db_session.add(soc_acc)
    db_session.commit()

    # Create published post
    post = Post(
        brand_id=brand_id,
        user_id=user_id,
        title="Published FB Post",
        caption="Live on FB",
        platforms=["facebook"],
        status=PostStatus.PUBLISHED.value,
        fb_post_id="1001_998877"
    )
    db_session.add(post)
    db_session.commit()

    with patch("app.services.meta_service.meta_service.delete_facebook_post", return_value={"success": True, "status": "deleted"}) as mock_delete:
        del_res = client.delete(f"/api/v1/posts/{post.id}", headers=headers)
        assert del_res.status_code == 200
        res_data = del_res.json()
        assert res_data["success"] is True
        assert res_data["deleted_external_targets"] == 1
        assert res_data["failed_external_targets"] == 0

        mock_delete.assert_called_once_with("1001_998877", "fb_secret_token_123")

    # Verify post is deleted from DB
    db_post = db_session.query(Post).filter(Post.id == post.id).first()
    assert db_post is None

def test_delete_published_instagram_post(client, db_session):
    headers, brand_id, user_id = get_auth_token_and_user(client)

    soc_acc = SocialAccount(
        user_id=user_id,
        brand_id=brand_id,
        platform="instagram",
        account_id="ig_acc_2002",
        account_name="@ig_brand_biz",
        access_token=encrypt_token("ig_secret_token_456"),
        status="CONNECTED"
    )
    db_session.add(soc_acc)
    db_session.commit()

    post = Post(
        brand_id=brand_id,
        user_id=user_id,
        title="Published IG Reel",
        caption="Live on IG",
        platforms=["instagram"],
        status=PostStatus.PUBLISHED.value,
        ig_media_id="17841400928371999"
    )
    db_session.add(post)
    db_session.commit()

    with patch("app.services.meta_service.meta_service.delete_instagram_media", return_value={"success": True, "status": "deleted"}) as mock_delete:
        del_res = client.delete(f"/api/v1/posts/{post.id}", headers=headers)
        assert del_res.status_code == 200
        res_data = del_res.json()
        assert res_data["success"] is True
        assert res_data["deleted_external_targets"] == 1
        assert res_data["failed_external_targets"] == 0

        mock_delete.assert_called_once_with("17841400928371999", "ig_secret_token_456")

    db_post = db_session.query(Post).filter(Post.id == post.id).first()
    assert db_post is None

def test_delete_multi_account_post(client, db_session):
    headers, brand_id, user_id = get_auth_token_and_user(client)

    fb_acc = SocialAccount(
        user_id=user_id, brand_id=brand_id, platform="facebook",
        account_id="fb_multi_1", account_name="FB Multi 1",
        access_token=encrypt_token("tok_fb_multi"), status="CONNECTED"
    )
    ig_acc = SocialAccount(
        user_id=user_id, brand_id=brand_id, platform="instagram",
        account_id="ig_multi_1", account_name="@ig_multi_1",
        access_token=encrypt_token("tok_ig_multi"), status="CONNECTED"
    )
    db_session.add_all([fb_acc, ig_acc])
    db_session.commit()

    post = Post(
        brand_id=brand_id, user_id=user_id, title="Multi Post",
        caption="Published to 2 accounts", platforms=["facebook", "instagram"],
        status=PostStatus.PUBLISHED.value
    )
    db_session.add(post)
    db_session.commit()

    batch = PublishingBatch(
        post_id=post.id, user_id=user_id, status=BatchStatus.SUCCESS.value,
        total_targets=2, successful_targets=2, failed_targets=0
    )
    db_session.add(batch)
    db_session.commit()

    job1 = PublishingJob(
        batch_id=batch.id, social_account_id=fb_acc.id, platform="facebook",
        status=JobStatus.SUCCESS.value, external_post_id="ext_fb_111", attempts=1
    )
    job2 = PublishingJob(
        batch_id=batch.id, social_account_id=ig_acc.id, platform="instagram",
        status=JobStatus.SUCCESS.value, external_post_id="ext_ig_222", attempts=1
    )
    db_session.add_all([job1, job2])
    db_session.commit()

    with patch("app.services.meta_service.meta_service.delete_facebook_post", return_value={"success": True}) as mock_fb, \
         patch("app.services.meta_service.meta_service.delete_instagram_media", return_value={"success": True}) as mock_ig:
        
        del_res = client.delete(f"/api/v1/posts/{post.id}", headers=headers)
        assert del_res.status_code == 200
        res_data = del_res.json()
        assert res_data["success"] is True
        assert res_data["deleted_external_targets"] == 2
        assert res_data["failed_external_targets"] == 0

        mock_fb.assert_called_once_with("ext_fb_111", "tok_fb_multi")
        mock_ig.assert_called_once_with("ext_ig_222", "tok_ig_multi")

    # Verify post and batches deleted from DB
    assert db_session.query(Post).filter(Post.id == post.id).first() is None
    assert db_session.query(PublishingBatch).filter(PublishingBatch.post_id == post.id).first() is None

def test_partial_external_deletion_failure(client, db_session):
    headers, brand_id, user_id = get_auth_token_and_user(client)

    fb_acc = SocialAccount(
        user_id=user_id, brand_id=brand_id, platform="facebook",
        account_id="fb_part_1", account_name="FB Partial",
        access_token=encrypt_token("tok_fb_part"), status="CONNECTED"
    )
    ig_acc = SocialAccount(
        user_id=user_id, brand_id=brand_id, platform="instagram",
        account_id="ig_part_1", account_name="@ig_partial",
        access_token=encrypt_token("tok_ig_part"), status="CONNECTED"
    )
    db_session.add_all([fb_acc, ig_acc])
    db_session.commit()

    post = Post(
        brand_id=brand_id, user_id=user_id, title="Partial Fail Post",
        caption="Testing partial failure", platforms=["facebook", "instagram"],
        status=PostStatus.PUBLISHED.value
    )
    db_session.add(post)
    db_session.commit()

    batch = PublishingBatch(
        post_id=post.id, user_id=user_id, status=BatchStatus.SUCCESS.value,
        total_targets=2, successful_targets=2, failed_targets=0
    )
    db_session.add(batch)
    db_session.commit()

    job1 = PublishingJob(
        batch_id=batch.id, social_account_id=fb_acc.id, platform="facebook",
        status=JobStatus.SUCCESS.value, external_post_id="ext_fb_succ", attempts=1
    )
    job2 = PublishingJob(
        batch_id=batch.id, social_account_id=ig_acc.id, platform="instagram",
        status=JobStatus.SUCCESS.value, external_post_id="ext_ig_fail", attempts=1
    )
    db_session.add_all([job1, job2])
    db_session.commit()

    with patch("app.services.meta_service.meta_service.delete_facebook_post", return_value={"success": True}), \
         patch("app.services.meta_service.meta_service.delete_instagram_media", side_effect=Exception("Meta Graph API error: Object rate limited")):
        
        del_res = client.delete(f"/api/v1/posts/{post.id}", headers=headers)
        assert del_res.status_code == 200
        res_data = del_res.json()
        assert res_data["success"] is False
        assert res_data["deleted_external_targets"] == 1
        assert res_data["failed_external_targets"] == 1
        assert len(res_data["details"]) == 2

    # CRITICAL SECURITY RULE: Post MUST remain in DB when external deletion fails!
    db_post = db_session.query(Post).filter(Post.id == post.id).first()
    assert db_post is not None
    assert "Deletion failed" in db_post.last_error

def test_missing_external_post_id(client, db_session):
    headers, brand_id, user_id = get_auth_token_and_user(client)

    post = Post(
        brand_id=brand_id, user_id=user_id, title="No External ID Post",
        caption="Published but no IDs", platforms=["facebook"],
        status=PostStatus.PUBLISHED.value, fb_post_id=None, ig_media_id=None
    )
    db_session.add(post)
    db_session.commit()

    del_res = client.delete(f"/api/v1/posts/{post.id}", headers=headers)
    assert del_res.status_code == 200
    res_data = del_res.json()
    assert res_data["success"] is True

    assert db_session.query(Post).filter(Post.id == post.id).first() is None

def test_already_deleted_external_post_idempotent(client, db_session):
    headers, brand_id, user_id = get_auth_token_and_user(client)

    soc_acc = SocialAccount(
        user_id=user_id, brand_id=brand_id, platform="facebook",
        account_id="fb_idemp_acc", account_name="FB Idempotent",
        access_token=encrypt_token("tok_idemp"), status="CONNECTED"
    )
    db_session.add(soc_acc)
    db_session.commit()

    post = Post(
        brand_id=brand_id, user_id=user_id, title="Already Deleted Post",
        caption="Object gone on FB", platforms=["facebook"],
        status=PostStatus.PUBLISHED.value, fb_post_id="ext_already_gone_99"
    )
    db_session.add(post)
    db_session.commit()

    with patch("app.services.meta_service.meta_service.delete_facebook_post", return_value={"success": True, "already_deleted": True}):
        del_res = client.delete(f"/api/v1/posts/{post.id}", headers=headers)
        assert del_res.status_code == 200
        res_data = del_res.json()
        assert res_data["success"] is True
        assert res_data["deleted_external_targets"] == 1

    assert db_session.query(Post).filter(Post.id == post.id).first() is None

def test_scheduled_post_deletion_prevents_publishing(client, db_session):
    headers, brand_id, user_id = get_auth_token_and_user(client)

    due_time = datetime.utcnow() - timedelta(minutes=5)
    post = Post(
        brand_id=brand_id, user_id=user_id, title="Scheduled Post to Cancel",
        caption="Should not publish", platforms=["facebook"],
        status=PostStatus.SCHEDULED.value, scheduled_at=due_time
    )
    db_session.add(post)
    db_session.commit()

    # Delete scheduled post
    del_res = client.delete(f"/api/v1/posts/{post.id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # Check that post service does not return or publish it
    published_posts = post_service.check_and_publish_due_posts(db_session, user_id=user_id)
    assert len(published_posts) == 0

def test_token_decryption_used_in_deletion(client, db_session):
    headers, brand_id, user_id = get_auth_token_and_user(client)

    secret_raw_token = "EAANNCr_SUPER_SECRET_RAW_TOKEN_99"
    enc_tok = encrypt_token(secret_raw_token)

    soc_acc = SocialAccount(
        user_id=user_id, brand_id=brand_id, platform="facebook",
        account_id="fb_tok_dec_acc", account_name="FB Token Decrypt Acc",
        access_token=enc_tok, status="CONNECTED"
    )
    db_session.add(soc_acc)
    db_session.commit()

    post = Post(
        brand_id=brand_id, user_id=user_id, title="Encrypted Token Post",
        caption="Secret token test", platforms=["facebook"],
        status=PostStatus.PUBLISHED.value, fb_post_id="ext_secret_fb_post"
    )
    db_session.add(post)
    db_session.commit()

    with patch("app.services.meta_service.meta_service.delete_facebook_post", return_value={"success": True}) as mock_delete:
        del_res = client.delete(f"/api/v1/posts/{post.id}", headers=headers)
        assert del_res.status_code == 200
        assert del_res.json()["success"] is True

        # Verify decrypted token was passed to meta_service.delete_facebook_post
        mock_delete.assert_called_once_with("ext_secret_fb_post", secret_raw_token)

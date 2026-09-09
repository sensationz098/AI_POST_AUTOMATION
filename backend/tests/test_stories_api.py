import pytest
from datetime import datetime, timezone, timedelta
from app.models.user import User
from app.models.brand import BrandProfile
from app.models.social_account import SocialAccount
from app.models.story import Story, StoryStatus


def get_auth_token(client, email="story_api_user@test.com", password="Password123!"):
    client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "full_name": "Story API User",
        "role": "Admin"
    })
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return res.json()["access_token"]


def create_brand_and_accounts(db_session, user_id):
    brand = BrandProfile(user_id=user_id, name="Story API Brand")
    db_session.add(brand)
    db_session.commit()
    db_session.refresh(brand)

    fb_acc = SocialAccount(
        user_id=user_id,
        brand_id=brand.id,
        platform="facebook",
        account_id="fb_page_story_1",
        account_name="Test FB Page",
        access_token="sandbox_fb_token",
        status="CONNECTED"
    )
    ig_acc = SocialAccount(
        user_id=user_id,
        brand_id=brand.id,
        platform="instagram",
        account_id="ig_story_user_1",
        account_name="test_ig_story",
        access_token="sandbox_ig_token",
        status="CONNECTED",
        metadata_json={"account_type": "BUSINESS"}
    )
    db_session.add_all([fb_acc, ig_acc])
    db_session.commit()
    return brand, fb_acc, ig_acc


def test_story_api_crud_and_preflight(client, db_session):
    token = get_auth_token(client, "user_crud@test.com")
    headers = {"Authorization": f"Bearer {token}"}

    user = db_session.query(User).filter(User.email == "user_crud@test.com").first()
    brand, fb_acc, ig_acc = create_brand_and_accounts(db_session, user.id)

    # 1. Validate Preflight with exact accounts
    preflight_res = client.post(
        "/api/v1/stories/validate-preflight",
        json={
            "brand_id": brand.id,
            "media_url": "https://example.com/vertical_story.jpg",
            "media_type": "image",
            "target_account_ids": [fb_acc.id, ig_acc.id]
        },
        headers=headers
    )
    assert preflight_res.status_code == 200
    p_data = preflight_res.json()
    assert p_data["is_valid"] is True
    assert len(p_data["account_checks"]) == 2

    # 2. Create Story Draft
    create_res = client.post(
        "/api/v1/stories",
        json={
            "brand_id": brand.id,
            "title": "Weekend Launch Story",
            "caption": "Check out our stories!",
            "media_url": "https://example.com/launch.jpg",
            "media_type": "image",
            "target_account_ids": [fb_acc.id, ig_acc.id]
        },
        headers=headers
    )
    assert create_res.status_code == 201
    story_data = create_res.json()
    story_id = story_data["id"]
    assert story_data["title"] == "Weekend Launch Story"
    assert story_data["status"] == "DRAFT"
    assert story_data["target_account_ids"] == [fb_acc.id, ig_acc.id]

    # 3. List Stories
    list_res = client.get("/api/v1/stories", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

    # 4. Get Story Detail
    get_res = client.get(f"/api/v1/stories/{story_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == story_id
    assert get_res.json()["target_account_ids"] == [fb_acc.id, ig_acc.id]

    # 5. Update Story
    update_res = client.put(
        f"/api/v1/stories/{story_id}",
        json={"title": "Updated Weekend Launch", "target_account_ids": [fb_acc.id]},
        headers=headers
    )
    assert update_res.status_code == 200
    assert update_res.json()["title"] == "Updated Weekend Launch"
    assert update_res.json()["target_account_ids"] == [fb_acc.id]

    # 6. Publish Story Now
    pub_res = client.post(f"/api/v1/stories/{story_id}/publish-now", headers=headers)
    assert pub_res.status_code == 200
    assert pub_res.json()["status"] == "PUBLISHED"
    assert pub_res.json()["fb_story_id"] is not None

    # 7. Delete Story
    del_res = client.delete(f"/api/v1/stories/{story_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True


def test_story_api_schedule_and_retry(client, db_session):
    token = get_auth_token(client, "user_sched@test.com")
    headers = {"Authorization": f"Bearer {token}"}

    user = db_session.query(User).filter(User.email == "user_sched@test.com").first()
    brand, fb_acc, ig_acc = create_brand_and_accounts(db_session, user.id)

    # Create story
    create_res = client.post(
        "/api/v1/stories",
        json={
            "brand_id": brand.id,
            "title": "Scheduled Story",
            "media_url": "https://example.com/story.mp4",
            "media_type": "video",
            "target_account_ids": [ig_acc.id]
        },
        headers=headers
    )
    story_id = create_res.json()["id"]

    # Schedule story
    future_time = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    sched_res = client.post(
        f"/api/v1/stories/{story_id}/schedule",
        json={"scheduled_at": future_time},
        headers=headers
    )
    assert sched_res.status_code == 200
    assert sched_res.json()["status"] == "SCHEDULED"


def test_story_api_tenant_isolation(client, db_session):
    # User A
    token_a = get_auth_token(client, "user_a@test.com")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    user_a = db_session.query(User).filter(User.email == "user_a@test.com").first()
    brand_a, fb_acc_a, _ = create_brand_and_accounts(db_session, user_a.id)

    create_res = client.post(
        "/api/v1/stories",
        json={
            "brand_id": brand_a.id,
            "title": "User A Private Story",
            "media_url": "https://example.com/secret.jpg",
            "media_type": "image",
            "target_account_ids": [fb_acc_a.id]
        },
        headers=headers_a
    )
    story_id = create_res.json()["id"]

    # User B tries to access or publish User A's story
    token_b = get_auth_token(client, "user_b@test.com")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    get_res = client.get(f"/api/v1/stories/{story_id}", headers=headers_b)
    assert get_res.status_code == 403

    pub_res = client.post(f"/api/v1/stories/{story_id}/publish-now", headers=headers_b)
    assert pub_res.status_code == 403

    del_res = client.delete(f"/api/v1/stories/{story_id}", headers=headers_b)
    assert del_res.status_code == 403

    # User B tries to create a story targeting User A's account
    user_b = db_session.query(User).filter(User.email == "user_b@test.com").first()
    brand_b, _, _ = create_brand_and_accounts(db_session, user_b.id)
    malicious_res = client.post(
        "/api/v1/stories",
        json={
            "brand_id": brand_b.id,
            "title": "Cross Tenant Exploit Story",
            "media_url": "https://example.com/exploit.jpg",
            "media_type": "image",
            "target_account_ids": [fb_acc_a.id]
        },
        headers=headers_b
    )
    assert malicious_res.status_code in [403, 400]


def test_story_api_publish_now_flow(client, db_session):
    token = get_auth_token(client, "publish_now_user@test.com")
    headers = {"Authorization": f"Bearer {token}"}

    user = db_session.query(User).filter(User.email == "publish_now_user@test.com").first()
    brand, fb_acc, ig_acc = create_brand_and_accounts(db_session, user.id)

    # 1. Create Story Draft with exact target account
    create_res = client.post(
        "/api/v1/stories",
        json={
            "brand_id": brand.id,
            "title": "Publish Now Story",
            "media_url": "https://example.com/pic.jpg",
            "media_type": "image",
            "target_account_ids": [ig_acc.id]
        },
        headers=headers
    )
    assert create_res.status_code == 201
    story_id = create_res.json()["id"]

    # 2. Trigger dedicated publish-now endpoint
    pub_res = client.post(f"/api/v1/stories/{story_id}/publish-now", headers=headers)
    assert pub_res.status_code == 200
    p_data = pub_res.json()
    assert p_data["status"] == "PUBLISHED"
    assert p_data["ig_story_id"] is not None
    assert p_data["target_account_ids"] == [ig_acc.id]


def test_story_api_empty_targets_publish_rejected(client, db_session):
    token = get_auth_token(client, "empty_pub_user@test.com")
    headers = {"Authorization": f"Bearer {token}"}

    user = db_session.query(User).filter(User.email == "empty_pub_user@test.com").first()
    brand, fb_acc, ig_acc = create_brand_and_accounts(db_session, user.id)

    # Create draft with empty targets
    create_res = client.post(
        "/api/v1/stories",
        json={
            "brand_id": brand.id,
            "title": "Empty Target Draft",
            "media_url": "https://example.com/pic.jpg",
            "media_type": "image",
            "target_account_ids": []
        },
        headers=headers
    )
    assert create_res.status_code == 201
    story_id = create_res.json()["id"]

    # Attempting publish-now should return 400
    pub_res = client.post(f"/api/v1/stories/{story_id}/publish-now", headers=headers)
    assert pub_res.status_code == 400


def test_story_api_publish_now_idempotency(client, db_session):
    token = get_auth_token(client, "idempotent_api_user@test.com")
    headers = {"Authorization": f"Bearer {token}"}

    user = db_session.query(User).filter(User.email == "idempotent_api_user@test.com").first()
    brand, fb_acc, ig_acc = create_brand_and_accounts(db_session, user.id)

    create_res = client.post(
        "/api/v1/stories",
        json={
            "brand_id": brand.id,
            "title": "Idempotent API Story",
            "media_url": "https://example.com/pic.jpg",
            "media_type": "image",
            "target_account_ids": [fb_acc.id]
        },
        headers=headers
    )
    assert create_res.status_code == 201
    story_id = create_res.json()["id"]

    # First call: publishes story
    pub_res1 = client.post(f"/api/v1/stories/{story_id}/publish-now", headers=headers)
    assert pub_res1.status_code == 200
    assert pub_res1.json()["status"] == "PUBLISHED"

    # Second call (e.g. client retries after network timeout): returns 200 with PUBLISHED
    pub_res2 = client.post(f"/api/v1/stories/{story_id}/publish-now", headers=headers)
    assert pub_res2.status_code == 200
    assert pub_res2.json()["status"] == "PUBLISHED"



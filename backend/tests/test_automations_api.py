import pytest
from app.models.user import User
from app.models.social_account import SocialAccount
from app.models.brand import BrandProfile
from app.models.post import Post, PostStatus
from app.models.automation import Automation, AutomationStatus, TriggerType, PostTargetType
from app.models.automation_execution import AutomationExecution, ExecutionStatus


def get_user_token(client, email="auto_user@example.com", password="Password123!"):
    reg_payload = {
        "email": email,
        "password": password,
        "full_name": "Automation Tester",
        "role": "Editor"
    }
    client.post("/api/v1/auth/register", json=reg_payload)
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return res.json()["access_token"]


def create_user_social_account(db_session, user_id, platform="instagram", account_id="ig_test_1"):
    acc = SocialAccount(
        user_id=user_id,
        platform=platform,
        account_id=account_id,
        account_name=f"Account {platform}",
        access_token="valid_access_token"
    )
    db_session.add(acc)
    db_session.commit()
    db_session.refresh(acc)
    return acc


def create_user_post(db_session, user_id, brand_id=None, external_id="ext_post_100", platform="instagram"):
    if not brand_id:
        brand = BrandProfile(user_id=user_id, name="Test Brand")
        db_session.add(brand)
        db_session.commit()
        db_session.refresh(brand)
        brand_id = brand.id

    post = Post(
        user_id=user_id,
        brand_id=brand_id,
        caption="Check out our new product launch!",
        status=PostStatus.PUBLISHED.value,
        platforms=[platform],
        ig_media_id=external_id if platform == "instagram" else None,
        fb_post_id=external_id if platform == "facebook" else None
    )
    db_session.add(post)
    db_session.commit()
    db_session.refresh(post)
    return post


class TestAutomationAPI:
    """Comprehensive test suite for Phase 2 Automation CRUD, Validation, and Lifecycle Management."""

    def test_01_create_automation_success_draft(self, client, db_session):
        """Test successful creation of an automation defaulting to DRAFT status."""
        token = get_user_token(client, "user1@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        user = db_session.query(User).filter(User.email == "user1@example.com").first()

        account = create_user_social_account(db_session, user.id, platform="instagram", account_id="ig_acc_1")
        post = create_user_post(db_session, user.id, external_id="ig_media_101", platform="instagram")

        payload = {
            "name": "Summer Promo Auto",
            "platform": "instagram",
            "social_account_id": account.id,
            "post_target_type": "SPECIFIC_POST",
            "internal_post_id": post.id,
            "trigger_type": "KEYWORD",
            "trigger_config": {
                "keywords": ["Promo", " DISCOUNT ", "price", "promo"]
            },
            "action_config": {
                "public_reply": {
                    "enabled": True,
                    "variations": ["Thanks! Check your DM 📬", "Sent details to your inbox! ✨"]
                },
                "private_message": {
                    "enabled": True,
                    "message": "Use promo code SUMMER50 for 50% off!"
                }
            }
        }

        res = client.post("/api/v1/automations/", json=payload, headers=headers)
        assert res.status_code == 201
        data = res.json()
        assert data["id"] is not None
        assert data["name"] == "Summer Promo Auto"
        assert data["platform"] == "instagram"
        assert data["status"] == "DRAFT"
        assert data["user_id"] == user.id
        assert data["social_account_id"] == account.id
        assert data["internal_post_id"] == post.id
        assert data["external_post_id"] == "ig_media_101"
        # Check normalized keywords
        assert data["trigger_config"]["keywords"] == ["promo", "discount", "price"]
        assert data["action_config"]["public_reply"]["enabled"] is True
        assert len(data["action_config"]["public_reply"]["variations"]) == 2
        assert data["action_config"]["private_message"]["enabled"] is True

    def test_02_create_facebook_automation(self, client, db_session):
        """Test creating a valid Facebook automation with ANY_COMMENT trigger."""
        token = get_user_token(client, "fb_user@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        user = db_session.query(User).filter(User.email == "fb_user@example.com").first()

        account = create_user_social_account(db_session, user.id, platform="facebook", account_id="fb_page_1")
        post = create_user_post(db_session, user.id, external_id="fb_post_202", platform="facebook")

        payload = {
            "name": "FB Any Comment Auto",
            "platform": "facebook",
            "social_account_id": account.id,
            "post_target_type": "SPECIFIC_POST",
            "internal_post_id": post.id,
            "trigger_type": "ANY_COMMENT",
            "action_config": {
                "public_reply": {
                    "enabled": True,
                    "variations": ["Hello from Facebook Page!"]
                }
            }
        }

        res = client.post("/api/v1/automations/", json=payload, headers=headers)
        assert res.status_code == 201
        data = res.json()
        assert data["platform"] == "facebook"
        assert data["trigger_type"] == "ANY_COMMENT"
        assert data["external_post_id"] == "fb_post_202"

    def test_03_validation_missing_or_invalid_account(self, client, db_session):
        """Test validation rejection on nonexistent or cross-user social accounts."""
        token1 = get_user_token(client, "alice@example.com")
        token2 = get_user_token(client, "bob@example.com")
        user2 = db_session.query(User).filter(User.email == "bob@example.com").first()

        bob_account = create_user_social_account(db_session, user2.id, platform="instagram")

        headers_alice = {"Authorization": f"Bearer {token1}"}

        # 1. Nonexistent account
        payload_nonexistent = {
            "name": "Bad Account Auto",
            "platform": "instagram",
            "social_account_id": 99999,
            "external_post_id": "ext_123",
            "trigger_type": "ANY_COMMENT",
            "action_config": {"public_reply": {"enabled": True, "variations": ["Hi!"]}}
        }
        res1 = client.post("/api/v1/automations/", json=payload_nonexistent, headers=headers_alice)
        assert res1.status_code == 404

        # 2. Cross-user account (Alice trying to use Bob's account)
        payload_cross_user = {
            "name": "Cross User Auto",
            "platform": "instagram",
            "social_account_id": bob_account.id,
            "external_post_id": "ext_123",
            "trigger_type": "ANY_COMMENT",
            "action_config": {"public_reply": {"enabled": True, "variations": ["Hi!"]}}
        }
        res2 = client.post("/api/v1/automations/", json=payload_cross_user, headers=headers_alice)
        assert res2.status_code == 404

    def test_04_validation_mismatched_platform_and_account(self, client, db_session):
        """Test validation rejection when automation platform does not match social account platform."""
        token = get_user_token(client, "mismatch_user@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        user = db_session.query(User).filter(User.email == "mismatch_user@example.com").first()

        fb_account = create_user_social_account(db_session, user.id, platform="facebook")

        # Automation says instagram, but social_account is facebook
        payload = {
            "name": "Mismatched Platform Auto",
            "platform": "instagram",
            "social_account_id": fb_account.id,
            "external_post_id": "ig_123",
            "trigger_type": "ANY_COMMENT",
            "action_config": {"public_reply": {"enabled": True, "variations": ["Hi!"]}}
        }
        res = client.post("/api/v1/automations/", json=payload, headers=headers)
        assert res.status_code == 400
        assert "does not match automation platform" in res.json()["detail"]

    def test_05_validation_target_post(self, client, db_session):
        """Test validation on missing post, nonexistent post, and cross-user post."""
        token_a = get_user_token(client, "user_a@example.com")
        token_b = get_user_token(client, "user_b@example.com")
        user_a = db_session.query(User).filter(User.email == "user_a@example.com").first()
        user_b = db_session.query(User).filter(User.email == "user_b@example.com").first()

        account_a = create_user_social_account(db_session, user_a.id, platform="instagram")
        post_b = create_user_post(db_session, user_b.id, platform="instagram")

        headers_a = {"Authorization": f"Bearer {token_a}"}

        # 1. No post specified
        payload_no_post = {
            "name": "No Post Auto",
            "platform": "instagram",
            "social_account_id": account_a.id,
            "trigger_type": "ANY_COMMENT",
            "action_config": {"public_reply": {"enabled": True, "variations": ["Hi!"]}}
        }
        res1 = client.post("/api/v1/automations/", json=payload_no_post, headers=headers_a)
        assert res1.status_code == 400

        # 2. Cross-user internal post
        payload_cross_post = {
            "name": "Cross Post Auto",
            "platform": "instagram",
            "social_account_id": account_a.id,
            "internal_post_id": post_b.id,
            "trigger_type": "ANY_COMMENT",
            "action_config": {"public_reply": {"enabled": True, "variations": ["Hi!"]}}
        }
        res2 = client.post("/api/v1/automations/", json=payload_cross_post, headers=headers_a)
        assert res2.status_code == 404

    def test_06_validation_triggers_and_keywords(self, client, db_session):
        """Test trigger validation for invalid type, empty keyword arrays, and keyword trimming."""
        token = get_user_token(client, "trig_user@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        user = db_session.query(User).filter(User.email == "trig_user@example.com").first()
        account = create_user_social_account(db_session, user.id, platform="instagram")

        # 1. Invalid trigger type
        payload_bad_type = {
            "name": "Bad Trigger Auto",
            "platform": "instagram",
            "social_account_id": account.id,
            "external_post_id": "ext_123",
            "trigger_type": "UNKNOWN_TRIGGER",
            "action_config": {"public_reply": {"enabled": True, "variations": ["Hi!"]}}
        }
        res1 = client.post("/api/v1/automations/", json=payload_bad_type, headers=headers)
        assert res1.status_code == 400

        # 2. KEYWORD trigger with missing keywords list
        payload_missing_kw = {
            "name": "Missing KW Auto",
            "platform": "instagram",
            "social_account_id": account.id,
            "external_post_id": "ext_123",
            "trigger_type": "KEYWORD",
            "trigger_config": {},
            "action_config": {"public_reply": {"enabled": True, "variations": ["Hi!"]}}
        }
        res2 = client.post("/api/v1/automations/", json=payload_missing_kw, headers=headers)
        assert res2.status_code == 400

        # 3. KEYWORD trigger with only whitespace/empty strings
        payload_empty_kw = {
            "name": "Empty KW Auto",
            "platform": "instagram",
            "social_account_id": account.id,
            "external_post_id": "ext_123",
            "trigger_type": "KEYWORD",
            "trigger_config": {"keywords": ["  ", ""]},
            "action_config": {"public_reply": {"enabled": True, "variations": ["Hi!"]}}
        }
        res3 = client.post("/api/v1/automations/", json=payload_empty_kw, headers=headers)
        assert res3.status_code == 400

    def test_07_validation_actions(self, client, db_session):
        """Test action validation for missing actions, empty variations, and empty DM message."""
        token = get_user_token(client, "act_user@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        user = db_session.query(User).filter(User.email == "act_user@example.com").first()
        account = create_user_social_account(db_session, user.id, platform="instagram")

        # 1. No actions enabled
        payload_no_actions = {
            "name": "No Actions Auto",
            "platform": "instagram",
            "social_account_id": account.id,
            "external_post_id": "ext_123",
            "trigger_type": "ANY_COMMENT",
            "action_config": {
                "public_reply": {"enabled": False},
                "private_message": {"enabled": False}
            }
        }
        res1 = client.post("/api/v1/automations/", json=payload_no_actions, headers=headers)
        assert res1.status_code == 400

        # 2. Public reply enabled without variations
        payload_no_variations = {
            "name": "No Variations Auto",
            "platform": "instagram",
            "social_account_id": account.id,
            "external_post_id": "ext_123",
            "trigger_type": "ANY_COMMENT",
            "action_config": {
                "public_reply": {"enabled": True, "variations": ["  ", ""]}
            }
        }
        res2 = client.post("/api/v1/automations/", json=payload_no_variations, headers=headers)
        assert res2.status_code == 400

        # 3. Private message enabled with empty message
        payload_empty_dm = {
            "name": "Empty DM Auto",
            "platform": "instagram",
            "social_account_id": account.id,
            "external_post_id": "ext_123",
            "trigger_type": "ANY_COMMENT",
            "action_config": {
                "private_message": {"enabled": True, "message": "   "}
            }
        }
        res3 = client.post("/api/v1/automations/", json=payload_empty_dm, headers=headers)
        assert res3.status_code == 400

    def test_08_list_and_get_automations_tenant_isolation(self, client, db_session):
        """Test listing and getting automations ensures strict tenant isolation."""
        token_u1 = get_user_token(client, "owner_one@example.com")
        token_u2 = get_user_token(client, "owner_two@example.com")
        user1 = db_session.query(User).filter(User.email == "owner_one@example.com").first()
        user2 = db_session.query(User).filter(User.email == "owner_two@example.com").first()

        acc1 = create_user_social_account(db_session, user1.id, platform="instagram", account_id="acc_u1")
        acc2 = create_user_social_account(db_session, user2.id, platform="instagram", account_id="acc_u2")

        # Create automation for user 1
        headers_u1 = {"Authorization": f"Bearer {token_u1}"}
        res_c1 = client.post("/api/v1/automations/", json={
            "name": "User 1 Automation",
            "platform": "instagram",
            "social_account_id": acc1.id,
            "external_post_id": "ext_post_u1",
            "trigger_type": "ANY_COMMENT",
            "action_config": {"public_reply": {"enabled": True, "variations": ["U1 Reply"]}}
        }, headers=headers_u1)
        auto1_id = res_c1.json()["id"]

        # Create automation for user 2
        headers_u2 = {"Authorization": f"Bearer {token_u2}"}
        res_c2 = client.post("/api/v1/automations/", json={
            "name": "User 2 Automation",
            "platform": "instagram",
            "social_account_id": acc2.id,
            "external_post_id": "ext_post_u2",
            "trigger_type": "ANY_COMMENT",
            "action_config": {"public_reply": {"enabled": True, "variations": ["U2 Reply"]}}
        }, headers=headers_u2)
        auto2_id = res_c2.json()["id"]

        # User 1 listing must only contain User 1's automation
        list_res1 = client.get("/api/v1/automations/", headers=headers_u1)
        assert list_res1.status_code == 200
        ids_u1 = [a["id"] for a in list_res1.json()]
        assert auto1_id in ids_u1
        assert auto2_id not in ids_u1

        # User 1 accessing User 2's automation returns 404
        get_res_cross = client.get(f"/api/v1/automations/{auto2_id}", headers=headers_u1)
        assert get_res_cross.status_code == 404

        # User 1 accessing own automation returns 200
        get_res_own = client.get(f"/api/v1/automations/{auto1_id}", headers=headers_u1)
        assert get_res_own.status_code == 200
        assert get_res_own.json()["name"] == "User 1 Automation"

    def test_09_update_automation(self, client, db_session):
        """Test updating name, trigger, and actions with validation."""
        token = get_user_token(client, "upd_user@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        user = db_session.query(User).filter(User.email == "upd_user@example.com").first()
        account = create_user_social_account(db_session, user.id, platform="instagram")

        res_c = client.post("/api/v1/automations/", json={
            "name": "Initial Name",
            "platform": "instagram",
            "social_account_id": account.id,
            "external_post_id": "post_upd_1",
            "trigger_type": "ANY_COMMENT",
            "action_config": {"public_reply": {"enabled": True, "variations": ["Initial"]}}
        }, headers=headers)
        auto_id = res_c.json()["id"]

        # Update name and switch to KEYWORD trigger
        patch_payload = {
            "name": "Updated Name",
            "trigger_type": "KEYWORD",
            "trigger_config": {"keywords": [" NEW_KEYWORD ", "shop"]},
            "action_config": {
                "public_reply": {"enabled": True, "variations": ["Updated Reply 1", "Updated Reply 2"]},
                "private_message": {"enabled": True, "message": "Updated DM text"}
            }
        }
        res_u = client.patch(f"/api/v1/automations/{auto_id}", json=patch_payload, headers=headers)
        assert res_u.status_code == 200
        data = res_u.json()
        assert data["name"] == "Updated Name"
        assert data["trigger_type"] == "KEYWORD"
        assert data["trigger_config"]["keywords"] == ["new_keyword", "shop"]
        assert len(data["action_config"]["public_reply"]["variations"]) == 2
        assert data["action_config"]["private_message"]["message"] == "Updated DM text"

    def test_10_status_lifecycle_activate_and_pause(self, client, db_session):
        """Test status transitions: DRAFT -> ACTIVE -> PAUSED -> ACTIVE and invalid pause on DRAFT."""
        token = get_user_token(client, "status_user@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        user = db_session.query(User).filter(User.email == "status_user@example.com").first()
        account = create_user_social_account(db_session, user.id, platform="instagram")

        res_c = client.post("/api/v1/automations/", json={
            "name": "Lifecycle Auto",
            "platform": "instagram",
            "social_account_id": account.id,
            "external_post_id": "post_life_1",
            "trigger_type": "ANY_COMMENT",
            "action_config": {"public_reply": {"enabled": True, "variations": ["Reply"]}}
        }, headers=headers)
        auto_id = res_c.json()["id"]
        assert res_c.json()["status"] == "DRAFT"

        # 1. Attempt to pause DRAFT directly -> Should fail
        res_pause_draft = client.post(f"/api/v1/automations/{auto_id}/pause", headers=headers)
        assert res_pause_draft.status_code == 400

        # 2. Activate DRAFT -> ACTIVE
        res_act = client.post(f"/api/v1/automations/{auto_id}/activate", headers=headers)
        assert res_act.status_code == 200
        assert res_act.json()["status"] == "ACTIVE"

        # 3. Pause ACTIVE -> PAUSED
        res_pause = client.post(f"/api/v1/automations/{auto_id}/pause", headers=headers)
        assert res_pause.status_code == 200
        assert res_pause.json()["status"] == "PAUSED"

        # 4. Re-activate PAUSED -> ACTIVE
        res_react = client.post(f"/api/v1/automations/{auto_id}/activate", headers=headers)
        assert res_react.status_code == 200
        assert res_react.json()["status"] == "ACTIVE"

    def test_11_delete_automation_and_cascade(self, client, db_session):
        """Test deleting an automation cascades cleanly and rejects unauthorized users."""
        token_owner = get_user_token(client, "del_owner@example.com")
        token_intruder = get_user_token(client, "del_intruder@example.com")
        owner = db_session.query(User).filter(User.email == "del_owner@example.com").first()
        account = create_user_social_account(db_session, owner.id, platform="instagram")

        headers_owner = {"Authorization": f"Bearer {token_owner}"}
        headers_intruder = {"Authorization": f"Bearer {token_intruder}"}

        res_c = client.post("/api/v1/automations/", json={
            "name": "Delete Target Auto",
            "platform": "instagram",
            "social_account_id": account.id,
            "external_post_id": "post_del_1",
            "trigger_type": "ANY_COMMENT",
            "action_config": {"public_reply": {"enabled": True, "variations": ["Reply"]}}
        }, headers=headers_owner)
        auto_id = res_c.json()["id"]

        # Attach an execution record to check cascade
        execution = AutomationExecution(
            automation_id=auto_id,
            user_id=owner.id,
            social_account_id=account.id,
            external_comment_id="comm_del_cascade",
            platform="instagram",
            status=ExecutionStatus.PENDING.value
        )
        db_session.add(execution)
        db_session.commit()
        exec_id = execution.id

        # Intruder trying to delete returns 404
        res_del_intruder = client.delete(f"/api/v1/automations/{auto_id}", headers=headers_intruder)
        assert res_del_intruder.status_code == 404

        # Owner deleting returns 200
        res_del_owner = client.delete(f"/api/v1/automations/{auto_id}", headers=headers_owner)
        assert res_del_owner.status_code == 200
        assert res_del_owner.json()["success"] is True

        # Ensure automation is gone
        res_get = client.get(f"/api/v1/automations/{auto_id}", headers=headers_owner)
        assert res_get.status_code == 404

        # Ensure execution was cascade deleted
        deleted_exec = db_session.query(AutomationExecution).filter(AutomationExecution.id == exec_id).first()
        assert deleted_exec is None

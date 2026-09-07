import pytest
from sqlalchemy.exc import IntegrityError
from app.models.user import User
from app.models.brand import BrandProfile
from app.models.social_account import SocialAccount
from app.models.post import Post, PostStatus
from app.models.social_comment import SocialComment
from app.models.automation import Automation, AutomationStatus, TriggerType, PostTargetType
from app.models.automation_execution import AutomationExecution, ExecutionStatus, ActionExecutionStatus
from app.repositories.automation_repository import automation_repository
from app.repositories.automation_execution_repository import automation_execution_repository


def create_sample_user(db_session, email="user@example.com"):
    user = User(
        email=email,
        hashed_password="hashed_pwd",
        full_name="Automation User",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def create_sample_brand(db_session, user_id, name="Test Brand"):
    brand = BrandProfile(
        user_id=user_id,
        name=name
    )
    db_session.add(brand)
    db_session.commit()
    db_session.refresh(brand)
    return brand


def create_sample_social_account(db_session, user_id, platform="instagram", account_id="ig_123"):
    account = SocialAccount(
        user_id=user_id,
        platform=platform,
        account_id=account_id,
        account_name=f"Test {platform.title()} Account",
        access_token="sample_token"
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


def create_sample_post(db_session, user_id, brand_id=None, external_post_id="post_999"):
    if not brand_id:
        brand = create_sample_brand(db_session, user_id)
        brand_id = brand.id

    post = Post(
        user_id=user_id,
        brand_id=brand_id,
        caption="Check out this product!",
        status=PostStatus.PUBLISHED.value,
        ig_media_id=external_post_id,
        fb_post_id=external_post_id
    )
    db_session.add(post)
    db_session.commit()
    db_session.refresh(post)
    return post


def create_sample_comment(db_session, user_id, social_account_id, platform="instagram", external_post_id="post_999", external_comment_id="comm_111"):
    comment = SocialComment(
        user_id=user_id,
        social_account_id=social_account_id,
        platform=platform,
        external_post_id=external_post_id,
        external_comment_id=external_comment_id,
        comment_text="How much does this cost?",
        commenter_id="customer_user_1",
        commenter_name="John Doe",
        webhook_object="instagram" if platform == "instagram" else "page"
    )
    db_session.add(comment)
    db_session.commit()
    db_session.refresh(comment)
    return comment


class TestAutomationDataModel:
    """Comprehensive test suite for Phase 1 Automation & AutomationExecution data models."""

    def test_01_automation_creation(self, db_session):
        """1. Test basic automation creation with default status and properties."""
        user = create_sample_user(db_session)
        account = create_sample_social_account(db_session, user.id)

        automation = Automation(
            user_id=user.id,
            social_account_id=account.id,
            name="Lead Gen Automation",
            platform="instagram",
            status=AutomationStatus.DRAFT.value,
            post_target_type=PostTargetType.SPECIFIC_POST.value,
            external_post_id="post_999",
            trigger_type=TriggerType.ANY_COMMENT.value,
            trigger_config={},
            action_config={
                "public_reply": {"enabled": True, "variations": ["Thanks! Check your DM."]},
                "private_message": {"enabled": True, "message": "Here is the discount link!"}
            }
        )
        db_session.add(automation)
        db_session.commit()
        db_session.refresh(automation)

        assert automation.id is not None
        assert automation.name == "Lead Gen Automation"
        assert automation.platform == "instagram"
        assert automation.status == AutomationStatus.DRAFT.value
        assert automation.created_at is not None
        assert automation.updated_at is not None

    def test_02_automation_ownership(self, db_session):
        """2. Test user ownership relationship and repository tenant isolation."""
        user1 = create_sample_user(db_session, email="owner1@example.com")
        user2 = create_sample_user(db_session, email="owner2@example.com")
        account1 = create_sample_social_account(db_session, user1.id)

        auto1 = Automation(
            user_id=user1.id,
            social_account_id=account1.id,
            name="User 1 Auto",
            platform="instagram",
            trigger_type=TriggerType.ANY_COMMENT.value,
            trigger_config={},
            action_config={}
        )
        db_session.add(auto1)
        db_session.commit()

        # Check repository returns it for user1, but None for user2
        found_user1 = automation_repository.get_by_id_and_user(db_session, auto1.id, user1.id)
        found_user2 = automation_repository.get_by_id_and_user(db_session, auto1.id, user2.id)

        assert found_user1 is not None
        assert found_user1.id == auto1.id
        assert found_user2 is None

        # Check backref relationship
        assert len(user1.automations) == 1
        assert user1.automations[0].name == "User 1 Auto"

    def test_03_automation_status_transitions(self, db_session):
        """3. Test automation status transitions (DRAFT -> ACTIVE -> PAUSED)."""
        user = create_sample_user(db_session)
        account = create_sample_social_account(db_session, user.id)

        auto = Automation(
            user_id=user.id,
            social_account_id=account.id,
            name="Status Lifecycle",
            platform="facebook",
            status=AutomationStatus.DRAFT.value,
            trigger_type=TriggerType.ANY_COMMENT.value,
            trigger_config={},
            action_config={}
        )
        db_session.add(auto)
        db_session.commit()
        assert auto.status == AutomationStatus.DRAFT.value

        # Transition to ACTIVE
        automation_repository.update(db_session, auto, {"status": AutomationStatus.ACTIVE.value})
        assert auto.status == AutomationStatus.ACTIVE.value

        # Transition to PAUSED
        automation_repository.update(db_session, auto, {"status": AutomationStatus.PAUSED.value})
        assert auto.status == AutomationStatus.PAUSED.value

    def test_04_specific_post_association(self, db_session):
        """4. Test specific post association (both external_post_id and internal Post foreign key)."""
        user = create_sample_user(db_session)
        account = create_sample_social_account(db_session, user.id)
        post = create_sample_post(db_session, user.id, external_post_id="meta_post_abc")

        auto = Automation(
            user_id=user.id,
            social_account_id=account.id,
            name="Post Specific Auto",
            platform="instagram",
            post_target_type=PostTargetType.SPECIFIC_POST.value,
            external_post_id="meta_post_abc",
            internal_post_id=post.id,
            trigger_type=TriggerType.ANY_COMMENT.value,
            trigger_config={},
            action_config={}
        )
        db_session.add(auto)
        db_session.commit()

        assert auto.post is not None
        assert auto.post.id == post.id
        assert auto.external_post_id == "meta_post_abc"

        # Check querying active automations by post
        auto.status = AutomationStatus.ACTIVE.value
        db_session.commit()

        active_list = automation_repository.get_active_by_post(
            db_session,
            social_account_id=account.id,
            external_post_id="meta_post_abc"
        )
        assert len(active_list) == 1
        assert active_list[0].id == auto.id

    def test_05_trigger_configuration_keywords(self, db_session):
        """5. Test trigger configuration with normalized keywords."""
        user = create_sample_user(db_session)
        account = create_sample_social_account(db_session, user.id)

        normalized_keywords = ["price", "cost", "dm", "link"]
        auto = Automation(
            user_id=user.id,
            social_account_id=account.id,
            name="Keyword Trigger Auto",
            platform="instagram",
            trigger_type=TriggerType.KEYWORD.value,
            trigger_config={"keywords": normalized_keywords},
            action_config={}
        )
        db_session.add(auto)
        db_session.commit()
        db_session.refresh(auto)

        assert auto.trigger_type == TriggerType.KEYWORD.value
        assert auto.trigger_config["keywords"] == ["price", "cost", "dm", "link"]

    def test_06_public_reply_configuration(self, db_session):
        """6. Test public reply configuration with multiple variations."""
        user = create_sample_user(db_session)
        account = create_sample_social_account(db_session, user.id)

        reply_variations = [
            "Hey! Sent you a DM with the link 📬",
            "Thanks for asking! Check your inbox ✉️",
            "Details sent straight to your DM! ✨"
        ]
        action_config = {
            "public_reply": {
                "enabled": True,
                "variations": reply_variations
            }
        }
        auto = Automation(
            user_id=user.id,
            social_account_id=account.id,
            name="Multi-Reply Auto",
            platform="instagram",
            trigger_type=TriggerType.ANY_COMMENT.value,
            trigger_config={},
            action_config=action_config
        )
        db_session.add(auto)
        db_session.commit()
        db_session.refresh(auto)

        assert auto.action_config["public_reply"]["enabled"] is True
        assert len(auto.action_config["public_reply"]["variations"]) == 3
        assert auto.action_config["public_reply"]["variations"][0] == reply_variations[0]

    def test_07_private_message_configuration(self, db_session):
        """7. Test private message (DM) action configuration."""
        user = create_sample_user(db_session)
        account = create_sample_social_account(db_session, user.id)

        dm_text = "Here is your exclusive 20% discount code: SAVE20! Visit https://example.com"
        action_config = {
            "private_message": {
                "enabled": True,
                "message": dm_text
            }
        }
        auto = Automation(
            user_id=user.id,
            social_account_id=account.id,
            name="DM Auto",
            platform="instagram",
            trigger_type=TriggerType.ANY_COMMENT.value,
            trigger_config={},
            action_config=action_config
        )
        db_session.add(auto)
        db_session.commit()
        db_session.refresh(auto)

        assert auto.action_config["private_message"]["enabled"] is True
        assert auto.action_config["private_message"]["message"] == dm_text

    def test_08_automation_execution_creation(self, db_session):
        """8. Test AutomationExecution creation and relationship binding."""
        user = create_sample_user(db_session)
        account = create_sample_social_account(db_session, user.id)
        comment = create_sample_comment(db_session, user.id, account.id, external_comment_id="comm_999")

        auto = Automation(
            user_id=user.id,
            social_account_id=account.id,
            name="Execution Test Auto",
            platform="instagram",
            trigger_type=TriggerType.ANY_COMMENT.value,
            trigger_config={},
            action_config={}
        )
        db_session.add(auto)
        db_session.commit()

        execution = AutomationExecution(
            automation_id=auto.id,
            user_id=user.id,
            social_account_id=account.id,
            comment_id=comment.id,
            external_comment_id="comm_999",
            external_post_id="post_999",
            platform="instagram",
            contact_identifier="cust_123",
            contact_name="Alice Smith",
            status=ExecutionStatus.PENDING.value,
            trigger_result={"matched": True, "trigger_type": "ANY_COMMENT"},
            public_reply_status=ActionExecutionStatus.PENDING.value,
            private_message_status=ActionExecutionStatus.PENDING.value
        )
        db_session.add(execution)
        db_session.commit()
        db_session.refresh(execution)

        assert execution.id is not None
        assert execution.automation.name == "Execution Test Auto"
        assert execution.comment.external_comment_id == "comm_999"
        assert execution.contact_name == "Alice Smith"
        assert execution.status == ExecutionStatus.PENDING.value

    def test_09_execution_status_transitions(self, db_session):
        """9. Test execution status lifecycle (PENDING -> RUNNING -> COMPLETED / PARTIAL_FAILURE / FAILED)."""
        user = create_sample_user(db_session)
        account = create_sample_social_account(db_session, user.id)
        auto = Automation(
            user_id=user.id,
            social_account_id=account.id,
            name="Status Auto",
            platform="facebook",
            trigger_type=TriggerType.ANY_COMMENT.value,
            trigger_config={},
            action_config={}
        )
        db_session.add(auto)
        db_session.commit()

        execution = AutomationExecution(
            automation_id=auto.id,
            user_id=user.id,
            social_account_id=account.id,
            external_comment_id="fb_comm_1",
            platform="facebook",
            status=ExecutionStatus.PENDING.value
        )
        db_session.add(execution)
        db_session.commit()

        # Step 1: Running
        execution.status = ExecutionStatus.RUNNING.value
        db_session.commit()
        assert execution.status == ExecutionStatus.RUNNING.value

        # Step 2: Partial failure (e.g. public reply succeeded, DM failed due to 24h window)
        execution.public_reply_status = ActionExecutionStatus.SUCCESS.value
        execution.public_reply_result = {"external_reply_id": "reply_123"}
        execution.private_message_status = ActionExecutionStatus.FAILED.value
        execution.private_message_result = {"error": "Messaging window expired"}
        execution.status = ExecutionStatus.PARTIAL_FAILURE.value
        execution.error_message = "Private message failed"
        db_session.commit()

        assert execution.status == ExecutionStatus.PARTIAL_FAILURE.value
        assert execution.public_reply_status == ActionExecutionStatus.SUCCESS.value
        assert execution.private_message_status == ActionExecutionStatus.FAILED.value

        # Step 3: Full completion on retry
        execution.private_message_status = ActionExecutionStatus.SUCCESS.value
        execution.status = ExecutionStatus.COMPLETED.value
        db_session.commit()
        assert execution.status == ExecutionStatus.COMPLETED.value

    def test_10_automation_and_comment_uniqueness_idempotency(self, db_session):
        """10. Test DB-level unique constraint preventing duplicate executions for the same (automation_id, external_comment_id)."""
        user = create_sample_user(db_session)
        account = create_sample_social_account(db_session, user.id)
        auto = Automation(
            user_id=user.id,
            social_account_id=account.id,
            name="Idempotency Auto",
            platform="instagram",
            trigger_type=TriggerType.ANY_COMMENT.value,
            trigger_config={},
            action_config={}
        )
        db_session.add(auto)
        db_session.commit()

        exec1 = AutomationExecution(
            automation_id=auto.id,
            user_id=user.id,
            social_account_id=account.id,
            external_comment_id="idemp_comment_123",
            platform="instagram",
            status=ExecutionStatus.COMPLETED.value
        )
        db_session.add(exec1)
        db_session.commit()

        # Duplicate attempt with same automation_id and external_comment_id
        exec2 = AutomationExecution(
            automation_id=auto.id,
            user_id=user.id,
            social_account_id=account.id,
            external_comment_id="idemp_comment_123",
            platform="instagram",
            status=ExecutionStatus.PENDING.value
        )
        db_session.add(exec2)
        with pytest.raises(IntegrityError):
            db_session.commit()

        db_session.rollback()

        # Verifying lookup repository method
        existing = automation_execution_repository.get_by_automation_and_comment(
            db_session,
            automation_id=auto.id,
            external_comment_id="idemp_comment_123"
        )
        assert existing is not None
        assert existing.id == exec1.id

    def test_11_cross_user_relationship_rejection(self, db_session):
        """11. Test ownership validation rejecting cross-user account/post association."""
        user_a = create_sample_user(db_session, email="usera@example.com")
        user_b = create_sample_user(db_session, email="userb@example.com")

        account_b = create_sample_social_account(db_session, user_b.id)
        post_b = create_sample_post(db_session, user_b.id)

        # Validate that User A attempting to create automation on User B's account is rejected
        is_valid = automation_repository.validate_ownership(
            db_session,
            user_id=user_a.id,
            social_account_id=account_b.id
        )
        assert is_valid is False

        # Validate that User A attempting to attach User B's post is rejected
        is_valid_post = automation_repository.validate_ownership(
            db_session,
            user_id=user_a.id,
            social_account_id=account_b.id,
            internal_post_id=post_b.id
        )
        assert is_valid_post is False

        # Validate that User B's own account is accepted
        is_valid_owner = automation_repository.validate_ownership(
            db_session,
            user_id=user_b.id,
            social_account_id=account_b.id,
            internal_post_id=post_b.id
        )
        assert is_valid_owner is True

    def test_12_cascade_deletion(self, db_session):
        """12. Test cascade delete behavior when Automation or User is deleted."""
        user = create_sample_user(db_session)
        account = create_sample_social_account(db_session, user.id)
        auto = Automation(
            user_id=user.id,
            social_account_id=account.id,
            name="Cascade Auto",
            platform="instagram",
            trigger_type=TriggerType.ANY_COMMENT.value,
            trigger_config={},
            action_config={}
        )
        db_session.add(auto)
        db_session.commit()

        exec_item = AutomationExecution(
            automation_id=auto.id,
            user_id=user.id,
            social_account_id=account.id,
            external_comment_id="cascade_comment",
            platform="instagram",
            status=ExecutionStatus.PENDING.value
        )
        db_session.add(exec_item)
        db_session.commit()

        exec_id = exec_item.id

        # Delete the automation
        db_session.delete(auto)
        db_session.commit()

        # Execution should be deleted via cascade
        deleted_exec = db_session.query(AutomationExecution).filter(AutomationExecution.id == exec_id).first()
        assert deleted_exec is None

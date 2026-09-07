import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.brand import BrandProfile
from app.models.social_account import SocialAccount
from app.models.post import Post, PostStatus
from app.models.social_comment import SocialComment
from app.models.social_comment_reply import SocialCommentReply
from app.models.automation import Automation, AutomationStatus, TriggerType, PostTargetType
from app.models.automation_execution import AutomationExecution, ExecutionStatus, ActionExecutionStatus
from app.services.automation_execution_service import automation_execution_service
from app.services.comment_trigger_service import comment_trigger_service
from app.services.comment_ingestion_service import meta_comment_ingestion_service
from app.services.meta_service import meta_service, MetaPublishException
from app.core.security import get_password_hash
from app.core.security_encryption import encrypt_token


@pytest.fixture
def test_user(db_session: Session) -> User:
    user = User(
        email="exec_user@socialai.com",
        hashed_password=get_password_hash("ValidPass123!"),
        full_name="Execution Test User",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def ig_account(db_session: Session, test_user: User) -> SocialAccount:
    acc = SocialAccount(
        user_id=test_user.id,
        platform="instagram",
        account_id="17841400099",
        account_name="test_ig_business",
        status="CONNECTED",
        access_token=encrypt_token("EAANNCr_valid_ig_token")
    )
    db_session.add(acc)
    db_session.commit()
    db_session.refresh(acc)
    return acc


@pytest.fixture
def fb_account(db_session: Session, test_user: User) -> SocialAccount:
    acc = SocialAccount(
        user_id=test_user.id,
        platform="facebook",
        account_id="10000000099",
        account_name="Test Facebook Page",
        status="CONNECTED",
        access_token=encrypt_token("EAANNCr_valid_fb_token")
    )
    db_session.add(acc)
    db_session.commit()
    db_session.refresh(acc)
    return acc


@pytest.fixture
def ig_automation(db_session: Session, test_user: User, ig_account: SocialAccount) -> Automation:
    auto = Automation(
        user_id=test_user.id,
        social_account_id=ig_account.id,
        name="IG Execution Auto",
        platform="instagram",
        status=AutomationStatus.ACTIVE.value,
        post_target_type=PostTargetType.SPECIFIC_POST.value,
        external_post_id="media_post_100",
        trigger_type=TriggerType.KEYWORD.value,
        trigger_config={"keywords": ["pricing", "cost"]},
        action_config={
            "public_reply": {
                "enabled": True,
                "variations": ["Thanks for asking! Check your DM 😊", "Sent you the pricing in DMs!"]
            },
            "private_message": {
                "enabled": True,
                "message": "Here is our full pricing brochure: https://example.com/pricing"
            }
        }
    )
    db_session.add(auto)
    db_session.commit()
    db_session.refresh(auto)
    return auto


@pytest.fixture
def fb_automation(db_session: Session, test_user: User, fb_account: SocialAccount) -> Automation:
    auto = Automation(
        user_id=test_user.id,
        social_account_id=fb_account.id,
        name="FB Execution Auto",
        platform="facebook",
        status=AutomationStatus.ACTIVE.value,
        post_target_type=PostTargetType.SPECIFIC_POST.value,
        external_post_id="post_fb_200",
        trigger_type=TriggerType.KEYWORD.value,
        trigger_config={"keywords": ["info", "details"]},
        action_config={
            "public_reply": {
                "enabled": True,
                "variations": ["Thanks for reaching out! Details sent to Messenger."]
            },
            "private_message": {
                "enabled": True,
                "message": "Hey! Here are the details you requested."
            }
        }
    )
    db_session.add(auto)
    db_session.commit()
    db_session.refresh(auto)
    return auto


@pytest.fixture
def ig_comment(db_session: Session, test_user: User, ig_account: SocialAccount) -> SocialComment:
    comm = SocialComment(
        user_id=test_user.id,
        social_account_id=ig_account.id,
        platform="instagram",
        external_comment_id="comm_ig_555",
        external_post_id="media_post_100",
        comment_text="What is the pricing?",
        commenter_id="user_igsid_123",
        commenter_name="customer_jane",
        webhook_object="instagram",
        processing_status="RECEIVED"
    )
    db_session.add(comm)
    db_session.commit()
    db_session.refresh(comm)
    return comm


@pytest.fixture
def fb_comment(db_session: Session, test_user: User, fb_account: SocialAccount) -> SocialComment:
    comm = SocialComment(
        user_id=test_user.id,
        social_account_id=fb_account.id,
        platform="facebook",
        external_comment_id="comm_fb_777",
        external_post_id="post_fb_200",
        comment_text="Can I get info please?",
        commenter_id="user_psid_456",
        commenter_name="customer_bob",
        webhook_object="page",
        processing_status="RECEIVED"
    )
    db_session.add(comm)
    db_session.commit()
    db_session.refresh(comm)
    return comm


# =========================================================================
# 1. CLAIMING AND CONCURRENCY TESTS
# =========================================================================

def test_pending_execution_can_be_claimed(db_session: Session, test_user: User, ig_account: SocialAccount, ig_automation: Automation, ig_comment: SocialComment):
    """Test 1: PENDING execution can be claimed atomically, transitioning to RUNNING."""
    exec_record = AutomationExecution(
        automation_id=ig_automation.id,
        user_id=test_user.id,
        social_account_id=ig_account.id,
        comment_id=ig_comment.id,
        external_comment_id=ig_comment.external_comment_id,
        platform="instagram",
        status=ExecutionStatus.PENDING.value
    )
    db_session.add(exec_record)
    db_session.commit()

    claimed = automation_execution_service.claim_execution(db_session, exec_record.id)
    assert claimed is not None
    assert claimed.id == exec_record.id
    assert claimed.status == ExecutionStatus.RUNNING.value


def test_already_running_execution_cannot_be_claimed_twice(db_session: Session, test_user: User, ig_account: SocialAccount, ig_automation: Automation, ig_comment: SocialComment):
    """Test 2: Already RUNNING execution cannot be claimed by a second worker."""
    exec_record = AutomationExecution(
        automation_id=ig_automation.id,
        user_id=test_user.id,
        social_account_id=ig_account.id,
        comment_id=ig_comment.id,
        external_comment_id=ig_comment.external_comment_id,
        platform="instagram",
        status=ExecutionStatus.RUNNING.value
    )
    db_session.add(exec_record)
    db_session.commit()

    claimed = automation_execution_service.claim_execution(db_session, exec_record.id)
    assert claimed is None


def test_already_completed_execution_cannot_execute_again(db_session: Session, test_user: User, ig_account: SocialAccount, ig_automation: Automation, ig_comment: SocialComment):
    """Test 3: Already COMPLETED execution cannot be claimed or executed again."""
    exec_record = AutomationExecution(
        automation_id=ig_automation.id,
        user_id=test_user.id,
        social_account_id=ig_account.id,
        comment_id=ig_comment.id,
        external_comment_id=ig_comment.external_comment_id,
        platform="instagram",
        status=ExecutionStatus.COMPLETED.value
    )
    db_session.add(exec_record)
    db_session.commit()

    claimed = automation_execution_service.claim_execution(db_session, exec_record.id)
    assert claimed is None

    # Calling execute_pending_execution returns None safely
    res = automation_execution_service.execute_pending_execution(exec_record.id, db=db_session)
    assert res is None


# =========================================================================
# 2. PUBLIC REPLY AND PRIVATE MESSAGE EXECUTION TESTS
# =========================================================================

def test_instagram_public_reply_success(db_session: Session, test_user: User, ig_account: SocialAccount, ig_automation: Automation, ig_comment: SocialComment):
    """Test 4: Instagram public comment reply dispatches via reply_to_instagram_comment."""
    # Disable private message for isolated public reply test
    ig_automation.action_config = {
        "public_reply": {"enabled": True, "variations": ["Variation A", "Variation B"]},
        "private_message": {"enabled": False}
    }
    db_session.commit()

    exec_record = AutomationExecution(
        automation_id=ig_automation.id,
        user_id=test_user.id,
        social_account_id=ig_account.id,
        comment_id=ig_comment.id,
        external_comment_id=ig_comment.external_comment_id,
        platform="instagram",
        status=ExecutionStatus.PENDING.value
    )
    db_session.add(exec_record)
    db_session.commit()

    with patch.object(meta_service, "reply_to_instagram_comment", return_value={"id": "ig_rep_12345"}) as mock_ig_reply:
        res = automation_execution_service.execute_pending_execution(exec_record.id, db=db_session)
        assert res is not None
        assert res.status == ExecutionStatus.COMPLETED.value
        assert res.public_reply_status == ActionExecutionStatus.SUCCESS.value
        assert res.public_reply_result["external_reply_id"] == "ig_rep_12345"
        assert res.private_message_status == ActionExecutionStatus.SKIPPED.value
        mock_ig_reply.assert_called_once()

    # Verify audit row in SocialCommentReply
    reply_row = db_session.query(SocialCommentReply).filter(
        SocialCommentReply.external_reply_id == "ig_rep_12345"
    ).first()
    assert reply_row is not None
    assert reply_row.platform == "instagram"


def test_facebook_public_reply_success(db_session: Session, test_user: User, fb_account: SocialAccount, fb_automation: Automation, fb_comment: SocialComment):
    """Test 5: Facebook public comment reply dispatches via reply_to_facebook_comment."""
    fb_automation.action_config = {
        "public_reply": {"enabled": True, "variations": ["FB Reply 1"]},
        "private_message": {"enabled": False}
    }
    db_session.commit()

    exec_record = AutomationExecution(
        automation_id=fb_automation.id,
        user_id=test_user.id,
        social_account_id=fb_account.id,
        comment_id=fb_comment.id,
        external_comment_id=fb_comment.external_comment_id,
        platform="facebook",
        status=ExecutionStatus.PENDING.value
    )
    db_session.add(exec_record)
    db_session.commit()

    with patch.object(meta_service, "reply_to_facebook_comment", return_value={"id": "fb_rep_998877"}) as mock_fb_reply:
        res = automation_execution_service.execute_pending_execution(exec_record.id, db=db_session)
        assert res is not None
        assert res.status == ExecutionStatus.COMPLETED.value
        assert res.public_reply_status == ActionExecutionStatus.SUCCESS.value
        assert res.public_reply_result["external_reply_id"] == "fb_rep_998877"
        assert res.private_message_status == ActionExecutionStatus.SKIPPED.value
        mock_fb_reply.assert_called_once()


def test_instagram_private_message_success(db_session: Session, test_user: User, ig_account: SocialAccount, ig_automation: Automation, ig_comment: SocialComment):
    """Test 6: Instagram private message dispatches via send_instagram_private_message."""
    ig_automation.action_config = {
        "public_reply": {"enabled": False},
        "private_message": {"enabled": True, "message": "Here is the exclusive link!"}
    }
    db_session.commit()

    exec_record = AutomationExecution(
        automation_id=ig_automation.id,
        user_id=test_user.id,
        social_account_id=ig_account.id,
        comment_id=ig_comment.id,
        external_comment_id=ig_comment.external_comment_id,
        contact_identifier=ig_comment.commenter_id,
        platform="instagram",
        status=ExecutionStatus.PENDING.value
    )
    db_session.add(exec_record)
    db_session.commit()

    with patch.object(meta_service, "send_instagram_private_message", return_value={"message_id": "ig_msg_mid_999"}) as mock_ig_dm:
        res = automation_execution_service.execute_pending_execution(exec_record.id, db=db_session)
        assert res is not None
        assert res.status == ExecutionStatus.COMPLETED.value
        assert res.private_message_status == ActionExecutionStatus.SUCCESS.value
        assert res.private_message_result["external_message_id"] == "ig_msg_mid_999"
        assert res.public_reply_status == ActionExecutionStatus.SKIPPED.value
        mock_ig_dm.assert_called_once_with(
            recipient_id="user_igsid_123",
            access_token="EAANNCr_valid_ig_token",
            message="Here is the exclusive link!",
            comment_id="comm_ig_555"
        )


def test_facebook_private_message_success(db_session: Session, test_user: User, fb_account: SocialAccount, fb_automation: Automation, fb_comment: SocialComment):
    """Test 7: Facebook private message dispatches via send_facebook_private_message."""
    fb_automation.action_config = {
        "public_reply": {"enabled": False},
        "private_message": {"enabled": True, "message": "Welcome to our Facebook Messenger!"}
    }
    db_session.commit()

    exec_record = AutomationExecution(
        automation_id=fb_automation.id,
        user_id=test_user.id,
        social_account_id=fb_account.id,
        comment_id=fb_comment.id,
        external_comment_id=fb_comment.external_comment_id,
        contact_identifier=fb_comment.commenter_id,
        platform="facebook",
        status=ExecutionStatus.PENDING.value
    )
    db_session.add(exec_record)
    db_session.commit()

    with patch.object(meta_service, "send_facebook_private_message", return_value={"message_id": "fb_msg_mid_456"}) as mock_fb_dm:
        res = automation_execution_service.execute_pending_execution(exec_record.id, db=db_session)
        assert res is not None
        assert res.status == ExecutionStatus.COMPLETED.value
        assert res.private_message_status == ActionExecutionStatus.SUCCESS.value
        assert res.private_message_result["external_message_id"] == "fb_msg_mid_456"
        assert res.public_reply_status == ActionExecutionStatus.SKIPPED.value
        mock_fb_dm.assert_called_once_with(
            recipient_id="user_psid_456",
            access_token="EAANNCr_valid_fb_token",
            message="Welcome to our Facebook Messenger!",
            comment_id="comm_fb_777"
        )


def test_both_public_reply_and_private_message_success(db_session: Session, test_user: User, ig_account: SocialAccount, ig_automation: Automation, ig_comment: SocialComment):
    """Test 10: Both public reply and private message execute and succeed together."""
    exec_record = AutomationExecution(
        automation_id=ig_automation.id,
        user_id=test_user.id,
        social_account_id=ig_account.id,
        comment_id=ig_comment.id,
        external_comment_id=ig_comment.external_comment_id,
        contact_identifier=ig_comment.commenter_id,
        platform="instagram",
        status=ExecutionStatus.PENDING.value
    )
    db_session.add(exec_record)
    db_session.commit()

    with patch.object(meta_service, "reply_to_instagram_comment", return_value={"id": "ig_rep_both_1"}) as mock_reply, \
         patch.object(meta_service, "send_instagram_private_message", return_value={"message_id": "ig_msg_both_1"}) as mock_dm:

        res = automation_execution_service.execute_pending_execution(exec_record.id, db=db_session)
        assert res is not None
        assert res.status == ExecutionStatus.COMPLETED.value
        assert res.public_reply_status == ActionExecutionStatus.SUCCESS.value
        assert res.private_message_status == ActionExecutionStatus.SUCCESS.value
        mock_reply.assert_called_once()
        mock_dm.assert_called_once()


# =========================================================================
# 3. PARTIAL FAILURE & RESILIENT RETRY TESTS
# =========================================================================

def test_public_reply_succeeds_but_private_message_fails(db_session: Session, test_user: User, ig_account: SocialAccount, ig_automation: Automation, ig_comment: SocialComment):
    """Test 11: Public reply succeeds but private message fails -> PARTIAL_FAILURE with public reply marked SUCCESS."""
    exec_record = AutomationExecution(
        automation_id=ig_automation.id,
        user_id=test_user.id,
        social_account_id=ig_account.id,
        comment_id=ig_comment.id,
        external_comment_id=ig_comment.external_comment_id,
        contact_identifier=ig_comment.commenter_id,
        platform="instagram",
        status=ExecutionStatus.PENDING.value
    )
    db_session.add(exec_record)
    db_session.commit()

    with patch.object(meta_service, "reply_to_instagram_comment", return_value={"id": "ig_rep_partial_1"}), \
         patch.object(meta_service, "send_instagram_private_message", side_effect=MetaPublishException("Temporary Rate Limit", status_code=429)):

        res = automation_execution_service.execute_pending_execution(exec_record.id, db=db_session)
        assert res is not None
        assert res.status == ExecutionStatus.PARTIAL_FAILURE.value
        assert res.public_reply_status == ActionExecutionStatus.SUCCESS.value
        assert res.public_reply_result["external_reply_id"] == "ig_rep_partial_1"
        assert res.private_message_status == ActionExecutionStatus.FAILED.value
        assert res.private_message_result["retryable"] is True


def test_retry_does_not_resend_successful_public_reply(db_session: Session, test_user: User, ig_account: SocialAccount, ig_automation: Automation, ig_comment: SocialComment):
    """Test 12: Retrying a PARTIAL_FAILURE execution only runs the failed private message, NOT the public reply."""
    exec_record = AutomationExecution(
        automation_id=ig_automation.id,
        user_id=test_user.id,
        social_account_id=ig_account.id,
        comment_id=ig_comment.id,
        external_comment_id=ig_comment.external_comment_id,
        contact_identifier=ig_comment.commenter_id,
        platform="instagram",
        status=ExecutionStatus.PARTIAL_FAILURE.value,
        public_reply_status=ActionExecutionStatus.SUCCESS.value,
        public_reply_result={"status": "SUCCESS", "external_reply_id": "already_sent_rep_1"},
        private_message_status=ActionExecutionStatus.FAILED.value,
        private_message_result={"status": "FAILED", "error": "rate limit"}
    )
    db_session.add(exec_record)
    db_session.commit()

    with patch.object(meta_service, "reply_to_instagram_comment") as mock_reply, \
         patch.object(meta_service, "send_instagram_private_message", return_value={"message_id": "dm_recovered_1"}) as mock_dm:

        res = automation_execution_service.execute_pending_execution(exec_record.id, db=db_session)
        assert res is not None
        assert res.status == ExecutionStatus.COMPLETED.value
        assert res.public_reply_status == ActionExecutionStatus.SUCCESS.value
        assert res.private_message_status == ActionExecutionStatus.SUCCESS.value

        # Crucial verification: Public reply was NEVER called during retry!
        mock_reply.assert_not_called()
        mock_dm.assert_called_once()


def test_private_message_succeeds_but_public_reply_fails_and_retries_safely(db_session: Session, test_user: User, ig_account: SocialAccount, ig_automation: Automation, ig_comment: SocialComment):
    """Test 13 & 14: Private message succeeds but public reply fails -> retry runs only public reply."""
    exec_record = AutomationExecution(
        automation_id=ig_automation.id,
        user_id=test_user.id,
        social_account_id=ig_account.id,
        comment_id=ig_comment.id,
        external_comment_id=ig_comment.external_comment_id,
        contact_identifier=ig_comment.commenter_id,
        platform="instagram",
        status=ExecutionStatus.PARTIAL_FAILURE.value,
        public_reply_status=ActionExecutionStatus.FAILED.value,
        public_reply_result={"status": "FAILED", "error": "500 server error"},
        private_message_status=ActionExecutionStatus.SUCCESS.value,
        private_message_result={"status": "SUCCESS", "external_message_id": "already_sent_dm_1"}
    )
    db_session.add(exec_record)
    db_session.commit()

    with patch.object(meta_service, "reply_to_instagram_comment", return_value={"id": "reply_recovered_1"}) as mock_reply, \
         patch.object(meta_service, "send_instagram_private_message") as mock_dm:

        res = automation_execution_service.execute_pending_execution(exec_record.id, db=db_session)
        assert res is not None
        assert res.status == ExecutionStatus.COMPLETED.value
        assert res.public_reply_status == ActionExecutionStatus.SUCCESS.value
        assert res.private_message_status == ActionExecutionStatus.SUCCESS.value

        # Crucial verification: Private message was NOT resent!
        mock_dm.assert_not_called()
        mock_reply.assert_called_once()


# =========================================================================
# 4. ERROR CLASSIFICATION AND RETRYABILITY TESTS
# =========================================================================

def test_retryable_429_and_5xx_errors():
    """Test 15 & 16: HTTP 429 rate limits and 5xx errors are classified as retryable."""
    err_429 = MetaPublishException("Rate limit reached", status_code=429)
    assert automation_execution_service.determine_retryability(err_429) is True

    err_500 = MetaPublishException("Internal Server Error", status_code=500)
    assert automation_execution_service.determine_retryability(err_500) is True

    err_503 = MetaPublishException("Service Unavailable", status_code=503)
    assert automation_execution_service.determine_retryability(err_503) is True


def test_network_timeout_is_retryable():
    """Test 17: Network timeout exceptions are classified as retryable."""
    err_timeout = Exception("HTTPSConnectionPool: Read timed out. (read timeout=15)")
    assert automation_execution_service.determine_retryability(err_timeout) is True


def test_permanent_400_and_permission_errors():
    """Test 18 & 19: Permanent 400 bad request and permission failures are non-retryable."""
    err_400 = MetaPublishException("Invalid parameter recipient_id", status_code=400)
    assert automation_execution_service.determine_retryability(err_400) is False

    err_perm = MetaPublishException("Permission denied for object", status_code=403, error_code=200)
    assert automation_execution_service.determine_retryability(err_perm) is False


# =========================================================================
# 5. GUARDRAILS AND INVALID CONTEXT TESTS
# =========================================================================

def test_draft_automation_cannot_execute(db_session: Session, test_user: User, ig_account: SocialAccount, ig_automation: Automation, ig_comment: SocialComment):
    """Test 25: DRAFT automation execution is rejected and marked FAILED."""
    ig_automation.status = AutomationStatus.DRAFT.value
    db_session.commit()

    exec_record = AutomationExecution(
        automation_id=ig_automation.id,
        user_id=test_user.id,
        social_account_id=ig_account.id,
        comment_id=ig_comment.id,
        external_comment_id=ig_comment.external_comment_id,
        platform="instagram",
        status=ExecutionStatus.PENDING.value
    )
    db_session.add(exec_record)
    db_session.commit()

    res = automation_execution_service.execute_pending_execution(exec_record.id, db=db_session)
    assert res is not None
    assert res.status == ExecutionStatus.FAILED.value
    assert "Must be ACTIVE" in res.error_message


def test_paused_automation_cannot_execute(db_session: Session, test_user: User, ig_account: SocialAccount, ig_automation: Automation, ig_comment: SocialComment):
    """Test 26: PAUSED automation execution is rejected and marked FAILED."""
    ig_automation.status = AutomationStatus.PAUSED.value
    db_session.commit()

    exec_record = AutomationExecution(
        automation_id=ig_automation.id,
        user_id=test_user.id,
        social_account_id=ig_account.id,
        comment_id=ig_comment.id,
        external_comment_id=ig_comment.external_comment_id,
        platform="instagram",
        status=ExecutionStatus.PENDING.value
    )
    db_session.add(exec_record)
    db_session.commit()

    res = automation_execution_service.execute_pending_execution(exec_record.id, db=db_session)
    assert res is not None
    assert res.status == ExecutionStatus.FAILED.value
    assert "Must be ACTIVE" in res.error_message


def test_disconnected_social_account_fails_execution(db_session: Session, test_user: User, ig_account: SocialAccount, ig_automation: Automation, ig_comment: SocialComment):
    """Test 22: Disconnected social account marks execution as FAILED."""
    ig_account.status = "TOKEN_EXPIRED"
    db_session.commit()

    exec_record = AutomationExecution(
        automation_id=ig_automation.id,
        user_id=test_user.id,
        social_account_id=ig_account.id,
        comment_id=ig_comment.id,
        external_comment_id=ig_comment.external_comment_id,
        platform="instagram",
        status=ExecutionStatus.PENDING.value
    )
    db_session.add(exec_record)
    db_session.commit()

    res = automation_execution_service.execute_pending_execution(exec_record.id, db=db_session)
    assert res is not None
    assert res.status == ExecutionStatus.FAILED.value
    assert "disconnected" in res.error_message.lower()


# =========================================================================
# 6. END-TO-END INTEGRATION TESTS
# =========================================================================

def test_instagram_webhook_to_execution_e2e(db_session: Session, test_user: User, ig_account: SocialAccount, ig_automation: Automation):
    """
    Test 31: End-to-end flow for Instagram:
    Webhook -> SocialComment -> Phase 3 Trigger -> PENDING AutomationExecution -> Execution Engine -> COMPLETED.
    """
    payload = {
        "object": "instagram",
        "entry": [
            {
                "id": ig_account.account_id,
                "time": 1710000000,
                "changes": [
                    {
                        "field": "comments",
                        "value": {
                            "id": "e2e_ig_comm_101",
                            "text": "Tell me the PRICING please!",
                            "media": {"id": "media_post_100"},
                            "from": {"id": "ig_buyer_888", "username": "buyer_jane"}
                        }
                    }
                ]
            }
        ]
    }

    # Step 1: Ingest webhook (Phase 3)
    ingested = meta_comment_ingestion_service.parse_and_ingest_payload(db_session, payload)
    assert len(ingested) == 1

    # Verify PENDING AutomationExecution was created
    exec_record = db_session.query(AutomationExecution).filter(
        AutomationExecution.automation_id == ig_automation.id,
        AutomationExecution.external_comment_id == "e2e_ig_comm_101"
    ).first()
    assert exec_record is not None
    assert exec_record.status == ExecutionStatus.PENDING.value

    # Step 2: Execute pending execution (Phase 4)
    with patch.object(meta_service, "reply_to_instagram_comment", return_value={"id": "e2e_rep_ig_1"}) as mock_reply, \
         patch.object(meta_service, "send_instagram_private_message", return_value={"message_id": "e2e_dm_ig_1"}) as mock_dm:

        completed = automation_execution_service.execute_pending_execution(exec_record.id, db=db_session)
        assert completed is not None
        assert completed.status == ExecutionStatus.COMPLETED.value
        assert completed.public_reply_status == ActionExecutionStatus.SUCCESS.value
        assert completed.private_message_status == ActionExecutionStatus.SUCCESS.value
        mock_reply.assert_called_once()
        mock_dm.assert_called_once()


def test_facebook_webhook_to_execution_e2e(db_session: Session, test_user: User, fb_account: SocialAccount, fb_automation: Automation):
    """
    Test 32: End-to-end flow for Facebook:
    Webhook -> SocialComment -> Phase 3 Trigger -> PENDING AutomationExecution -> Execution Engine -> COMPLETED.
    """
    payload = {
        "object": "page",
        "entry": [
            {
                "id": fb_account.account_id,
                "time": 1710000000,
                "changes": [
                    {
                        "field": "feed",
                        "value": {
                            "item": "comment",
                            "verb": "add",
                            "comment_id": "e2e_fb_comm_202",
                            "post_id": "post_fb_200",
                            "message": "Send me details please",
                            "from": {"id": "fb_buyer_999", "name": "Buyer Bob"}
                        }
                    }
                ]
            }
        ]
    }

    # Step 1: Ingest webhook (Phase 3)
    ingested = meta_comment_ingestion_service.parse_and_ingest_payload(db_session, payload)
    assert len(ingested) == 1

    # Verify PENDING AutomationExecution was created
    exec_record = db_session.query(AutomationExecution).filter(
        AutomationExecution.automation_id == fb_automation.id,
        AutomationExecution.external_comment_id == "e2e_fb_comm_202"
    ).first()
    assert exec_record is not None
    assert exec_record.status == ExecutionStatus.PENDING.value

    # Step 2: Execute pending execution (Phase 4)
    with patch.object(meta_service, "reply_to_facebook_comment", return_value={"id": "e2e_rep_fb_2"}) as mock_reply, \
         patch.object(meta_service, "send_facebook_private_message", return_value={"message_id": "e2e_dm_fb_2"}) as mock_dm:

        completed = automation_execution_service.execute_pending_execution(exec_record.id, db=db_session)
        assert completed is not None
        assert completed.status == ExecutionStatus.COMPLETED.value
        assert completed.public_reply_status == ActionExecutionStatus.SUCCESS.value
        assert completed.private_message_status == ActionExecutionStatus.SUCCESS.value
        mock_reply.assert_called_once()
        mock_dm.assert_called_once()


def test_public_reply_disabled_zero_meta_calls(db_session: Session, test_user: User, ig_account: SocialAccount, ig_automation: Automation, ig_comment: SocialComment):
    """Test 8: Disabled public reply sets status SKIPPED and produces zero Meta reply calls."""
    ig_automation.action_config = {
        "public_reply": {"enabled": False},
        "private_message": {"enabled": True, "message": "DM only"}
    }
    db_session.commit()

    exec_record = AutomationExecution(
        automation_id=ig_automation.id,
        user_id=test_user.id,
        social_account_id=ig_account.id,
        comment_id=ig_comment.id,
        external_comment_id=ig_comment.external_comment_id,
        contact_identifier=ig_comment.commenter_id,
        platform="instagram",
        status=ExecutionStatus.PENDING.value
    )
    db_session.add(exec_record)
    db_session.commit()

    with patch.object(meta_service, "reply_to_instagram_comment") as mock_reply, \
         patch.object(meta_service, "send_instagram_private_message", return_value={"message_id": "dm_only_1"}) as mock_dm:

        res = automation_execution_service.execute_pending_execution(exec_record.id, db=db_session)
        assert res is not None
        assert res.public_reply_status == ActionExecutionStatus.SKIPPED.value
        mock_reply.assert_not_called()
        mock_dm.assert_called_once()


def test_private_message_disabled_zero_meta_calls(db_session: Session, test_user: User, ig_account: SocialAccount, ig_automation: Automation, ig_comment: SocialComment):
    """Test 9: Disabled private message sets status SKIPPED and produces zero Meta messaging calls."""
    ig_automation.action_config = {
        "public_reply": {"enabled": True, "variations": ["Reply only"]},
        "private_message": {"enabled": False}
    }
    db_session.commit()

    exec_record = AutomationExecution(
        automation_id=ig_automation.id,
        user_id=test_user.id,
        social_account_id=ig_account.id,
        comment_id=ig_comment.id,
        external_comment_id=ig_comment.external_comment_id,
        platform="instagram",
        status=ExecutionStatus.PENDING.value
    )
    db_session.add(exec_record)
    db_session.commit()

    with patch.object(meta_service, "reply_to_instagram_comment", return_value={"id": "rep_only_1"}) as mock_reply, \
         patch.object(meta_service, "send_instagram_private_message") as mock_dm:

        res = automation_execution_service.execute_pending_execution(exec_record.id, db=db_session)
        assert res is not None
        assert res.private_message_status == ActionExecutionStatus.SKIPPED.value
        mock_dm.assert_not_called()
        mock_reply.assert_called_once()


def test_deterministic_variation_rotation(db_session: Session, test_user: User, ig_account: SocialAccount, ig_automation: Automation, ig_comment: SocialComment):
    """Verify deterministic variation rotation for public replies based on execution ID."""
    variations = ["Option A", "Option B", "Option C"]
    ig_automation.action_config = {
        "public_reply": {"enabled": True, "variations": variations},
        "private_message": {"enabled": False}
    }
    db_session.commit()

    e1 = AutomationExecution(automation_id=ig_automation.id, user_id=test_user.id, social_account_id=ig_account.id, external_comment_id="rot_c1", platform="instagram", status=ExecutionStatus.PENDING.value)
    e2 = AutomationExecution(automation_id=ig_automation.id, user_id=test_user.id, social_account_id=ig_account.id, external_comment_id="rot_c2", platform="instagram", status=ExecutionStatus.PENDING.value)
    e3 = AutomationExecution(automation_id=ig_automation.id, user_id=test_user.id, social_account_id=ig_account.id, external_comment_id="rot_c3", platform="instagram", status=ExecutionStatus.PENDING.value)
    db_session.add_all([e1, e2, e3])
    db_session.commit()
    db_session.refresh(e1)
    db_session.refresh(e2)
    db_session.refresh(e3)

    calls = []
    with patch.object(meta_service, "reply_to_instagram_comment", side_effect=lambda comment_id, access_token, message: calls.append((comment_id, message)) or {"id": f"rep_{comment_id}"}):
        automation_execution_service.execute_pending_execution(e1.id, db=db_session)
        automation_execution_service.execute_pending_execution(e2.id, db=db_session)
        automation_execution_service.execute_pending_execution(e3.id, db=db_session)

    assert len(calls) == 3
    assert calls[0][1] == variations[e1.id % len(variations)]
    assert calls[1][1] == variations[e2.id % len(variations)]
    assert calls[2][1] == variations[e3.id % len(variations)]


def test_process_pending_executions_batch(db_session: Session, test_user: User, ig_account: SocialAccount, ig_automation: Automation, ig_comment: SocialComment):
    """Verify batch processing of pending executions."""
    e1 = AutomationExecution(automation_id=ig_automation.id, user_id=test_user.id, social_account_id=ig_account.id, comment_id=ig_comment.id, external_comment_id="batch_c1", platform="instagram", status=ExecutionStatus.PENDING.value)
    e2 = AutomationExecution(automation_id=ig_automation.id, user_id=test_user.id, social_account_id=ig_account.id, comment_id=ig_comment.id, external_comment_id="batch_c2", platform="instagram", status=ExecutionStatus.PENDING.value)
    db_session.add_all([e1, e2])
    db_session.commit()
    db_session.refresh(e1)
    db_session.refresh(e2)

    with patch.object(meta_service, "reply_to_instagram_comment", return_value={"id": "rep_b1"}), \
         patch.object(meta_service, "send_instagram_private_message", return_value={"message_id": "dm_b1"}):

        processed = automation_execution_service.process_pending_executions(db_session, limit=10)
        assert len(processed) >= 2
        processed_ids = [p.id for p in processed]
        assert e1.id in processed_ids
        assert e2.id in processed_ids
        for p in processed:
            assert p.status == ExecutionStatus.COMPLETED.value


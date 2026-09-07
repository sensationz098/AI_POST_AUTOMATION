import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.user import User
from app.models.brand import BrandProfile
from app.models.social_account import SocialAccount
from app.models.post import Post, PostStatus
from app.models.social_comment import SocialComment
from app.models.social_comment_reply import SocialCommentReply
from app.models.automation import Automation, AutomationStatus, TriggerType, PostTargetType
from app.models.automation_execution import AutomationExecution, ExecutionStatus, ActionExecutionStatus
from app.services.comment_trigger_service import comment_trigger_service
from app.services.comment_ingestion_service import meta_comment_ingestion_service
from app.core.security import get_password_hash


@pytest.fixture
def test_user(db_session: Session) -> User:
    user = User(
        email="trigger_user@socialai.com",
        hashed_password=get_password_hash("ValidPass123!"),
        full_name="Trigger Test User",
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
        account_id="17841400001",
        account_name="test_ig_account",
        status="CONNECTED",
        access_token="valid_ig_token"
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
        account_id="10000000001",
        account_name="Test Facebook Page",
        status="CONNECTED",
        access_token="valid_fb_token"
    )
    db_session.add(acc)
    db_session.commit()
    db_session.refresh(acc)
    return acc


@pytest.fixture
def brand(db_session: Session, test_user: User) -> BrandProfile:
    b = BrandProfile(
        user_id=test_user.id,
        name="Trigger Brand",
        tone_of_voice="Professional",
        cta_style="Direct",
        brand_colors=["#123456"]
    )
    db_session.add(b)
    db_session.commit()
    db_session.refresh(b)
    return b


@pytest.fixture
def ig_post(db_session: Session, test_user: User, brand: BrandProfile) -> Post:
    p = Post(
        user_id=test_user.id,
        brand_id=brand.id,
        title="IG Trigger Post",
        caption="Check out our new launch! Comment price for details.",
        platforms=["instagram"],
        status=PostStatus.PUBLISHED.value,
        ig_media_id="media_ig_123"
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


@pytest.fixture
def fb_post(db_session: Session, test_user: User, brand: BrandProfile) -> Post:
    p = Post(
        user_id=test_user.id,
        brand_id=brand.id,
        title="FB Trigger Post",
        caption="Facebook post content.",
        platforms=["facebook"],
        status=PostStatus.PUBLISHED.value,
        fb_post_id="post_fb_456"
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


# =========================================================================
# 1. KEYWORD MATCHING UNIT TESTS
# =========================================================================

def test_keyword_normalization():
    """Verify keywords are normalized: lowercase, stripped, deduplicated, empty removed."""
    raw = [" Price ", "COST", "  ", "price", "Link ", "link"]
    normalized = comment_trigger_service.normalize_keywords(raw)
    assert normalized == ["price", "cost", "link"]


def test_keyword_word_boundary_matching():
    """Verify word-boundary matching and prevention of false-positive substrings."""
    keywords = ["price", "info please", "cost"]

    # Direct match
    matched, kw = comment_trigger_service.match_keyword("What is the price?", keywords)
    assert matched is True
    assert kw == "price"

    # Multi-word phrase match
    matched, kw = comment_trigger_service.match_keyword("Send me info please!", keywords)
    assert matched is True
    assert kw == "info please"

    # Case insensitivity & punctuation
    matched, kw = comment_trigger_service.match_keyword("PRICE???", keywords)
    assert matched is True
    assert kw == "price"

    # False positive substring prevention: 'surprise' should NOT match 'price'
    matched, kw = comment_trigger_service.match_keyword("What a great surprise today!", keywords)
    assert matched is False
    assert kw is None

    # No match
    matched, kw = comment_trigger_service.match_keyword("Hello there how are you", keywords)
    assert matched is False
    assert kw is None


# =========================================================================
# 2. TRIGGER ENGINE EVALUATION TESTS
# =========================================================================

def test_any_comment_trigger_matching(db_session: Session, test_user: User, ig_account: SocialAccount, ig_post: Post):
    """Verify ANY_COMMENT trigger matches eligible comment and creates PENDING execution."""
    auto = Automation(
        user_id=test_user.id,
        social_account_id=ig_account.id,
        name="Any Comment Auto",
        platform="instagram",
        status=AutomationStatus.ACTIVE.value,
        post_target_type=PostTargetType.SPECIFIC_POST.value,
        external_post_id="media_ig_123",
        internal_post_id=ig_post.id,
        trigger_type=TriggerType.ANY_COMMENT.value,
        trigger_config={},
        action_config={
            "public_reply": {"enabled": True, "variations": ["Thanks! Check DM"]},
            "private_message": {"enabled": True, "message": "Here is the info"}
        }
    )
    db_session.add(auto)
    db_session.commit()

    comment = SocialComment(
        user_id=test_user.id,
        social_account_id=ig_account.id,
        platform="instagram",
        external_comment_id="comm_101",
        external_post_id="media_ig_123",
        comment_text="Just saying hi!",
        commenter_id="user_buyer_999",
        commenter_name="buyer_jane",
        webhook_object="instagram",
        processing_status="RECEIVED"
    )
    db_session.add(comment)
    db_session.commit()

    executions = comment_trigger_service.evaluate_comment(db_session, comment, ig_account)
    assert len(executions) == 1
    exec_record = executions[0]
    assert exec_record.automation_id == auto.id
    assert exec_record.status == ExecutionStatus.PENDING.value
    assert exec_record.public_reply_status == ActionExecutionStatus.PENDING.value
    assert exec_record.private_message_status == ActionExecutionStatus.PENDING.value
    assert exec_record.trigger_result["matched"] is True
    assert exec_record.trigger_result["trigger_type"] == "ANY_COMMENT"


def test_keyword_trigger_matching(db_session: Session, test_user: User, ig_account: SocialAccount, ig_post: Post):
    """Verify KEYWORD trigger matches when keyword is present."""
    auto = Automation(
        user_id=test_user.id,
        social_account_id=ig_account.id,
        name="Keyword Auto",
        platform="instagram",
        status=AutomationStatus.ACTIVE.value,
        post_target_type=PostTargetType.SPECIFIC_POST.value,
        external_post_id="media_ig_123",
        internal_post_id=ig_post.id,
        trigger_type=TriggerType.KEYWORD.value,
        trigger_config={"keywords": ["price", "cost", "info"]},
        action_config={
            "public_reply": {"enabled": True, "variations": ["Reply variation"]},
            "private_message": {"enabled": False, "message": None}
        }
    )
    db_session.add(auto)
    db_session.commit()

    comment = SocialComment(
        user_id=test_user.id,
        social_account_id=ig_account.id,
        platform="instagram",
        external_comment_id="comm_102",
        external_post_id="media_ig_123",
        comment_text="What's the PRICE for this?",
        commenter_id="user_buyer_999",
        commenter_name="buyer_jane",
        webhook_object="instagram",
        processing_status="RECEIVED"
    )
    db_session.add(comment)
    db_session.commit()

    executions = comment_trigger_service.evaluate_comment(db_session, comment, ig_account)
    assert len(executions) == 1
    exec_record = executions[0]
    assert exec_record.status == ExecutionStatus.PENDING.value
    assert exec_record.public_reply_status == ActionExecutionStatus.PENDING.value
    assert exec_record.private_message_status == ActionExecutionStatus.SKIPPED.value
    assert exec_record.trigger_result["matched_keyword"] == "price"


def test_keyword_trigger_non_matching(db_session: Session, test_user: User, ig_account: SocialAccount, ig_post: Post):
    """Verify KEYWORD trigger creates 0 executions when comment does not contain target keywords."""
    auto = Automation(
        user_id=test_user.id,
        social_account_id=ig_account.id,
        name="Keyword Auto",
        platform="instagram",
        status=AutomationStatus.ACTIVE.value,
        post_target_type=PostTargetType.SPECIFIC_POST.value,
        external_post_id="media_ig_123",
        trigger_type=TriggerType.KEYWORD.value,
        trigger_config={"keywords": ["price", "cost"]},
        action_config={"public_reply": {"enabled": True, "variations": ["Var 1"]}}
    )
    db_session.add(auto)
    db_session.commit()

    comment = SocialComment(
        user_id=test_user.id,
        social_account_id=ig_account.id,
        platform="instagram",
        external_comment_id="comm_103",
        external_post_id="media_ig_123",
        comment_text="Nice photo!",
        commenter_id="user_buyer_999",
        webhook_object="instagram",
        processing_status="RECEIVED"
    )
    db_session.add(comment)
    db_session.commit()

    executions = comment_trigger_service.evaluate_comment(db_session, comment, ig_account)
    assert len(executions) == 0


# =========================================================================
# 3. OWNER / SELF-COMMENT AND ECHO PROTECTION
# =========================================================================

def test_owner_self_comment_ignored(db_session: Session, test_user: User, ig_account: SocialAccount, ig_post: Post):
    """Verify comments from connected account owner are ignored."""
    auto = Automation(
        user_id=test_user.id,
        social_account_id=ig_account.id,
        name="Any Auto",
        platform="instagram",
        status=AutomationStatus.ACTIVE.value,
        post_target_type=PostTargetType.SPECIFIC_POST.value,
        external_post_id="media_ig_123",
        trigger_type=TriggerType.ANY_COMMENT.value,
        trigger_config={},
        action_config={"public_reply": {"enabled": True, "variations": ["Var 1"]}}
    )
    db_session.add(auto)
    db_session.commit()

    # Commenter ID matches the account's own account_id
    owner_comment = SocialComment(
        user_id=test_user.id,
        social_account_id=ig_account.id,
        platform="instagram",
        external_comment_id="comm_owner_1",
        external_post_id="media_ig_123",
        comment_text="Replying to everyone soon!",
        commenter_id=ig_account.account_id,
        commenter_name=ig_account.account_name,
        webhook_object="instagram",
        processing_status="RECEIVED"
    )
    db_session.add(owner_comment)
    db_session.commit()

    executions = comment_trigger_service.evaluate_comment(db_session, owner_comment, ig_account)
    assert len(executions) == 0


def test_owner_reply_echo_ignored(db_session: Session, test_user: User, ig_account: SocialAccount, ig_post: Post):
    """Verify webhook echo of a reply posted by Sensationz owner is ignored."""
    auto = Automation(
        user_id=test_user.id,
        social_account_id=ig_account.id,
        name="Any Auto",
        platform="instagram",
        status=AutomationStatus.ACTIVE.value,
        post_target_type=PostTargetType.SPECIFIC_POST.value,
        external_post_id="media_ig_123",
        trigger_type=TriggerType.ANY_COMMENT.value,
        trigger_config={},
        action_config={"public_reply": {"enabled": True, "variations": ["Var 1"]}}
    )
    db_session.add(auto)

    # Recorded owner reply in social_comment_replies table
    reply = SocialCommentReply(
        comment_id=1,
        user_id=test_user.id,
        platform="instagram",
        external_reply_id="echo_reply_999",
        message="Thanks for reaching out!",
        status="SUCCESS"
    )
    db_session.add(reply)
    db_session.commit()

    echo_comment = SocialComment(
        user_id=test_user.id,
        social_account_id=ig_account.id,
        platform="instagram",
        external_comment_id="echo_reply_999",
        external_post_id="media_ig_123",
        comment_text="Thanks for reaching out!",
        commenter_id="random_id",
        webhook_object="instagram",
        processing_status="RECEIVED"
    )
    db_session.add(echo_comment)
    db_session.commit()

    executions = comment_trigger_service.evaluate_comment(db_session, echo_comment, ig_account)
    assert len(executions) == 0


# =========================================================================
# 4. INACTIVE / MISMATCHED AUTOMATIONS
# =========================================================================

def test_draft_and_paused_automations_ignored(db_session: Session, test_user: User, ig_account: SocialAccount):
    """Verify DRAFT and PAUSED automations do not trigger executions."""
    draft_auto = Automation(
        user_id=test_user.id,
        social_account_id=ig_account.id,
        name="Draft Auto",
        platform="instagram",
        status=AutomationStatus.DRAFT.value,
        post_target_type=PostTargetType.SPECIFIC_POST.value,
        external_post_id="media_ig_123",
        trigger_type=TriggerType.ANY_COMMENT.value,
        trigger_config={},
        action_config={"public_reply": {"enabled": True, "variations": ["Var 1"]}}
    )
    paused_auto = Automation(
        user_id=test_user.id,
        social_account_id=ig_account.id,
        name="Paused Auto",
        platform="instagram",
        status=AutomationStatus.PAUSED.value,
        post_target_type=PostTargetType.SPECIFIC_POST.value,
        external_post_id="media_ig_123",
        trigger_type=TriggerType.ANY_COMMENT.value,
        trigger_config={},
        action_config={"public_reply": {"enabled": True, "variations": ["Var 1"]}}
    )
    db_session.add_all([draft_auto, paused_auto])
    db_session.commit()

    comment = SocialComment(
        user_id=test_user.id,
        social_account_id=ig_account.id,
        platform="instagram",
        external_comment_id="comm_104",
        external_post_id="media_ig_123",
        comment_text="Price please",
        commenter_id="user_buyer_999",
        webhook_object="instagram",
        processing_status="RECEIVED"
    )
    db_session.add(comment)
    db_session.commit()

    executions = comment_trigger_service.evaluate_comment(db_session, comment, ig_account)
    assert len(executions) == 0


def test_mismatched_post_account_platform_ignored(
    db_session: Session,
    test_user: User,
    ig_account: SocialAccount,
    fb_account: SocialAccount
):
    """Verify mismatched post, account, or platform does not trigger automation."""
    # IG Automation on Post A
    auto = Automation(
        user_id=test_user.id,
        social_account_id=ig_account.id,
        name="IG Post A Auto",
        platform="instagram",
        status=AutomationStatus.ACTIVE.value,
        post_target_type=PostTargetType.SPECIFIC_POST.value,
        external_post_id="media_post_A",
        trigger_type=TriggerType.ANY_COMMENT.value,
        trigger_config={},
        action_config={"public_reply": {"enabled": True, "variations": ["Var 1"]}}
    )
    db_session.add(auto)
    db_session.commit()

    # Case 1: Comment on Post B (wrong post)
    comm_wrong_post = SocialComment(
        user_id=test_user.id,
        social_account_id=ig_account.id,
        platform="instagram",
        external_comment_id="comm_post_b",
        external_post_id="media_post_B",
        comment_text="Hello",
        commenter_id="buyer_1",
        webhook_object="instagram",
        processing_status="RECEIVED"
    )
    executions = comment_trigger_service.evaluate_comment(db_session, comm_wrong_post, ig_account)
    assert len(executions) == 0

    # Case 2: Facebook comment (wrong platform / wrong account)
    comm_fb = SocialComment(
        user_id=test_user.id,
        social_account_id=fb_account.id,
        platform="facebook",
        external_comment_id="comm_fb_1",
        external_post_id="media_post_A",
        comment_text="Hello",
        commenter_id="buyer_1",
        webhook_object="page",
        processing_status="RECEIVED"
    )
    executions = comment_trigger_service.evaluate_comment(db_session, comm_fb, fb_account)
    assert len(executions) == 0


# =========================================================================
# 5. MULTIPLE AUTOMATIONS & IDEMPOTENCY
# =========================================================================

def test_multiple_matching_automations_on_same_post(
    db_session: Session,
    test_user: User,
    ig_account: SocialAccount
):
    """Verify multiple matching automations for the same post each create an execution."""
    auto_any = Automation(
        user_id=test_user.id,
        social_account_id=ig_account.id,
        name="Any Comment Auto",
        platform="instagram",
        status=AutomationStatus.ACTIVE.value,
        post_target_type=PostTargetType.SPECIFIC_POST.value,
        external_post_id="media_multi_1",
        trigger_type=TriggerType.ANY_COMMENT.value,
        trigger_config={},
        action_config={"public_reply": {"enabled": True, "variations": ["Var 1"]}}
    )
    auto_kw = Automation(
        user_id=test_user.id,
        social_account_id=ig_account.id,
        name="Price Keyword Auto",
        platform="instagram",
        status=AutomationStatus.ACTIVE.value,
        post_target_type=PostTargetType.SPECIFIC_POST.value,
        external_post_id="media_multi_1",
        trigger_type=TriggerType.KEYWORD.value,
        trigger_config={"keywords": ["price"]},
        action_config={"private_message": {"enabled": True, "message": "Price is $10"}}
    )
    db_session.add_all([auto_any, auto_kw])
    db_session.commit()

    comment = SocialComment(
        user_id=test_user.id,
        social_account_id=ig_account.id,
        platform="instagram",
        external_comment_id="comm_multi_1",
        external_post_id="media_multi_1",
        comment_text="Can I get the price?",
        commenter_id="buyer_1",
        webhook_object="instagram",
        processing_status="RECEIVED"
    )
    db_session.add(comment)
    db_session.commit()

    executions = comment_trigger_service.evaluate_comment(db_session, comment, ig_account)
    assert len(executions) == 2
    auto_ids = {e.automation_id for e in executions}
    assert auto_ids == {auto_any.id, auto_kw.id}


def test_idempotent_duplicate_webhook_processing(
    db_session: Session,
    test_user: User,
    ig_account: SocialAccount
):
    """Verify calling evaluate_comment on duplicate delivery returns existing execution and does not create duplicate."""
    auto = Automation(
        user_id=test_user.id,
        social_account_id=ig_account.id,
        name="Idempotency Test Auto",
        platform="instagram",
        status=AutomationStatus.ACTIVE.value,
        post_target_type=PostTargetType.SPECIFIC_POST.value,
        external_post_id="media_idem_1",
        trigger_type=TriggerType.ANY_COMMENT.value,
        trigger_config={},
        action_config={"public_reply": {"enabled": True, "variations": ["Var 1"]}}
    )
    db_session.add(auto)
    db_session.commit()

    comment = SocialComment(
        user_id=test_user.id,
        social_account_id=ig_account.id,
        platform="instagram",
        external_comment_id="comm_idem_999",
        external_post_id="media_idem_1",
        comment_text="Hello world",
        commenter_id="buyer_1",
        webhook_object="instagram",
        processing_status="RECEIVED"
    )
    db_session.add(comment)
    db_session.commit()

    # First event delivery
    execs_1 = comment_trigger_service.evaluate_comment(db_session, comment, ig_account)
    assert len(execs_1) == 1
    first_id = execs_1[0].id

    # Second duplicate event delivery
    execs_2 = comment_trigger_service.evaluate_comment(db_session, comment, ig_account)
    assert len(execs_2) == 1
    assert execs_2[0].id == first_id

    # Verify database has exactly 1 row
    all_execs = db_session.query(AutomationExecution).filter(
        AutomationExecution.automation_id == auto.id,
        AutomationExecution.external_comment_id == "comm_idem_999"
    ).all()
    assert len(all_execs) == 1


def test_concurrent_duplicate_race_safety(
    db_session: Session,
    test_user: User,
    ig_account: SocialAccount
):
    """Verify IntegrityError on concurrent insert race safely resolves to existing execution."""
    auto = Automation(
        user_id=test_user.id,
        social_account_id=ig_account.id,
        name="Race Test Auto",
        platform="instagram",
        status=AutomationStatus.ACTIVE.value,
        post_target_type=PostTargetType.SPECIFIC_POST.value,
        external_post_id="media_race_1",
        trigger_type=TriggerType.ANY_COMMENT.value,
        trigger_config={},
        action_config={"public_reply": {"enabled": True, "variations": ["Var 1"]}}
    )
    db_session.add(auto)
    db_session.commit()

    comment = SocialComment(
        user_id=test_user.id,
        social_account_id=ig_account.id,
        platform="instagram",
        external_comment_id="comm_race_1",
        external_post_id="media_race_1",
        comment_text="Hello race",
        commenter_id="buyer_1",
        webhook_object="instagram",
        processing_status="RECEIVED"
    )
    db_session.add(comment)
    db_session.commit()

    # Simulate existing execution created by winning concurrent thread
    existing = AutomationExecution(
        automation_id=auto.id,
        user_id=test_user.id,
        social_account_id=ig_account.id,
        comment_id=comment.id,
        external_comment_id=comment.external_comment_id,
        external_post_id=comment.external_post_id,
        platform=auto.platform,
        status=ExecutionStatus.PENDING.value
    )
    db_session.add(existing)
    db_session.commit()

    # Calling create_execution_idempotent returns existing
    res = comment_trigger_service.create_execution_idempotent(db_session, auto, comment)
    assert res is not None
    assert res.id == existing.id


# =========================================================================
# 6. WEBHOOK INGESTION PIPELINE INTEGRATION TESTS
# =========================================================================

def test_facebook_webhook_ingestion_triggers_automation(
    db_session: Session,
    test_user: User,
    fb_account: SocialAccount,
    fb_post: Post
):
    """Verify Facebook comment webhook parses comment, creates SocialComment, and triggers active automation."""
    auto = Automation(
        user_id=test_user.id,
        social_account_id=fb_account.id,
        name="FB Hook Auto",
        platform="facebook",
        status=AutomationStatus.ACTIVE.value,
        post_target_type=PostTargetType.SPECIFIC_POST.value,
        external_post_id="post_fb_456",
        trigger_type=TriggerType.KEYWORD.value,
        trigger_config={"keywords": ["info", "price"]},
        action_config={
            "public_reply": {"enabled": True, "variations": ["Thanks for commenting!"]},
            "private_message": {"enabled": True, "message": "Here is details"}
        }
    )
    db_session.add(auto)
    db_session.commit()

    # Simulate incoming Facebook webhook payload
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
                            "comment_id": "fb_comm_web_1",
                            "post_id": "post_fb_456",
                            "message": "Send me info please!",
                            "from": {"id": "fb_user_123", "name": "FB Customer"}
                        }
                    }
                ]
            }
        ]
    }

    ingested = meta_comment_ingestion_service.parse_and_ingest_payload(db_session, payload)
    assert len(ingested) == 1
    assert ingested[0].external_comment_id == "fb_comm_web_1"

    # Verify AutomationExecution was created
    execution = db_session.query(AutomationExecution).filter(
        AutomationExecution.automation_id == auto.id,
        AutomationExecution.external_comment_id == "fb_comm_web_1"
    ).first()

    assert execution is not None
    assert execution.status == ExecutionStatus.PENDING.value
    assert execution.contact_identifier == "fb_user_123"
    assert execution.contact_name == "FB Customer"
    assert execution.trigger_result["matched_keyword"] == "info"


def test_instagram_webhook_ingestion_triggers_automation(
    db_session: Session,
    test_user: User,
    ig_account: SocialAccount,
    ig_post: Post
):
    """Verify Instagram comment webhook parses comment, creates SocialComment, and triggers active automation."""
    auto = Automation(
        user_id=test_user.id,
        social_account_id=ig_account.id,
        name="IG Hook Auto",
        platform="instagram",
        status=AutomationStatus.ACTIVE.value,
        post_target_type=PostTargetType.SPECIFIC_POST.value,
        external_post_id="media_ig_123",
        trigger_type=TriggerType.ANY_COMMENT.value,
        trigger_config={},
        action_config={
            "public_reply": {"enabled": True, "variations": ["DM sent!"]},
            "private_message": {"enabled": True, "message": "Link in DM"}
        }
    )
    db_session.add(auto)
    db_session.commit()

    # Simulate incoming Instagram webhook payload
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
                            "id": "ig_comm_web_1",
                            "text": "Loving this post!",
                            "media": {"id": "media_ig_123"},
                            "from": {"id": "ig_user_456", "username": "ig_fan"}
                        }
                    }
                ]
            }
        ]
    }

    ingested = meta_comment_ingestion_service.parse_and_ingest_payload(db_session, payload)
    assert len(ingested) == 1
    assert ingested[0].external_comment_id == "ig_comm_web_1"

    # Verify AutomationExecution was created
    execution = db_session.query(AutomationExecution).filter(
        AutomationExecution.automation_id == auto.id,
        AutomationExecution.external_comment_id == "ig_comm_web_1"
    ).first()

    assert execution is not None
    assert execution.status == ExecutionStatus.PENDING.value
    assert execution.contact_identifier == "ig_user_456"
    assert execution.contact_name == "ig_fan"
    assert execution.trigger_result["trigger_type"] == "ANY_COMMENT"


def test_no_external_api_dispatch_in_phase_3(
    db_session: Session,
    test_user: User,
    ig_account: SocialAccount,
    ig_post: Post
):
    """Verify Phase 3 strictly creates PENDING execution without dispatching any Meta replies or DMs."""
    with patch("requests.post") as mock_post, patch("requests.get") as mock_get:
        auto = Automation(
            user_id=test_user.id,
            social_account_id=ig_account.id,
            name="No Dispatch Auto",
            platform="instagram",
            status=AutomationStatus.ACTIVE.value,
            post_target_type=PostTargetType.SPECIFIC_POST.value,
            external_post_id="media_ig_123",
            trigger_type=TriggerType.ANY_COMMENT.value,
            trigger_config={},
            action_config={
                "public_reply": {"enabled": True, "variations": ["Reply"]},
                "private_message": {"enabled": True, "message": "DM"}
            }
        )
        db_session.add(auto)
        db_session.commit()

        comment = SocialComment(
            user_id=test_user.id,
            social_account_id=ig_account.id,
            platform="instagram",
            external_comment_id="comm_nodispatch_1",
            external_post_id="media_ig_123",
            comment_text="Hello",
            commenter_id="user_1",
            webhook_object="instagram",
            processing_status="RECEIVED"
        )
        db_session.add(comment)
        db_session.commit()

        executions = comment_trigger_service.evaluate_comment(db_session, comment, ig_account)
        assert len(executions) == 1
        assert executions[0].status == ExecutionStatus.PENDING.value

        # Zero external requests should be made
        mock_post.assert_not_called()
        mock_get.assert_not_called()


def test_instagram_webhook_keyword_non_matching_creates_zero_executions(
    db_session: Session,
    test_user: User,
    ig_account: SocialAccount,
    ig_post: Post
):
    """Verify Instagram webhook comment with non-matching keyword ingests comment but creates 0 executions."""
    auto = Automation(
        user_id=test_user.id,
        social_account_id=ig_account.id,
        name="IG Keyword Auto",
        platform="instagram",
        status=AutomationStatus.ACTIVE.value,
        post_target_type=PostTargetType.SPECIFIC_POST.value,
        external_post_id="media_ig_123",
        trigger_type=TriggerType.KEYWORD.value,
        trigger_config={"keywords": ["coupon", "discount"]},
        action_config={
            "public_reply": {"enabled": True, "variations": ["Check DM"]},
            "private_message": {"enabled": True, "message": "Code is 20OFF"}
        }
    )
    db_session.add(auto)
    db_session.commit()

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
                            "id": "ig_comm_nomatch_1",
                            "text": "Great photo! Beautiful view.",
                            "media": {"id": "media_ig_123"},
                            "from": {"id": "ig_user_789", "username": "ig_wanderer"}
                        }
                    }
                ]
            }
        ]
    }

    ingested = meta_comment_ingestion_service.parse_and_ingest_payload(db_session, payload)
    assert len(ingested) == 1
    assert ingested[0].external_comment_id == "ig_comm_nomatch_1"

    # Verify zero AutomationExecution records created
    execs = db_session.query(AutomationExecution).filter(
        AutomationExecution.external_comment_id == "ig_comm_nomatch_1"
    ).all()
    assert len(execs) == 0


def test_instagram_webhook_duplicate_delivery_idempotency(
    db_session: Session,
    test_user: User,
    ig_account: SocialAccount,
    ig_post: Post
):
    """Verify duplicate Instagram webhook delivery creates exactly 1 execution and remains idempotent."""
    auto = Automation(
        user_id=test_user.id,
        social_account_id=ig_account.id,
        name="IG Idempotent Auto",
        platform="instagram",
        status=AutomationStatus.ACTIVE.value,
        post_target_type=PostTargetType.SPECIFIC_POST.value,
        external_post_id="media_ig_123",
        trigger_type=TriggerType.KEYWORD.value,
        trigger_config={"keywords": ["deal"]},
        action_config={
            "public_reply": {"enabled": True, "variations": ["DM sent"]},
            "private_message": {"enabled": True, "message": "Here is the deal"}
        }
    )
    db_session.add(auto)
    db_session.commit()

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
                            "id": "ig_comm_dup_101",
                            "text": "Send me the deal please!",
                            "media": {"id": "media_ig_123"},
                            "from": {"id": "ig_user_deal_1", "username": "deal_seeker"}
                        }
                    }
                ]
            }
        ]
    }

    # Delivery 1
    meta_comment_ingestion_service.parse_and_ingest_payload(db_session, payload)
    # Delivery 2 (Duplicate webhook from Meta)
    meta_comment_ingestion_service.parse_and_ingest_payload(db_session, payload)

    all_execs = db_session.query(AutomationExecution).filter(
        AutomationExecution.automation_id == auto.id,
        AutomationExecution.external_comment_id == "ig_comm_dup_101"
    ).all()

    assert len(all_execs) == 1
    assert all_execs[0].status == ExecutionStatus.PENDING.value
    assert all_execs[0].trigger_result["matched_keyword"] == "deal"


def test_instagram_comment_trigger_observable_logging(
    db_session: Session,
    test_user: User,
    ig_account: SocialAccount,
    ig_post: Post,
    caplog: pytest.LogCaptureFixture
):
    """Verify exact observable [COMMENT_TRIGGER] log statements are produced for Instagram evaluation."""
    import logging
    caplog.set_level(logging.INFO)

    auto = Automation(
        user_id=test_user.id,
        social_account_id=ig_account.id,
        name="Observable IG Auto",
        platform="instagram",
        status=AutomationStatus.ACTIVE.value,
        post_target_type=PostTargetType.SPECIFIC_POST.value,
        external_post_id="media_ig_123",
        trigger_type=TriggerType.KEYWORD.value,
        trigger_config={"keywords": ["pricing"]},
        action_config={
            "public_reply": {"enabled": True, "variations": ["Sent!"]},
            "private_message": {"enabled": True, "message": "Pricing details"}
        }
    )
    db_session.add(auto)
    db_session.commit()

    comment = SocialComment(
        user_id=test_user.id,
        social_account_id=ig_account.id,
        platform="instagram",
        external_comment_id="comm_observe_1",
        external_post_id="media_ig_123",
        comment_text="What is your pricing?",
        commenter_id="ig_customer_55",
        commenter_name="customer_sarah",
        webhook_object="instagram",
        processing_status="RECEIVED"
    )
    db_session.add(comment)
    db_session.commit()

    executions = comment_trigger_service.evaluate_comment(db_session, comment, ig_account)
    assert len(executions) == 1

    log_text = caplog.text
    assert "[COMMENT_TRIGGER] Evaluating Instagram comment comm_observe_1" in log_text
    assert f"[COMMENT_TRIGGER] account_id={ig_account.account_id} social_account_id={ig_account.id}" in log_text
    assert "[COMMENT_TRIGGER] external_post_id=media_ig_123" in log_text
    assert "[COMMENT_TRIGGER] candidate_automations=1" in log_text
    assert f"[COMMENT_TRIGGER] automation_id={auto.id} status=ACTIVE trigger_type=KEYWORD" in log_text
    assert "[COMMENT_TRIGGER] keyword_match=true matched_keyword=pricing" in log_text
    assert f"[COMMENT_TRIGGER] execution_created={executions[0].id} status=PENDING" in log_text


def test_instagram_webhook_with_metadata_account_lookup(
    db_session: Session,
    test_user: User
):
    """Verify Instagram webhook resolution works when account_id is found in metadata_json."""
    acc = SocialAccount(
        user_id=test_user.id,
        platform="instagram",
        account_id="page_linked_id_999",
        account_name="meta_ig_account",
        status="CONNECTED",
        access_token="valid_token",
        metadata_json={
            "instagram_business_account": {"id": "ig_biz_id_888"}
        }
    )
    db_session.add(acc)
    db_session.commit()

    auto = Automation(
        user_id=test_user.id,
        social_account_id=acc.id,
        name="Meta Lookup Auto",
        platform="instagram",
        status=AutomationStatus.ACTIVE.value,
        post_target_type=PostTargetType.SPECIFIC_POST.value,
        external_post_id="media_meta_1",
        trigger_type=TriggerType.ANY_COMMENT.value,
        trigger_config={},
        action_config={"public_reply": {"enabled": True, "variations": ["Thanks"]}}
    )
    db_session.add(auto)
    db_session.commit()

    payload = {
        "object": "instagram",
        "entry": [
            {
                "id": "ig_biz_id_888",
                "time": 1710000000,
                "changes": [
                    {
                        "field": "comments",
                        "value": {
                            "id": "comm_meta_lookup_1",
                            "text": "Awesome post!",
                            "media": {"id": "media_meta_1"},
                            "from": {"id": "user_buyer_11", "username": "ig_user_11"}
                        }
                    }
                ]
            }
        ]
    }

    ingested = meta_comment_ingestion_service.parse_and_ingest_payload(db_session, payload)
    assert len(ingested) == 1

    execs = db_session.query(AutomationExecution).filter(
        AutomationExecution.automation_id == auto.id,
        AutomationExecution.external_comment_id == "comm_meta_lookup_1"
    ).all()
    assert len(execs) == 1
    assert execs[0].status == ExecutionStatus.PENDING.value


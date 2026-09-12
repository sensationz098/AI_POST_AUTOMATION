import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.user import User
from app.models.social_account import SocialAccount
from app.models.social_comment import SocialComment
from app.models.social_comment_reply import SocialCommentReply
from app.models.automation import Automation, AutomationStatus, TriggerType, PostTargetType
from app.models.automation_execution import AutomationExecution, ExecutionStatus, ActionExecutionStatus
from app.core.security import create_access_token
from app.core.security_encryption import encrypt_token

client = TestClient(app)

@pytest.fixture
def inbox_user(db_session: Session):
    user = User(
        email=f"inbox_user_{datetime.now(timezone.utc).timestamp()}@socialai.com",
        hashed_password="HashedPassword123!",
        is_active=True,
        full_name="Inbox Test User"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def inbox_auth_headers(inbox_user: User):
    token = create_access_token(subject=str(inbox_user.id), role=inbox_user.role or "user")
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def other_inbox_user(db_session: Session):
    user = User(
        email=f"other_inbox_user_{datetime.now(timezone.utc).timestamp()}@socialai.com",
        hashed_password="HashedPassword123!",
        is_active=True,
        full_name="Other Inbox User"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def other_inbox_headers(other_inbox_user: User):
    token = create_access_token(subject=str(other_inbox_user.id), role=other_inbox_user.role or "user")
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def setup_inbox_data(db_session: Session, inbox_user: User, other_inbox_user: User):
    # Connected accounts
    ig_acc = SocialAccount(
        user_id=inbox_user.id,
        platform="instagram",
        account_id="ig_inbox_acc_1",
        account_name="my_ig_brand",
        status="CONNECTED",
        access_token=encrypt_token("IG_ACCESS_TOKEN")
    )
    fb_acc = SocialAccount(
        user_id=inbox_user.id,
        platform="facebook",
        account_id="fb_inbox_page_1",
        account_name="My FB Brand",
        status="CONNECTED",
        access_token=encrypt_token("FB_ACCESS_TOKEN")
    )
    db_session.add_all([ig_acc, fb_acc])
    db_session.commit()
    db_session.refresh(ig_acc)
    db_session.refresh(fb_acc)

    # Automation
    auto = Automation(
        user_id=inbox_user.id,
        social_account_id=ig_acc.id,
        platform="instagram",
        name="Price Inquiry Responder",
        status=AutomationStatus.ACTIVE.value,
        post_target_type=PostTargetType.SPECIFIC_POST.value,
        external_post_id="post_inbox_100",
        trigger_type=TriggerType.KEYWORD.value,
        trigger_config={"keywords": ["price", "cost"]},
        action_config={"public_reply": {"enabled": True, "variations": ["Check DM!"]}}
    )
    db_session.add(auto)
    db_session.commit()
    db_session.refresh(auto)

    now = datetime.now(timezone.utc)

    # 1. Comment that was AUTOMATED
    c_auto = SocialComment(
        user_id=inbox_user.id,
        social_account_id=ig_acc.id,
        platform="instagram",
        external_comment_id="comm_inbox_auto_1",
        external_post_id="post_inbox_100",
        comment_text="How much is the price?",
        commenter_id="user_buyer_1",
        commenter_name="BuyerOne",
        event_timestamp=now - timedelta(minutes=10),
        webhook_object="instagram",
        processing_status="PROCESSED"
    )
    db_session.add(c_auto)
    db_session.commit()
    db_session.refresh(c_auto)

    exec_record = AutomationExecution(
        automation_id=auto.id,
        user_id=inbox_user.id,
        social_account_id=ig_acc.id,
        comment_id=c_auto.id,
        external_comment_id="comm_inbox_auto_1",
        external_post_id="post_inbox_100",
        platform="instagram",
        contact_identifier="user_buyer_1",
        contact_name="BuyerOne",
        status=ExecutionStatus.COMPLETED.value,
        trigger_result={"matched": True, "trigger_type": "KEYWORD", "matched_keyword": "price"},
        public_reply_status=ActionExecutionStatus.SUCCESS.value
    )
    db_session.add(exec_record)

    # 2. Comment that NEEDS REPLY
    c_needs_reply = SocialComment(
        user_id=inbox_user.id,
        social_account_id=ig_acc.id,
        platform="instagram",
        external_comment_id="comm_inbox_needs_reply_1",
        external_post_id="post_inbox_100",
        comment_text="Do you ship to Canada?",
        commenter_id="user_buyer_2",
        commenter_name="BuyerTwo",
        event_timestamp=now - timedelta(minutes=5),
        webhook_object="instagram",
        processing_status="RECEIVED"
    )
    db_session.add(c_needs_reply)

    # 3. Comment that was REPLIED to manually
    c_replied = SocialComment(
        user_id=inbox_user.id,
        social_account_id=fb_acc.id,
        platform="facebook",
        external_comment_id="comm_inbox_replied_1",
        external_post_id="fb_post_200",
        comment_text="What are your hours?",
        commenter_id="user_buyer_3",
        commenter_name="BuyerThree",
        event_timestamp=now - timedelta(hours=1),
        webhook_object="page",
        processing_status="PROCESSED"
    )
    db_session.add(c_replied)
    db_session.commit()
    db_session.refresh(c_replied)

    reply_rec = SocialCommentReply(
        comment_id=c_replied.id,
        user_id=inbox_user.id,
        platform="facebook",
        message="We are open 9am to 6pm!",
        external_reply_id="fb_reply_999",
        status="SUCCESS"
    )
    db_session.add(reply_rec)

    # 4. Comment that is IGNORED (e.g. owner self comment)
    c_owner = SocialComment(
        user_id=inbox_user.id,
        social_account_id=fb_acc.id,
        platform="facebook",
        external_comment_id="comm_inbox_owner_1",
        external_post_id="fb_post_200",
        comment_text="Don't forget to like and share!",
        commenter_id="fb_inbox_page_1",
        commenter_name="My FB Brand",
        event_timestamp=now - timedelta(hours=2),
        webhook_object="page",
        processing_status="IGNORED"
    )
    db_session.add(c_owner)

    # 5. Comment that is FAILED
    c_failed = SocialComment(
        user_id=inbox_user.id,
        social_account_id=ig_acc.id,
        platform="instagram",
        external_comment_id="comm_inbox_failed_1",
        external_post_id="post_inbox_100",
        comment_text="Error comment test",
        commenter_id="user_buyer_4",
        commenter_name="BuyerFour",
        event_timestamp=now - timedelta(hours=3),
        webhook_object="instagram",
        processing_status="FAILED"
    )
    db_session.add(c_failed)

    # 6. Other user's comment (Tenant Isolation test)
    c_other = SocialComment(
        user_id=other_inbox_user.id,
        social_account_id=9999,
        platform="instagram",
        external_comment_id="comm_other_tenant_1",
        comment_text="Secret comment from other user",
        commenter_name="SecretUser",
        webhook_object="instagram",
        processing_status="RECEIVED"
    )
    db_session.add(c_other)

    db_session.commit()

    return {
        "user": inbox_user,
        "ig_acc": ig_acc,
        "fb_acc": fb_acc,
        "auto": auto,
        "c_auto": c_auto,
        "c_needs_reply": c_needs_reply,
        "c_replied": c_replied,
        "c_owner": c_owner,
        "c_failed": c_failed,
        "c_other": c_other
    }

def test_inbox_enriched_response_format(inbox_auth_headers, setup_inbox_data):
    """Verify GET /social-comments/ returns automation_execution, lifecycle_status, and status_reason."""
    res = client.get("/api/v1/social-comments/", headers=inbox_auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 5

    # Check automated comment
    auto_item = next((c for c in data if c["external_comment_id"] == "comm_inbox_auto_1"), None)
    assert auto_item is not None
    assert auto_item["lifecycle_status"] == "AUTOMATED"
    assert "Price Inquiry Responder" in auto_item["status_reason"]
    assert auto_item["automation_execution"] is not None
    assert auto_item["automation_execution"]["automation_name"] == "Price Inquiry Responder"
    assert auto_item["automation_execution"]["matched_keyword"] == "price"

    # Check needs reply comment
    needs_reply_item = next((c for c in data if c["external_comment_id"] == "comm_inbox_needs_reply_1"), None)
    assert needs_reply_item is not None
    assert needs_reply_item["lifecycle_status"] == "NEEDS_REPLY"
    assert needs_reply_item["status_reason"] == "No automation matched this comment."

    # Check replied comment
    replied_item = next((c for c in data if c["external_comment_id"] == "comm_inbox_replied_1"), None)
    assert replied_item is not None
    assert replied_item["lifecycle_status"] == "REPLIED"
    assert len(replied_item["replies"]) == 1

    # Check owner comment
    owner_item = next((c for c in data if c["external_comment_id"] == "comm_inbox_owner_1"), None)
    assert owner_item is not None
    assert owner_item["lifecycle_status"] == "OWNER_COMMENT"

    # Check failed comment
    failed_item = next((c for c in data if c["external_comment_id"] == "comm_inbox_failed_1"), None)
    assert failed_item is not None
    assert failed_item["lifecycle_status"] == "FAILED"

def test_inbox_status_filters(inbox_auth_headers, setup_inbox_data):
    """Verify filtering by status query parameter."""
    # Filter: needs_reply
    res = client.get("/api/v1/social-comments/?status=needs_reply", headers=inbox_auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert all(c["lifecycle_status"] == "NEEDS_REPLY" for c in data)
    assert any(c["external_comment_id"] == "comm_inbox_needs_reply_1" for c in data)

    # Filter: automated
    res = client.get("/api/v1/social-comments/?status=automated", headers=inbox_auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert all(c["lifecycle_status"] == "AUTOMATED" for c in data)
    assert any(c["external_comment_id"] == "comm_inbox_auto_1" for c in data)

    # Filter: replied
    res = client.get("/api/v1/social-comments/?status=replied", headers=inbox_auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert all(c["lifecycle_status"] == "REPLIED" for c in data)
    assert any(c["external_comment_id"] == "comm_inbox_replied_1" for c in data)

def test_inbox_search_filter(inbox_auth_headers, setup_inbox_data):
    """Verify searching comment text and commenter names."""
    res = client.get("/api/v1/social-comments/?search=Canada", headers=inbox_auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["external_comment_id"] == "comm_inbox_needs_reply_1"

    res2 = client.get("/api/v1/social-comments/?search=BuyerOne", headers=inbox_auth_headers)
    assert res2.status_code == 200
    data2 = res2.json()
    assert len(data2) == 1
    assert data2[0]["external_comment_id"] == "comm_inbox_auto_1"

def test_inbox_summary_endpoint(inbox_auth_headers, setup_inbox_data):
    """Verify GET /social-comments/inbox-summary returns exact status counts and connected platform health."""
    res = client.get("/api/v1/social-comments/inbox-summary", headers=inbox_auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "status_counts" in data
    assert "health" in data

    counts = data["status_counts"]
    assert counts["all"] >= 5
    assert counts["needs_reply"] >= 1
    assert counts["automated"] >= 1
    assert counts["replied"] >= 1
    assert counts["ignored"] >= 1
    assert counts["failed"] >= 1

    health = data["health"]
    assert health["instagram_connected"] is True
    assert health["facebook_connected"] is True
    assert health["active_automations_count"] >= 1

def test_inbox_tenant_isolation(inbox_auth_headers, other_inbox_headers, setup_inbox_data):
    """Verify strict user isolation (User A cannot see User B's comments)."""
    res = client.get("/api/v1/social-comments/", headers=inbox_auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert not any(c["external_comment_id"] == "comm_other_tenant_1" for c in data)

    res_other = client.get("/api/v1/social-comments/", headers=other_inbox_headers)
    assert res_other.status_code == 200
    data_other = res_other.json()
    assert len(data_other) == 1
    assert data_other[0]["external_comment_id"] == "comm_other_tenant_1"

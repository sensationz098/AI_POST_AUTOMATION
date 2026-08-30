import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.user import User
from app.models.social_account import SocialAccount
from app.models.social_comment import SocialComment
from app.models.social_comment_reply import SocialCommentReply
from app.core.security_encryption import encrypt_token
from app.services.meta_service import meta_service, MetaPublishException

client = TestClient(app)

@pytest.fixture
def test_user(db_session: Session):
    email = f"replyuser_{datetime.now(timezone.utc).timestamp()}@socialai.com"
    user = User(
        email=email,
        hashed_password="HashedPassword123!",
        is_active=True,
        full_name="Reply Test User"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def auth_headers(test_user: User):
    from app.core.security import create_access_token
    token = create_access_token(subject=str(test_user.id), role=test_user.role or "user")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_user(db_session: Session):
    email = f"otheruser_{datetime.now(timezone.utc).timestamp()}@socialai.com"
    user = User(
        email=email,
        hashed_password="HashedPassword123!",
        is_active=True,
        full_name="Other User"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def fb_account(db_session: Session, test_user: User):
    acc = SocialAccount(
        user_id=test_user.id,
        platform="facebook",
        account_id="fb_page_1001",
        account_name="Test FB Page",
        access_token=encrypt_token("EAANNCr_test_fb_page_token"),
        status="CONNECTED"
    )
    db_session.add(acc)
    db_session.commit()
    db_session.refresh(acc)
    return acc

@pytest.fixture
def ig_account(db_session: Session, test_user: User):
    acc = SocialAccount(
        user_id=test_user.id,
        platform="instagram",
        account_id="ig_account_2002",
        account_name="@test_ig_business",
        access_token=encrypt_token("EAANNCr_test_ig_page_token"),
        status="CONNECTED"
    )
    db_session.add(acc)
    db_session.commit()
    db_session.refresh(acc)
    return acc

@pytest.fixture
def fb_comment(db_session: Session, test_user: User, fb_account: SocialAccount):
    comment = SocialComment(
        user_id=test_user.id,
        social_account_id=fb_account.id,
        platform="facebook",
        external_comment_id="fb_comment_999",
        external_post_id="fb_post_888",
        comment_text="Great post on Facebook!",
        commenter_name="Facebook Fan",
        webhook_object="page",
        processing_status="RECEIVED"
    )
    db_session.add(comment)
    db_session.commit()
    db_session.refresh(comment)
    return comment

@pytest.fixture
def ig_comment(db_session: Session, test_user: User, ig_account: SocialAccount):
    comment = SocialComment(
        user_id=test_user.id,
        social_account_id=ig_account.id,
        platform="instagram",
        external_comment_id="ig_comment_777",
        external_post_id="ig_media_666",
        comment_text="Love this Reel!",
        commenter_name="InstaFollower",
        webhook_object="instagram",
        processing_status="RECEIVED"
    )
    db_session.add(comment)
    db_session.commit()
    db_session.refresh(comment)
    return comment


def test_user_can_reply_to_facebook_comment(client: TestClient, auth_headers: dict, fb_comment: SocialComment, db_session: Session):
    """Test 1: Authenticated user can reply to their own Facebook comment."""
    with patch.object(meta_service, "reply_to_facebook_comment", return_value={"id": "fb_reply_12345"}) as mock_reply:
        res = client.post(
            f"/api/v1/social-comments/{fb_comment.id}/reply",
            headers=auth_headers,
            json={"message": "Thank you for commenting!"}
        )

        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["platform"] == "facebook"
        assert data["external_reply_id"] == "fb_reply_12345"
        mock_reply.assert_called_once_with(
            comment_id="fb_comment_999",
            access_token="EAANNCr_test_fb_page_token",
            message="Thank you for commenting!"
        )

    # Verify audit persistence
    db_session.refresh(fb_comment)
    assert len(fb_comment.replies) == 1
    assert fb_comment.replies[0].message == "Thank you for commenting!"
    assert fb_comment.replies[0].external_reply_id == "fb_reply_12345"
    assert fb_comment.replies[0].status == "SUCCESS"


def test_user_can_reply_to_instagram_comment(client: TestClient, auth_headers: dict, ig_comment: SocialComment, db_session: Session):
    """Test 2: Authenticated user can reply to their own Instagram comment."""
    with patch.object(meta_service, "reply_to_instagram_comment", return_value={"id": "ig_reply_67890"}) as mock_reply:
        res = client.post(
            f"/api/v1/social-comments/{ig_comment.id}/reply",
            headers=auth_headers,
            json={"message": "Thanks for following us!"}
        )

        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["platform"] == "instagram"
        assert data["external_reply_id"] == "ig_reply_67890"
        mock_reply.assert_called_once_with(
            comment_id="ig_comment_777",
            access_token="EAANNCr_test_ig_page_token",
            message="Thanks for following us!"
        )

    # Verify audit persistence
    db_session.refresh(ig_comment)
    assert len(ig_comment.replies) == 1
    assert ig_comment.replies[0].message == "Thanks for following us!"
    assert ig_comment.replies[0].external_reply_id == "ig_reply_67890"
    assert ig_comment.replies[0].status == "SUCCESS"


def test_user_cannot_reply_to_another_users_comment(client: TestClient, db_session: Session, other_user: User, fb_comment: SocialComment):

    """Test 3: User cannot reply to another user's comment."""
    from app.core.security import create_access_token
    other_headers = {"Authorization": f"Bearer {create_access_token(subject=str(other_user.id), role=other_user.role or 'user')}"}


    res = client.post(
        f"/api/v1/social-comments/{fb_comment.id}/reply",
        headers=other_headers,
        json={"message": "Sneaky reply attempt!"}
    )

    assert res.status_code in (404, 403)
    assert "access denied" in res.json()["detail"].lower() or "not found" in res.json()["detail"].lower()


def test_backend_never_accepts_access_token_from_frontend(client: TestClient, auth_headers: dict, fb_comment: SocialComment):
    """Test 4: Backend ignores access_token or extra fields sent by frontend."""
    with patch.object(meta_service, "reply_to_facebook_comment", return_value={"id": "fb_reply_safe"}) as mock_reply:
        res = client.post(
            f"/api/v1/social-comments/{fb_comment.id}/reply",
            headers=auth_headers,
            json={
                "message": "Valid message",
                "access_token": "MALICIOUS_FRONTEND_TOKEN",
                "page_id": "99999",
                "user_id": 99
            }
        )

        assert res.status_code == 200
        # Check that server-side decrypted token was used, NOT the frontend token
        mock_reply.assert_called_once_with(
            comment_id="fb_comment_999",
            access_token="EAANNCr_test_fb_page_token",
            message="Valid message"
        )


def test_access_tokens_never_appear_in_api_responses(client: TestClient, auth_headers: dict, fb_comment: SocialComment):
    """Test 5: Access tokens never appear in API responses."""
    with patch.object(meta_service, "reply_to_facebook_comment", return_value={"id": "fb_reply_safe"}):
        res = client.post(
            f"/api/v1/social-comments/{fb_comment.id}/reply",
            headers=auth_headers,
            json={"message": "Testing safe response"}
        )

        res_str = res.text
        assert "EAANNCr_test_fb_page_token" not in res_str
        assert "access_token" not in res.json()


def test_empty_and_whitespace_replies_are_rejected(client: TestClient, auth_headers: dict, fb_comment: SocialComment):
    """Test 7 & 8: Empty and whitespace-only replies are rejected without contacting Meta."""
    with patch.object(meta_service, "reply_to_facebook_comment") as mock_reply:
        # Empty message
        res1 = client.post(
            f"/api/v1/social-comments/{fb_comment.id}/reply",
            headers=auth_headers,
            json={"message": ""}
        )
        assert res1.status_code == 400
        assert "empty" in res1.json()["detail"].lower()

        # Whitespace-only message
        res2 = client.post(
            f"/api/v1/social-comments/{fb_comment.id}/reply",
            headers=auth_headers,
            json={"message": "   \n\t  "}
        )
        assert res2.status_code == 400
        assert "whitespace" in res2.json()["detail"].lower()

        mock_reply.assert_not_called()


def test_overly_long_replies_are_rejected(client: TestClient, auth_headers: dict, fb_comment: SocialComment):
    """Test 9: Overly long replies (>2000 chars) are rejected without contacting Meta."""
    long_msg = "A" * 2001
    with patch.object(meta_service, "reply_to_facebook_comment") as mock_reply:
        res = client.post(
            f"/api/v1/social-comments/{fb_comment.id}/reply",
            headers=auth_headers,
            json={"message": long_msg}
        )

        assert res.status_code == 400
        assert "exceeds maximum" in res.json()["detail"].lower()
        mock_reply.assert_not_called()


def test_facebook_and_instagram_use_correct_reply_api_operations():
    """Test 10 & 11: Facebook uses POST /{comment_id}/comments, Instagram uses POST /{comment_id}/replies."""
    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"id": "reply_123"}

        # FB reply
        meta_service.reply_to_facebook_comment(comment_id="fb_c_123", access_token="token_fb", message="hello fb")
        fb_call_url = mock_post.call_args_list[-1][0][0]
        assert "/fb_c_123/comments" in fb_call_url

        # IG reply
        meta_service.reply_to_instagram_comment(comment_id="ig_c_456", access_token="token_ig", message="hello ig")
        ig_call_url = mock_post.call_args_list[-1][0][0]
        assert "/ig_c_456/replies" in ig_call_url


def test_meta_api_failure_handled_safely(client: TestClient, auth_headers: dict, fb_comment: SocialComment, db_session: Session):
    """Test 12: Meta API failure is handled safely returning status: failed."""
    with patch.object(meta_service, "reply_to_facebook_comment", side_effect=MetaPublishException("Graph API Error 100")):
        res = client.post(
            f"/api/v1/social-comments/{fb_comment.id}/reply",
            headers=auth_headers,
            json={"message": "Will fail"}
        )

        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "failed"
        assert data["message"] == "Unable to publish reply. Please try again."

    # Audit should log FAILED status
    db_session.refresh(fb_comment)
    assert len(fb_comment.replies) == 1
    assert fb_comment.replies[0].status == "FAILED"


def test_missing_or_disconnected_social_account_handled_safely(client: TestClient, auth_headers: dict, fb_comment: SocialComment, fb_account: SocialAccount, db_session: Session):
    """Test 13: Disconnected account blocks reply."""
    fb_account.status = "TOKEN_EXPIRED"
    db_session.commit()

    res = client.post(
        f"/api/v1/social-comments/{fb_comment.id}/reply",
        headers=auth_headers,
        json={"message": "Try to reply"}
    )

    assert res.status_code == 400
    assert "reconnect your account" in res.json()["detail"].lower()


def test_multiple_replies_represented_safely(client: TestClient, auth_headers: dict, fb_comment: SocialComment, db_session: Session):
    """Test 16: Multiple replies can be added and retrieved for a single comment."""
    with patch.object(meta_service, "reply_to_facebook_comment", side_effect=[{"id": "reply_1"}, {"id": "reply_2"}]):
        res1 = client.post(
            f"/api/v1/social-comments/{fb_comment.id}/reply",
            headers=auth_headers,
            json={"message": "First reply"}
        )
        assert res1.json()["external_reply_id"] == "reply_1"

        # Wait past 10s window simulation or send different message
        res2 = client.post(
            f"/api/v1/social-comments/{fb_comment.id}/reply",
            headers=auth_headers,
            json={"message": "Second distinct reply"}
        )
        assert res2.json()["external_reply_id"] == "reply_2"

    db_session.refresh(fb_comment)
    assert len(fb_comment.replies) == 2


    # GET /social-comments/ should include both replies
    get_res = client.get("/api/v1/social-comments/", headers=auth_headers)
    c_list = get_res.json()
    target = next((c for c in c_list if c["id"] == fb_comment.id), None)
    assert target is not None
    assert len(target["replies"]) == 2
    assert target["replies"][0]["message"] == "First reply"
    assert target["replies"][1]["message"] == "Second distinct reply"


def test_duplicate_submission_protection(client: TestClient, auth_headers: dict, fb_comment: SocialComment):
    """Test 17: Rapid duplicate submissions are detected and prevented by backend."""
    with patch.object(meta_service, "reply_to_facebook_comment", return_value={"id": "fb_reply_dup"}) as mock_reply:
        # First request
        res1 = client.post(
            f"/api/v1/social-comments/{fb_comment.id}/reply",
            headers=auth_headers,
            json={"message": "Identical message"}
        )
        assert res1.json()["status"] == "success"
        assert mock_reply.call_count == 1

        # Immediate duplicate request with exact same message
        res2 = client.post(
            f"/api/v1/social-comments/{fb_comment.id}/reply",
            headers=auth_headers,
            json={"message": "Identical message"}
        )
        assert res2.json()["status"] == "success"
        assert "Duplicate reply detected" in res2.json()["message"]
        # Meta API was NOT called a second time
        assert mock_reply.call_count == 1

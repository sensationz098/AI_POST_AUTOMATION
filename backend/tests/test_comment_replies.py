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


def test_comment_with_matching_facebook_post(client: TestClient, auth_headers: dict, test_user: User, fb_comment: SocialComment, db_session: Session):
    from app.models.post import Post
    from app.models.brand import BrandProfile

    brand = BrandProfile(name="Test Brand", user_id=test_user.id, brand_colors=[], tone_of_voice="Friendly", cta_style="Direct")
    db_session.add(brand)
    db_session.commit()

    post = Post(
        brand_id=brand.id,
        user_id=test_user.id,
        title="Summer Sale FB Post",
        caption="Check out our FB sale!",
        image_url="https://example.com/fb.jpg",
        media_type="image",
        thumbnail_url="https://example.com/fb_thumb.jpg",
        fb_post_id="fb_post_888",
        platforms=["facebook"]
    )
    db_session.add(post)
    db_session.commit()

    res = client.get("/api/v1/social-comments/", headers=auth_headers)
    assert res.status_code == 200
    comments = res.json()
    target = next((c for c in comments if c["id"] == fb_comment.id), None)
    assert target is not None
    assert target["post"] is not None
    assert target["post"]["id"] == post.id
    assert target["post"]["title"] == "Summer Sale FB Post"
    assert target["post"]["caption"] == "Check out our FB sale!"
    assert target["post"]["platform"] == "facebook"


def test_comment_with_matching_instagram_post(client: TestClient, auth_headers: dict, test_user: User, ig_comment: SocialComment, db_session: Session):
    from app.models.post import Post
    from app.models.brand import BrandProfile

    brand = BrandProfile(name="Test Brand IG", user_id=test_user.id, brand_colors=[], tone_of_voice="Friendly", cta_style="Direct")
    db_session.add(brand)
    db_session.commit()

    post = Post(
        brand_id=brand.id,
        user_id=test_user.id,
        title="Summer Reel IG",
        caption="Watch our new Reel!",
        image_url="https://example.com/ig.jpg",
        media_type="video",
        thumbnail_url="https://example.com/ig_thumb.jpg",
        ig_media_id="ig_media_666",
        platforms=["instagram"]
    )
    db_session.add(post)
    db_session.commit()

    res = client.get("/api/v1/social-comments/", headers=auth_headers)
    assert res.status_code == 200
    comments = res.json()
    target = next((c for c in comments if c["id"] == ig_comment.id), None)
    assert target is not None
    assert target["post"] is not None
    assert target["post"]["id"] == post.id
    assert target["post"]["title"] == "Summer Reel IG"
    assert target["post"]["platform"] == "instagram"


def test_comment_with_no_matching_post(client: TestClient, auth_headers: dict, fb_comment: SocialComment):
    res = client.get("/api/v1/social-comments/", headers=auth_headers)
    assert res.status_code == 200
    comments = res.json()
    target = next((c for c in comments if c["id"] == fb_comment.id), None)
    assert target is not None
    assert target["post"] is None


def test_user_cannot_receive_another_users_post_context(client: TestClient, auth_headers: dict, test_user: User, other_user: User, fb_comment: SocialComment, db_session: Session):
    from app.models.post import Post
    from app.models.brand import BrandProfile

    other_brand = BrandProfile(name="Other Brand", user_id=other_user.id, brand_colors=[], tone_of_voice="Friendly", cta_style="Direct")
    db_session.add(other_brand)
    db_session.commit()

    other_post = Post(
        brand_id=other_brand.id,
        user_id=other_user.id,
        title="Secret Other User Post",
        caption="Do not expose this",
        fb_post_id="fb_post_888",
        platforms=["facebook"]
    )
    db_session.add(other_post)
    db_session.commit()

    res = client.get("/api/v1/social-comments/", headers=auth_headers)
    assert res.status_code == 200
    comments = res.json()
    target = next((c for c in comments if c["id"] == fb_comment.id), None)
    assert target is not None
    assert target["post"] is None


def test_owner_reply_webhook_duplication_prevented(client: TestClient, auth_headers: dict, test_user: User, fb_comment: SocialComment, db_session: Session):
    """Verify owner reply webhook echo does not create duplicate SocialComment."""
    # 1. Owner replies via API
    with patch.object(meta_service, "reply_to_facebook_comment", return_value={"id": "fb_reply_echo_123"}):
        res = client.post(
            f"/api/v1/social-comments/{fb_comment.id}/reply",
            headers=auth_headers,
            json={"message": "Official owner reply"}
        )
        assert res.status_code == 200
        assert res.json()["external_reply_id"] == "fb_reply_echo_123"

    # 2. Meta webhook sends event for the exact same reply ID
    from app.services.comment_ingestion_service import meta_comment_ingestion_service
    webhook_payload = {
        "object": "page",
        "entry": [{
            "id": "fb_page_123", # matches account
            "changes": [{
                "field": "feed",
                "value": {
                    "item": "comment",
                    "comment_id": "fb_reply_echo_123",
                    "message": "Official owner reply"
                }
            }]
        }]
    }

    # Ensure account exists for account matching in webhook
    from app.repositories.social_account_repository import social_account_repo
    social_account_repo.create_or_update(
        db=db_session, user_id=test_user.id, platform="facebook", account_id="fb_page_123", account_name="Test Page", access_token="tok_123"
    )

    ingested = meta_comment_ingestion_service.parse_and_ingest_payload(db=db_session, payload=webhook_payload)
    # The ingestion service MUST skip creating a SocialComment for this owner reply echo
    assert len(ingested) == 0

    # Verify DB has no SocialComment with external_comment_id = "fb_reply_echo_123"
    duplicate_comment = db_session.query(SocialComment).filter_by(external_comment_id="fb_reply_echo_123").first()
    assert duplicate_comment is None


def test_existing_duplicate_social_comment_excluded_from_api(client: TestClient, auth_headers: dict, test_user: User, fb_comment: SocialComment, db_session: Session):
    """Verify pre-existing duplicate SocialComment with external_comment_id matching SocialCommentReply is suppressed from GET API."""
    from app.models.social_comment_reply import SocialCommentReply

    # Create audit reply
    reply = SocialCommentReply(
        comment_id=fb_comment.id,
        user_id=test_user.id,
        platform="facebook",
        message="Owner reply text",
        external_reply_id="dup_external_123",
        status="SUCCESS"
    )
    db_session.add(reply)

    # Create pre-existing duplicate SocialComment representing the same webhook echo
    dup_comment = SocialComment(
        user_id=test_user.id,
        social_account_id=fb_comment.social_account_id,
        platform="facebook",
        external_comment_id="dup_external_123",
        comment_text="Owner reply text",
        webhook_object="page",
        created_at=fb_comment.created_at
    )
    db_session.add(dup_comment)
    db_session.commit()

    res = client.get("/api/v1/social-comments/", headers=auth_headers)
    assert res.status_code == 200
    comments = res.json()

    # The top-level comments response must contain fb_comment but NOT dup_comment
    returned_ids = [c["external_comment_id"] for c in comments]
    assert fb_comment.external_comment_id in returned_ids
    assert "dup_external_123" not in returned_ids


def test_user_reply_id_does_not_suppress_other_user_comment(client: TestClient, auth_headers: dict, test_user: User, other_user: User, fb_comment: SocialComment, db_session: Session):
    """Verify User A's reply ID does not suppress User B's comment with the same external_comment_id."""
    from app.models.social_comment_reply import SocialCommentReply
    from app.models.social_account import SocialAccount

    # User B has an owner reply with ID "shared_reply_id"
    other_reply = SocialCommentReply(
        comment_id=9999,
        user_id=other_user.id,
        platform="facebook",
        message="Other user reply",
        external_reply_id="shared_reply_id",
        status="SUCCESS"
    )
    db_session.add(other_reply)

    # User A (test_user) has a genuine customer comment with external_comment_id = "shared_reply_id"
    user_a_acc = db_session.query(SocialAccount).filter_by(user_id=test_user.id).first()
    user_a_comment = SocialComment(
        user_id=test_user.id,
        social_account_id=user_a_acc.id,
        platform="facebook",
        external_comment_id="shared_reply_id",
        comment_text="Customer comment for User A",
        webhook_object="page"
    )
    db_session.add(user_a_comment)
    db_session.commit()

    # Query GET API as test_user (User A)
    res = client.get("/api/v1/social-comments/", headers=auth_headers)
    assert res.status_code == 200
    comments = res.json()

    # User A MUST see their comment even though User B has a reply with the same external_reply_id
    comment_ids = [c["external_comment_id"] for c in comments]
    assert "shared_reply_id" in comment_ids


def test_meta_post_fallback_success_and_failure(client: TestClient, auth_headers: dict, test_user: User, db_session: Session):
    """Test Stage 2 Meta Graph API fallback for unresolved post IDs and graceful failure handling."""
    from app.models.social_account import SocialAccount
    from app.core.security_encryption import encrypt_token

    # Setup connected Instagram account
    ig_account = SocialAccount(
        user_id=test_user.id,
        platform="instagram",
        account_id="ig_acc_meta_test",
        account_name="Meta Test IG",
        access_token=encrypt_token("mock_access_token_123"),
        status="CONNECTED"
    )
    db_session.add(ig_account)
    db_session.commit()

    # Create comment referencing external_post_id "unresolved_ig_post_1" not in local Post table
    c1 = SocialComment(
        user_id=test_user.id,
        social_account_id=ig_account.id,
        platform="instagram",
        external_comment_id="c_meta_1",
        external_post_id="unresolved_ig_post_1",
        comment_text="Comment on unresolved IG post",
        webhook_object="instagram"
    )
    db_session.add(c1)
    db_session.commit()

    # Mock meta_service.fetch_instagram_media_info to simulate successful Meta API resolution
    mock_meta_response = {
        "id": "unresolved_ig_post_1",
        "caption": "Meta Fallback Post Caption",
        "media_type": "IMAGE",
        "media_url": "https://example.com/meta_img.jpg",
        "thumbnail_url": "https://example.com/meta_thumb.jpg"
    }

    with patch.object(meta_service, "fetch_instagram_media_info", return_value=mock_meta_response) as mock_fetch:
        res = client.get("/api/v1/social-comments/", headers=auth_headers)
        assert res.status_code == 200
        comments = res.json()
        target = next((c for c in comments if c["external_comment_id"] == "c_meta_1"), None)
        assert target is not None
        assert target["post"] is not None
        assert target["post"]["caption"] == "Meta Fallback Post Caption"
        assert target["post"]["source"] == "meta"
        assert mock_fetch.called

    # Test Meta Fallback Failure returns post: null without breaking comments API (returns HTTP 200)
    with patch.object(meta_service, "fetch_instagram_media_info", side_effect=Exception("Meta API Down")):
        res = client.get("/api/v1/social-comments/", headers=auth_headers)
        assert res.status_code == 200
        comments = res.json()
        target = next((c for c in comments if c["external_comment_id"] == "c_meta_1"), None)
        assert target is not None
        assert target["post"] is None


def test_meta_fallback_request_caching(client: TestClient, auth_headers: dict, test_user: User, db_session: Session):
    """Verify multiple comments on the same unresolved post only trigger ONE Meta API call."""
    from app.models.social_account import SocialAccount
    from app.core.security_encryption import encrypt_token

    ig_account = SocialAccount(
        user_id=test_user.id,
        platform="instagram",
        account_id="ig_acc_cache_test",
        account_name="Cache Test IG",
        access_token=encrypt_token("mock_access_token_123"),
        status="CONNECTED"
    )
    db_session.add(ig_account)
    db_session.commit()

    # 3 comments referencing the same external_post_id "shared_unresolved_post_999"
    for i in range(1, 4):
        db_session.add(SocialComment(
            user_id=test_user.id,
            social_account_id=ig_account.id,
            platform="instagram",
            external_comment_id=f"c_shared_{i}",
            external_post_id="shared_unresolved_post_999",
            comment_text=f"Shared post comment {i}",
            webhook_object="instagram"
        ))
    db_session.commit()

    mock_meta_response = {
        "id": "shared_unresolved_post_999",
        "caption": "Shared Post Caption",
        "media_type": "IMAGE"
    }

    with patch.object(meta_service, "fetch_instagram_media_info", return_value=mock_meta_response) as mock_fetch:
        res = client.get("/api/v1/social-comments/", headers=auth_headers)
        assert res.status_code == 200
        # Meta API fetch method MUST be called exactly once for all 3 comments!
        assert mock_fetch.call_count == 1


def test_pagination_with_owner_reply_exclusion(client: TestClient, auth_headers: dict, test_user: User, fb_comment: SocialComment, db_session: Session):
    """Verify excluding owner reply echoes does not break skip, limit, and pagination ordering."""
    from app.models.social_comment_reply import SocialCommentReply
    from app.models.social_account import SocialAccount

    acc = db_session.query(SocialAccount).filter_by(user_id=test_user.id).first()

    # Create 5 SocialComments, where comments 2 and 4 are owner reply echoes
    for i in range(1, 6):
        c_id = f"pag_c_{i}"
        db_session.add(SocialComment(
            user_id=test_user.id,
            social_account_id=acc.id,
            platform="facebook",
            external_comment_id=c_id,
            comment_text=f"Comment {i}",
            webhook_object="page"
        ))
    
    # Mark pag_c_2 and pag_c_4 as owner replies in SocialCommentReply
    db_session.add(SocialCommentReply(comment_id=1, user_id=test_user.id, platform="facebook", message="r2", external_reply_id="pag_c_2", status="SUCCESS"))
    db_session.add(SocialCommentReply(comment_id=1, user_id=test_user.id, platform="facebook", message="r4", external_reply_id="pag_c_4", status="SUCCESS"))
    db_session.commit()

    # Request skip=0, limit=3
    res = client.get("/api/v1/social-comments/?skip=0&limit=3", headers=auth_headers)
    assert res.status_code == 200
    comments = res.json()

    # Should return exactly 3 top-level comments (excluding pag_c_2 and pag_c_4)
    returned_ids = [c["external_comment_id"] for c in comments]
    assert len(returned_ids) == 3
    assert "pag_c_2" not in returned_ids
    assert "pag_c_4" not in returned_ids


# ==============================================================================
# COMMENT DELETION TESTS
# ==============================================================================

def test_delete_facebook_comment_success(client: TestClient, auth_headers: dict, test_user: User, fb_comment: SocialComment, db_session: Session):
    """Verify owner can delete Facebook comment: calls Meta API, marks DB deleted, and excludes from list API."""
    with patch.object(meta_service, "delete_facebook_comment", return_value={"success": True, "status": "deleted"}) as mock_meta_del:
        res = client.delete(f"/api/v1/social-comments/{fb_comment.id}", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["status"] == "success"

        # Verify Meta API call
        mock_meta_del.assert_called_once_with(
            external_comment_id=fb_comment.external_comment_id,
            access_token="EAANNCr_test_fb_page_token"
        )

    # Verify DB state updated
    db_session.refresh(fb_comment)
    assert fb_comment.is_deleted is True
    assert fb_comment.processing_status == "DELETED"
    assert fb_comment.deleted_at is not None

    # Verify excluded from GET comments API
    get_res = client.get("/api/v1/social-comments/", headers=auth_headers)
    assert get_res.status_code == 200
    ids = [c["id"] for c in get_res.json()]
    assert fb_comment.id not in ids


def test_delete_instagram_comment_success(client: TestClient, auth_headers: dict, test_user: User, ig_comment: SocialComment, db_session: Session):
    """Verify owner can delete Instagram comment: calls Meta API, marks DB deleted, and excludes from list API."""
    with patch.object(meta_service, "delete_instagram_comment", return_value={"success": True, "status": "deleted"}) as mock_meta_del:
        res = client.delete(f"/api/v1/social-comments/{ig_comment.id}", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["status"] == "success"

        # Verify Meta API call
        mock_meta_del.assert_called_once_with(
            external_comment_id=ig_comment.external_comment_id,
            access_token="EAANNCr_test_ig_page_token"
        )

    # Verify DB state updated
    db_session.refresh(ig_comment)
    assert ig_comment.is_deleted is True

    # Verify excluded from GET comments API
    get_res = client.get("/api/v1/social-comments/", headers=auth_headers)
    assert get_res.status_code == 200
    ids = [c["id"] for c in get_res.json()]
    assert ig_comment.id not in ids


def test_delete_comment_meta_failure_retains_local_record(client: TestClient, auth_headers: dict, test_user: User, fb_comment: SocialComment, db_session: Session):
    """Verify Meta API failure prevents local DB deletion mark and comment remains active in list API."""
    with patch.object(meta_service, "delete_facebook_comment", side_effect=Exception("Meta API permissions error")):
        res = client.delete(f"/api/v1/social-comments/{fb_comment.id}", headers=auth_headers)
        assert res.status_code == 400
        assert "Unable to delete this comment from Facebook" in res.json()["detail"]

    # Verify DB record remains active
    db_session.refresh(fb_comment)
    assert fb_comment.is_deleted is False

    # Verify comment still visible in GET comments API
    get_res = client.get("/api/v1/social-comments/", headers=auth_headers)
    assert get_res.status_code == 200
    ids = [c["id"] for c in get_res.json()]
    assert fb_comment.id in ids


def test_user_cannot_delete_another_users_comment(client: TestClient, other_user: User, fb_comment: SocialComment, db_session: Session):
    """Verify User B cannot delete User A's comment (returns 404, Meta API never called)."""
    from app.core.security import create_access_token
    other_headers = {"Authorization": f"Bearer {create_access_token(subject=str(other_user.id), role=other_user.role or 'user')}"}
    with patch.object(meta_service, "delete_facebook_comment") as mock_meta_del:
        res = client.delete(f"/api/v1/social-comments/{fb_comment.id}", headers=other_headers)
        assert res.status_code == 404
        assert not mock_meta_del.called

    # DB comment remains untouched
    db_session.refresh(fb_comment)
    assert fb_comment.is_deleted is False


def test_already_deleted_comment_idempotent(client: TestClient, auth_headers: dict, fb_comment: SocialComment, db_session: Session):
    """Verify repeated delete request on an already deleted comment is idempotent."""
    fb_comment.is_deleted = True
    fb_comment.processing_status = "DELETED"
    db_session.commit()

    with patch.object(meta_service, "delete_facebook_comment") as mock_meta_del:
        res = client.delete(f"/api/v1/social-comments/{fb_comment.id}", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["message"] == "Comment is already deleted."
        assert not mock_meta_del.called


def test_webhook_resurrection_protection(db_session: Session, fb_comment: SocialComment):
    """Verify a comment marked is_deleted=True is not resurrected when a subsequent webhook arrives."""
    from app.services.comment_ingestion_service import meta_comment_ingestion_service

    # Mark comment as deleted
    fb_comment.is_deleted = True
    db_session.commit()

    # Simulate webhook entry for the same external_comment_id
    payload = {
        "object": "page",
        "entry": [
            {
                "id": "1001",
                "time": 1700000000,
                "changes": [
                    {
                        "field": "feed",
                        "value": {
                            "item": "comment",
                            "verb": "add",
                            "id": fb_comment.external_comment_id,
                            "post_id": "post_100",
                            "message": "Resurrection attempt"
                        }
                    }
                ]
            }
        ]
    }

    ingested = meta_comment_ingestion_service.parse_and_ingest_payload(db_session, payload)
    assert len(ingested) == 0

    # Ensure comment in DB remains deleted and text is unedited
    db_session.refresh(fb_comment)
    assert fb_comment.is_deleted is True
    assert fb_comment.comment_text != "Resurrection attempt"


def test_pagination_with_deleted_comments(client: TestClient, auth_headers: dict, test_user: User, fb_comment: SocialComment, db_session: Session):
    """Verify soft-deleted comments do not break pagination limits or offset ordering."""
    from app.models.social_account import SocialAccount

    acc = db_session.query(SocialAccount).filter_by(user_id=test_user.id).first()

    # Create 5 comments, mark 2 as deleted
    created_comments = []
    for i in range(1, 6):
        c = SocialComment(
            user_id=test_user.id,
            social_account_id=acc.id,
            platform="facebook",
            external_comment_id=f"del_pag_c_{i}",
            comment_text=f"Pag comment {i}",
            webhook_object="page",
            is_deleted=(i in (2, 4))
        )
        db_session.add(c)
        created_comments.append(c)
    db_session.commit()

    # Query skip=0, limit=3
    res = client.get("/api/v1/social-comments/?skip=0&limit=3", headers=auth_headers)
    assert res.status_code == 200
    comments = res.json()

    returned_ids = [c["external_comment_id"] for c in comments]
    assert len(returned_ids) == 3
    assert "del_pag_c_2" not in returned_ids
    assert "del_pag_c_4" not in returned_ids


def test_social_account_filtering_all_accounts(client: TestClient, auth_headers: dict, test_user: User, fb_comment: SocialComment, ig_comment: SocialComment):
    """Verify omitting social_account_id returns all comments belonging to current user across accounts."""
    res = client.get("/api/v1/social-comments/", headers=auth_headers)
    assert res.status_code == 200
    ids = [c["id"] for c in res.json()]
    assert fb_comment.id in ids
    assert ig_comment.id in ids


def test_social_account_filtering_specific_account(client: TestClient, auth_headers: dict, test_user: User, fb_comment: SocialComment, ig_comment: SocialComment):
    """Verify passing valid social_account_id filters comments to that specific account only."""
    res = client.get(f"/api/v1/social-comments/?social_account_id={fb_comment.social_account_id}", headers=auth_headers)
    assert res.status_code == 200
    comments = res.json()
    assert all(c["social_account_id"] == fb_comment.social_account_id for c in comments)
    ids = [c["id"] for c in comments]
    assert fb_comment.id in ids
    assert ig_comment.id not in ids


def test_social_account_filtering_other_user_account_rejected(client: TestClient, auth_headers: dict, db_session: Session):
    """Verify passing a social_account_id belonging to another user is rejected with safe 404."""
    other_user = User(email="other_acc_owner@example.com", hashed_password="pw", full_name="Other User")
    db_session.add(other_user)
    db_session.commit()
    db_session.refresh(other_user)

    other_acc = SocialAccount(
        user_id=other_user.id,
        platform="facebook",
        account_id="other_fb_page_123",
        account_name="Other Page",
        access_token="enc_tok",
        status="CONNECTED"
    )
    db_session.add(other_acc)
    db_session.commit()
    db_session.refresh(other_acc)

    res = client.get(f"/api/v1/social-comments/?social_account_id={other_acc.id}", headers=auth_headers)
    assert res.status_code == 404
    assert res.json()["detail"] == "Social account not found"


def test_social_account_filtering_combined_with_platform_filter(client: TestClient, auth_headers: dict, test_user: User, fb_comment: SocialComment, ig_comment: SocialComment):
    """Verify combining social_account_id with platform query param works correctly."""
    # FB account + platform=facebook -> returns FB comment
    res1 = client.get(f"/api/v1/social-comments/?social_account_id={fb_comment.social_account_id}&platform=facebook", headers=auth_headers)
    assert res1.status_code == 200
    ids1 = [c["id"] for c in res1.json()]
    assert fb_comment.id in ids1

    # FB account + platform=instagram -> returns 0 comments safely
    res2 = client.get(f"/api/v1/social-comments/?social_account_id={fb_comment.social_account_id}&platform=instagram", headers=auth_headers)
    assert res2.status_code == 200
    assert len(res2.json()) == 0


def test_social_account_filtering_excludes_deleted_and_reply_echoes(client: TestClient, auth_headers: dict, test_user: User, fb_comment: SocialComment, db_session: Session):
    """Verify social_account_id filtering preserves soft-delete exclusion and owner reply echo suppression."""
    fb_comment.is_deleted = True
    db_session.commit()

    res = client.get(f"/api/v1/social-comments/?social_account_id={fb_comment.social_account_id}", headers=auth_headers)
    assert res.status_code == 200
    ids = [c["id"] for c in res.json()]
    assert fb_comment.id not in ids




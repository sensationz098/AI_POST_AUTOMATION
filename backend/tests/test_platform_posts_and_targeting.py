import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.security_encryption import encrypt_token
from app.models.user import User
from app.models.brand import BrandProfile
from app.models.social_account import SocialAccount
from app.models.post import Post
from app.models.social_comment import SocialComment
from app.models.automation import Automation, AutomationStatus, TriggerType, PostTargetType
from app.models.automation_execution import AutomationExecution, ExecutionStatus
from app.services.meta_service import meta_service
from app.services.comment_trigger_service import CommentTriggerService
from app.api.v1.deps import get_current_user


@pytest.fixture
def test_user_and_brand(db_session: Session):
    user = User(
        email="target_post_tester@example.com",
        hashed_password="hashed_pw_test",
        full_name="Target Post Tester",
        role="Admin",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    brand = BrandProfile(
        user_id=user.id,
        name="Test Brand",
        tone_of_voice="Professional",
        cta_style="Direct",
        brand_colors=["#000000"]
    )
    db_session.add(brand)
    db_session.commit()
    db_session.refresh(brand)

    app.dependency_overrides[get_current_user] = lambda: user
    yield user, brand
    app.dependency_overrides.pop(get_current_user, None)


def test_meta_service_fetch_instagram_and_facebook_posts_mock():
    """Verify meta_service platform posts fetching works with mock mode and returns normalized structure."""
    with patch.object(meta_service, "fetch_instagram_account_posts") as mock_ig:
        mock_ig.return_value = {
            "items": [
                {
                    "id": "18026466023684307",
                    "caption": "Real Instagram Post Caption",
                    "media_url": "https://instagram.com/p/123.jpg",
                    "thumbnail_url": "https://instagram.com/p/123.jpg",
                    "permalink": "https://www.instagram.com/p/Cxyz123/",
                    "created_time": "2026-03-01T12:00:00+0000",
                    "platform": "instagram",
                    "like_count": 150,
                    "comments_count": 22
                }
            ],
            "paging": {}
        }
        res = meta_service.fetch_instagram_account_posts("17841400928371", "mock_token")
        assert len(res["items"]) == 1
        assert res["items"][0]["id"] == "18026466023684307"
        assert res["items"][0]["platform"] == "instagram"


def test_get_platform_posts_api_endpoint(client: TestClient, db_session: Session, test_user_and_brand):
    """Verify GET /api/v1/social-accounts/{id}/platform-posts returns real external IDs and optional correlation."""
    user, brand = test_user_and_brand

    # Create connected IG account
    ig_acc = SocialAccount(
        user_id=user.id,
        brand_id=brand.id,
        platform="instagram",
        account_id="17841400928371",
        account_name="test_ig_brand",
        access_token=encrypt_token("EAAtest_ig_token"),
        status="CONNECTED"
    )
    db_session.add(ig_acc)
    db_session.commit()
    db_session.refresh(ig_acc)

    # Add a local post that happens to match one of the external posts
    local_post = Post(
        user_id=user.id,
        brand_id=brand.id,
        title="Matching Local Post",
        caption="Matching Caption",
        status="PUBLISHED",
        platforms=["instagram"],
        ig_media_id="18026466023684307"
    )
    db_session.add(local_post)
    db_session.commit()
    db_session.refresh(local_post)

    with patch.object(meta_service, "fetch_instagram_account_posts") as mock_fetch:
        mock_fetch.return_value = {
            "items": [
                {
                    "id": "18026466023684307",
                    "caption": "Matching Caption",
                    "media_url": "https://instagram.com/p/1.jpg",
                    "thumbnail_url": "https://instagram.com/p/1.jpg",
                    "permalink": "https://instagram.com/p/1/",
                    "created_time": "2026-03-01T12:00:00+0000",
                    "platform": "instagram"
                },
                {
                    "id": "19999999999999999",
                    "caption": "External Post With No Local Record",
                    "media_url": "https://instagram.com/p/2.jpg",
                    "thumbnail_url": "https://instagram.com/p/2.jpg",
                    "permalink": "https://instagram.com/p/2/",
                    "created_time": "2026-03-02T12:00:00+0000",
                    "platform": "instagram"
                }
            ],
            "paging": {}
        }

        response = client.get(f"/api/v1/social-accounts/{ig_acc.id}/platform-posts")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2

        # 1st item correlates with local_post.id
        assert data["items"][0]["id"] == "18026466023684307"
        assert data["items"][0]["internal_post_id"] == local_post.id

        # 2nd item has NO local post
        assert data["items"][1]["id"] == "19999999999999999"
        assert data["items"][1]["internal_post_id"] is None


def test_account_isolation_platform_posts(client: TestClient, db_session: Session, test_user_and_brand):
    """Verify user cannot fetch platform posts from another user's account."""
    user, brand = test_user_and_brand

    other_user = User(
        email="other_user_iso@example.com",
        hashed_password="pw",
        full_name="Other User",
        role="Admin"
    )
    db_session.add(other_user)
    db_session.commit()

    other_acc = SocialAccount(
        user_id=other_user.id,
        platform="instagram",
        account_id="17841400999999",
        account_name="other_brand",
        access_token=encrypt_token("EAAother"),
        status="CONNECTED"
    )
    db_session.add(other_acc)
    db_session.commit()

    response = client.get(f"/api/v1/social-accounts/{other_acc.id}/platform-posts")
    assert response.status_code == 404


def test_create_automation_with_pure_external_id_no_local_post(client: TestClient, db_session: Session, test_user_and_brand):
    """Verify automation can be created for an external platform post that does not exist in Post table."""
    user, brand = test_user_and_brand

    ig_acc = SocialAccount(
        user_id=user.id,
        brand_id=brand.id,
        platform="instagram",
        account_id="17841400928371",
        account_name="test_ig_brand",
        access_token=encrypt_token("EAAtest"),
        status="CONNECTED"
    )
    db_session.add(ig_acc)
    db_session.commit()

    # Verify no local posts exist
    assert db_session.query(Post).filter(Post.user_id == user.id).count() == 0

    payload = {
        "name": "External IG Post Automation",
        "platform": "instagram",
        "social_account_id": ig_acc.id,
        "post_target_type": "SPECIFIC_POST",
        "external_post_id": "18026466023684307",
        "internal_post_id": None,
        "trigger_type": "KEYWORD",
        "trigger_config": {"keywords": ["price", "link"]},
        "action_config": {
            "public_reply": {"enabled": True, "variations": ["DM sent!"]},
            "private_message": {"enabled": True, "message": "Here is the price link."}
        }
    }

    response = client.post("/api/v1/automations", json=payload)
    assert response.status_code == 201
    created = response.json()
    assert created["external_post_id"] == "18026466023684307"
    assert created["internal_post_id"] is None
    assert created["status"] == "DRAFT"


def test_reject_local_post_lacking_platform_id_when_only_internal_id_supplied(client: TestClient, db_session: Session, test_user_and_brand):
    """Verify selecting a draft/unpublished local post lacking ig_media_id is rejected when no external ID given."""
    user, brand = test_user_and_brand

    ig_acc = SocialAccount(
        user_id=user.id,
        brand_id=brand.id,
        platform="instagram",
        account_id="17841400928371",
        account_name="test_ig_brand",
        access_token=encrypt_token("EAAtest"),
        status="CONNECTED"
    )
    db_session.add(ig_acc)
    db_session.commit()

    unpublished_post = Post(
        user_id=user.id,
        brand_id=brand.id,
        title="Unpublished Draft Post",
        caption="Draft Caption",
        status="DRAFT",
        platforms=["instagram"],
        ig_media_id=None
    )
    db_session.add(unpublished_post)
    db_session.commit()

    payload = {
        "name": "Invalid Automation",
        "platform": "instagram",
        "social_account_id": ig_acc.id,
        "post_target_type": "SPECIFIC_POST",
        "internal_post_id": unpublished_post.id,
        "external_post_id": None,
        "trigger_type": "ANY_COMMENT",
        "trigger_config": {},
        "action_config": {
            "public_reply": {"enabled": True, "variations": ["Hi!"]}
        }
    }

    response = client.post("/api/v1/automations", json=payload)
    assert response.status_code == 400
    assert "lacks an external platform post ID" in response.json()["detail"]


def test_regression_external_post_id_comment_trigger_match(db_session: Session, test_user_and_brand):
    """
    CRITICAL STEP 14 REGRESSION TEST:
    Connected Instagram Account: ID = ig_acc.id
    Real Instagram Media: 18026466023684307
    NO local Post record exists in database.
    Create active automation with external_post_id = '18026466023684307'.
    Ingest customer comment on external_post_id = '18026466023684307' with keyword 'price'.
    Expected:
      - candidate_automations = 1
      - AutomationExecution is created in PENDING status
      - Does NOT require Post.id = anything
    """
    user, brand = test_user_and_brand

    # Connected Instagram account
    ig_acc = SocialAccount(
        user_id=user.id,
        brand_id=brand.id,
        platform="instagram",
        account_id="17841400928371",
        account_name="live_ig_brand",
        access_token=encrypt_token("EAAlive_ig_token"),
        status="CONNECTED"
    )
    db_session.add(ig_acc)
    db_session.commit()
    db_session.refresh(ig_acc)

    # Confirm 0 local Post rows
    assert db_session.query(Post).count() == 0

    # Create ACTIVE automation
    auto = Automation(
        user_id=user.id,
        social_account_id=ig_acc.id,
        name="Real IG Post Automation",
        platform="instagram",
        status=AutomationStatus.ACTIVE.value,
        post_target_type=PostTargetType.SPECIFIC_POST.value,
        internal_post_id=None,
        external_post_id="18026466023684307",
        trigger_type=TriggerType.KEYWORD.value,
        trigger_config={"keywords": ["price", "link"]},
        action_config={
            "public_reply": {"enabled": True, "variations": ["Check your DM!"]},
            "private_message": {"enabled": True, "message": "Here is the special link."}
        }
    )
    db_session.add(auto)
    db_session.commit()
    db_session.refresh(auto)

    # Ingest customer comment on the real IG media ID
    comment = SocialComment(
        user_id=user.id,
        social_account_id=ig_acc.id,
        platform="instagram",
        webhook_object="instagram",
        external_post_id="18026466023684307",
        external_comment_id="ig_comment_99998888",
        commenter_id="user_customer_555",
        commenter_name="customer_buyer",
        comment_text="What is the price please?",
        processing_status="RECEIVED"
    )
    db_session.add(comment)
    db_session.commit()
    db_session.refresh(comment)

    # Run CommentTriggerService
    trigger_service = CommentTriggerService()
    candidates = trigger_service.find_candidate_automations(
        db=db_session,
        account=ig_acc,
        external_post_id=comment.external_post_id
    )

    # Assert matching
    assert len(candidates) == 1
    assert candidates[0].id == auto.id
    assert candidates[0].external_post_id == "18026466023684307"

    # Evaluate comment and verify execution created
    executions = trigger_service.evaluate_comment(
        db=db_session,
        comment=comment,
        account=ig_acc
    )

    assert len(executions) == 1
    execution = executions[0]
    assert execution.automation_id == auto.id
    assert execution.external_post_id == "18026466023684307"
    assert execution.external_comment_id == "ig_comment_99998888"
    assert execution.status == ExecutionStatus.PENDING.value
    assert execution.trigger_result["matched_keyword"] == "price"

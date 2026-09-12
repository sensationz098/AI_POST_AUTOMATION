import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.security_encryption import encrypt_token
from app.models.user import User
from app.models.brand import BrandProfile
from app.models.social_account import SocialAccount
from app.models.post import Post
from app.models.publishing_batch import PublishingBatch, PublishingJob
from app.api.v1.deps import get_current_user


@pytest.fixture
def multi_publish_test_setup(db_session: Session):
    user = User(
        email="multi_pub_guard_tester@example.com",
        hashed_password="hashed_pw_test",
        full_name="Multi Publish Guard Tester",
        role="Admin",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    brand = BrandProfile(
        user_id=user.id,
        name="Multi Pub Brand",
        tone_of_voice="Professional",
        cta_style="Direct",
        brand_colors=["#000000"]
    )
    db_session.add(brand)
    db_session.commit()
    db_session.refresh(brand)

    # 1. Connected Facebook Account
    fb_acc = SocialAccount(
        user_id=user.id,
        brand_id=brand.id,
        platform="facebook",
        account_id="109823471029888",
        account_name="Facebook Page Official",
        access_token=encrypt_token("EAAtest_fb_token"),
        status="CONNECTED"
    )
    # 2. Connected Instagram Account
    ig_acc = SocialAccount(
        user_id=user.id,
        brand_id=brand.id,
        platform="instagram",
        account_id="17841400928371999",
        account_name="instagram_official",
        access_token=encrypt_token("EAAtest_ig_token"),
        status="CONNECTED"
    )
    # 3. Connected YouTube Account
    yt_acc = SocialAccount(
        user_id=user.id,
        brand_id=brand.id,
        platform="youtube",
        account_id="UC_youtube_test_channel_40",
        account_name="YouTube Official Channel #40",
        access_token=encrypt_token("ya29.youtube_token"),
        status="CONNECTED"
    )

    db_session.add_all([fb_acc, ig_acc, yt_acc])
    db_session.commit()
    db_session.refresh(fb_acc)
    db_session.refresh(ig_acc)
    db_session.refresh(yt_acc)

    post = Post(
        user_id=user.id,
        brand_id=brand.id,
        title="Test Multi Publish Post",
        caption="Amazing cross-platform announcement!",
        status="DRAFT",
        image_url="https://res.cloudinary.com/test/image/upload/sample.jpg",
        media_type="image"
    )
    db_session.add(post)
    db_session.commit()
    db_session.refresh(post)

    app.dependency_overrides[get_current_user] = lambda: user
    yield user, brand, post, fb_acc, ig_acc, yt_acc
    app.dependency_overrides.pop(get_current_user, None)


def test_publish_multi_rejects_youtube_account_with_http_400(client: TestClient, db_session: Session, multi_publish_test_setup):
    """Verify POST /posts/publish-multi returns HTTP 400 when a YouTube account ID is included."""
    user, brand, post, fb_acc, ig_acc, yt_acc = multi_publish_test_setup

    initial_batch_count = db_session.query(PublishingBatch).count()
    initial_job_count = db_session.query(PublishingJob).count()

    response = client.post(
        "/api/v1/posts/publish-multi",
        json={
            "post_id": post.id,
            "social_account_ids": [fb_acc.id, ig_acc.id, yt_acc.id],
            "media_type": "image"
        }
    )

    assert response.status_code == 400
    data = response.json()
    assert "supports Facebook and Instagram only" in data["detail"]
    assert "youtube" in data["detail"]

    # Verify defense-in-depth: NO PublishingBatch or PublishingJob was persisted
    assert db_session.query(PublishingBatch).count() == initial_batch_count
    assert db_session.query(PublishingJob).count() == initial_job_count


def test_publish_multi_rejects_sole_youtube_account_with_http_400(client: TestClient, db_session: Session, multi_publish_test_setup):
    """Verify POST /posts/publish-multi with only YouTube account returns HTTP 400 without creating batch or jobs."""
    user, brand, post, fb_acc, ig_acc, yt_acc = multi_publish_test_setup

    initial_batch_count = db_session.query(PublishingBatch).count()
    initial_job_count = db_session.query(PublishingJob).count()

    response = client.post(
        "/api/v1/posts/publish-multi",
        json={
            "post_id": post.id,
            "social_account_ids": [yt_acc.id],
            "media_type": "video"
        }
    )

    assert response.status_code == 400
    data = response.json()
    assert "supports Facebook and Instagram only" in data["detail"]
    assert "youtube" in data["detail"]

    # Verify no batch or jobs persisted
    assert db_session.query(PublishingBatch).count() == initial_batch_count
    assert db_session.query(PublishingJob).count() == initial_job_count


def test_publish_multi_succeeds_for_facebook_and_instagram(client: TestClient, db_session: Session, multi_publish_test_setup):
    """Verify POST /posts/publish-multi succeeds (HTTP 201) when selecting only Facebook + Instagram."""
    user, brand, post, fb_acc, ig_acc, yt_acc = multi_publish_test_setup

    with patch("app.services.publisher_service.PublishingEngine.execute_batch") as mock_exec:
        mock_exec.return_value = {"batch_id": 1, "status": "SUCCESS"}

        response = client.post(
            "/api/v1/posts/publish-multi",
            json={
                "post_id": post.id,
                "social_account_ids": [fb_acc.id, ig_acc.id],
                "media_type": "image"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["post_id"] == post.id
        assert data["total_targets"] == 2
        assert len(data["jobs"]) == 2

        job_platforms = {j["platform"] for j in data["jobs"]}
        assert job_platforms == {"facebook", "instagram"}


def test_publish_multi_ownership_validation_persists(client: TestClient, db_session: Session, multi_publish_test_setup):
    """Verify requesting accounts not belonging to user returns HTTP 404."""
    user, brand, post, fb_acc, ig_acc, yt_acc = multi_publish_test_setup

    response = client.post(
        "/api/v1/posts/publish-multi",
        json={
            "post_id": post.id,
            "social_account_ids": [99999],  # Non-existent or non-owned account
            "media_type": "image"
        }
    )

    assert response.status_code == 404
    data = response.json()
    assert "No matching authorized social accounts found" in data["detail"]

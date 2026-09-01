import pytest
from unittest.mock import patch
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.models.user import User
from app.models.brand import BrandProfile
from app.models.social_account import SocialAccount
from app.models.social_comment import SocialComment
from app.models.external_post_context import ExternalPostContext
from app.models.post import Post, PostStatus
from app.core.security_encryption import encrypt_token

@pytest.fixture
def test_user(db_session: Session):
    email = f"comments_user_{datetime.now(timezone.utc).timestamp()}@socialai.com"
    user = User(
        email=email,
        hashed_password="HashedPassword123!",
        is_active=True,
        full_name="Comment Test User"
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

def test_social_comments_account_context_and_post_resolution(client, db_session, test_user, auth_headers):
    """
    Verify GET /api/v1/social-comments/ returns account details and 3-tier resolved post context.
    """
    # Setup Brand
    brand = BrandProfile(user_id=test_user.id, name="Test Brand")
    db_session.add(brand)
    db_session.commit()
    db_session.refresh(brand)

    # 1. Setup Social Account
    sa = SocialAccount(
        user_id=test_user.id,
        brand_id=brand.id,
        platform="instagram",
        account_id="17841400928371",
        account_name="sensatiz_performing_arts",
        access_token=encrypt_token("mock_access_token"),
        status="CONNECTED"
    )
    db_session.add(sa)
    db_session.commit()
    db_session.refresh(sa)

    # 2. Setup Social Comments: One local post, one external post needing resolution
    local_post = Post(
        user_id=test_user.id,
        brand_id=brand.id,
        title="Local Published Post",
        caption="Local Post Caption",
        status=PostStatus.PUBLISHED,
        ig_media_id="local_ig_123"
    )
    db_session.add(local_post)
    db_session.commit()
    db_session.refresh(local_post)

    c1 = SocialComment(
        user_id=test_user.id,
        social_account_id=sa.id,
        platform="instagram",
        external_comment_id="comment_111",
        external_post_id="local_ig_123",
        comment_text="Great local post!",
        commenter_name="Alice",
        webhook_object="instagram",
        processing_status="RECEIVED"
    )
    c2 = SocialComment(
        user_id=test_user.id,
        social_account_id=sa.id,
        platform="instagram",
        external_comment_id="comment_222",
        external_post_id="ext_ig_999",
        comment_text="Nice external video!",
        commenter_name="Bob",
        webhook_object="instagram",
        processing_status="RECEIVED"
    )
    db_session.add_all([c1, c2])
    db_session.commit()

    # Mock Meta API lookup for external post ext_ig_999
    with patch("app.services.meta_service.meta_service.fetch_instagram_media_info") as mock_ig_fetch:
        mock_ig_fetch.return_value = {
            "id": "ext_ig_999",
            "caption": "External Reel Video\nSecond line",
            "media_type": "VIDEO",
            "media_url": "https://example.com/video.mp4",
            "thumbnail_url": "https://example.com/thumb.jpg",
            "permalink": "https://www.instagram.com/reel/C12345/",
            "timestamp": "2026-09-01T12:00:00Z"
        }

        response = client.get("/api/v1/social-comments/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        # Verify c1 (Local Post match)
        c1_data = next(c for c in data if c["id"] == c1.id)
        assert c1_data["account"]["account_name"] == "sensatiz_performing_arts"
        assert c1_data["account"]["username"] == "sensatiz_performing_arts"
        assert c1_data["post"]["source"] == "local"
        assert c1_data["post"]["title"] == "Local Published Post"

        # Verify c2 (External Meta Post resolution & caching)
        c2_data = next(c for c in data if c["id"] == c2.id)
        assert c2_data["account"]["account_name"] == "sensatiz_performing_arts"
        assert c2_data["post"]["source"] == "meta"
        assert c2_data["post"]["title"] == "External Reel Video"
        assert c2_data["post"]["permalink"] == "https://www.instagram.com/reel/C12345/"

        # Verify DB caching: ExternalPostContext should be saved with social_account_id
        ext_ctx = db_session.query(ExternalPostContext).filter_by(external_post_id="ext_ig_999").first()
        assert ext_ctx is not None
        assert ext_ctx.social_account_id == sa.id
        assert ext_ctx.status == "ACTIVE"
        assert ext_ctx.caption == "External Reel Video\nSecond line"

    # Second call should use DB cache (0 Meta API calls)
    with patch("app.services.meta_service.meta_service.fetch_instagram_media_info") as mock_ig_fetch2:
        response2 = client.get("/api/v1/social-comments/", headers=auth_headers)
        assert response2.status_code == 200
        mock_ig_fetch2.assert_not_called()


def test_social_comments_unavailable_post_fallback(client, db_session, test_user, auth_headers):
    """
    Verify that when Meta API returns error/404 for post info, the system caches UNAVAILABLE status gracefully.
    """
    sa = SocialAccount(
        user_id=test_user.id,
        platform="facebook",
        account_id="109823471029",
        account_name="Rizwan FB Page",
        access_token=encrypt_token("mock_token"),
        status="CONNECTED"
    )
    db_session.add(sa)
    db_session.commit()

    c = SocialComment(
        user_id=test_user.id,
        social_account_id=sa.id,
        platform="facebook",
        external_comment_id="fb_comment_333",
        external_post_id="deleted_fb_post_000",
        comment_text="Comment on deleted post",
        webhook_object="page",
        processing_status="RECEIVED"
    )
    db_session.add(c)
    db_session.commit()

    with patch("app.services.meta_service.meta_service.fetch_facebook_post_info") as mock_fb_fetch:
        mock_fb_fetch.return_value = None  # Simulating post deleted/not found

        response = client.get("/api/v1/social-comments/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

        comment_res = data[0]
        # Receiving account is still clearly identified!
        assert comment_res["account"]["account_name"] == "Rizwan FB Page"
        assert comment_res["account"]["platform"] == "facebook"
        # Post info is None (UI displays "Post details could not be loaded")
        assert comment_res["post"] is None

        # Verify UNAVAILABLE context was cached in DB with social_account_id
        ext_ctx = db_session.query(ExternalPostContext).filter_by(external_post_id="deleted_fb_post_000").first()
        assert ext_ctx is not None
        assert ext_ctx.social_account_id == sa.id
        assert ext_ctx.status == "UNAVAILABLE"


def test_external_post_context_account_isolation(client, db_session, test_user, auth_headers):
    """
    Verify that ExternalPostContext is strictly isolated per connected SocialAccount.
    Two SocialAccounts with comments sharing the same external_post_id do not bleed cached metadata.
    """
    sa_a = SocialAccount(
        user_id=test_user.id,
        platform="facebook",
        account_id="fb_acc_aaa",
        account_name="Account A Page",
        access_token=encrypt_token("token_a"),
        status="CONNECTED"
    )
    sa_b = SocialAccount(
        user_id=test_user.id,
        platform="facebook",
        account_id="fb_acc_bbb",
        account_name="Account B Page",
        access_token=encrypt_token("token_b"),
        status="CONNECTED"
    )
    db_session.add_all([sa_a, sa_b])
    db_session.commit()
    db_session.refresh(sa_a)
    db_session.refresh(sa_b)

    # Context for Account A already cached
    ctx_a = ExternalPostContext(
        platform="facebook",
        social_account_id=sa_a.id,
        external_post_id="shared_post_100",
        caption="Account A Unique Caption",
        status="ACTIVE"
    )
    db_session.add(ctx_a)

    # Comments for both accounts on shared_post_100
    ca = SocialComment(
        user_id=test_user.id,
        social_account_id=sa_a.id,
        platform="facebook",
        external_comment_id="c_a_1",
        external_post_id="shared_post_100",
        comment_text="Comment for Account A",
        webhook_object="page"
    )
    cb = SocialComment(
        user_id=test_user.id,
        social_account_id=sa_b.id,
        platform="facebook",
        external_comment_id="c_b_1",
        external_post_id="shared_post_100",
        comment_text="Comment for Account B",
        webhook_object="page"
    )
    db_session.add_all([ca, cb])
    db_session.commit()

    # Meta API call should only fetch for Account B (since Account A hit DB cache)
    with patch("app.services.meta_service.meta_service.fetch_facebook_post_info") as mock_fb_fetch:
        mock_fb_fetch.return_value = {
            "id": "shared_post_100",
            "message": "Account B Unique Caption",
            "permalink_url": "https://facebook.com/b/100"
        }

        res = client.get("/api/v1/social-comments/", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()

        ca_data = next(c for c in data if c["id"] == ca.id)
        cb_data = next(c for c in data if c["id"] == cb.id)

        # Account A receives Account A's cached caption
        assert ca_data["post"]["caption"] == "Account A Unique Caption"
        # Account B receives Account B's API-fetched caption
        assert cb_data["post"]["caption"] == "Account B Unique Caption"

        # Verify two isolated ExternalPostContext records exist in DB under unique (social_account_id, platform, external_post_id)
        contexts = db_session.query(ExternalPostContext).filter_by(external_post_id="shared_post_100").all()
        assert len(contexts) == 2
        account_map = {ctx.social_account_id: ctx.caption for ctx in contexts}
        assert account_map[sa_a.id] == "Account A Unique Caption"
        assert account_map[sa_b.id] == "Account B Unique Caption"


def test_unavailable_post_context_account_isolation(client, db_session, test_user, auth_headers):
    """
    Verify UNAVAILABLE cached status on Account A does not block post resolution for Account B.
    """
    sa_a = SocialAccount(
        user_id=test_user.id,
        platform="instagram",
        account_id="ig_acc_aaa",
        account_name="Account A IG",
        access_token=encrypt_token("token_a"),
        status="CONNECTED"
    )
    sa_b = SocialAccount(
        user_id=test_user.id,
        platform="instagram",
        account_id="ig_acc_bbb",
        account_name="Account B IG",
        access_token=encrypt_token("token_b"),
        status="CONNECTED"
    )
    db_session.add_all([sa_a, sa_b])
    db_session.commit()
    db_session.refresh(sa_a)
    db_session.refresh(sa_b)

    # Account A cached as UNAVAILABLE for post_200
    ctx_a = ExternalPostContext(
        platform="instagram",
        social_account_id=sa_a.id,
        external_post_id="post_200",
        status="UNAVAILABLE"
    )
    db_session.add(ctx_a)

    cb = SocialComment(
        user_id=test_user.id,
        social_account_id=sa_b.id,
        platform="instagram",
        external_comment_id="c_b_200",
        external_post_id="post_200",
        comment_text="Comment on Account B post 200",
        webhook_object="instagram"
    )
    db_session.add(cb)
    db_session.commit()

    # Meta API fetch for Account B succeeds
    with patch("app.services.meta_service.meta_service.fetch_instagram_media_info") as mock_ig_fetch:
        mock_ig_fetch.return_value = {
            "id": "post_200",
            "caption": "Active Post on Account B",
            "media_type": "IMAGE"
        }

        res = client.get("/api/v1/social-comments/", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        cb_data = next(c for c in data if c["id"] == cb.id)
        assert cb_data["post"]["caption"] == "Active Post on Account B"

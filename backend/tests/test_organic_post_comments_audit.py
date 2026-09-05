import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.social_account import SocialAccount
from app.models.post import Post, PostStatus
from app.models.social_comment import SocialComment
from app.models.social_comment_reply import SocialCommentReply
from app.models.external_post_context import ExternalPostContext
from app.repositories.social_comment_repository import social_comment_repo
from app.services.meta_service import meta_service
from app.core.security_encryption import encrypt_token


@pytest.fixture
def test_user(db_session: Session):
    u = User(
        email="organic_tester@example.com",
        full_name="Organic Tester",
        hashed_password="fakehashpw123",
        is_active=True
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def other_user(db_session: Session):
    u = User(
        email="other_organic@example.com",
        full_name="Other Organic User",
        hashed_password="fakehashpw123",
        is_active=True
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def fb_account(db_session: Session, test_user: User):
    acc = SocialAccount(
        user_id=test_user.id,
        platform="facebook",
        account_name="Organic FB Page",
        account_id="1001432206614811",
        access_token=encrypt_token("valid_fb_token_123"),
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
        account_name="organic_ig_brand",
        account_id="178414000111222",
        access_token=encrypt_token("valid_ig_token_456"),
        status="CONNECTED"
    )
    db_session.add(acc)
    db_session.commit()
    db_session.refresh(acc)
    return acc


@pytest.fixture
def native_fb_post(db_session: Session, test_user: User):
    from app.models.brand import BrandProfile
    brand = BrandProfile(user_id=test_user.id, name="Audit Brand")
    db_session.add(brand)
    db_session.commit()

    p = Post(
        user_id=test_user.id,
        brand_id=brand.id,
        title="Spring Launch Announcement",
        caption="Check out our new organic spring products!",
        image_url="https://example.com/spring.jpg",
        media_type="image",
        platforms=["facebook"],
        status=PostStatus.PUBLISHED.value,
        fb_post_id="1001432206614811_9876543210",
        published_at=datetime.now(timezone.utc) - timedelta(days=2)
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


@pytest.fixture
def native_ig_post(db_session: Session, test_user: User):
    from app.models.brand import BrandProfile
    brand = db_session.query(BrandProfile).filter_by(user_id=test_user.id).first()
    if not brand:
        brand = BrandProfile(user_id=test_user.id, name="Audit Brand")
        db_session.add(brand)
        db_session.commit()

    p = Post(
        user_id=test_user.id,
        brand_id=brand.id,
        title="Instagram Reel Spotlight",
        caption="Behind the scenes at our studio #bts",
        image_url="https://example.com/reel.jpg",
        media_type="video",
        platforms=["instagram"],
        status=PostStatus.PUBLISHED.value,
        ig_media_id="17987654321098765",
        published_at=datetime.now(timezone.utc) - timedelta(days=1)
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


# 1. Internal Post.id resolution
def test_organic_post_resolution_by_internal_id(
    client: TestClient, 
    db_session: Session, 
    test_user: User, 
    native_fb_post: Post,
    fb_account: SocialAccount
):
    from app.api.v1.deps import get_current_user
    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: test_user
    try:
        # Add a comment to the post
        c = SocialComment(
            user_id=test_user.id,
            social_account_id=fb_account.id,
            platform="facebook",
            external_comment_id="fb_c_int_1",
            external_post_id=native_fb_post.fb_post_id,
            comment_text="Love this spring launch!",
            commenter_name="Sarah",
            webhook_object="page"
        )
        db_session.add(c)
        db_session.commit()

        # Query using internal Post.id (integer)
        res = client.get(f"/api/v1/social-comments/posts/{native_fb_post.id}")
        assert res.status_code == 200
        data = res.json()
        assert data["post"]["id"] == native_fb_post.id
        assert data["post"]["title"] == "Spring Launch Announcement"
        assert data["post"]["caption"] == "Check out our new organic spring products!"
        assert data["top_level_comment_count"] == 1
        assert len(data["comments"]) == 1
        assert data["comments"][0]["comment_text"] == "Love this spring launch!"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


# 2. Facebook compound fb_post_id resolution
def test_organic_post_resolution_by_compound_fb_post_id(
    client: TestClient, 
    db_session: Session, 
    test_user: User, 
    native_fb_post: Post,
    fb_account: SocialAccount
):
    from app.api.v1.deps import get_current_user
    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: test_user
    try:
        c = SocialComment(
            user_id=test_user.id,
            social_account_id=fb_account.id,
            platform="facebook",
            external_comment_id="fb_c_cmp_1",
            external_post_id=native_fb_post.fb_post_id,
            comment_text="Compound ID works!",
            commenter_name="Alex",
            webhook_object="page"
        )
        db_session.add(c)
        db_session.commit()

        # Query using compound ID: "1001432206614811_9876543210"
        res = client.get(f"/api/v1/social-comments/posts/{native_fb_post.fb_post_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["post"]["id"] == native_fb_post.id
        assert data["post"]["title"] == "Spring Launch Announcement"
        assert data["top_level_comment_count"] == 1
        assert data["comments"][0]["comment_text"] == "Compound ID works!"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


# 3. Facebook short post ID resolution
def test_organic_post_resolution_by_short_post_id(
    client: TestClient, 
    db_session: Session, 
    test_user: User, 
    native_fb_post: Post,
    fb_account: SocialAccount
):
    from app.api.v1.deps import get_current_user
    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: test_user
    try:
        c = SocialComment(
            user_id=test_user.id,
            social_account_id=fb_account.id,
            platform="facebook",
            external_comment_id="fb_c_short_1",
            external_post_id="1001432206614811_9876543210",
            comment_text="Short ID query matches compound comment!",
            commenter_name="Taylor",
            webhook_object="page"
        )
        db_session.add(c)
        db_session.commit()

        # Query using short post ID: "9876543210"
        res = client.get("/api/v1/social-comments/posts/9876543210")
        assert res.status_code == 200
        data = res.json()
        assert data["post"]["id"] == native_fb_post.id
        assert data["top_level_comment_count"] == 1
        assert data["comments"][0]["comment_text"] == "Short ID query matches compound comment!"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


# 4. Instagram ig_media_id resolution
def test_organic_post_resolution_by_ig_media_id(
    client: TestClient, 
    db_session: Session, 
    test_user: User, 
    native_ig_post: Post,
    ig_account: SocialAccount
):
    from app.api.v1.deps import get_current_user
    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: test_user
    try:
        c = SocialComment(
            user_id=test_user.id,
            social_account_id=ig_account.id,
            platform="instagram",
            external_comment_id="ig_c_123",
            external_post_id=native_ig_post.ig_media_id,
            comment_text="Great reel!",
            commenter_name="ig_fan",
            webhook_object="instagram"
        )
        db_session.add(c)
        db_session.commit()

        res = client.get(f"/api/v1/social-comments/posts/{native_ig_post.ig_media_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["post"]["id"] == native_ig_post.id
        assert data["post"]["platform"] == "instagram"
        assert data["top_level_comment_count"] == 1
        assert data["comments"][0]["comment_text"] == "Great reel!"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


# 5. User/account isolation
def test_organic_post_user_account_isolation(
    client: TestClient, 
    db_session: Session, 
    test_user: User, 
    other_user: User, 
    native_fb_post: Post,
    fb_account: SocialAccount
):
    from app.api.v1.deps import get_current_user
    from app.main import app

    c = SocialComment(
        user_id=test_user.id,
        social_account_id=fb_account.id,
        platform="facebook",
        external_comment_id="fb_c_secret_1",
        external_post_id=native_fb_post.fb_post_id,
        comment_text="Private organic comment",
        commenter_name="VIP Client",
        webhook_object="page"
    )
    db_session.add(c)
    db_session.commit()

    # User B queries User A's post
    app.dependency_overrides[get_current_user] = lambda: other_user
    try:
        res = client.get(f"/api/v1/social-comments/posts/{native_fb_post.id}")
        assert res.status_code == 200
        data = res.json()
        # Other user must NOT see User A's comments or native post metadata
        assert data["top_level_comment_count"] == 0
        assert len(data["comments"]) == 0
    finally:
        app.dependency_overrides.pop(get_current_user, None)


# 6 & 7. Top-level count semantics and reply nesting
def test_organic_post_count_semantics_and_reply_nesting(
    client: TestClient, 
    db_session: Session, 
    test_user: User, 
    native_fb_post: Post,
    fb_account: SocialAccount
):
    from app.api.v1.deps import get_current_user
    from app.main import app

    now = datetime.now(timezone.utc)
    # Parent comment 1
    p1 = SocialComment(
        user_id=test_user.id,
        social_account_id=fb_account.id,
        platform="facebook",
        external_comment_id="fb_p1",
        external_post_id=native_fb_post.fb_post_id,
        parent_comment_id=None,
        comment_text="Parent comment 1",
        commenter_name="Alice",
        event_timestamp=now - timedelta(hours=3),
        webhook_object="page"
    )
    # Parent comment 2
    p2 = SocialComment(
        user_id=test_user.id,
        social_account_id=fb_account.id,
        platform="facebook",
        external_comment_id="fb_p2",
        external_post_id=native_fb_post.fb_post_id,
        parent_comment_id=None,
        comment_text="Parent comment 2",
        commenter_name="Bob",
        event_timestamp=now - timedelta(hours=2),
        webhook_object="page"
    )
    # Child reply from customer under p1
    rep_meta = SocialComment(
        user_id=test_user.id,
        social_account_id=fb_account.id,
        platform="facebook",
        external_comment_id="fb_c_rep_1",
        external_post_id=native_fb_post.fb_post_id,
        parent_comment_id="fb_p1",
        comment_text="Customer follow-up reply",
        commenter_name="Charlie",
        event_timestamp=now - timedelta(hours=1),
        webhook_object="page"
    )
    db_session.add_all([p1, p2, rep_meta])
    db_session.commit()

    # Manual owner reply under p1
    rep_owner = SocialCommentReply(
        comment_id=p1.id,
        user_id=test_user.id,
        platform="facebook",
        message="Thank you Alice from the Brand!",
        status="SUCCESS",
        external_reply_id="fb_owner_rep_1"
    )
    db_session.add(rep_owner)
    db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: test_user
    try:
        res = client.get(f"/api/v1/social-comments/posts/{native_fb_post.fb_post_id}")
        assert res.status_code == 200
        data = res.json()

        # Primary count must be 2 (top-level only), replies = 2, total interactions = 4
        assert data["top_level_comment_count"] == 2
        assert data["reply_count"] == 2
        assert data["total_interaction_count"] == 4
        assert len(data["comments"]) == 2

        # Check nested replies under p1
        p1_data = next(c for c in data["comments"] if c["external_comment_id"] == "fb_p1")
        assert len(p1_data["replies"]) == 2
        
        # Verify reply attribution
        meta_rep = next(r for r in p1_data["replies"] if r["source"] == "meta")
        assert meta_rep["message"] == "Customer follow-up reply"
        assert meta_rep["commenter_name"] == "Charlie"

        owner_rep = next(r for r in p1_data["replies"] if r["source"] == "owner")
        assert owner_rep["message"] == "Thank you Alice from the Brand!"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


# 8 & 9. Newest and Oldest sorting
def test_organic_post_newest_oldest_sorting(
    client: TestClient, 
    db_session: Session, 
    test_user: User, 
    native_fb_post: Post,
    fb_account: SocialAccount
):
    from app.api.v1.deps import get_current_user
    from app.main import app

    now = datetime.now(timezone.utc)
    c_older = SocialComment(
        user_id=test_user.id,
        social_account_id=fb_account.id,
        platform="facebook",
        external_comment_id="fb_sort_old",
        external_post_id=native_fb_post.fb_post_id,
        comment_text="Older comment",
        event_timestamp=now - timedelta(days=2),
        webhook_object="page"
    )
    c_newer = SocialComment(
        user_id=test_user.id,
        social_account_id=fb_account.id,
        platform="facebook",
        external_comment_id="fb_sort_new",
        external_post_id=native_fb_post.fb_post_id,
        comment_text="Newer comment",
        event_timestamp=now - timedelta(minutes=5),
        webhook_object="page"
    )
    db_session.add_all([c_older, c_newer])
    db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: test_user
    try:
        # Descending (Newest first)
        res_desc = client.get(f"/api/v1/social-comments/posts/{native_fb_post.fb_post_id}?sort_order=desc")
        data_desc = res_desc.json()
        assert data_desc["comments"][0]["external_comment_id"] == "fb_sort_new"
        assert data_desc["comments"][1]["external_comment_id"] == "fb_sort_old"

        # Ascending (Oldest first)
        res_asc = client.get(f"/api/v1/social-comments/posts/{native_fb_post.fb_post_id}?sort_order=asc")
        data_asc = res_asc.json()
        assert data_asc["comments"][0]["external_comment_id"] == "fb_sort_old"
        assert data_asc["comments"][1]["external_comment_id"] == "fb_sort_new"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


# 10 & 11. Replied and Unreplied filters
def test_organic_post_status_filtering(
    client: TestClient, 
    db_session: Session, 
    test_user: User, 
    native_fb_post: Post,
    fb_account: SocialAccount
):
    from app.api.v1.deps import get_current_user
    from app.main import app

    c_unreplied = SocialComment(
        user_id=test_user.id,
        social_account_id=fb_account.id,
        platform="facebook",
        external_comment_id="fb_filter_unreplied",
        external_post_id=native_fb_post.fb_post_id,
        comment_text="I need help",
        webhook_object="page"
    )
    c_replied = SocialComment(
        user_id=test_user.id,
        social_account_id=fb_account.id,
        platform="facebook",
        external_comment_id="fb_filter_replied",
        external_post_id=native_fb_post.fb_post_id,
        comment_text="Thank you!",
        webhook_object="page"
    )
    db_session.add_all([c_unreplied, c_replied])
    db_session.commit()

    reply = SocialCommentReply(
        comment_id=c_replied.id,
        user_id=test_user.id,
        platform="facebook",
        message="Glad to help!",
        status="SUCCESS"
    )
    db_session.add(reply)
    db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: test_user
    try:
        # Unreplied filter
        res_unrep = client.get(f"/api/v1/social-comments/posts/{native_fb_post.fb_post_id}?reply_status=unreplied")
        data_unrep = res_unrep.json()
        assert len(data_unrep["comments"]) == 1
        assert data_unrep["comments"][0]["external_comment_id"] == "fb_filter_unreplied"

        # Replied filter
        res_rep = client.get(f"/api/v1/social-comments/posts/{native_fb_post.fb_post_id}?reply_status=replied")
        data_rep = res_rep.json()
        assert len(data_rep["comments"]) == 1
        assert data_rep["comments"][0]["external_comment_id"] == "fb_filter_replied"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


# 12. Pagination on organic post comments
def test_organic_post_pagination_skip_limit(
    client: TestClient, 
    db_session: Session, 
    test_user: User, 
    native_fb_post: Post,
    fb_account: SocialAccount
):
    from app.api.v1.deps import get_current_user
    from app.main import app

    # Create 5 comments
    comments = []
    for i in range(5):
        c = SocialComment(
            user_id=test_user.id,
            social_account_id=fb_account.id,
            platform="facebook",
            external_comment_id=f"fb_page_c_{i}",
            external_post_id=native_fb_post.fb_post_id,
            comment_text=f"Comment {i}",
            event_timestamp=datetime.now(timezone.utc) + timedelta(minutes=i),
            webhook_object="page"
        )
        comments.append(c)
    db_session.add_all(comments)
    db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: test_user
    try:
        # Page 1: skip=0, limit=2
        res1 = client.get(f"/api/v1/social-comments/posts/{native_fb_post.fb_post_id}?skip=0&limit=2")
        data1 = res1.json()
        assert data1["top_level_comment_count"] == 5
        assert len(data1["comments"]) == 2

        # Page 2: skip=2, limit=2
        res2 = client.get(f"/api/v1/social-comments/posts/{native_fb_post.fb_post_id}?skip=2&limit=2")
        data2 = res2.json()
        assert len(data2["comments"]) == 2

        # Ensure no overlap
        p1_ids = {c["id"] for c in data1["comments"]}
        p2_ids = {c["id"] for c in data2["comments"]}
        assert p1_ids.isdisjoint(p2_ids)
    finally:
        app.dependency_overrides.pop(get_current_user, None)


# 13. Instagram comment sync
def test_instagram_organic_comment_sync(
    db_session: Session, 
    test_user: User, 
    ig_account: SocialAccount, 
    native_ig_post: Post
):
    mock_ig_comments = [
        {
            "id": "ig_sync_c_1",
            "text": "How much does this cost?",
            "timestamp": "2026-09-05T10:00:00+00:00",
            "username": "shopper_ig",
            "from": {"id": "user_ig_99", "username": "shopper_ig"},
            "replies": {
                "data": [
                    {
                        "id": "ig_sync_reply_1",
                        "text": "It costs $49!",
                        "timestamp": "2026-09-05T10:05:00+00:00",
                        "username": "brand_mod",
                        "from": {"id": "brand_user_1", "username": "brand_mod"}
                    }
                ]
            }
        }
    ]

    with patch.object(meta_service, "fetch_comments_for_instagram_media", return_value=(mock_ig_comments, {"status_code": 200})):
        res = meta_service.sync_comments_for_instagram_post(
            db=db_session,
            user_id=test_user.id,
            media_id=native_ig_post.ig_media_id,
            social_account_id=ig_account.id
        )
        assert res["success"] is True
        assert res["comments_fetched"] == 1
        assert res["comments_saved"] == 2  # 1 parent + 1 reply

        # Verify DB records
        saved_parent = db_session.query(SocialComment).filter_by(external_comment_id="ig_sync_c_1").first()
        assert saved_parent is not None
        assert saved_parent.comment_text == "How much does this cost?"
        assert saved_parent.commenter_name == "shopper_ig"

        saved_reply = db_session.query(SocialComment).filter_by(external_comment_id="ig_sync_reply_1").first()
        assert saved_reply is not None
        assert saved_reply.parent_comment_id == "ig_sync_c_1"


# 14, 15, 16. Facebook and Instagram Organic Replying
def test_organic_replying_facebook_and_instagram(
    client: TestClient, 
    db_session: Session, 
    test_user: User, 
    fb_account: SocialAccount, 
    ig_account: SocialAccount
):
    from app.api.v1.deps import get_current_user
    from app.main import app

    fb_c = SocialComment(
        user_id=test_user.id,
        social_account_id=fb_account.id,
        platform="facebook",
        external_comment_id="fb_target_c1",
        comment_text="Can I get a discount?",
        webhook_object="page"
    )
    ig_c = SocialComment(
        user_id=test_user.id,
        social_account_id=ig_account.id,
        platform="instagram",
        external_comment_id="ig_target_c2",
        comment_text="Where is your store located?",
        webhook_object="instagram"
    )
    db_session.add_all([fb_c, ig_c])
    db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: test_user
    try:
        # Facebook reply
        with patch.object(meta_service, "reply_to_facebook_comment", return_value={"id": "fb_reply_100"}):
            res_fb = client.post(
                f"/api/v1/social-comments/{fb_c.id}/reply",
                json={"message": "Use code SPRING10 for 10% off!"}
            )
            assert res_fb.status_code == 200
            assert res_fb.json()["external_reply_id"] == "fb_reply_100"

        # Instagram reply
        with patch.object(meta_service, "reply_to_instagram_comment", return_value={"id": "ig_reply_200"}):
            res_ig = client.post(
                f"/api/v1/social-comments/{ig_c.id}/reply",
                json={"message": "We are located at 5th Avenue!"}
            )
            assert res_ig.status_code == 200
            assert res_ig.json()["external_reply_id"] == "ig_reply_200"
    finally:
        app.dependency_overrides.pop(get_current_user, None)

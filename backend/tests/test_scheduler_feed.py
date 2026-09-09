import pytest
from datetime import datetime, timezone, timedelta
from app.models.user import User
from app.models.brand import BrandProfile
from app.models.social_account import SocialAccount
from app.models.post import Post, PostStatus
from app.models.story import Story, StoryStatus
from app.core.security_encryption import encrypt_token


def get_auth_token(client, email="sched_feed_user@test.com", password="Password123!"):
    client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "full_name": "Scheduler Feed User",
        "role": "Admin"
    })
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return res.json()["access_token"]


def setup_user_with_posts_and_stories(client, db_session, email="sched_feed_user@test.com"):
    token = get_auth_token(client, email=email)
    headers = {"Authorization": f"Bearer {token}"}

    user = db_session.query(User).filter(User.email == email).first()

    brand = BrandProfile(user_id=user.id, name="Feed Brand")
    db_session.add(brand)
    db_session.commit()
    db_session.refresh(brand)

    fb_acc = SocialAccount(
        user_id=user.id,
        brand_id=brand.id,
        platform="facebook",
        account_id="fb_page_sched",
        account_name="Scheduler FB Page",
        access_token=encrypt_token("tok_fb_sched"),
        status="CONNECTED"
    )
    ig_acc = SocialAccount(
        user_id=user.id,
        brand_id=brand.id,
        platform="instagram",
        account_id="ig_biz_sched",
        account_name="@sched_ig_biz",
        access_token=encrypt_token("tok_ig_sched"),
        status="CONNECTED",
        metadata_json={"account_type": "BUSINESS"}
    )
    db_session.add_all([fb_acc, ig_acc])
    db_session.commit()
    db_session.refresh(fb_acc)
    db_session.refresh(ig_acc)

    now = datetime.now(timezone.utc)

    # 1. Post
    post = Post(
        brand_id=brand.id,
        user_id=user.id,
        title="Weekly Promo Post",
        caption="Check out our latest offer!",
        platforms=["facebook", "instagram"],
        status=PostStatus.SCHEDULED.value,
        scheduled_at=now + timedelta(hours=2),
        image_url="https://example.com/promo.jpg"
    )

    # 2. Story (targeting only ig_acc)
    story = Story(
        brand_id=brand.id,
        user_id=user.id,
        title="Flash Sale Story",
        caption="24 Hour Flash Sale!",
        media_url="https://res.cloudinary.com/demo/image/upload/flash_story.jpg",
        media_type="image",
        target_account_ids=[ig_acc.id],
        platforms=["instagram"],
        status=StoryStatus.SCHEDULED.value,
        scheduled_at=now + timedelta(hours=4)
    )

    db_session.add_all([post, story])
    db_session.commit()
    db_session.refresh(post)
    db_session.refresh(story)

    return headers, user, brand, fb_acc, ig_acc, post, story


def test_scheduler_feed_returns_both_posts_and_stories(client, db_session):
    """Verify GET /api/v1/posts/scheduler-feed returns both posts and stories with correct item_type tags."""
    headers, user, brand, fb_acc, ig_acc, post, story = setup_user_with_posts_and_stories(client, db_session, "feed1@test.com")

    res = client.get("/api/v1/posts/scheduler-feed", headers=headers)
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 2

    # Check item types
    types = [i["item_type"] for i in items]
    assert "post" in types
    assert "story" in types

    story_item = next(i for i in items if i["item_type"] == "story")
    assert story_item["id"] == story.id
    assert story_item["title"] == "Flash Sale Story"
    assert story_item["target_account_ids"] == [ig_acc.id]
    assert len(story_item["target_accounts"]) == 1
    assert story_item["target_accounts"][0]["account_name"] == "@sched_ig_biz"

    post_item = next(i for i in items if i["item_type"] == "post")
    assert post_item["id"] == post.id
    assert post_item["title"] == "Weekly Promo Post"


def test_scheduler_feed_filter_by_item_type(client, db_session):
    """Verify scheduler-feed filtering by item_type='story' and item_type='post'."""
    headers, user, brand, fb_acc, ig_acc, post, story = setup_user_with_posts_and_stories(client, db_session, "feed_filter@test.com")

    # Stories only
    res_story = client.get("/api/v1/posts/scheduler-feed?item_type=story", headers=headers)
    assert res_story.status_code == 200
    story_items = res_story.json()
    assert len(story_items) == 1
    assert story_items[0]["item_type"] == "story"

    # Posts only
    res_post = client.get("/api/v1/posts/scheduler-feed?item_type=post", headers=headers)
    assert res_post.status_code == 200
    post_items = res_post.json()
    assert len(post_items) == 1
    assert post_items[0]["item_type"] == "post"


def test_story_deletion_removes_from_scheduler_feed(client, db_session):
    """Verify deleting a story removes it from the scheduler feed and cancels scheduling."""
    headers, user, brand, fb_acc, ig_acc, post, story = setup_user_with_posts_and_stories(client, db_session, "feed_del@test.com")

    # Delete the story
    del_res = client.delete(f"/api/v1/stories/{story.id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # Feed should now only have the post
    res = client.get("/api/v1/posts/scheduler-feed", headers=headers)
    items = res.json()
    assert len(items) == 1
    assert items[0]["item_type"] == "post"

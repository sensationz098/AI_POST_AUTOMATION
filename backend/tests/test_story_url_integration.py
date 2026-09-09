import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from app.models.user import User
from app.models.brand import BrandProfile
from app.models.social_account import SocialAccount
from app.models.story import Story, StoryStatus
from app.core.security_encryption import encrypt_token
from app.core.security import get_password_hash
from app.services.story_service import story_service
from app.services.meta_service import meta_service


def get_auth_headers(client, email="story_url_test@test.com", password="Password123!"):
    client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "full_name": "Story URL User",
        "role": "Admin"
    })
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def setup_story_test_env(db_session, user_email="story_url_test@test.com"):
    user = db_session.query(User).filter(User.email == user_email).first()
    if not user:
        user = User(
            email=user_email,
            hashed_password=get_password_hash("Password123!"),
            full_name="Story URL User",
            role="Admin",
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    brand = db_session.query(BrandProfile).filter(BrandProfile.user_id == user.id).first()
    if not brand:
        brand = BrandProfile(user_id=user.id, name="Story URL Brand")
        db_session.add(brand)
        db_session.commit()
        db_session.refresh(brand)

    fb_acc = SocialAccount(
        user_id=user.id,
        brand_id=brand.id,
        platform="facebook",
        account_id="916776691089067",
        account_name="Official FB Page",
        access_token=encrypt_token("tok_fb_test"),
        status="CONNECTED",
        metadata_json={"page_id": "916776691089067"}
    )
    ig_acc = SocialAccount(
        user_id=user.id,
        brand_id=brand.id,
        platform="instagram",
        account_id="17841443294223730",
        account_name="@brand_official",
        access_token=encrypt_token("tok_ig_test"),
        status="CONNECTED",
        metadata_json={"username": "brand_official"}
    )
    db_session.add_all([fb_acc, ig_acc])
    db_session.commit()
    db_session.refresh(fb_acc)
    db_session.refresh(ig_acc)

    return user, brand, fb_acc, ig_acc


class TestStoryPublishUrlHandling:
    def test_fb_story_with_valid_permalink(self, db_session):
        """When Meta returns a valid Story permalink, store it."""
        user, brand, fb_acc, _ = setup_story_test_env(db_session, "fb_valid_perm@test.com")
        story = Story(
            user_id=user.id,
            brand_id=brand.id,
            title="FB Story",
            media_url="https://res.cloudinary.com/demo/image/upload/story.jpg",
            media_type="image",
            target_account_ids=[fb_acc.id],
            status=StoryStatus.DRAFT.value
        )
        db_session.add(story)
        db_session.commit()
        db_session.refresh(story)

        valid_permalink = "https://www.facebook.com/stories/916776691089067/1698866234536797/"
        mock_res = {
            "id": "1698866234536797",
            "status": "published",
            "url": valid_permalink,
            "page_url": "https://www.facebook.com/916776691089067"
        }
        with patch.object(story_service, "publish_facebook_story", return_value=mock_res):
            updated = story_service.publish_story(db_session, story.id, user.id)
            assert updated.status == StoryStatus.PUBLISHED.value
            assert updated.fb_story_id == "1698866234536797"
            assert updated.fb_story_url == valid_permalink

    def test_fb_story_without_individual_permalink_no_fake_url(self, db_session):
        """When Meta does not provide a permalink, fb_story_url must be None (never fake https://facebook.com/{page_id})."""
        user, brand, fb_acc, _ = setup_story_test_env(db_session, "fb_no_perm@test.com")
        story = Story(
            user_id=user.id,
            brand_id=brand.id,
            title="FB Story No Perm",
            media_url="https://res.cloudinary.com/demo/image/upload/story.jpg",
            media_type="image",
            target_account_ids=[fb_acc.id],
            status=StoryStatus.DRAFT.value
        )
        db_session.add(story)
        db_session.commit()
        db_session.refresh(story)

        mock_res = {
            "id": "1698866234536797",
            "status": "published",
            "url": None,  # No valid permalink
            "page_url": "https://www.facebook.com/916776691089067"
        }
        with patch.object(story_service, "publish_facebook_story", return_value=mock_res):
            updated = story_service.publish_story(db_session, story.id, user.id)
            assert updated.status == StoryStatus.PUBLISHED.value
            assert updated.fb_story_id == "1698866234536797"
            assert updated.fb_story_url is None  # MUST NOT be fake https://www.facebook.com/916776691089067

    def test_ig_story_with_valid_username(self, db_session):
        """When Instagram story publishes, ig_story_url must be https://www.instagram.com/stories/{username}/."""
        user, brand, _, ig_acc = setup_story_test_env(db_session, "ig_valid_user@test.com")
        story = Story(
            user_id=user.id,
            brand_id=brand.id,
            title="IG Story Valid User",
            media_url="https://res.cloudinary.com/demo/image/upload/story.jpg",
            media_type="image",
            target_account_ids=[ig_acc.id],
            status=StoryStatus.DRAFT.value
        )
        db_session.add(story)
        db_session.commit()
        db_session.refresh(story)

        mock_res = {
            "id": "18021105707861393",
            "container_id": "container_123",
            "status": "published",
            "url": "https://www.instagram.com/stories/brand_official/",
            "username": "brand_official"
        }
        with patch.object(story_service, "publish_instagram_story", return_value=mock_res):
            updated = story_service.publish_story(db_session, story.id, user.id)
            assert updated.status == StoryStatus.PUBLISHED.value
            assert updated.ig_story_id == "18021105707861393"
            assert updated.ig_username == "brand_official"
            assert updated.ig_story_url == "https://www.instagram.com/stories/brand_official/"

    def test_ig_story_without_username_no_broken_url(self, db_session):
        """When Instagram username cannot be resolved, ig_story_url must be None (never https://instagram.com/stories/)."""
        user, brand, _, ig_acc = setup_story_test_env(db_session, "ig_no_user@test.com")
        story = Story(
            user_id=user.id,
            brand_id=brand.id,
            title="IG Story No User",
            media_url="https://res.cloudinary.com/demo/image/upload/story.jpg",
            media_type="image",
            target_account_ids=[ig_acc.id],
            status=StoryStatus.DRAFT.value
        )
        db_session.add(story)
        db_session.commit()
        db_session.refresh(story)

        mock_res = {
            "id": "18021105707861393",
            "container_id": "container_123",
            "status": "published",
            "url": None,  # No username
            "username": None
        }
        with patch.object(story_service, "publish_instagram_story", return_value=mock_res):
            updated = story_service.publish_story(db_session, story.id, user.id)
            assert updated.status == StoryStatus.PUBLISHED.value
            assert updated.ig_story_id == "18021105707861393"
            assert updated.ig_story_url is None  # MUST NOT be https://www.instagram.com/stories/

    def test_partial_success_fb_success_ig_failed(self, db_session):
        """Facebook success + Instagram failed records fb_story_id and fb_story_url, while ig remains unset."""
        user, brand, fb_acc, ig_acc = setup_story_test_env(db_session, "partial_fb_ok@test.com")
        story = Story(
            user_id=user.id,
            brand_id=brand.id,
            title="Partial FB OK",
            media_url="https://res.cloudinary.com/demo/image/upload/story.jpg",
            media_type="image",
            target_account_ids=[fb_acc.id, ig_acc.id],
            status=StoryStatus.DRAFT.value
        )
        db_session.add(story)
        db_session.commit()
        db_session.refresh(story)

        mock_fb_res = {
            "id": "1698866234536797",
            "status": "published",
            "url": "https://www.facebook.com/stories/916776691089067/1698866234536797/",
            "page_url": "https://www.facebook.com/916776691089067"
        }
        with patch.object(story_service, "publish_facebook_story", return_value=mock_fb_res), \
             patch.object(story_service, "publish_instagram_story", side_effect=Exception("Instagram timeout")):

            updated = story_service.publish_story(db_session, story.id, user.id)
            # Story is published because at least one account succeeded
            assert updated.status == StoryStatus.PUBLISHED.value
            assert updated.fb_story_id == "1698866234536797"
            assert updated.fb_story_url == "https://www.facebook.com/stories/916776691089067/1698866234536797/"
            assert updated.ig_story_id is None
            assert updated.ig_story_url is None

    def test_partial_success_ig_success_fb_failed(self, db_session):
        """Instagram success + Facebook failed records ig_story_id and ig_story_url, while fb remains unset."""
        user, brand, fb_acc, ig_acc = setup_story_test_env(db_session, "partial_ig_ok@test.com")
        story = Story(
            user_id=user.id,
            brand_id=brand.id,
            title="Partial IG OK",
            media_url="https://res.cloudinary.com/demo/image/upload/story.jpg",
            media_type="image",
            target_account_ids=[fb_acc.id, ig_acc.id],
            status=StoryStatus.DRAFT.value
        )
        db_session.add(story)
        db_session.commit()
        db_session.refresh(story)

        mock_ig_res = {
            "id": "18021105707861393",
            "container_id": "container_123",
            "status": "published",
            "url": "https://www.instagram.com/stories/brand_official/",
            "username": "brand_official"
        }
        with patch.object(story_service, "publish_facebook_story", side_effect=Exception("Facebook error")), \
             patch.object(story_service, "publish_instagram_story", return_value=mock_ig_res):

            updated = story_service.publish_story(db_session, story.id, user.id)
            assert updated.status == StoryStatus.PUBLISHED.value
            assert updated.ig_story_id == "18021105707861393"
            assert updated.ig_story_url == "https://www.instagram.com/stories/brand_official/"
            assert updated.fb_story_id is None
            assert updated.fb_story_url is None

    def test_scheduler_feed_sanitizes_urls(self, client, db_session):
        """Scheduler feed endpoint rejects broken fake URLs if present in legacy rows and resolves clean ones."""
        headers = get_auth_headers(client, "feed_url_test@test.com")
        user = db_session.query(User).filter(User.email == "feed_url_test@test.com").first()
        brand = BrandProfile(user_id=user.id, name="Feed Test Brand")
        db_session.add(brand)
        db_session.commit()
        db_session.refresh(brand)

        fb_acc = SocialAccount(
            user_id=user.id,
            brand_id=brand.id,
            platform="facebook",
            account_id="916776691089067",
            account_name="Official FB Page",
            access_token=encrypt_token("tok_fb_feed"),
            status="CONNECTED",
            metadata_json={"page_id": "916776691089067"}
        )
        ig_acc = SocialAccount(
            user_id=user.id,
            brand_id=brand.id,
            platform="instagram",
            account_id="17841443294223730",
            account_name="@brand_official",
            access_token=encrypt_token("tok_ig_feed"),
            status="CONNECTED",
            metadata_json={"username": "brand_official"}
        )
        db_session.add_all([fb_acc, ig_acc])
        db_session.commit()
        db_session.refresh(fb_acc)
        db_session.refresh(ig_acc)

        # Create a story with broken legacy URLs
        legacy_story = Story(
            user_id=user.id,
            brand_id=brand.id,
            title="Legacy Story",
            media_url="https://res.cloudinary.com/demo/image/upload/story.jpg",
            media_type="image",
            target_account_ids=[fb_acc.id, ig_acc.id],
            status=StoryStatus.PUBLISHED.value,
            published_at=datetime.now(timezone.utc),
            fb_story_id="1698866234536797",
            fb_story_url="https://www.facebook.com/916776691089067",  # Broken Page-ID URL
            ig_story_id="18021105707861393",
            ig_story_url="https://www.instagram.com/stories/"  # Broken no-username URL
        )
        db_session.add(legacy_story)
        db_session.commit()
        db_session.refresh(legacy_story)

        res = client.get("/api/v1/posts/scheduler-feed", headers=headers)
        assert res.status_code == 200
        items = res.json()
        story_item = next(i for i in items if i["id"] == legacy_story.id and i["item_type"].lower() == "story")

        # The fake FB page URL must NOT be returned; it is repaired into a valid story permalink
        assert story_item["fb_url"] == "https://www.facebook.com/stories/916776691089067/1698866234536797/"
        assert story_item["fb_url"] != "https://www.facebook.com/916776691089067"
        # The broken IG URL must be repaired using the account's resolved username
        assert story_item["ig_url"] == "https://www.instagram.com/stories/brand_official/"
        assert story_item["ig_url"] != "https://www.instagram.com/stories/"

    def test_both_platforms_successful_records_both_ids_and_urls(self, client, db_session):
        """When both FB and IG succeed, scheduler feed returns both fb_id, fb_url, ig_id, and ig_url."""
        headers = get_auth_headers(client, "dual_success@test.com")
        user = db_session.query(User).filter(User.email == "dual_success@test.com").first()
        brand = BrandProfile(user_id=user.id, name="Dual Brand")
        db_session.add(brand)
        db_session.commit()
        db_session.refresh(brand)

        fb_acc = SocialAccount(
            user_id=user.id,
            brand_id=brand.id,
            platform="facebook",
            account_id="916776691089067",
            account_name="Official FB Page",
            access_token=encrypt_token("tok_fb_dual"),
            status="CONNECTED",
            metadata_json={"page_id": "916776691089067"}
        )
        ig_acc = SocialAccount(
            user_id=user.id,
            brand_id=brand.id,
            platform="instagram",
            account_id="17841443294223730",
            account_name="@brand_official",
            access_token=encrypt_token("tok_ig_dual"),
            status="CONNECTED",
            metadata_json={"username": "brand_official"}
        )
        db_session.add_all([fb_acc, ig_acc])
        db_session.commit()
        db_session.refresh(fb_acc)
        db_session.refresh(ig_acc)

        story = Story(
            user_id=user.id,
            brand_id=brand.id,
            title="Dual Published Story",
            media_url="https://res.cloudinary.com/demo/image/upload/story.jpg",
            media_type="image",
            target_account_ids=[fb_acc.id, ig_acc.id],
            status=StoryStatus.DRAFT.value
        )
        db_session.add(story)
        db_session.commit()
        db_session.refresh(story)

        mock_fb_res = {
            "id": "1698866234536797",
            "status": "published",
            "url": "https://www.facebook.com/stories/916776691089067/1698866234536797/",
            "page_url": "https://www.facebook.com/916776691089067"
        }
        mock_ig_res = {
            "id": "18021105707861393",
            "container_id": "container_123",
            "status": "published",
            "url": "https://www.instagram.com/stories/brand_official/",
            "username": "brand_official"
        }
        with patch.object(story_service, "publish_facebook_story", return_value=mock_fb_res), \
             patch.object(story_service, "publish_instagram_story", return_value=mock_ig_res):

            updated = story_service.publish_story(db_session, story.id, user.id)
            assert updated.status == StoryStatus.PUBLISHED.value
            assert updated.fb_story_id == "1698866234536797"
            assert updated.fb_story_url == "https://www.facebook.com/stories/916776691089067/1698866234536797/"
            assert updated.ig_story_id == "18021105707861393"
            assert updated.ig_story_url == "https://www.instagram.com/stories/brand_official/"

        res = client.get("/api/v1/posts/scheduler-feed", headers=headers)
        assert res.status_code == 200
        items = res.json()
        story_item = next(i for i in items if i["id"] == story.id and i["item_type"].lower() == "story")

        assert story_item["fb_id"] == "1698866234536797"
        assert story_item["fb_url"] == "https://www.facebook.com/stories/916776691089067/1698866234536797/"
        assert story_item["ig_id"] == "18021105707861393"
        assert story_item["ig_url"] == "https://www.instagram.com/stories/brand_official/"

    def test_story_delete_only_calls_published_platforms(self, db_session):
        """When deleting a story with only Facebook published, no Instagram delete call is made."""
        user, brand, fb_acc, ig_acc = setup_story_test_env(db_session, "del_partial@test.com")
        story = Story(
            user_id=user.id,
            brand_id=brand.id,
            title="FB Only Story",
            media_url="https://res.cloudinary.com/demo/image/upload/story.jpg",
            media_type="image",
            target_account_ids=[fb_acc.id, ig_acc.id],
            status=StoryStatus.PUBLISHED.value,
            published_at=datetime.now(timezone.utc),
            fb_story_id="1698866234536797",
            fb_story_url="https://www.facebook.com/stories/916776691089067/1698866234536797/",
            ig_story_id=None,  # Not published to IG
            ig_story_url=None
        )
        db_session.add(story)
        db_session.commit()
        db_session.refresh(story)

        called_deletions = []

        def mock_fb_delete(post_id, token):
            called_deletions.append(("facebook", post_id))
            return True

        def mock_ig_delete(media_id, token):
            called_deletions.append(("instagram", media_id))
            return True

        with patch.object(meta_service, "delete_facebook_post", side_effect=mock_fb_delete), \
             patch.object(meta_service, "delete_instagram_media", side_effect=mock_ig_delete):
            res = story_service.delete_story(db_session, story.id, user.id)
            assert res["success"] is True
            # Verified only FB was called, zero IG delete calls
            assert len(called_deletions) == 1
            assert called_deletions[0] == ("facebook", "1698866234536797")

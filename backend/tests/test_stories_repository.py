import pytest
from datetime import datetime, timezone, timedelta
from app.models.story import Story, StoryStatus
from app.models.user import User
from app.models.brand import BrandProfile
from app.repositories.story_repository import story_repo
from app.core.security import get_password_hash


def create_test_user_and_brand(db_session, email="story_repo_user@test.com"):
    user = User(
        email=email,
        hashed_password=get_password_hash("Secret123!"),
        full_name="Story Repo User",
        role="Admin"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    brand = BrandProfile(
        user_id=user.id,
        name="Story Test Brand"
    )
    db_session.add(brand)
    db_session.commit()
    db_session.refresh(brand)
    return user, brand


def test_story_repository_crud(db_session):
    user, brand = create_test_user_and_brand(db_session, "crud_user@test.com")

    # Create
    story = Story(
        brand_id=brand.id,
        user_id=user.id,
        title="Summer Promo Story",
        caption="Check out our summer discounts!",
        media_url="https://res.cloudinary.com/demo/image/upload/sample.jpg",
        media_type="image",
        target_account_ids=[101, 102],
        platforms=["instagram", "facebook"],
        status=StoryStatus.DRAFT.value
    )
    created = story_repo.create(db_session, story)
    assert created.id is not None
    assert created.title == "Summer Promo Story"
    assert created.target_account_ids == [101, 102]
    assert created.status == StoryStatus.DRAFT.value

    # Get by ID
    fetched = story_repo.get(db_session, created.id)
    assert fetched is not None
    assert fetched.id == created.id

    # Get by User
    user_stories = story_repo.get_by_user(db_session, user.id)
    assert len(user_stories) == 1

    # Get by Brand
    brand_stories = story_repo.get_by_brand(db_session, brand.id)
    assert len(brand_stories) == 1

    # Update
    updated = story_repo.update(db_session, fetched, {"title": "Updated Summer Promo"})
    assert updated.title == "Updated Summer Promo"

    # Delete
    deleted = story_repo.delete(db_session, created.id)
    assert deleted is not None
    assert story_repo.get(db_session, created.id) is None


def test_story_repository_due_and_retryable(db_session):
    user, brand = create_test_user_and_brand(db_session, "scheduler_user@test.com")
    now = datetime.now(timezone.utc)

    # 1. Past scheduled story (due)
    past_due_story = Story(
        brand_id=brand.id,
        user_id=user.id,
        title="Past Due Story",
        media_url="https://res.cloudinary.com/demo/image/upload/sample.jpg",
        media_type="image",
        platforms=["instagram"],
        status=StoryStatus.SCHEDULED.value,
        scheduled_at=now - timedelta(minutes=10)
    )
    # 2. Future scheduled story (not due)
    future_story = Story(
        brand_id=brand.id,
        user_id=user.id,
        title="Future Story",
        media_url="https://res.cloudinary.com/demo/image/upload/sample.jpg",
        media_type="image",
        platforms=["instagram"],
        status=StoryStatus.SCHEDULED.value,
        scheduled_at=now + timedelta(hours=2)
    )
    # 3. Failed retryable story
    failed_story = Story(
        brand_id=brand.id,
        user_id=user.id,
        title="Failed Story",
        media_url="https://res.cloudinary.com/demo/image/upload/sample.jpg",
        media_type="image",
        platforms=["facebook"],
        status=StoryStatus.FAILED.value,
        retry_count=1,
        max_retries=3
    )
    # 4. Max retries exhausted
    exhausted_story = Story(
        brand_id=brand.id,
        user_id=user.id,
        title="Exhausted Story",
        media_url="https://res.cloudinary.com/demo/image/upload/sample.jpg",
        media_type="image",
        platforms=["facebook"],
        status=StoryStatus.FAILED.value,
        retry_count=3,
        max_retries=3
    )

    db_session.add_all([past_due_story, future_story, failed_story, exhausted_story])
    db_session.commit()

    due = story_repo.get_due_scheduled_stories(db_session, now)
    assert len(due) == 1
    assert due[0].title == "Past Due Story"

    retryable = story_repo.get_failed_retryable_stories(db_session)
    assert len(retryable) == 1
    assert retryable[0].title == "Failed Story"

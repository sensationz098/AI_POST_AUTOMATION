import pytest
from app.core.story_url_helper import (
    sanitize_instagram_username,
    build_instagram_story_url,
    build_facebook_story_url,
    is_valid_instagram_story_url,
    is_valid_facebook_story_url,
    resolve_instagram_username_from_social_account,
)
from app.models.social_account import SocialAccount


class TestStoryUrlHelper:
    def test_sanitize_instagram_username(self):
        assert sanitize_instagram_username("@sensationz") == "sensationz"
        assert sanitize_instagram_username("  @my.brand_official  ") == "my.brand_official"
        assert sanitize_instagram_username("ValidUser123") == "ValidUser123"
        assert sanitize_instagram_username("") is None
        assert sanitize_instagram_username("   ") is None
        assert sanitize_instagram_username("invalid username with spaces") is None
        assert sanitize_instagram_username("bad!name?") is None
        assert sanitize_instagram_username("a" * 31) is None  # max 30 chars
        assert sanitize_instagram_username("a" * 30) == "a" * 30

    def test_build_instagram_story_url(self):
        assert build_instagram_story_url("sensationz") == "https://www.instagram.com/stories/sensationz/"
        assert build_instagram_story_url("@sensationz") == "https://www.instagram.com/stories/sensationz/"
        assert build_instagram_story_url("") is None
        assert build_instagram_story_url(None) is None
        assert build_instagram_story_url("invalid bad name") is None

    def test_is_valid_instagram_story_url(self):
        # Valid URLs
        assert is_valid_instagram_story_url("https://www.instagram.com/stories/sensationz/") is True
        assert is_valid_instagram_story_url("https://www.instagram.com/stories/sensationz") is True
        assert is_valid_instagram_story_url("https://instagram.com/stories/brand.official/") is True
        assert is_valid_instagram_story_url("https://www.instagram.com/stories/user_name_123/123456789/") is True
        assert is_valid_instagram_story_url("https://www.instagram.com/stories/highlights/123456789/") is True

        # Invalid URLs that previously caused bugs
        assert is_valid_instagram_story_url("https://www.instagram.com/stories/") is False
        assert is_valid_instagram_story_url("https://www.instagram.com/stories") is False
        assert is_valid_instagram_story_url("https://instagram.com/stories/") is False
        assert is_valid_instagram_story_url(None) is False
        assert is_valid_instagram_story_url("") is False
        assert is_valid_instagram_story_url("https://example.com/stories/user") is False

    def test_build_facebook_story_url(self):
        assert build_facebook_story_url("916776691089067", "1698866234536797") == "https://www.facebook.com/stories/916776691089067/1698866234536797/"
        assert build_facebook_story_url("123", "456") == "https://www.facebook.com/stories/123/456/"
        assert build_facebook_story_url(None, "123") is None
        assert build_facebook_story_url("123", None) is None
        assert build_facebook_story_url("invalid", "123") is None
        assert build_facebook_story_url("123", "invalid") is None

    def test_is_valid_facebook_story_url(self):
        # Valid URLs
        assert is_valid_facebook_story_url("https://www.facebook.com/stories/916776691089067/123456789/") is True
        assert is_valid_facebook_story_url("https://www.facebook.com/permalink.php?story_fbid=123&id=456") is True
        assert is_valid_facebook_story_url("https://facebook.com/stories/916776691089067/123456789") is True

        # Invalid fake Page-ID Story URLs that previously caused bugs
        assert is_valid_facebook_story_url("https://www.facebook.com/916776691089067") is False
        assert is_valid_facebook_story_url("https://facebook.com/123456789") is False
        assert is_valid_facebook_story_url("https://www.facebook.com/916776691089067/") is False
        assert is_valid_facebook_story_url("https://facebook.com/stories/123456") is False  # bare single ID without page/story pair
        assert is_valid_facebook_story_url(None) is False
        assert is_valid_facebook_story_url("") is False
        assert is_valid_facebook_story_url("https://example.com/story/123") is False

    def test_resolve_instagram_username_from_social_account(self):
        # 1. From metadata_json["username"]
        acc1 = SocialAccount(
            account_name="My Display Name",
            metadata_json={"username": "meta_username_clean"}
        )
        assert resolve_instagram_username_from_social_account(acc1) == "meta_username_clean"

        # 2. From metadata_json["username"] with leading @
        acc2 = SocialAccount(
            account_name="My Display Name",
            metadata_json={"username": "@meta_username_at"}
        )
        assert resolve_instagram_username_from_social_account(acc2) == "meta_username_at"

        # 3. From account_name when metadata username is missing
        acc3 = SocialAccount(
            account_name="@account_name_handle",
            metadata_json={}
        )
        assert resolve_instagram_username_from_social_account(acc3) == "account_name_handle"

        # 4. Fallback fails if invalid characters in account_name and no metadata username
        acc4 = SocialAccount(
            account_name="Invalid Name With Spaces",
            metadata_json={}
        )
        assert resolve_instagram_username_from_social_account(acc4) is None

        # 5. None account
        assert resolve_instagram_username_from_social_account(None) is None

import re
import logging
from typing import Optional, Tuple, Any

logger = logging.getLogger(__name__)


def sanitize_instagram_username(raw_username: Optional[str]) -> Optional[str]:
    """
    Extract a valid, sanitized Instagram username.
    - Strips whitespace and leading '@'.
    - Validates against Instagram username rules: 1-30 chars, alphanumeric, dots, underscores.
    - Rejects placeholders like 'stories', 'undefined', empty strings, or bare numbers if invalid.
    """
    if not raw_username or not isinstance(raw_username, str):
        return None
    cleaned = raw_username.strip().lstrip("@").strip()
    if not cleaned:
        return None
    # Rejects obvious non-usernames or placeholders
    if cleaned.lower() in [
        "stories", "story", "undefined", "null", "none", "n/a", "unknown", "instagram", "ig"
    ]:
        return None
    # Instagram username format: 1-30 characters of letters, numbers, periods, and underscores
    if re.match(r"^[a-zA-Z0-9._]{1,30}$", cleaned):
        return cleaned
    return None


def build_instagram_story_url(username: Optional[str]) -> Optional[str]:
    """
    Constructs a valid Instagram story URL for a username.
    Returns None if username is invalid or empty.
    NEVER returns 'https://www.instagram.com/stories/' without a username.
    """
    clean_user = sanitize_instagram_username(username)
    if not clean_user:
        return None
    return f"https://www.instagram.com/stories/{clean_user}/"


def is_valid_instagram_story_url(url: Optional[str]) -> bool:
    """
    Validates that a URL is a legitimate Instagram Story or media destination.
    Rejects https://www.instagram.com/stories/ with no username.
    """
    if not url or not isinstance(url, str):
        return False
    trimmed = url.strip()
    # Check invalid bare roots or bare /stories/
    invalid_patterns = [
        r"^https?://(www\.)?instagram\.com/?$",
        r"^https?://(www\.)?instagram\.com/stories/?$",
        r"^https?://(www\.)?instagram\.com/stories//$",
    ]
    for pattern in invalid_patterns:
        if re.match(pattern, trimmed, re.IGNORECASE):
            return False

    # Valid pattern: /stories/<username>/ (where username is a valid IG handle) or /stories/<username>/<media_id>/
    story_match = re.match(
        r"^https?://(www\.)?instagram\.com/stories/([a-zA-Z0-9._]{1,30})(?:/\d+)?/?(\?.*)?$",
        trimmed,
        re.IGNORECASE
    )
    if story_match:
        user_segment = story_match.group(2)
        if user_segment.lower() in ["stories", "story", "undefined", "null", "none", "n/a", "unknown"]:
            return False
        return True

    # Also accept highlights: /stories/highlights/...
    highlights_match = re.match(
        r"^https?://(www\.)?instagram\.com/stories/highlights/\d+/?(\?.*)?$",
        trimmed,
        re.IGNORECASE
    )
    if highlights_match:
        return True

    # Also accept permanent IG media URLs (e.g. /p/..., /reel/...)
    media_match = re.match(
        r"^https?://(www\.)?instagram\.com/(p|reel|tv)/[a-zA-Z0-9_-]+/?(\?.*)?$",
        trimmed,
        re.IGNORECASE
    )
    return bool(media_match)


def is_valid_facebook_story_url(url: Optional[str]) -> bool:
    """
    Validates that a URL is a legitimate Facebook Story or permalink.
    Rejects bare numeric ID URLs like https://www.facebook.com/123456789 or https://www.facebook.com/stories/123456789
    unless it is a legitimate permalink structure.
    """
    if not url or not isinstance(url, str):
        return False
    trimmed = url.strip()
    # Reject bare root, bare /stories/, bare numeric post/page IDs
    invalid_patterns = [
        r"^https?://(www\.)?facebook\.com/?$",
        r"^https?://(www\.)?facebook\.com/stories/?$",
        r"^https?://(www\.)?facebook\.com/stories/\d+/?$",  # Bare numeric ID in /stories/ fails in browser
        r"^https?://(www\.)?facebook\.com/\d+/?$",  # Bare numeric ID (e.g. https://www.facebook.com/916776691089067)
    ]
    for pattern in invalid_patterns:
        if re.match(pattern, trimmed, re.IGNORECASE):
            return False

    # Must be on facebook.com or fb.watch domain
    if not (
        trimmed.startswith("https://www.facebook.com/")
        or trimmed.startswith("https://facebook.com/")
        or trimmed.startswith("https://fb.watch/")
    ):
        return False

    return True


def resolve_instagram_username_from_social_account(account: Any) -> Optional[str]:
    """
    Safely extract and sanitize an Instagram username from a SocialAccount instance or dictionary.
    """
    if not account:
        return None

    meta = getattr(account, "metadata_json", None)
    if not isinstance(meta, dict) and isinstance(account, dict):
        meta = account.get("metadata_json") or account.get("metadata")

    if isinstance(meta, dict):
        # 1. Direct 'username' key
        u = meta.get("username")
        sanitized = sanitize_instagram_username(u)
        if sanitized and not sanitized.startswith("ig_"):
            return sanitized

        # 2. In metadata 'account_name' if present
        u2 = meta.get("account_name")
        sanitized2 = sanitize_instagram_username(u2)
        if sanitized2 and not sanitized2.startswith("ig_"):
            return sanitized2

    # 3. SocialAccount.account_name
    acc_name = getattr(account, "account_name", None)
    if not acc_name and isinstance(account, dict):
        acc_name = account.get("account_name")
    sanitized_acc = sanitize_instagram_username(acc_name)
    if sanitized_acc:
        return sanitized_acc

    # 4. Fallback to synthetic username in meta if nothing else
    if isinstance(meta, dict):
        u_fallback = meta.get("username")
        sanitized_fallback = sanitize_instagram_username(u_fallback)
        if sanitized_fallback:
            return sanitized_fallback

    return None

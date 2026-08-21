import logging
from typing import Optional
from app.services.cloudinary_service import upload_media_to_cloudinary

logger = logging.getLogger(__name__)

def resolve_media_type(
    explicit_media_type: Optional[str] = None,
    stored_media_type: Optional[str] = None,
    media_url: Optional[str] = None
) -> tuple[str, bool]:
    """
    Safely resolve media type into ('image' | 'video', is_video: bool).
    Preference order:
    1. Explicit passed media_type (from request payload or method argument)
    2. Stored post.media_type (from database model)
    3. Legacy URL inference as a final fallback
    """
    if explicit_media_type and str(explicit_media_type).strip():
        norm = str(explicit_media_type).strip().lower()
        if norm in ["video", "reels", "reel"]:
            return "video", True
        elif norm in ["image", "photo", "picture"]:
            return "image", False

    if stored_media_type and str(stored_media_type).strip():
        norm = str(stored_media_type).strip().lower()
        if norm in ["video", "reels", "reel"]:
            return "video", True
        elif norm in ["image", "photo", "picture"]:
            return "image", False

    url_lower = (media_url or "").lower()
    is_video_inferred = bool(
        url_lower.startswith("data:video") or
        "video" in url_lower or
        any(ext in url_lower for ext in [".mp4", ".mov", ".webm", ".m4v"])
    )
    if is_video_inferred:
        return "video", True
    return "image", False


def upload_base64_to_public_https(
    base64_str: str,
    media_type: Optional[str] = None
) -> Optional[str]:
    """Upload image or video media to Cloudinary HTTPS CDN for Meta Facebook & Instagram Graph API."""
    return upload_media_to_cloudinary(base64_str, media_type=media_type)

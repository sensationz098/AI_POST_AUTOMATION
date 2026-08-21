import base64
import io
import logging
from typing import Optional
from PIL import Image
import cloudinary
import cloudinary.uploader
from app.core.config import settings

logger = logging.getLogger(__name__)

def is_cloudinary_configured() -> bool:
    return bool(
        settings.CLOUDINARY_CLOUD_NAME and
        settings.CLOUDINARY_API_KEY and
        settings.CLOUDINARY_API_SECRET and
        not settings.CLOUDINARY_CLOUD_NAME.startswith("your-")
    )

def _init_cloudinary():
    if is_cloudinary_configured():
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True
        )

def upload_media_to_cloudinary(
    media_str_or_bytes: str,
    filename_prefix: str = "post_media",
    media_type: Optional[str] = None
) -> Optional[str]:
    """
    Upload media (photo or video) to Cloudinary and return a public HTTPS CDN URL.
    Supports base64 data URIs, raw bytes, or public HTTP URLs.
    """
    if not media_str_or_bytes:
        return None

    # If already a public HTTPS URL from Cloudinary or another trusted domain
    if isinstance(media_str_or_bytes, str) and (media_str_or_bytes.startswith("https://res.cloudinary.com/") or media_str_or_bytes.startswith("https://images.unsplash.com/")):
        return media_str_or_bytes

    if not is_cloudinary_configured():
        logger.warning("Cloudinary is not configured. Falling back to input URL if HTTP/HTTPS.")
        if isinstance(media_str_or_bytes, str) and (media_str_or_bytes.startswith("http://") or media_str_or_bytes.startswith("https://")):
            return media_str_or_bytes
        return None

    try:
        _init_cloudinary()

        # Parse base64 header if present
        header = ""
        encoded_data = media_str_or_bytes
        if isinstance(media_str_or_bytes, str) and "," in media_str_or_bytes:
            header, encoded_data = media_str_or_bytes.split(",", 1)

        is_video = (
            (media_type and media_type.lower() == "video") or
            "video" in header.lower() or
            any(ext in str(media_str_or_bytes).lower() for ext in [".mp4", ".mov", ".webm", ".m4v"])
        )
        resource_type = "video" if is_video else "image"


        if isinstance(encoded_data, str) and (encoded_data.startswith("http://") or encoded_data.startswith("https://")):
            res = cloudinary.uploader.upload(
                encoded_data,
                folder="social_ai_automation",
                resource_type=resource_type
            )
        else:
            raw_bytes = base64.b64decode(encoded_data) if isinstance(encoded_data, str) else encoded_data

            # File size sanity checks (max 10MB images, max 100MB videos)
            max_bytes = 100 * 1024 * 1024 if is_video else 10 * 1024 * 1024
            if len(raw_bytes) > max_bytes:
                logger.error(f"Media file size ({len(raw_bytes)} bytes) exceeds max limit ({max_bytes} bytes).")
                return None

            file_obj = io.BytesIO(raw_bytes)
            res = cloudinary.uploader.upload(
                file_obj,
                folder="social_ai_automation",
                resource_type=resource_type
            )

        secure_url = res.get("secure_url") or res.get("url")
        if secure_url:
            logger.info(f"Successfully uploaded media to Cloudinary CDN: {secure_url}")
            return secure_url
    except Exception as e:
        logger.error(f"Failed to upload media to Cloudinary: {e}")

    return None

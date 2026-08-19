import base64
import io
import logging
from typing import Optional
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

def upload_media_to_cloudinary(media_str_or_bytes: str, filename_prefix: str = "post_media") -> Optional[str]:
    """
    Upload media (photo or video) to Cloudinary and return a public HTTPS CDN URL.
    Supports base64 data URIs, raw bytes, or public HTTP URLs.
    """
    if not media_str_or_bytes or not isinstance(media_str_or_bytes, str):
        return None

    logger.info(f"Received image value prefix: {str(media_str_or_bytes)[:100]}")

    # CASE 3: Public HTTP/HTTPS URL (Do not attempt base64 decoding)
    if media_str_or_bytes.startswith("http://") or media_str_or_bytes.startswith("https://"):
        if media_str_or_bytes.startswith("https://res.cloudinary.com/") or media_str_or_bytes.startswith("https://images.unsplash.com/"):
            return media_str_or_bytes

        if not is_cloudinary_configured():
            return media_str_or_bytes

        try:
            _init_cloudinary()
            is_video = any(ext in media_str_or_bytes.lower() for ext in [".mp4", ".mov", ".webm", ".m4v"])
            res = cloudinary.uploader.upload(
                media_str_or_bytes,
                folder="social_ai_automation",
                resource_type="video" if is_video else "image"
            )
            secure_url = res.get("secure_url") or res.get("url")
            if secure_url:
                logger.info(f"Uploaded public URL media to Cloudinary CDN: {secure_url}")
                return secure_url
        except Exception as e:
            logger.error(f"Failed to upload public URL to Cloudinary: {e}")
            return media_str_or_bytes

    # CASE 4: Reject blob: URLs as invalid for server-side decoding
    if media_str_or_bytes.startswith("blob:"):
        logger.error(f"Cannot decode browser local blob URL on backend: {media_str_or_bytes[:100]}")
        return None

    # CASE 2: Base64 Data URI or raw base64 string
    try:
        header = ""
        encoded_data = media_str_or_bytes.strip()

        if "," in encoded_data:
            header, encoded_data = encoded_data.split(",", 1)

        # Remove whitespace & linebreaks
        encoded_data = "".join(encoded_data.split())

        # Ensure base64 length padding is a multiple of 4
        missing_padding = len(encoded_data) % 4
        if missing_padding:
            encoded_data += "=" * (4 - missing_padding)

        try:
            raw_bytes = base64.b64decode(encoded_data, validate=True)
        except Exception as b64_err:
            logger.error(f"Invalid base64-encoded string: {b64_err}")
            return None

        is_video = "video" in header.lower() or any(ext in str(media_str_or_bytes[:50]).lower() for ext in [".mp4", ".mov", ".webm", ".m4v"])
        resource_type = "video" if is_video else "image"

        if not is_cloudinary_configured():
            logger.warning("Cloudinary is not configured. Base64 media cannot be converted to public CDN URL.")
            return None

        _init_cloudinary()
        file_obj = io.BytesIO(raw_bytes)
        res = cloudinary.uploader.upload(
            file_obj,
            folder="social_ai_automation",
            resource_type=resource_type
        )

        secure_url = res.get("secure_url") or res.get("url")
        if secure_url:
            logger.info(f"Successfully uploaded base64 media to Cloudinary CDN: {secure_url}")
            return secure_url
    except Exception as e:
        logger.error(f"Failed to upload base64 media to Cloudinary: {e}")

    return None

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
    media_input: Any,
    filename_prefix: str = "post_media",
    media_type: Optional[str] = None
) -> Optional[str]:
    """
    Upload media (photo or video) to Cloudinary and return a public HTTPS CDN URL.
    Supports file streams (UploadFile.file), raw bytes, base64 data URIs, or public HTTP URLs.
    """
    if not media_input:
        return None

    # If already a public HTTPS URL from Cloudinary or another trusted domain
    if isinstance(media_input, str) and (media_input.startswith("https://res.cloudinary.com/") or media_input.startswith("https://images.unsplash.com/")):
        return media_input

    if not is_cloudinary_configured():
        logger.warning("Cloudinary is not configured. Falling back to input URL if HTTP/HTTPS.")
        if isinstance(media_input, str) and (media_input.startswith("http://") or media_input.startswith("https://")):
            return media_input
        return None

    try:
        _init_cloudinary()

        is_video = (
            (media_type and media_type.lower() == "video") or
            (isinstance(media_input, str) and ("video" in media_input.lower() or any(ext in media_input.lower() for ext in [".mp4", ".mov", ".webm", ".m4v"])))
        )
        resource_type = "video" if is_video else "image"
        max_bytes = settings.MAX_VIDEO_UPLOAD_BYTES if is_video else settings.MAX_IMAGE_UPLOAD_BYTES

        # Case A: Public HTTP / HTTPS URL string
        if isinstance(media_input, str) and (media_input.startswith("http://") or media_input.startswith("https://")):
            res = cloudinary.uploader.upload(
                media_input,
                folder="social_ai_automation",
                resource_type=resource_type
            )

        # Case B: File-like stream object (e.g. FastAPI UploadFile.file / SpooledTemporaryFile)
        elif hasattr(media_input, "read") or hasattr(media_input, "seek"):
            if hasattr(media_input, "seek"):
                try:
                    media_input.seek(0)
                except Exception:
                    pass

            res = cloudinary.uploader.upload(
                media_input,
                folder="social_ai_automation",
                resource_type=resource_type
            )

        # Case C: Base64 string or raw bytes
        else:
            header = ""
            encoded_data = media_input
            if isinstance(media_input, str) and "," in media_input:
                header, encoded_data = media_input.split(",", 1)

            raw_bytes = base64.b64decode(encoded_data) if isinstance(encoded_data, str) else encoded_data

            if len(raw_bytes) > max_bytes:
                max_mb = max_bytes / (1024 * 1024)
                logger.error(f"Media file size ({len(raw_bytes)} bytes) exceeds max limit ({max_mb:.0f} MB).")
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
        logger.error(f"Failed to upload media to Cloudinary: {e}", exc_info=True)

    return None

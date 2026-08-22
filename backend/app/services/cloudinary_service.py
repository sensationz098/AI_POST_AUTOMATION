import base64
import io
import os
import time
import logging
from typing import Optional, Any, Union
from PIL import Image
import cloudinary
import cloudinary.uploader
from app.core.config import settings

logger = logging.getLogger(__name__)

CHUNK_SIZE_BYTES = 6 * 1024 * 1024  # 6 MB per chunk for upload_large
CHUNK_UPLOAD_THRESHOLD_BYTES = 100 * 1024 * 1024  # 100 MB threshold for chunked upload


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
    Uses chunked upload_large() for video files > 100 MB.
    """
    if not media_input:
        return None

    # If already a public HTTPS URL from Cloudinary or another trusted domain
    if isinstance(media_input, str) and (
        media_input.startswith("https://res.cloudinary.com/") or
        media_input.startswith("https://images.unsplash.com/")
    ):
        return media_input

    if not is_cloudinary_configured():
        logger.warning("Cloudinary is not configured. Falling back to input URL if HTTP/HTTPS.")
        if isinstance(media_input, str) and (media_input.startswith("http://") or media_input.startswith("https://")):
            return media_input
        return None

    try:
        _init_cloudinary()
        start_time = time.time()

        is_video = (
            (media_type and media_type.lower() == "video") or
            (isinstance(media_input, str) and ("video" in media_input.lower() or any(ext in media_input.lower() for ext in [".mp4", ".mov", ".webm", ".m4v"])))
        )
        resource_type = "video" if is_video else "image"
        max_bytes = settings.MAX_VIDEO_UPLOAD_BYTES if is_video else settings.MAX_IMAGE_UPLOAD_BYTES

        # Case A: Public HTTP / HTTPS URL string
        if isinstance(media_input, str) and (media_input.startswith("http://") or media_input.startswith("https://")):
            logger.info(f"[UPLOAD_TRACE] CLOUDINARY_STANDARD_UPLOAD | type=URL | filename={filename_prefix} | resource_type={resource_type}")
            res = cloudinary.uploader.upload(
                media_input,
                folder="social_ai_automation",
                resource_type=resource_type
            )

        # Case B: File stream object, raw bytes, or base64
        else:
            file_size = 0
            if hasattr(media_input, "seek") and hasattr(media_input, "tell"):
                try:
                    media_input.seek(0, os.SEEK_END)
                    file_size = media_input.tell()
                    media_input.seek(0)
                except Exception:
                    file_size = 0

            target_data = media_input

            # Base64 string or raw bytes resolution
            if isinstance(media_input, str) and not (media_input.startswith("http://") or media_input.startswith("https://")):
                header = ""
                encoded_data = media_input
                if "," in media_input:
                    header, encoded_data = media_input.split(",", 1)
                raw_bytes = base64.b64decode(encoded_data)
                file_size = len(raw_bytes)
                target_data = io.BytesIO(raw_bytes)

            elif isinstance(media_input, (bytes, bytearray)):
                file_size = len(media_input)
                target_data = io.BytesIO(media_input)

            # Enforce max application limit
            if file_size > max_bytes:
                max_mb = max_bytes / (1024 * 1024)
                file_size_mb = file_size / (1024 * 1024)
                logger.error(f"[UPLOAD_TRACE] CLOUDINARY_REJECTED_SIZE | file_size={file_size_mb:.1f}MB | max_allowed={max_mb:.0f}MB")
                return None

            # Route based on file size and type (Chunked upload_large for videos > 100 MB)
            if is_video and file_size > CHUNK_UPLOAD_THRESHOLD_BYTES:
                chunk_mb = CHUNK_SIZE_BYTES / (1024 * 1024)
                file_size_mb = file_size / (1024 * 1024)
                logger.info(
                    f"[UPLOAD_TRACE] CLOUDINARY_CHUNKED_UPLOAD | filename={filename_prefix} | "
                    f"size_mb={file_size_mb:.1f}MB | chunk_size_mb={chunk_mb:.1f}MB | resource_type={resource_type}"
                )

                res = cloudinary.uploader.upload_large(
                    target_data,
                    folder="social_ai_automation",
                    resource_type=resource_type,
                    chunk_size=CHUNK_SIZE_BYTES
                )
            else:
                file_size_mb = file_size / (1024 * 1024) if file_size else 0
                logger.info(
                    f"[UPLOAD_TRACE] CLOUDINARY_STANDARD_UPLOAD | filename={filename_prefix} | "
                    f"size_mb={file_size_mb:.1f}MB | resource_type={resource_type}"
                )
                res = cloudinary.uploader.upload(
                    target_data,
                    folder="social_ai_automation",
                    resource_type=resource_type
                )

        secure_url = res.get("secure_url") or res.get("url")
        elapsed = time.time() - start_time
        if secure_url:
            logger.info(f"[UPLOAD_TRACE] CLOUDINARY_SUCCESS | secure_url={secure_url} | elapsed={elapsed:.2f}s")
            return secure_url
        else:
            logger.error(f"[UPLOAD_TRACE] CLOUDINARY_FAILURE | response={res} | elapsed={elapsed:.2f}s")
    except Exception as e:
        logger.error(f"[UPLOAD_TRACE] CLOUDINARY_ERROR | exception={e}", exc_info=True)

    return None

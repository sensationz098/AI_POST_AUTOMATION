import logging
import cloudinary
import cloudinary.uploader
from app.core.config import settings

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self):
        if settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY and settings.CLOUDINARY_API_SECRET:
            cloudinary.config(
                cloud_name=settings.CLOUDINARY_CLOUD_NAME,
                api_key=settings.CLOUDINARY_API_KEY,
                api_secret=settings.CLOUDINARY_API_SECRET,
                secure=True
            )
            self.configured = True
        else:
            self.configured = False

    def upload_image(self, file_path_or_url: str, folder: str = "social_ai_posts") -> str:
        if self.configured:
            try:
                result = cloudinary.uploader.upload(
                    file_path_or_url,
                    folder=folder,
                    resource_type="image"
                )
                return result.get("secure_url", file_path_or_url)
            except Exception as e:
                logger.error(f"Cloudinary upload failed: {e}")
                return file_path_or_url
        return file_path_or_url

storage_service = StorageService()

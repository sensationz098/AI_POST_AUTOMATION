import requests
import logging
from typing import Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class MetaGraphService:
    BASE_URL = f"https://graph.facebook.com/{settings.META_GRAPH_API_VERSION}"

    def publish_to_facebook_page(
        self, page_id: str, access_token: str, message: str, image_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Publish a post or photo post to a Facebook Page via Meta Graph API."""
        if not page_id or not access_token or page_id == "sandbox":
            logger.info("Meta Graph API: Executing Sandbox FB Publish Simulation.")
            return {"id": f"fb_mock_post_{abs(hash(message)) % 1000000}", "status": "published_sandbox"}

        try:
            url = f"{self.BASE_URL}/{page_id}/photos"
            if image_url and image_url.startswith("data:image"):
                import base64
                header, encoded = image_url.split(",", 1)
                mime_type = header.split(";")[0].split(":")[1] if ";" in header else "image/png"
                ext = mime_type.split("/")[1] if "/" in mime_type else "png"
                img_bytes = base64.b64decode(encoded)

                files = {
                    "source": (f"post_photo.{ext}", img_bytes, mime_type)
                }
                data = {
                    "caption": message,
                    "access_token": access_token
                }
                response = requests.post(url, data=data, files=files, timeout=30)
            elif image_url:
                payload = {
                    "url": image_url,
                    "caption": message,
                    "access_token": access_token
                }
                response = requests.post(url, data=payload, timeout=15)
            else:
                feed_url = f"{self.BASE_URL}/{page_id}/feed"
                payload = {
                    "message": message,
                    "access_token": access_token
                }
                response = requests.post(feed_url, data=payload, timeout=15)
            
            res_data = response.json()
            if response.status_code != 200:
                error_msg = res_data.get("error", {}).get("message", "Facebook API Error")
                raise Exception(f"Facebook Graph API Error ({response.status_code}): {error_msg}")
            
            return res_data
        except Exception as e:
            logger.error(f"Meta Service Facebook publish error: {e}")
            raise e

    def publish_to_instagram_business(
        self, ig_user_id: str, access_token: str, caption: str, image_url: str
    ) -> Dict[str, Any]:
        """
        Publish to Instagram Business Account via 2-Step Container Graph API flow:
        Step 1: Create IG Media Container (POST /{ig-user-id}/media)
        Step 2: Publish IG Media Container (POST /{ig-user-id}/media_publish)
        """
        if not ig_user_id or not access_token or ig_user_id == "sandbox":
            logger.info("Meta Graph API: Executing Sandbox IG Publish Simulation.")
            return {
                "container_id": f"ig_container_mock_{abs(hash(caption)) % 100000}",
                "id": f"ig_media_mock_{abs(hash(caption)) % 1000000}",
                "status": "published_sandbox"
            }

        try:
            # Step 1: Create Media Container
            container_url = f"{self.BASE_URL}/{ig_user_id}/media"
            container_payload = {
                "image_url": image_url,
                "caption": caption,
                "access_token": access_token
            }
            container_res = requests.post(container_url, data=container_payload, timeout=15)
            c_data = container_res.json()
            if container_res.status_code != 200:
                err = c_data.get("error", {}).get("message", "IG Container Error")
                raise Exception(f"IG Container Creation Failed: {err}")

            creation_id = c_data.get("id")

            # Step 2: Publish Media Container
            publish_url = f"{self.BASE_URL}/{ig_user_id}/media_publish"
            publish_payload = {
                "creation_id": creation_id,
                "access_token": access_token
            }
            pub_res = requests.post(publish_url, data=publish_payload, timeout=15)
            p_data = pub_res.json()
            if pub_res.status_code != 200:
                err = p_data.get("error", {}).get("message", "IG Publish Error")
                raise Exception(f"IG Media Publish Failed: {err}")

            return {
                "container_id": creation_id,
                "id": p_data.get("id"),
                "status": "published"
            }
        except Exception as e:
            logger.error(f"Meta Service Instagram publish error: {e}")
            raise e

meta_service = MetaGraphService()

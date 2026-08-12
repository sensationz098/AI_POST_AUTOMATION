import logging
import time
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.publishing_batch import BatchStatus, JobStatus, PublishingJob
from app.models.social_account import SocialAccount
from app.repositories.publishing_repository import publishing_repo
from app.repositories.social_account_repository import social_account_repo
from app.services.meta_service import meta_service
from app.services.post_service import upload_base64_to_public_https

logger = logging.getLogger(__name__)

from app.core.database import SessionLocal
from app.core.security_encryption import decrypt_token

def classify_error(err_str: str) -> tuple[str, str]:
    """Classify technical exceptions into human-readable error codes and messages."""
    err_lower = err_str.lower()
    if "token" in err_lower or "expired" in err_lower or "session" in err_lower or "oauth" in err_lower:
        return "TOKEN_EXPIRED", "Account authorization expired. Please reconnect this account."
    if "permission" in err_lower or "access" in err_lower or "denied" in err_lower:
        return "PERMISSION_ERROR", "Insufficient Page permissions. Reconnect account with required scopes."
    if "rate" in err_lower or "limit" in err_lower or "429" in err_lower:
        return "RATE_LIMIT", "Meta API rate limit reached. Retrying automatically shortly."
    if "media" in err_lower or "image" in err_lower or "video" in err_lower or "format" in err_lower:
        return "INVALID_MEDIA", "Media file format or aspect ratio is incompatible with Meta requirements."
    return "PLATFORM_ERROR", f"Meta Graph API error: {err_str[:150]}"

class FacebookPublisher:
    def publish(self, account: SocialAccount, caption: str, public_media_url: Optional[str], is_video: bool) -> str:
        final_url = public_media_url
        if final_url and (final_url.startswith("blob:") or final_url.startswith("data:")):
            final_url = "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=1080&auto=format&fit=crop&q=80"

        token = decrypt_token(account.access_token) or account.access_token
        res = meta_service.publish_to_facebook_page(
            page_id=account.account_id,
            access_token=token,
            message=caption,
            image_url=final_url,
            is_video=is_video
        )
        post_id = res.get("id")
        if not post_id:
            raise Exception(f"Facebook Graph API returned no post ID: {res}")
        return str(post_id)

class InstagramPublisher:
    def publish(self, account: SocialAccount, caption: str, public_media_url: Optional[str], is_video: bool) -> str:
        final_url = public_media_url
        if not final_url or final_url.startswith("data:") or final_url.startswith("blob:"):
            final_url = "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=1080&auto=format&fit=crop&q=80"
        
        token = decrypt_token(account.access_token) or account.access_token
        res = meta_service.publish_to_instagram_business(
            ig_user_id=account.account_id,
            access_token=token,
            caption=caption,
            image_url=final_url,
            is_video=is_video
        )
        media_id = res.get("id") or res.get("container_id")
        if not media_id:
            raise Exception(f"Instagram Graph API returned no media ID: {res}")
        return str(media_id)

class PublishingEngine:
    def __init__(self):
        self.fb_publisher = FacebookPublisher()
        self.ig_publisher = InstagramPublisher()

    def process_single_job_in_thread(
        self,
        job_id: int,
        social_account_id: int,
        caption: str,
        public_media_url: Optional[str],
        is_video: bool
    ) -> Dict[str, Any]:
        """Execute job in a dedicated thread-local database session."""
        thread_db = SessionLocal()
        try:
            acc = social_account_repo.get_by_id(thread_db, social_account_id)
            if not acc:
                publishing_repo.update_job_status(thread_db, job_id, JobStatus.FAILED.value, error_message="Social account not found.")
                return {"job_id": job_id, "status": "FAILED", "error": "Account not found"}

            publishing_repo.update_job_status(thread_db, job_id, JobStatus.PROCESSING.value)

            if acc.status == "TOKEN_EXPIRED":
                code, msg = "TOKEN_EXPIRED", "Account authorization expired. Please reconnect this account."
                publishing_repo.update_job_status(thread_db, job_id, JobStatus.FAILED.value, error_code=code, error_message=msg)
                return {"job_id": job_id, "status": "FAILED", "error": msg}

            try:
                if acc.platform == "facebook":
                    ext_id = self.fb_publisher.publish(acc, caption, public_media_url, is_video)
                elif acc.platform == "instagram":
                    ext_id = self.ig_publisher.publish(acc, caption, public_media_url, is_video)
                else:
                    raise Exception(f"Unsupported platform: {acc.platform}")

                publishing_repo.update_job_status(thread_db, job_id, JobStatus.SUCCESS.value, external_post_id=ext_id)
                return {"job_id": job_id, "status": "SUCCESS", "external_id": ext_id}
            except Exception as e:
                err_str = str(e)
                code, msg = classify_error(err_str)
                if code == "TOKEN_EXPIRED":
                    social_account_repo.mark_status(thread_db, acc.id, "TOKEN_EXPIRED")
                publishing_repo.update_job_status(thread_db, job_id, JobStatus.FAILED.value, error_code=code, error_message=msg)
                return {"job_id": job_id, "status": "FAILED", "error": msg}
        finally:
            thread_db.close()

    def process_single_job(
        self,
        db: Session,
        job_id: int,
        account: SocialAccount,
        caption: str,
        public_media_url: Optional[str],
        is_video: bool
    ) -> Dict[str, Any]:
        """Execute a single publishing job synchronously."""
        return self.process_single_job_in_thread(
            job_id=job_id,
            social_account_id=account.id,
            caption=caption,
            public_media_url=public_media_url,
            is_video=is_video
        )

    def execute_batch(
        self,
        db: Session,
        batch_id: int,
        post_caption: str,
        raw_media_url: Optional[str],
        accounts: List[SocialAccount]
    ) -> Dict[str, Any]:
        """Execute multi-account batch publishing concurrently with thread-isolated DB sessions."""
        batch = publishing_repo.get_batch(db, batch_id)
        if not batch:
            raise Exception(f"PublishingBatch ID={batch_id} not found.")

        publishing_repo.update_batch_summary(db, batch_id)

        public_media_url = raw_media_url
        if raw_media_url and (raw_media_url.startswith("data:") or raw_media_url.startswith("blob:")):
            public_media_url = upload_base64_to_public_https(raw_media_url) or raw_media_url

        raw_url_lower = (raw_media_url or "").lower()
        pub_url_lower = (public_media_url or "").lower()
        is_video = bool(
            "video" in raw_url_lower or "video" in pub_url_lower or
            any(ext in pub_url_lower for ext in [".mp4", ".mov", ".webm", ".m4v"]) or
            any(ext in raw_url_lower for ext in [".mp4", ".mov", ".webm", ".m4v"])
        )

        jobs = db.query(PublishingJob).filter(
            PublishingJob.batch_id == batch_id
        ).all()

        account_map = {acc.id: acc for acc in accounts}

        with ThreadPoolExecutor(max_workers=min(5, max(1, len(jobs)))) as executor:
            future_to_job = {}
            for job in jobs:
                acc = account_map.get(job.social_account_id)
                if acc:
                    future = executor.submit(
                        self.process_single_job_in_thread,
                        job.id, acc.id, post_caption, public_media_url, is_video
                    )
                    future_to_job[future] = job.id

            for future in as_completed(future_to_job):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Worker exception during batch publishing job: {e}")

        updated_batch = publishing_repo.update_batch_summary(db, batch_id)
        return {
            "batch_id": batch_id,
            "status": updated_batch.status,
            "total": updated_batch.total_targets,
            "successful": updated_batch.successful_targets,
            "failed": updated_batch.failed_targets
        }

publishing_engine = PublishingEngine()

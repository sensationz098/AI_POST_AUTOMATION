import logging
import time
from typing import Dict, Any, List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.publishing_batch import BatchStatus, JobStatus, PublishingJob
from app.models.social_account import SocialAccount
from app.repositories.publishing_repository import publishing_repo
from app.repositories.social_account_repository import social_account_repo
from app.services.meta_service import meta_service, MetaPublishException
from app.services.media_service import resolve_media_type, upload_base64_to_public_https
from app.core.database import SessionLocal
from app.core.security_encryption import decrypt_token
from app.core.logging_config import sanitize_url
from app.models.post import Post

logger = logging.getLogger(__name__)


def classify_error(err_str: str) -> tuple[str, str]:
    """Classify technical exceptions into human-readable error codes and messages."""
    err_lower = err_str.lower()
    if "timeout" in err_lower or "timed out" in err_lower:
        return "PUBLISH_TIMEOUT", f"Publishing process timed out: {err_str[:200]}"
    if "token" in err_lower or "expired" in err_lower or "session" in err_lower or "oauth" in err_lower:
        return "TOKEN_EXPIRED", "Account authorization expired. Please reconnect this account."
    if "permission" in err_lower or "access" in err_lower or "denied" in err_lower:
        return "PERMISSION_ERROR", "Insufficient Page permissions. Reconnect account with required scopes."
    if "rate" in err_lower or "limit" in err_lower or "429" in err_lower:
        return "RATE_LIMIT", "Meta API rate limit reached. Retrying automatically shortly."
    if "media" in err_lower or "image" in err_lower or "video" in err_lower or "format" in err_lower or "cdn" in err_lower:
        return "INVALID_MEDIA", f"Media requirements error: {err_str[:200]}"
    return "PLATFORM_ERROR", f"Meta Graph API error: {err_str[:200]}"


class FacebookPublisher:
    def publish(self, account: SocialAccount, caption: str, public_media_url: Optional[str], is_video: bool, thumbnail_url: Optional[str] = None) -> str:
        logger.info(f"[PUBLISH_TRACE] META_SERVICE_ENTERED | platform=facebook | account_id={account.account_id} | is_video={is_video} | thumbnail_url={sanitize_url(thumbnail_url)}")
        final_url = public_media_url
        if is_video:
            if not final_url or final_url.startswith("blob:") or final_url.startswith("data:") or not (final_url.startswith("http://") or final_url.startswith("https://")):
                raise Exception("Facebook video publishing failed: Media URL is invalid or could not be uploaded to a public HTTPS CDN. Video publishing requires a publicly accessible HTTPS URL.")
        else:
            if final_url and (final_url.startswith("blob:") or final_url.startswith("data:")):
                final_url = upload_base64_to_public_https(final_url) or final_url
                if final_url.startswith("blob:") or final_url.startswith("data:"):
                    from app.core.config import settings
                    if not (settings.META_MOCK_MODE and settings.APP_ENV.lower() != "production"):
                        raise Exception("Facebook photo publishing failed: Media URL could not be uploaded to a public HTTPS CDN.")
                    final_url = "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=1080&auto=format&fit=crop&q=80"

        token = decrypt_token(account.access_token) or account.access_token
        res = meta_service.publish_to_facebook_page(
            page_id=account.account_id,
            access_token=token,
            message=caption,
            image_url=final_url,
            is_video=is_video,
            thumbnail_url=thumbnail_url
        )
        post_id = res.get("id")
        if not post_id:
            raise Exception(f"Facebook Graph API returned no post ID: {res}")
        return str(post_id)


class InstagramPublisher:
    def publish(
        self,
        account: SocialAccount,
        caption: str,
        public_media_url: Optional[str],
        is_video: bool,
        thumbnail_url: Optional[str] = None,
        on_container_created: Optional[Callable[[str], None]] = None,
        existing_container_id: Optional[str] = None,
        publish_started_at: Optional[datetime] = None
    ) -> str:
        logger.info(f"[PUBLISH_TRACE] META_SERVICE_ENTERED | platform=instagram | account_id={account.account_id} | is_video={is_video} | thumbnail_url={sanitize_url(thumbnail_url)}")
        final_url = public_media_url
        if is_video:
            if not final_url or final_url.startswith("blob:") or final_url.startswith("data:") or not (final_url.startswith("http://") or final_url.startswith("https://")):
                raise Exception("Instagram video publishing failed: Media URL is invalid or could not be uploaded to a public HTTPS CDN. Video publishing requires a publicly accessible HTTPS URL.")
        else:
            if not final_url or final_url.startswith("data:") or final_url.startswith("blob:"):
                if final_url:
                    final_url = upload_base64_to_public_https(final_url) or final_url
                if not final_url or final_url.startswith("blob:") or final_url.startswith("data:"):
                    from app.core.config import settings
                    if not (settings.META_MOCK_MODE and settings.APP_ENV.lower() != "production"):
                        raise Exception("Instagram photo publishing failed: A valid public HTTPS image URL is required.")
                    final_url = "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=1080&auto=format&fit=crop&q=80"
        
        token = decrypt_token(account.access_token) or account.access_token
        res = meta_service.publish_to_instagram_business(
            ig_user_id=account.account_id,
            access_token=token,
            caption=caption,
            image_url=final_url,
            is_video=is_video,
            thumbnail_url=thumbnail_url,
            on_container_created=on_container_created,
            existing_container_id=existing_container_id,
            publish_started_at=publish_started_at
        )
        media_id = res.get("id")
        if not media_id:
            raise Exception(f"Instagram Graph API returned no published media ID (container_id={res.get('container_id')}): {res}")
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
        is_video: bool,
        batch_id: Optional[int] = None,
        resolved_media_type: Optional[str] = None,
        thumbnail_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute job in a dedicated thread-local database session."""
        start_time = time.time()
        publish_started_at = datetime.now(timezone.utc)
        logger.info(f"[PUBLISH_TRACE] THREAD_JOB_STARTED | batch_id={batch_id} | job_id={job_id} | social_account_id={social_account_id}")
        thread_db = SessionLocal()
        try:
            acc = social_account_repo.get_by_id(thread_db, social_account_id)
            if not acc:
                publishing_repo.update_job_status(thread_db, job_id, JobStatus.FAILED.value, error_message="Social account not found.")
                logger.error(f"[PUBLISH_TRACE] PUBLISH_JOB_FAILED | batch_id={batch_id} | job_id={job_id} | platform=unknown | error_code=ACCOUNT_NOT_FOUND | error_class=Exception | error=Social account not found | elapsed={round(time.time() - start_time, 2)}s")
                return {"job_id": job_id, "status": "FAILED", "error": "Account not found"}

            publishing_repo.update_job_status(thread_db, job_id, JobStatus.PROCESSING.value)

            logger.info(
                f"[PUBLISH_TRACE] PUBLISH_JOB_STARTED | batch_id={batch_id} | job_id={job_id} | "
                f"social_account_id={social_account_id} | platform={acc.platform} | "
                f"resolved_media_type={resolved_media_type or ('video' if is_video else 'image')} | is_video={is_video} | "
                f"media_url={sanitize_url(public_media_url)}"
            )

            if acc.status == "TOKEN_EXPIRED":
                code, msg = "TOKEN_EXPIRED", "Account authorization expired. Please reconnect this account."
                publishing_repo.update_job_status(thread_db, job_id, JobStatus.FAILED.value, error_code=code, error_message=msg)
                logger.error(f"[PUBLISH_TRACE] PUBLISH_JOB_FAILED | batch_id={batch_id} | job_id={job_id} | platform={acc.platform} | error_code={code} | error_class=Exception | error={msg} | elapsed={round(time.time() - start_time, 2)}s")
                return {"job_id": job_id, "status": "FAILED", "error": msg}

            job = thread_db.query(PublishingJob).filter(PublishingJob.id == job_id).first()
            existing_c_id = job.ig_container_id if job else None

            def container_created_callback(c_id: str):
                publishing_repo.update_job_container_id(thread_db, job_id, c_id)

            try:
                if acc.platform == "facebook":
                    ext_id = self.fb_publisher.publish(acc, caption, public_media_url, is_video, thumbnail_url=thumbnail_url)
                elif acc.platform == "instagram":
                    ext_id = self.ig_publisher.publish(
                        acc,
                        caption,
                        public_media_url,
                        is_video,
                        thumbnail_url=thumbnail_url,
                        on_container_created=container_created_callback,
                        existing_container_id=existing_c_id,
                        publish_started_at=publish_started_at
                    )
                else:
                    raise Exception(f"Unsupported platform: {acc.platform}")

                publishing_repo.update_job_status(thread_db, job_id, JobStatus.SUCCESS.value, external_post_id=ext_id)
                elapsed = round(time.time() - start_time, 2)
                logger.info(f"[PUBLISH_TRACE] PUBLISH_JOB_SUCCESS | batch_id={batch_id} | job_id={job_id} | platform={acc.platform} | external_id={ext_id} | elapsed={elapsed}s")
                return {"job_id": job_id, "status": "SUCCESS", "external_id": ext_id}
            except Exception as e:
                err_str = str(e)
                code, msg = classify_error(err_str)
                if not isinstance(e, MetaPublishException) and (code in ["PUBLISH_FAILED", "PLATFORM_ERROR"] or not code):
                    code = "UNEXPECTED_PUBLISH_ERROR"
                    msg = f"Unexpected worker error: {err_str}"
                if code == "TOKEN_EXPIRED":
                    social_account_repo.mark_status(thread_db, acc.id, "TOKEN_EXPIRED")

                meta_status = getattr(e, "status_code", None)
                meta_code = getattr(e, "error_code", None)
                meta_subcode = getattr(e, "error_subcode", None)
                meta_msg = getattr(e, "error_message", None)

                publishing_repo.update_job_status(
                    thread_db,
                    job_id,
                    JobStatus.FAILED.value,
                    error_code=code,
                    error_message=msg,
                    meta_status_code=meta_status,
                    meta_error_code=meta_code,
                    meta_error_subcode=meta_subcode,
                    meta_error_message=meta_msg
                )
                elapsed = round(time.time() - start_time, 2)
                logger.error(f"[PUBLISH_TRACE] PUBLISH_JOB_FAILED | batch_id={batch_id} | job_id={job_id} | platform={acc.platform} | error_code={code} | meta_status={meta_status} | error_class={e.__class__.__name__} | error={msg} | elapsed={elapsed}s")
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
        accounts: List[SocialAccount],
        media_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute multi-account batch publishing concurrently with thread-isolated DB sessions."""
        batch_start_time = time.time()
        batch = publishing_repo.get_batch(db, batch_id)
        if not batch:
            raise Exception(f"PublishingBatch ID={batch_id} not found.")

        publishing_repo.update_batch_summary(db, batch_id)

        public_media_url = raw_media_url
        if raw_media_url and (raw_media_url.startswith("data:") or raw_media_url.startswith("blob:")):
            public_media_url = upload_base64_to_public_https(raw_media_url) or raw_media_url

        # Retrieve stored media_type & thumbnail_url from Post model if available
        post = db.query(Post).filter(Post.id == batch.post_id).first()
        stored_type = getattr(post, "media_type", None) if post else None
        thumbnail_url = getattr(post, "thumbnail_url", None) if post else None

        resolved_media_type, is_video = resolve_media_type(
            explicit_media_type=media_type,
            stored_media_type=stored_type,
            media_url=raw_media_url or public_media_url
        )

        # Only pass thumbnail_url if it's a video
        effective_thumb_url = thumbnail_url if is_video else None

        jobs = db.query(PublishingJob).filter(
            PublishingJob.batch_id == batch_id
        ).all()

        logger.info(f"[PUBLISH_TRACE] BATCH_EXECUTION_STARTED | batch_id={batch_id} | post_id={batch.post_id} | total_jobs={len(jobs)}")
        logger.info(
            f"[PUBLISH_TRACE] MEDIA_TYPE_RESOLVED | batch_id={batch_id} | post_id={batch.post_id} | "
            f"resolved_media_type={resolved_media_type} | is_video={is_video} | media_url={sanitize_url(public_media_url)} | "
            f"thumbnail_url={sanitize_url(effective_thumb_url)}"
        )

        account_map = {acc.id: acc for acc in accounts}

        with ThreadPoolExecutor(max_workers=min(5, max(1, len(jobs)))) as executor:
            future_to_job = {}
            for job in jobs:
                acc = account_map.get(job.social_account_id)
                if acc:
                    future = executor.submit(
                        self.process_single_job_in_thread,
                        job.id, acc.id, post_caption, public_media_url, is_video,
                        batch_id, resolved_media_type, effective_thumb_url
                    )
                    future_to_job[future] = job.id

            for future in as_completed(future_to_job):
                j_id = future_to_job[future]
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"[PUBLISH_TRACE] Worker exception during batch publishing job {j_id}: {e}")
                    try:
                        publishing_repo.update_job_status(
                            db,
                            j_id,
                            JobStatus.FAILED.value,
                            error_code="UNEXPECTED_PUBLISH_ERROR",
                            error_message=f"Unexpected worker error: {str(e)}"
                        )
                    except Exception as fail_err:
                        logger.error(f"[PUBLISH_TRACE] Failed to mark job {j_id} as FAILED: {fail_err}")

        db.expire_all()
        updated_batch = publishing_repo.update_batch_summary(db, batch_id)

        batch_elapsed = round(time.time() - batch_start_time, 2)
        logger.info(
            f"[PUBLISH_TRACE] PUBLISH_BATCH_COMPLETED | batch_id={batch_id} | status={updated_batch.status} | "
            f"total={updated_batch.total_targets} | successful={updated_batch.successful_targets} | "
            f"failed={updated_batch.failed_targets} | elapsed={batch_elapsed}s"
        )
        return {
            "batch_id": batch_id,
            "status": updated_batch.status,
            "total": updated_batch.total_targets,
            "successful": updated_batch.successful_targets,
            "failed": updated_batch.failed_targets
        }

publishing_engine = PublishingEngine()


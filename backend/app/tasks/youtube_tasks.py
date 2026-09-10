import logging
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.core.config import settings
from app.repositories.youtube_upload_repository import youtube_upload_repo
from app.repositories.social_account_repository import social_account_repo
from app.services.youtube_service import youtube_service
from app.models.youtube_upload import YouTubeUploadStatus

logger = logging.getLogger(__name__)

@celery_app.task(name="app.tasks.youtube_tasks.poll_youtube_video_processing_task")
def poll_youtube_video_processing_task(upload_id: str, attempt: int = 1):
    """
    Celery background task: Poll YouTube Data API v3 videos.list
    to track video encoding and quality check processing status.
    Uses bounded exponential backoff.
    """
    db = SessionLocal()
    try:
        upload = youtube_upload_repo.get_by_upload_id(db, upload_id)
        if not upload:
            logger.warning(f"[YOUTUBE_POLL_TASK] Upload record {upload_id} not found. Terminating task.")
            return {"status": "NOT_FOUND"}

        # Stop if already in a final state or cancelled
        if upload.upload_status in (
            YouTubeUploadStatus.READY.value,
            YouTubeUploadStatus.FAILED.value,
            YouTubeUploadStatus.CANCELLED.value,
        ):
            logger.info(f"[YOUTUBE_POLL_TASK] Upload {upload_id} is in final state ({upload.upload_status}). Terminating task.")
            return {"status": upload.upload_status}

        if not upload.video_id:
            logger.warning(f"[YOUTUBE_POLL_TASK] Upload {upload_id} has no video_id yet. Stopping.")
            return {"status": "NO_VIDEO_ID"}

        # Fetch valid access token for YouTube account
        account = social_account_repo.get_by_id(db, upload.social_account_id)
        if not account:
            logger.error(f"[YOUTUBE_POLL_TASK] SocialAccount {upload.social_account_id} not found for upload {upload_id}.")
            youtube_upload_repo.mark_failed(db, upload_id, "Connected YouTube channel account not found.")
            return {"status": "ACCOUNT_NOT_FOUND"}

        try:
            access_token = youtube_service.get_valid_access_token_for_account(db, account)
        except Exception as e:
            logger.error(f"[YOUTUBE_POLL_TASK] Failed to obtain access token for upload {upload_id}: {e}")
            if attempt >= settings.YOUTUBE_PROCESSING_MAX_ATTEMPTS:
                youtube_upload_repo.mark_failed(db, upload_id, f"Authentication token resolution failed: {str(e)}")
            else:
                delay = min(settings.YOUTUBE_PROCESSING_POLL_INITIAL_SECONDS * (1.5 ** (attempt - 1)), settings.YOUTUBE_PROCESSING_POLL_MAX_SECONDS)
                poll_youtube_video_processing_task.apply_async(args=[upload_id, attempt + 1], countdown=int(delay))
            return {"status": "AUTH_ERROR", "error": str(e)}

        # Query YouTube processing status
        try:
            proc_data = youtube_service.fetch_video_processing_status(access_token, upload.video_id)
        except Exception as e:
            logger.error(f"[YOUTUBE_POLL_TASK] Error querying processing status for {upload_id} (attempt {attempt}): {e}")
            if attempt < settings.YOUTUBE_PROCESSING_MAX_ATTEMPTS:
                delay = min(settings.YOUTUBE_PROCESSING_POLL_INITIAL_SECONDS * (1.5 ** (attempt - 1)), settings.YOUTUBE_PROCESSING_POLL_MAX_SECONDS)
                poll_youtube_video_processing_task.apply_async(args=[upload_id, attempt + 1], countdown=int(delay))
            return {"status": "QUERY_ERROR", "error": str(e)}

        if proc_data.get("is_ready"):
            logger.info(f"[YOUTUBE_POLL_TASK] Video {upload.video_id} for upload {upload_id} is READY.")
            youtube_upload_repo.mark_processing_status(
                db=db,
                upload_id=upload_id,
                processing_status="succeeded",
                upload_status=YouTubeUploadStatus.READY.value,
            )
            return {"status": "READY", "video_id": upload.video_id, "processing_status": "succeeded"}

        if proc_data.get("is_failed"):
            failure_reason = proc_data.get("processing_failure_reason") or "YouTube video processing failed."
            logger.warning(f"[YOUTUBE_POLL_TASK] Video {upload.video_id} for upload {upload_id} FAILED: {failure_reason}")
            youtube_upload_repo.mark_processing_status(
                db=db,
                upload_id=upload_id,
                processing_status="failed",
                upload_status=YouTubeUploadStatus.FAILED.value,
                failure_reason=failure_reason,
            )
            return {"status": "FAILED", "reason": failure_reason}

        # Video is still processing (e.g. "processing" or "uploaded")
        current_proc_status = proc_data.get("processing_status", "processing")
        youtube_upload_repo.mark_processing_status(
            db=db,
            upload_id=upload_id,
            processing_status=current_proc_status,
            upload_status=YouTubeUploadStatus.PROCESSING.value,
        )

        if attempt < settings.YOUTUBE_PROCESSING_MAX_ATTEMPTS:
            delay = min(
                settings.YOUTUBE_PROCESSING_POLL_INITIAL_SECONDS * (1.5 ** (attempt - 1)),
                settings.YOUTUBE_PROCESSING_POLL_MAX_SECONDS
            )
            logger.info(
                f"[YOUTUBE_POLL_TASK] Video {upload.video_id} still processing ({current_proc_status}). "
                f"Scheduling attempt {attempt + 1}/{settings.YOUTUBE_PROCESSING_MAX_ATTEMPTS} in {int(delay)}s."
            )
            poll_youtube_video_processing_task.apply_async(args=[upload_id, attempt + 1], countdown=int(delay))
            return {"status": "PROCESSING", "attempt": attempt, "next_poll_seconds": int(delay)}
        else:
            logger.warning(
                f"[YOUTUBE_POLL_TASK] Upload {upload_id} reached max processing attempts ({settings.YOUTUBE_PROCESSING_MAX_ATTEMPTS}). "
                f"Leaving in PROCESSING state for manual refresh."
            )
            return {"status": "MAX_ATTEMPTS_REACHED"}
    finally:
        db.close()

poll_youtube_video_processing = poll_youtube_video_processing_task

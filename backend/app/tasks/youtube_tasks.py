import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.core.config import settings
from app.repositories.youtube_upload_repository import youtube_upload_repo
from app.repositories.social_account_repository import social_account_repo
from app.services.youtube_service import youtube_service
from app.models.youtube_upload import YouTubeUploadStatus

logger = logging.getLogger(__name__)

def check_and_update_youtube_processing_status(db: Session, upload_id: str) -> Dict[str, Any]:
    """
    Query YouTube Data API for video encoding/processing status and update database.
    Authoritative state machine transitions:
    - On processingStatus == "succeeded" -> upload_status = "READY", processing_status = "succeeded"
    - On processingStatus == "failed" / "terminated" -> upload_status = "FAILED", processing_status = "failed"
    - On processing / uploaded -> upload_status = "PROCESSING"
    """
    upload = youtube_upload_repo.get_by_upload_id(db, upload_id)
    if not upload:
        logger.warning(f"[YOUTUBE_POLL] Upload record {upload_id} not found in database.")
        return {"status": "NOT_FOUND", "upload_id": upload_id}

    # Stop if already in a final state or cancelled
    if upload.upload_status in (
        YouTubeUploadStatus.READY.value,
        YouTubeUploadStatus.FAILED.value,
        YouTubeUploadStatus.CANCELLED.value,
    ):
        logger.info(
            f"[YOUTUBE_POLL] upload_id={upload_id}, video_id={upload.video_id} is already in terminal state '{upload.upload_status}'. Skipping check."
        )
        return {"status": upload.upload_status, "upload_id": upload_id, "video_id": upload.video_id}

    if not upload.video_id:
        logger.warning(f"[YOUTUBE_POLL] upload_id={upload_id} has no video_id yet. Cannot check YouTube status.")
        return {"status": "NO_VIDEO_ID", "upload_id": upload_id}

    # Fetch valid access token for YouTube account (refreshes expired token automatically)
    account = social_account_repo.get_by_id(db, upload.social_account_id)
    if not account:
        logger.error(f"[YOUTUBE_POLL] SocialAccount {upload.social_account_id} not found for upload {upload_id}.")
        youtube_upload_repo.mark_failed(db, upload_id, "Connected YouTube channel account not found.")
        return {"status": "ACCOUNT_NOT_FOUND", "upload_id": upload_id}

    try:
        access_token = youtube_service.get_valid_access_token_for_account(db, account)
    except Exception as e:
        logger.error(f"[YOUTUBE_POLL] Auth/Token error for upload_id={upload_id}, video_id={upload.video_id}: {e}")
        return {"status": "AUTH_ERROR", "upload_id": upload_id, "video_id": upload.video_id, "error": str(e)}

    # Query YouTube processing status (videos.list part=processingDetails,status,snippet)
    try:
        proc_data = youtube_service.fetch_video_processing_status(access_token, upload.video_id)
    except Exception as e:
        logger.error(f"[YOUTUBE_POLL] YouTube API query error for upload_id={upload_id}, video_id={upload.video_id}: {e}")
        return {"status": "QUERY_ERROR", "upload_id": upload_id, "video_id": upload.video_id, "error": str(e)}

    if proc_data.get("is_ready"):
        youtube_upload_repo.mark_processing_status(
            db=db,
            upload_id=upload_id,
            processing_status="succeeded",
            upload_status=YouTubeUploadStatus.READY.value,
        )
        logger.info(
            f"[YOUTUBE_POLL] upload_id={upload_id}, video_id={upload.video_id} -> YouTube API processingStatus='succeeded', uploadStatus='{proc_data.get('upload_status')}' -> DB upload_status='READY'"
        )
        return {
            "status": "READY",
            "upload_id": upload_id,
            "video_id": upload.video_id,
            "processing_status": "succeeded",
            "video_url": f"https://www.youtube.com/watch?v={upload.video_id}",
        }

    if proc_data.get("is_failed"):
        failure_reason = proc_data.get("processing_failure_reason") or "YouTube video processing failed."
        youtube_upload_repo.mark_processing_status(
            db=db,
            upload_id=upload_id,
            processing_status="failed",
            upload_status=YouTubeUploadStatus.FAILED.value,
            failure_reason=failure_reason,
        )
        logger.warning(
            f"[YOUTUBE_POLL] upload_id={upload_id}, video_id={upload.video_id} -> YouTube API processingStatus='failed' (reason='{failure_reason}') -> DB upload_status='FAILED'"
        )
        return {
            "status": "FAILED",
            "upload_id": upload_id,
            "video_id": upload.video_id,
            "processing_status": "failed",
            "reason": failure_reason,
        }

    # Video is still processing (e.g. "processing" or "uploaded")
    current_proc_status = proc_data.get("processing_status", "processing")
    youtube_upload_repo.mark_processing_status(
        db=db,
        upload_id=upload_id,
        processing_status=current_proc_status,
        upload_status=YouTubeUploadStatus.PROCESSING.value,
    )
    logger.info(
        f"[YOUTUBE_POLL] upload_id={upload_id}, video_id={upload.video_id} -> YouTube API processingStatus='{current_proc_status}', uploadStatus='{proc_data.get('upload_status')}' -> DB remains 'PROCESSING'"
    )
    return {
        "status": "PROCESSING",
        "upload_id": upload_id,
        "video_id": upload.video_id,
        "processing_status": current_proc_status,
        "upload_status": proc_data.get("upload_status"),
    }


@celery_app.task(name="app.tasks.youtube_tasks.poll_youtube_video_processing_task")
def poll_youtube_video_processing_task(upload_id: str, attempt: int = 1):
    """
    Optional Celery background task for environments where Celery workers exist.
    Polls YouTube Data API v3 videos.list with exponential backoff.
    """
    db = SessionLocal()
    try:
        result = check_and_update_youtube_processing_status(db, upload_id)
        current_status = result.get("status")

        if current_status == "PROCESSING" or current_status == "QUERY_ERROR":
            if attempt < settings.YOUTUBE_PROCESSING_MAX_ATTEMPTS:
                delay = min(
                    settings.YOUTUBE_PROCESSING_POLL_INITIAL_SECONDS * (1.5 ** (attempt - 1)),
                    settings.YOUTUBE_PROCESSING_POLL_MAX_SECONDS
                )
                logger.info(
                    f"[YOUTUBE_POLL_TASK] Upload {upload_id} in {current_status}. "
                    f"Scheduling attempt {attempt + 1}/{settings.YOUTUBE_PROCESSING_MAX_ATTEMPTS} in {int(delay)}s."
                )
                poll_youtube_video_processing_task.apply_async(args=[upload_id, attempt + 1], countdown=int(delay))
                return {"status": "PROCESSING", "attempt": attempt, "next_poll_seconds": int(delay)}
            else:
                logger.warning(
                    f"[YOUTUBE_POLL_TASK] Upload {upload_id} reached max processing attempts ({settings.YOUTUBE_PROCESSING_MAX_ATTEMPTS}). "
                    f"Leaving in PROCESSING state for Web Service reliability poller."
                )
                return {"status": "MAX_ATTEMPTS_REACHED"}

        return result
    finally:
        db.close()


def process_pending_youtube_processing_uploads(db: Session, limit: int = 10) -> List[Dict[str, Any]]:
    """
    FastAPI Background Reliability Poller (runs directly inside the free Render Web Service):
    Directly checks YouTube Data API for all active PROCESSING uploads that have not been checked recently.
    Does NOT require a paid Celery worker or Redis instance.
    """
    pending_uploads = youtube_upload_repo.list_pending_processing(db, older_than_seconds=10, limit=limit)
    if not pending_uploads:
        return []

    results = []
    for up in pending_uploads:
        try:
            res = check_and_update_youtube_processing_status(db, up.upload_id)
            results.append({"upload_id": up.upload_id, "video_id": up.video_id, "result": res})
        except Exception as e:
            logger.warning(f"[YOUTUBE_RELIABILITY_POLLER] Failed to check processing status for upload_id={up.upload_id}: {e}")
    return results

poll_youtube_video_processing = poll_youtube_video_processing_task

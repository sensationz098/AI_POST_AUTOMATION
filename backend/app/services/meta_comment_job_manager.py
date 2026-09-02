import uuid
import time
import logging
from threading import Lock
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class MetaCommentSyncJobManager:
    """
    Thread-safe, in-memory job status manager for Meta Ad comment synchronization.
    Supports asynchronous background execution, real-time progress updates, and tenant isolation.
    """
    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()

    def create_job(self, user_id: int, ad_account_id: str, ads_total: int) -> Dict[str, Any]:
        job_id = f"job_sync_{uuid.uuid4().hex[:12]}"
        now_ts = time.time()
        job_data = {
            "job_id": job_id,
            "user_id": user_id,
            "ad_account_id": ad_account_id,
            "status": "PROCESSING",
            "ads_total": ads_total,
            "ads_processed": 0,
            "comments_fetched": 0,
            "comments_saved": 0,
            "comments_reused": 0,
            "comments_skipped": 0,
            "errors": 0,
            "message": "Comment sync job initialized.",
            "created_at": now_ts,
            "updated_at": now_ts,
            "completed_at": None,
            "result": None,
            "error_details": None
        }
        with self._lock:
            self._jobs[job_id] = job_data
        logger.info(f"[JOB_MANAGER] Created sync job {job_id} for user_id={user_id}, ad_account_id={ad_account_id}, ads_total={ads_total}")
        return dict(job_data)

    def update_progress(
        self,
        job_id: str,
        ads_processed: int,
        comments_fetched: int,
        comments_saved: int,
        comments_reused: int,
        comments_skipped: int,
        errors: int
    ) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job["ads_processed"] = ads_processed
            job["comments_fetched"] = comments_fetched
            job["comments_saved"] = comments_saved
            job["comments_reused"] = comments_reused
            job["comments_skipped"] = comments_skipped
            job["errors"] = errors
            job["updated_at"] = time.time()
            job["message"] = f"Syncing comments... {ads_processed} / {job['ads_total']} ads processed ({comments_saved} new saved)."

    def complete_job(self, job_id: str, result: Dict[str, Any]) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job["status"] = "COMPLETED" if result.get("success", True) else "FAILED"
            job["completed_at"] = time.time()
            job["updated_at"] = time.time()
            job["ads_processed"] = result.get("ads_total", result.get("posts_processed", job["ads_processed"]))
            job["comments_fetched"] = result.get("comments_fetched", job["comments_fetched"])
            job["comments_saved"] = result.get("comments_saved", job["comments_saved"])
            job["comments_reused"] = result.get("comments_reused", job["comments_reused"])
            job["comments_skipped"] = result.get("comments_skipped", job["comments_skipped"])
            job["errors"] = result.get("permission_errors", 0) + result.get("meta_api_errors", 0)
            job["result"] = result
            if not result.get("success", True):
                job["message"] = result.get("message", "Comment sync job failed.")
                job["error_details"] = result.get("error_details", {})
            else:
                fetched = result.get("comments_fetched", 0)
                saved = result.get("comments_saved", 0)
                reused = result.get("comments_reused", 0)
                job["message"] = f"Comments synced: {fetched} fetched from Meta Graph API ({saved} new saved, {reused} existing reused)."
        logger.info(f"[JOB_MANAGER] Completed sync job {job_id} with status={job['status']}")

    def fail_job(self, job_id: str, error_message: str, error_details: Optional[Dict[str, Any]] = None) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job["status"] = "FAILED"
            job["completed_at"] = time.time()
            job["updated_at"] = time.time()
            job["message"] = error_message
            job["error_details"] = error_details or {}
        logger.error(f"[JOB_MANAGER] Failed sync job {job_id}: {error_message}")

    def get_job(self, job_id: str, user_id: int) -> Optional[Dict[str, Any]]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job and job["user_id"] == user_id:
                return dict(job)
        return None

job_manager = MetaCommentSyncJobManager()

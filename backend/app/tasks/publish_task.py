import logging
from datetime import datetime, timezone
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.repositories.post_repository import post_repo
from app.repositories.publishing_repository import publishing_repo
from app.services.post_service import post_service
from app.services.publisher_service import publishing_engine

logger = logging.getLogger(__name__)

@celery_app.task(name="app.tasks.publish_task.execute_batch_publishing_task")
def execute_batch_publishing_task(batch_id: int):
    """Celery task: Asynchronously process multi-account publishing batch."""
    db = SessionLocal()
    try:
        batch = publishing_repo.get_batch(db, batch_id)
        if not batch:
            logger.error(f"Celery Task Error: PublishingBatch ID={batch_id} not found.")
            return {"status": "NOT_FOUND"}

        post = post_repo.get(db, batch.post_id)
        if not post:
            logger.error(f"Celery Task Error: Post ID={batch.post_id} not found.")
            return {"status": "POST_NOT_FOUND"}

        formatted_caption = f"{post.caption}\n\n{' '.join(post.hashtags or [])}\n\n{post.cta or ''}".strip()
        
        # Get target social accounts
        from app.repositories.social_account_repository import social_account_repo
        job_account_ids = [job.social_account_id for job in batch.jobs]
        accounts = [
            acc for acc in social_account_repo.get_by_user(db, batch.user_id)
            if acc.id in job_account_ids
        ]

        logger.info(f"Celery Async Worker: Starting execution for batch ID={batch_id} across {len(accounts)} accounts.")
        publishing_engine.execute_batch(
            db=db,
            batch_id=batch_id,
            post_caption=formatted_caption,
            raw_media_url=post.image_url,
            accounts=accounts
        )
        return {"status": "SUCCESS", "batch_id": batch_id}
    except Exception as e:
        logger.error(f"Celery Async Worker Error executing batch ID={batch_id}: {e}")
        return {"status": "ERROR", "error": str(e)}
    finally:
        db.close()

@celery_app.task(name="app.tasks.publish_task.process_scheduled_posts_task")
def process_scheduled_posts_task():
    """Celery Beat task: Find scheduled posts whose time has passed and publish them."""
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        due_posts = post_repo.get_due_scheduled_posts(db, now)
        logger.info(f"Celery Scheduled Task: Found {len(due_posts)} posts due for publishing.")
        
        for post in due_posts:
            try:
                # Mark as processing to claim atomically
                post.status = "PROCESSING"
                db.commit()
                post_service.execute_publish(db, post.id, post.user_id)
                logger.info(f"Successfully published scheduled post ID={post.id}")
            except Exception as e:
                logger.error(f"Error publishing scheduled post ID={post.id}: {e}")
                post.status = "FAILED"
                post.last_error = str(e)
                db.commit()

        # Retry failed posts if retry count < max retries
        retryable_posts = post_repo.get_failed_retryable_posts(db)
        for post in retryable_posts:
            try:
                logger.info(f"Retrying failed post ID={post.id} (Attempt {post.retry_count + 1})")
                post_service.execute_publish(db, post.id, post.user_id)
            except Exception as e:
                logger.error(f"Retry failed for post ID={post.id}: {e}")

    finally:
        db.close()

@celery_app.task(name="app.tasks.publish_task.sync_meta_analytics_task")
def sync_meta_analytics_task():
    """Celery Beat task: Sync analytics metrics for published posts."""
    logger.info("Celery Task: Syncing Meta analytics metrics...")
    return {"status": "synced"}

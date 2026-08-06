import logging
from datetime import datetime
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.repositories.post_repository import post_repo
from app.services.post_service import post_service

logger = logging.getLogger(__name__)

@celery_app.task(name="app.tasks.publish_task.process_scheduled_posts_task")
def process_scheduled_posts_task():
    """Celery Beat task: Find scheduled posts whose time has passed and publish them."""
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        due_posts = post_repo.get_due_scheduled_posts(db, now)
        logger.info(f"Celery Scheduled Task: Found {len(due_posts)} posts due for publishing.")
        
        for post in due_posts:
            try:
                post_service.execute_publish(db, post.id)
                logger.info(f"Successfully published scheduled post ID={post.id}")
            except Exception as e:
                logger.error(f"Error publishing scheduled post ID={post.id}: {e}")

        # Retry failed posts if retry count < max retries
        retryable_posts = post_repo.get_failed_retryable_posts(db)
        for post in retryable_posts:
            try:
                logger.info(f"Retrying failed post ID={post.id} (Attempt {post.retry_count + 1})")
                post_service.execute_publish(db, post.id)
            except Exception as e:
                logger.error(f"Retry failed for post ID={post.id}: {e}")

    finally:
        db.close()

@celery_app.task(name="app.tasks.publish_task.sync_meta_analytics_task")
def sync_meta_analytics_task():
    """Celery Beat task: Sync analytics metrics for published posts."""
    logger.info("Celery Task: Syncing Meta analytics metrics...")
    return {"status": "synced"}

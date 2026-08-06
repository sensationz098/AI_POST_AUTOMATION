from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "social_ai_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.publish_task"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "check-and-publish-scheduled-posts-every-minute": {
            "task": "app.tasks.publish_task.process_scheduled_posts_task",
            "schedule": 60.0,  # runs every 60 seconds
        },
        "sync-analytics-every-hour": {
            "task": "app.tasks.publish_task.sync_meta_analytics_task",
            "schedule": 3600.0,  # runs every hour
        }
    }
)

import ssl
from celery import Celery
from app.core.config import settings

broker_url = settings.get_celery_broker_url()
backend_url = settings.get_celery_result_backend()

celery_app = Celery(
    "social_ai_worker",
    broker=broker_url,
    backend=backend_url,
    include=["app.tasks.publish_task", "app.tasks.youtube_tasks"]
)

conf_dict = {
    "task_serializer": "json",
    "accept_content": ["json"],
    "result_serializer": "json",
    "timezone": "UTC",
    "enable_utc": True,
    "broker_connection_retry_on_startup": True,
    "beat_schedule": {
        "check-and-publish-scheduled-posts-every-minute": {
            "task": "app.tasks.publish_task.process_scheduled_posts_task",
            "schedule": 60.0,  # runs every 60 seconds
        },
        "sync-analytics-every-hour": {
            "task": "app.tasks.publish_task.sync_meta_analytics_task",
            "schedule": 3600.0,  # runs every hour
        }
    }
}

# Configure SSL for managed Redis with TLS (e.g. Render, Upstash rediss://)
if broker_url.startswith("rediss://"):
    conf_dict["broker_use_ssl"] = {"ssl_cert_reqs": ssl.CERT_NONE}
if backend_url.startswith("rediss://"):
    conf_dict["redis_backend_use_ssl"] = {"ssl_cert_reqs": ssl.CERT_NONE}

celery_app.conf.update(**conf_dict)

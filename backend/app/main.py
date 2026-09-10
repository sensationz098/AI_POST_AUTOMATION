import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.database import engine, Base
from app.core.rate_limit import limiter
import app.models  # Register all models with SQLAlchemy Base

setup_logging()
logger = logging.getLogger(__name__)

# Import API routers
from app.api.v1.auth import router as auth_router
from app.api.v1.brands import router as brand_router
from app.api.v1.posts import router as post_router
from app.api.v1.ai import router as ai_router
from app.api.v1.meta import router as meta_router
from app.api.v1.social_accounts import router as social_accounts_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.audit import router as audit_router
from app.api.v1.health import router as health_router
from app.api.v1.webhooks import router as webhooks_router
from app.api.v1.social_comments import router as social_comments_router
from app.api.v1.automations import router as automations_router
from app.api.v1.stories import router as stories_router
from app.api.v1.youtube import router as youtube_router
import asyncio
from contextlib import asynccontextmanager

async def background_automation_execution_poller():
    """
    Background reliability poller running inside FastAPI.
    Polls every 10 seconds to catch and execute any PENDING or retryable
    executions caused by unexpected worker crashes, process restarts, or missed dispatches.
    """
    logger.info("[EXECUTION_WORKER] Background automation execution poller initialized.")
    while True:
        try:
            await asyncio.sleep(10)
            from app.core.database import SessionLocal
            from app.services.automation_execution_service import automation_execution_service
            from app.tasks.youtube_tasks import process_pending_youtube_processing_uploads
            db = SessionLocal()
            try:
                processed = automation_execution_service.process_pending_executions(db, limit=25)
                if processed:
                    logger.info(f"[EXECUTION_WORKER] Reliability poller processed {len(processed)} pending execution(s).")
                yt_processed = process_pending_youtube_processing_uploads(db, limit=10)
                if yt_processed:
                    logger.info(f"[EXECUTION_WORKER] YouTube reliability poller checked {len(yt_processed)} processing upload(s).")
            finally:
                db.close()
        except asyncio.CancelledError:
            logger.info("[EXECUTION_WORKER] Background poller gracefully cancelled.")
            break
        except Exception as e:
            logger.error(f"[EXECUTION_WORKER] Error in background poller: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Launch background poller task
    poller_task = asyncio.create_task(background_automation_execution_poller())
    try:
        yield
    finally:
        # Shutdown: Gracefully cancel background poller
        poller_task.cancel()
        try:
            await poller_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    description="Production-Ready AI Social Media Automation Platform for Facebook & Instagram API.",
    lifespan=lifespan
)

# Register slowapi rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Enforce production-safe restricted CORS configuration for credentialed requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Static files route for local asset cache
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Register v1 API routers
app.include_router(health_router, prefix=settings.API_V1_STR)
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(brand_router, prefix=settings.API_V1_STR)
app.include_router(post_router, prefix=settings.API_V1_STR)
app.include_router(ai_router, prefix=settings.API_V1_STR)
app.include_router(meta_router, prefix=settings.API_V1_STR)
app.include_router(social_accounts_router, prefix=settings.API_V1_STR)
app.include_router(analytics_router, prefix=settings.API_V1_STR)
app.include_router(audit_router, prefix=settings.API_V1_STR)
app.include_router(webhooks_router, prefix=settings.API_V1_STR)
app.include_router(social_comments_router, prefix=settings.API_V1_STR)
app.include_router(automations_router, prefix=settings.API_V1_STR)
app.include_router(stories_router, prefix=settings.API_V1_STR)
app.include_router(youtube_router, prefix=settings.API_V1_STR)


@app.get("/")
def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.APP_ENV,
        "health": f"{settings.API_V1_STR}/health",
        "readiness": f"{settings.API_V1_STR}/ready"
    }

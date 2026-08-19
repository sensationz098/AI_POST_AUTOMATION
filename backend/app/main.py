import os
import logging
import traceback
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import engine, Base
import app.models  # Register all models with SQLAlchemy Base

# Auto-create DB tables if they don't exist
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    logging.warning(f"Database table auto-creation warning: {e}")

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

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    description="Production-Ready AI Social Media Automation Platform for Facebook & Instagram API."
)

# Global unhandled exception handler to prevent 500 server crash
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error on {request.method} {request.url}: {exc}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": str(exc) or "Internal Server Error",
            "path": str(request.url.path),
            "status": 500
        }
    )

# Enforce production-safe restricted CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.APP_ENV != "production" else settings.cors_origins,
    allow_credentials=True if settings.APP_ENV == "production" else False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Catch-all OPTIONS preflight handler to prevent 405 Method Not Allowed on browser preflight
@app.options("/{path:path}")
def options_preflight_handler(path: str):
    return JSONResponse(
        status_code=200,
        content={"message": "OK"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
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

@app.get("/")
def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.APP_ENV,
        "health": f"{settings.API_V1_STR}/health",
        "readiness": f"{settings.API_V1_STR}/ready"
    }

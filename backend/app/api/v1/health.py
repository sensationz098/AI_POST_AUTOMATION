from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis_client

router = APIRouter(tags=["Healthcheck"])

@router.get("/health")
def healthcheck():
    """Basic liveness probe."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.APP_ENV
    }

@router.get("/ready")
def readiness_check(db: Session = Depends(get_db)):
    """Production readiness probe validating DB, Redis, and configuration."""
    checks = {
        "database": False,
        "redis": False,
        "environment": True
    }
    
    # 1. Test PostgreSQL DB connectivity
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception as e:
        checks["database_error"] = str(e)

    # 2. Test Redis connectivity
    r = get_redis_client()
    if r:
        try:
            r.ping()
            checks["redis"] = True
        except Exception as e:
            checks["redis_error"] = str(e)

    all_ready = checks["database"] and checks["redis"]
    if not all_ready and settings.APP_ENV == "production":
        raise HTTPException(
            status_code=status.HTTP_530_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready", "checks": checks}
        )

    return {
        "status": "ready" if all_ready else "degraded",
        "checks": checks
    }

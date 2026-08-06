from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.schemas.audit import AuditLogResponse
from app.services.audit_service import audit_service
from app.api.v1.deps import require_admin, get_current_user
from app.models.user import User

router = APIRouter(prefix="/audit", tags=["Audit & Activity History"])

@router.get("/logs", response_model=List[AuditLogResponse])
def get_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve system audit logs and action history."""
    return audit_service.get_logs(db, limit=limit)

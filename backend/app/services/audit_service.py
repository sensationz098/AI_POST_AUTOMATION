from typing import List, Optional
from sqlalchemy.orm import Session
from app.repositories.audit_repository import audit_repo
from app.schemas.audit import AuditLogResponse
from app.models.audit import AuditLog

class AuditService:
    def get_logs(self, db: Session, limit: int = 50, user_id: Optional[int] = None) -> List[AuditLogResponse]:
        query = db.query(AuditLog)
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        logs = query.order_by(AuditLog.created_at.desc()).limit(limit).all()
        return [AuditLogResponse.model_validate(log) for log in logs]

audit_service = AuditService()

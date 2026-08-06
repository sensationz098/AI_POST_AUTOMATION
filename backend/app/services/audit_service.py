from typing import List
from sqlalchemy.orm import Session
from app.repositories.audit_repository import audit_repo
from app.schemas.audit import AuditLogResponse

class AuditService:
    def get_logs(self, db: Session, limit: int = 50) -> List[AuditLogResponse]:
        logs = audit_repo.get_recent(db, limit=limit)
        return [AuditLogResponse.model_validate(log) for log in logs]

audit_service = AuditService()

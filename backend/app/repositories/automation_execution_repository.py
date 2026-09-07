from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.repositories.base import BaseRepository
from app.models.automation_execution import AutomationExecution, ExecutionStatus


class AutomationExecutionRepository(BaseRepository[AutomationExecution]):
    def __init__(self):
        super().__init__(AutomationExecution)

    def get_by_id_and_user(self, db: Session, execution_id: int, user_id: int) -> Optional[AutomationExecution]:
        """Fetch execution by ID ensuring user ownership."""
        return db.query(AutomationExecution).filter(
            AutomationExecution.id == execution_id,
            AutomationExecution.user_id == user_id
        ).first()

    def get_by_automation_and_comment(
        self,
        db: Session,
        automation_id: int,
        external_comment_id: str
    ) -> Optional[AutomationExecution]:
        """Fetch existing execution for a given automation and external comment (idempotency check)."""
        return db.query(AutomationExecution).filter(
            AutomationExecution.automation_id == automation_id,
            AutomationExecution.external_comment_id == external_comment_id
        ).first()

    def get_by_automation(
        self,
        db: Session,
        automation_id: int,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[AutomationExecution]:
        """List executions for a given automation."""
        query = db.query(AutomationExecution).filter(AutomationExecution.automation_id == automation_id)
        if status:
            query = query.filter(AutomationExecution.status == status)
        return query.order_by(AutomationExecution.created_at.desc()).offset(skip).limit(limit).all()

    def get_by_user(
        self,
        db: Session,
        user_id: int,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[AutomationExecution]:
        """List executions for a user across all automations."""
        query = db.query(AutomationExecution).filter(AutomationExecution.user_id == user_id)
        if status:
            query = query.filter(AutomationExecution.status == status)
        return query.order_by(AutomationExecution.created_at.desc()).offset(skip).limit(limit).all()


automation_execution_repository = AutomationExecutionRepository()

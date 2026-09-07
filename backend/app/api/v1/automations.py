import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.deps import get_current_user
from app.models.user import User
from app.schemas.automation import (
    AutomationCreate,
    AutomationUpdate,
    AutomationResponse,
    AutomationDeleteResponse,
)
from app.services.automation_service import automation_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/automations", tags=["Comment Automations"])


@router.post("/", response_model=AutomationResponse, status_code=status.HTTP_201_CREATED)
def create_automation(
    automation_in: AutomationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new comment automation in DRAFT status with full configuration validation."""
    return automation_service.create_automation(db, current_user.id, automation_in)


@router.get("/", response_model=List[AutomationResponse])
def list_automations(
    status: Optional[str] = Query(None, description="Filter by status (DRAFT, ACTIVE, PAUSED)"),
    platform: Optional[str] = Query(None, description="Filter by platform (facebook, instagram)"),
    social_account_id: Optional[int] = Query(None, description="Filter by social account ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all comment automations belonging to the authenticated user."""
    return automation_service.get_user_automations(
        db=db,
        user_id=current_user.id,
        status=status,
        platform=platform,
        social_account_id=social_account_id,
        skip=skip,
        limit=limit
    )


@router.get("/{automation_id}", response_model=AutomationResponse)
def get_automation(
    automation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get single automation details by ID."""
    return automation_service.get_automation(db, automation_id, current_user.id)


@router.patch("/{automation_id}", response_model=AutomationResponse)
def update_automation(
    automation_id: int,
    automation_in: AutomationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update automation settings and configuration."""
    return automation_service.update_automation(db, automation_id, current_user.id, automation_in)


@router.delete("/{automation_id}", response_model=AutomationDeleteResponse)
def delete_automation(
    automation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Safely delete an automation owned by the authenticated user."""
    return automation_service.delete_automation(db, automation_id, current_user.id)


@router.post("/{automation_id}/activate", response_model=AutomationResponse)
def activate_automation(
    automation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Activate an automation after validating account, post, trigger, and action configuration."""
    return automation_service.activate_automation(db, automation_id, current_user.id)


@router.post("/{automation_id}/pause", response_model=AutomationResponse)
def pause_automation(
    automation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Pause an active automation."""
    return automation_service.pause_automation(db, automation_id, current_user.id)

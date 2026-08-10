from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.schemas.post import PostCreate, PostUpdate, PostResponse, SchedulePostRequest
from app.services.post_service import post_service
from app.api.v1.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/posts", tags=["Social Posts Workflow"])

@router.post("/", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(
    post_in: PostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a draft post for approval or scheduling."""
    return post_service.create_post(db, current_user.id, post_in)

@router.get("/brand/{brand_id}", response_model=List[PostResponse])
def get_brand_posts(
    brand_id: int,
    status: Optional[str] = Query(None, description="Filter by status: DRAFT, APPROVED, SCHEDULED, PUBLISHED, FAILED"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve posts for a specific brand profile (auto-triggering due scheduled posts publishing)."""
    post_service.check_and_publish_due_posts(db)
    return post_service.get_brand_posts(db, brand_id, status)

@router.get("/{post_id}", response_model=PostResponse)
def get_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get single post by ID."""
    return post_service.get_post(db, post_id)

@router.put("/{post_id}", response_model=PostResponse)
def update_post(
    post_id: int,
    post_in: PostUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update post content, status, or image."""
    return post_service.update_post(db, post_id, current_user.id, post_in)

@router.post("/{post_id}/approve", response_model=PostResponse)
def approve_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Approve a post for publication."""
    return post_service.approve_post(db, post_id, current_user.id)

@router.post("/{post_id}/schedule", response_model=PostResponse)
def schedule_post(
    post_id: int,
    request: SchedulePostRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Schedule post for future automated publishing."""
    return post_service.schedule_post(db, post_id, current_user.id, request.scheduled_at)

@router.post("/{post_id}/publish-now", response_model=PostResponse)
def publish_now(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Immediately trigger Meta Graph API publishing for Facebook & Instagram."""
    return post_service.execute_publish(db, post_id)

@router.post("/{post_id}/retry", response_model=PostResponse)
def retry_failed(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retry publication for a failed post."""
    return post_service.retry_failed_post(db, post_id, current_user.id)

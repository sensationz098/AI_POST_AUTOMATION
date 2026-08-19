from fastapi import APIRouter, Depends, status, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
import logging

from app.core.database import get_db
from app.schemas.post import PostCreate, PostUpdate, PostResponse, SchedulePostRequest
from app.schemas.social_account import MultiPublishRequest, PublishingBatchResponse
from app.services.post_service import post_service
from app.repositories.social_account_repository import social_account_repo
from app.models.publishing_batch import BatchStatus, JobStatus, PublishingJob
from app.api.v1.deps import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/posts", tags=["Social Posts Workflow"])

@router.post("/", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_post(
    post_in: PostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a draft post for approval or scheduling."""
    return post_service.create_post(db, current_user.id, post_in)

@router.get("/", response_model=List[PostResponse])
@router.get("", response_model=List[PostResponse], include_in_schema=False)
def get_user_posts(
    status: Optional[str] = Query(None, description="Filter by status: DRAFT, APPROVED, SCHEDULED, PUBLISHED, FAILED"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve all posts created by authenticated user."""
    return post_service.get_user_posts(db, current_user.id, status)

@router.get("/brand/{brand_id}", response_model=List[PostResponse])
@router.get("/brand/{brand_id}/", response_model=List[PostResponse], include_in_schema=False)
def get_brand_posts(
    brand_id: int,
    status: Optional[str] = Query(None, description="Filter by status: DRAFT, APPROVED, SCHEDULED, PUBLISHED, FAILED"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve posts for a specific brand profile (auto-triggering due scheduled posts publishing)."""
    return post_service.get_brand_posts(db, brand_id, current_user.id, status)

# Direct Studio Publish Payload Endpoint (Handles both /publish-now and /publish-now/)
@router.post("/publish-now", response_model=PostResponse)
@router.post("/publish-now/", response_model=PostResponse, include_in_schema=False)
def publish_now_direct(
    post_in: PostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create and immediately publish post to Meta Graph API channels with 100% exception safety."""
    try:
        new_post = post_service.create_post(db, current_user.id, post_in)
        published_post = post_service.execute_publish(db, new_post.id, current_user.id)
        
        if published_post.status == "FAILED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=published_post.last_error or "Meta publishing failed. Please check your connected social account and permissions."
            )
        return published_post
    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        logger.error(f"Error in publish_now_direct: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Publishing Error: {str(e)}"
        )

# Direct Studio Schedule Payload Endpoint (Handles both /schedule and /schedule/)
@router.post("/schedule", response_model=PostResponse)
@router.post("/schedule/", response_model=PostResponse, include_in_schema=False)
def schedule_direct(
    post_in: PostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create and schedule post for future automated publishing with 100% exception safety."""
    try:
        post_in.status = "SCHEDULED"
        new_post = post_service.create_post(db, current_user.id, post_in)
        if post_in.scheduled_at:
            return post_service.schedule_post(db, new_post.id, current_user.id, post_in.scheduled_at)
        return new_post
    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        logger.error(f"Error in schedule_direct: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Scheduling Error: {str(e)}"
        )

@router.get("/{post_id}", response_model=PostResponse)
def get_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get single post by ID."""
    return post_service.get_post(db, post_id, current_user.id)

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
@router.post("/{post_id}/approve/", response_model=PostResponse, include_in_schema=False)
def approve_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Approve a post for publication."""
    return post_service.approve_post(db, post_id, current_user.id)

@router.post("/{post_id}/schedule", response_model=PostResponse)
@router.post("/{post_id}/schedule/", response_model=PostResponse, include_in_schema=False)
def schedule_post_by_id(
    post_id: int,
    request: SchedulePostRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Schedule existing post for future automated publishing."""
    return post_service.schedule_post(db, post_id, current_user.id, request.scheduled_at)

@router.post("/{post_id}/publish-now", response_model=PostResponse)
@router.post("/{post_id}/publish-now/", response_model=PostResponse, include_in_schema=False)
def publish_now_by_id(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Immediately trigger Meta Graph API publishing for existing post."""
    return post_service.execute_publish(db, post_id, current_user.id)

@router.post("/{post_id}/retry", response_model=PostResponse)
@router.post("/{post_id}/retry/", response_model=PostResponse, include_in_schema=False)
def retry_failed(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retry publication for a failed post."""
    return post_service.retry_failed_post(db, post_id, current_user.id)

@router.get("/batch/{batch_id}", response_model=PublishingBatchResponse)
def get_publishing_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve detailed status of a publishing batch and individual target jobs."""
    from app.repositories.publishing_repository import publishing_repo
    batch = publishing_repo.get_batch(db, batch_id)
    if not batch or batch.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publishing batch not found."
        )
    return batch

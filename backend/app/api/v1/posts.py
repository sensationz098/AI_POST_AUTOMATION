import logging
from fastapi import APIRouter, Depends, status, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.schemas.post import PostCreate, PostUpdate, PostResponse, SchedulePostRequest
from app.schemas.social_account import MultiPublishRequest, PublishingBatchResponse
from app.services.post_service import post_service
from app.services.publisher_service import publishing_engine
from app.repositories.publishing_repository import publishing_repo
from app.repositories.social_account_repository import social_account_repo
from app.models.publishing_batch import BatchStatus, JobStatus, PublishingJob
from app.api.v1.deps import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/posts", tags=["Social Posts Workflow"])


@router.post("/", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(
    post_in: PostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a draft post for approval or scheduling."""
    return post_service.create_post(db, current_user.id, post_in)

@router.get("/", response_model=List[PostResponse])
def get_user_posts(
    status: Optional[str] = Query(None, description="Filter by status: DRAFT, APPROVED, SCHEDULED, PUBLISHED, FAILED"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve all posts created by authenticated user."""
    return post_service.get_user_posts(db, current_user.id, status)

@router.get("/brand/{brand_id}", response_model=List[PostResponse])
def get_brand_posts(
    brand_id: int,
    status: Optional[str] = Query(None, description="Filter by status: DRAFT, APPROVED, SCHEDULED, PUBLISHED, FAILED"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve posts for a specific brand profile (auto-triggering due scheduled posts publishing)."""
    return post_service.get_brand_posts(db, brand_id, current_user.id, status)

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
    return post_service.execute_publish(db, post_id, current_user.id)

@router.post("/{post_id}/retry", response_model=PostResponse)
def retry_failed(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retry publication for a failed post."""
    return post_service.retry_failed_post(db, post_id, current_user.id)

# 🚀 MULTI-ACCOUNT PUBLISHING ENDPOINTS 🚀

@router.post("/publish-multi", response_model=PublishingBatchResponse, status_code=status.HTTP_201_CREATED)
@router.post("/multi-publish", response_model=PublishingBatchResponse, status_code=status.HTTP_201_CREATED)
def publish_multi_account(
    request: MultiPublishRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Publish one post to multiple selected Facebook Pages and Instagram Accounts concurrently.
    Supports idempotency, per-account job tracking, token expiration detection, and partial batch success.
    """
    logger.info(
        f"[PUBLISH_TRACE] PUBLISH_MULTI_RECEIVED | post_id={request.post_id} | "
        f"social_account_ids={request.social_account_ids} | user_id={current_user.id} | "
        f"req_media_type={request.media_type}"
    )
    post = post_service.get_post(db, request.post_id, current_user.id)
    if not request.social_account_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one target social account must be selected."
        )

    # Fetch user's authorized target social accounts
    accounts = [
        acc for acc in social_account_repo.get_by_user(db, current_user.id)
        if acc.id in request.social_account_ids
    ]
    if not accounts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No matching authorized social accounts found for publishing."
        )

    # 1. Create or retrieve PublishingBatch with idempotency safeguard
    idempotency_key = request.idempotency_key or f"batch_{post.id}_{abs(hash(tuple(request.social_account_ids)))}"
    batch = publishing_repo.create_batch(
        db=db,
        post_id=post.id,
        user_id=current_user.id,
        total_targets=len(accounts),
        idempotency_key=idempotency_key
    )

    logger.info(f"[PUBLISH_TRACE] PUBLISH_BATCH_STARTED | batch_id={batch.id} | post_id={post.id} | total_targets={len(accounts)}")

    # 2. Initialize PublishingJob entries for targets
    existing_jobs = db.query(PublishingJob).filter(
        PublishingJob.batch_id == batch.id
    ).all()

    if not existing_jobs:
        for acc in accounts:
            publishing_repo.create_job(db, batch.id, acc.id, acc.platform)

    # 3. Format caption & execute batch publishing engine concurrently
    formatted_caption = f"{post.caption}\n\n{' '.join(post.hashtags or [])}\n\n{post.cta or ''}".strip()
    publishing_engine.execute_batch(
        db=db,
        batch_id=batch.id,
        post_caption=formatted_caption,
        raw_media_url=post.image_url,
        accounts=accounts,
        media_type=request.media_type or getattr(post, "media_type", None)
    )


    # 4. Refresh & return complete PublishingBatchResponse
    db.expire_all()
    res_batch = publishing_repo.update_batch_summary(db, batch.id)
    if not res_batch:
        res_batch = publishing_repo.get_batch(db, batch.id)
    
    # Update main Post status based on batch result
    if res_batch.status in [BatchStatus.SUCCESS.value, BatchStatus.PARTIAL_SUCCESS.value] or res_batch.successful_targets > 0:
        post.status = "PUBLISHED"
        post.published_at = post.published_at or res_batch.completed_at
        if res_batch.failed_targets > 0:
            post.last_error = f"Published to {res_batch.successful_targets} of {res_batch.total_targets} target accounts."
        else:
            post.last_error = None
    else:
        post.status = "FAILED"
        post.last_error = f"Multi-account publishing failed on {res_batch.failed_targets} target accounts."
    db.commit()

    return res_batch

@router.get("/batch/{batch_id}", response_model=PublishingBatchResponse)
def get_publishing_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve detailed status of a publishing batch and individual target jobs."""
    batch = publishing_repo.get_batch(db, batch_id)
    if not batch or batch.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publishing batch not found."
        )
    return batch

@router.post("/batch/{batch_id}/retry", response_model=PublishingBatchResponse)
def retry_failed_batch_jobs(
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retry ONLY the failed target jobs within a multi-account publishing batch."""
    batch = publishing_repo.get_batch(db, batch_id)
    if not batch or batch.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publishing batch not found."
        )

    failed_jobs = [j for j in batch.jobs if j.status == JobStatus.FAILED.value]
    if not failed_jobs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No failed jobs to retry in this batch."
        )

    failed_account_ids = [j.social_account_id for j in failed_jobs]
    accounts = [
        acc for acc in social_account_repo.get_by_user(db, current_user.id)
        if acc.id in failed_account_ids
    ]

    post = post_service.get_post(db, batch.post_id)
    formatted_caption = f"{post.caption}\n\n{' '.join(post.hashtags or [])}\n\n{post.cta or ''}".strip()

    publishing_engine.execute_batch(
        db=db,
        batch_id=batch.id,
        post_caption=formatted_caption,
        raw_media_url=post.image_url,
        accounts=accounts
    )

    return publishing_repo.get_batch(db, batch.id)


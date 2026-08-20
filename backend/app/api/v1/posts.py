from fastapi import APIRouter, Depends, status, Query, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
import logging

from app.core.database import get_db
from app.schemas.post import PostCreate, PostUpdate, PostResponse, SchedulePostRequest
from app.schemas.social_account import MultiPublishRequest, PublishingBatchResponse
from app.services.post_service import post_service, run_background_publish_batch
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
    """
    Create post, initialize PublishingBatch/Jobs for exact target SocialAccount IDs,
    and execute synchronous multi-account parallel publishing with timing diagnostics.
    """
    import time
    from app.models.social_account import SocialAccount
    from app.services.publisher_service import publishing_engine
    from app.repositories.publishing_repository import publishing_repo
    from app.models.publishing_batch import BatchStatus

    t0 = time.time()
    logger.info(f"⏱️ [PERF LOG] REQUEST RECEIVED at t=0ms for user_id={current_user.id}")

    try:
        target_ids = post_in.target_account_ids or post_in.social_account_ids
        new_post = post_service.create_post(db, current_user.id, post_in)
        t_created = (time.time() - t0) * 1000
        logger.info(f"⏱️ [PERF LOG] POST CREATED (id={new_post.id}) at t={t_created:.1f}ms")

        batch = post_service.create_and_start_publish_batch(
            db=db,
            post=new_post,
            user_id=current_user.id,
            target_account_ids=target_ids
        )

        # Retrieve exact selected target social accounts
        target_accounts = db.query(SocialAccount).filter(
            SocialAccount.user_id == current_user.id,
            SocialAccount.id.in_(target_ids) if target_ids else True
        ).all()

        # Execute parallel batch publishing asynchronously via Celery worker
        db.commit()
        from app.tasks.publish_task import execute_batch_publishing_task
        execute_batch_publishing_task.delay(batch.id)

        new_post.status = "PUBLISHING"
        db.commit()
        db.refresh(new_post)

        t_end = (time.time() - t0) * 1000
        logger.info(f"⏱️ [PERF LOG] ASYNC RESPONSE SENT at t={t_end:.1f}ms (Total elapsed: {t_end:.1f}ms)")

        res = PostResponse.model_validate(new_post)
        res.batch_id = batch.id
        return res
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
    """Immediately trigger background Celery task multi-account publishing for existing post."""
    from app.tasks.publish_task import execute_batch_publishing_task
    post = post_service.get_post(db, post_id, current_user.id)
    batch = post_service.create_and_start_publish_batch(
        db=db,
        post=post,
        user_id=current_user.id
    )

    execute_batch_publishing_task.delay(batch.id)

    res = PostResponse.model_validate(post)
    res.batch_id = batch.id
    return res

@router.post("/{post_id}/retry", response_model=PostResponse)
@router.post("/{post_id}/retry/", response_model=PostResponse, include_in_schema=False)
def retry_failed(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retry publication for a failed post."""
    return post_service.retry_failed_post(db, post_id, current_user.id)

# 🚀 MULTI-ACCOUNT PUBLISHING ENDPOINTS (ASYNC CELERY QUEUED) 🚀

@router.post("/publish-multi", response_model=PublishingBatchResponse, status_code=status.HTTP_201_CREATED)
@router.post("/multi-publish", response_model=PublishingBatchResponse, status_code=status.HTTP_201_CREATED)
@router.post("/publish-multi/", response_model=PublishingBatchResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
@router.post("/multi-publish/", response_model=PublishingBatchResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def publish_multi_account(
    request: MultiPublishRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Asynchronously publish one post to multiple selected Facebook Pages and Instagram Accounts via Celery.
    Supports idempotency, per-account job tracking, token expiration detection, and partial batch success.
    Returns the PublishingBatch response immediately.
    """
    from app.repositories.publishing_repository import publishing_repo
    from app.repositories.social_account_repository import social_account_repo
    from app.models.publishing_batch import BatchStatus, PublishingJob
    from app.tasks.publish_task import execute_batch_publishing_task

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
    idempotency_key = request.idempotency_key or f"batch_{post.id}_{abs(hash(tuple(sorted(request.social_account_ids))))}"
    batch = publishing_repo.create_batch(
        db=db,
        post_id=post.id,
        user_id=current_user.id,
        total_targets=len(accounts),
        idempotency_key=idempotency_key
    )

    # Idempotency check: If an existing batch is already PROCESSING, SUCCESS, or PARTIAL_SUCCESS, do NOT enqueue another task
    if batch.status in [BatchStatus.PROCESSING.value, BatchStatus.SUCCESS.value, BatchStatus.PARTIAL_SUCCESS.value]:
        return batch

    # 2. Initialize PublishingJob entries for targets
    existing_jobs = db.query(PublishingJob).filter(
        PublishingJob.batch_id == batch.id
    ).all()

    is_new_jobs = False
    if not existing_jobs:
        for acc in accounts:
            publishing_repo.create_job(db, batch.id, acc.id, acc.platform)
        is_new_jobs = True

    post.status = "PUBLISHING"

    # 3. Commit DB transaction BEFORE queuing Celery task so worker finds committed batch & jobs
    db.commit()
    db.refresh(batch)

    # 4. Queue task to Celery worker asynchronously
    if is_new_jobs or batch.status == BatchStatus.QUEUED.value:
        execute_batch_publishing_task.delay(batch.id)

    # 5. Immediately return PublishingBatchResponse
    return batch

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

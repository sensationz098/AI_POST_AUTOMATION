import os
import time
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.api.v1.deps import get_current_user
from app.models.user import User
from app.models.story import StoryStatus
from app.schemas.story import (
    StoryCreate,
    StoryUpdate,
    StoryScheduleRequest,
    StoryResponse,
    StoryValidationResult
)
from app.services.story_service import story_service
from app.services.cloudinary_service import upload_media_to_cloudinary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stories", tags=["Stories Automation Workflow"])


@router.post("/upload-media")
async def upload_story_media(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload image or video media directly for Stories.
    Streams directly to Cloudinary without loading full file into memory.
    """
    start_time = time.time()
    filename = file.filename or "story_media"
    content_type = file.content_type or ""

    is_vid = content_type.startswith("video/") or any(
        filename.lower().endswith(ext) for ext in [".mp4", ".mov", ".webm", ".m4v"]
    )
    media_type = "video" if is_vid else "image"

    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)

    max_allowed_bytes = settings.MAX_VIDEO_UPLOAD_BYTES if is_vid else settings.MAX_IMAGE_UPLOAD_BYTES
    max_mb = max_allowed_bytes / (1024 * 1024)

    if file_size > max_allowed_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size ({file_size / (1024*1024):.1f} MB) exceeds maximum allowed story upload limit of {max_mb:.0f} MB."
        )

    cdn_url = upload_media_to_cloudinary(file.file, filename_prefix=filename, media_type=media_type)
    if not cdn_url:
        if is_vid:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Cloudinary video storage upload failed. Please verify storage configuration."
            )
        # Small image fallback
        local_dir = "uploads"
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, f"story_{int(time.time())}_{filename}")
        file.file.seek(0)
        with open(local_path, "wb") as f:
            f.write(file.file.read())
        cdn_url = f"/uploads/{os.path.basename(local_path)}"

    return {
        "url": cdn_url,
        "media_type": media_type,
        "filename": filename,
        "size_bytes": file_size,
        "elapsed_seconds": round(time.time() - start_time, 2)
    }


@router.post("/validate-preflight", response_model=StoryValidationResult)
def validate_story_preflight(
    story_in: StoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check media URLs, aspect ratio, and account capabilities before creating or publishing a Story."""
    return story_service.validate_story_preflight(db, story_in, current_user.id)


@router.post("", response_model=StoryResponse, status_code=status.HTTP_201_CREATED)
def create_story(
    story_in: StoryCreate,
    publish_now: bool = Query(False, description="Publish immediately upon creation"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new Story draft, scheduled Story, or publish immediately."""
    story = story_service.create_story(db, story_in, current_user.id)
    if publish_now:
        return story_service.publish_story(db, story.id, current_user.id)
    elif story.scheduled_at and story.status == StoryStatus.SCHEDULED.value:
        return story_service.schedule_story(db, story.id, current_user.id, story.scheduled_at)
    return story


@router.get("", response_model=List[StoryResponse])
def get_stories(
    brand_id: Optional[int] = Query(None, description="Filter stories by brand ID"),
    status: Optional[str] = Query(None, description="Filter stories by status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all stories for the authenticated user."""
    return story_service.get_user_stories(db, current_user.id, brand_id, status)


@router.get("/{story_id}", response_model=StoryResponse)
def get_story(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific story by ID."""
    return story_service.get_story(db, story_id, current_user.id)


@router.put("/{story_id}", response_model=StoryResponse)
def update_story(
    story_id: int,
    story_in: StoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a Story."""
    return story_service.update_story(db, story_id, current_user.id, story_in)


@router.delete("/{story_id}")
def delete_story(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a Story."""
    success = story_service.delete_story(db, story_id, current_user.id)
    return {"success": success, "message": f"Story ID {story_id} deleted successfully."}


@router.post("/{story_id}/publish-now", response_model=StoryResponse)
def publish_story_now(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Publish a Story immediately across targeted platforms."""
    return story_service.publish_story(db, story_id, current_user.id)


@router.post("/{story_id}/schedule", response_model=StoryResponse)
def schedule_story(
    story_id: int,
    req: StoryScheduleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Schedule a Story for publication at a future timestamp."""
    return story_service.schedule_story(db, story_id, current_user.id, req.scheduled_at)


@router.post("/{story_id}/retry", response_model=StoryResponse)
def retry_story(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retry publishing a failed Story."""
    return story_service.retry_story(db, story_id, current_user.id)

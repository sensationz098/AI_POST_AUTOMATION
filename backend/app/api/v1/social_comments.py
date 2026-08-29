from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.v1.deps import get_current_user
from app.models.user import User
from app.repositories.social_comment_repository import social_comment_repo

router = APIRouter(prefix="/social-comments", tags=["Social Comments"])

@router.get("/", response_model=List[dict])
def get_user_social_comments(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    platform: Optional[str] = Query(None, description="Filter by platform ('facebook' or 'instagram')"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve ingested social comments for the authenticated user only.
    Enforces user isolation and excludes any sensitive credentials.
    """
    comments = social_comment_repo.get_by_user_id(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        platform=platform
    )
    
    return [
        {
            "id": c.id,
            "social_account_id": c.social_account_id,
            "platform": c.platform,
            "external_comment_id": c.external_comment_id,
            "external_post_id": c.external_post_id,
            "parent_comment_id": c.parent_comment_id,
            "comment_text": c.comment_text,
            "commenter_id": c.commenter_id,
            "commenter_name": c.commenter_name,
            "event_timestamp": c.event_timestamp.isoformat() if c.event_timestamp else None,
            "webhook_object": c.webhook_object,
            "processing_status": c.processing_status,
            "created_at": c.created_at.isoformat() if c.created_at else None
        }
        for c in comments
    ]

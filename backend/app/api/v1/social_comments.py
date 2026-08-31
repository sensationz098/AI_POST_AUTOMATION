import logging
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.v1.deps import get_current_user
from app.models.user import User
from app.models.social_account import SocialAccount
from app.models.social_comment_reply import SocialCommentReply
from app.repositories.social_comment_repository import social_comment_repo
from app.core.security_encryption import decrypt_token
from app.services.meta_service import meta_service, MetaPublishException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/social-comments", tags=["Social Comments"])

class CommentReplyRequest(BaseModel):
    message: str = Field(..., description="Manual reply text message")

MAX_REPLY_LENGTH = 2000

@router.get("/", response_model=List[dict])
def get_user_social_comments(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    platform: Optional[str] = Query(None, description="Filter by platform ('facebook' or 'instagram')"),
    social_account_id: Optional[int] = Query(None, description="Filter by connected social account ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve ingested social comments for the authenticated user only.
    Enforces user isolation and excludes any sensitive credentials.
    Supports filtering by specific social_account_id owned by current_user.
    Filters out owner reply echoes at DB and API response layers.
    Includes persistent, chronologically sorted reply history for each comment.
    Includes associated post context (local DB or Meta Graph API fallback).
    """
    if social_account_id is not None:
        account = db.query(SocialAccount).filter(
            SocialAccount.id == social_account_id,
            SocialAccount.user_id == current_user.id
        ).first()
        if not account:
            raise HTTPException(status_code=404, detail="Social account not found")

    comments = social_comment_repo.get_by_user_id(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        platform=platform,
        social_account_id=social_account_id
    )
    
    # Defensive Protection: Fetch external_reply_ids for current_user to exclude any webhook echoes
    owner_reply_ids = {
        r[0] for r in db.query(SocialCommentReply.external_reply_id).filter(
            SocialCommentReply.user_id == current_user.id,
            SocialCommentReply.external_reply_id.isnot(None)
        ).all() if r[0]
    }
    
    # Stage 1: Batch lookup matching posts in local DB for current_user
    ext_post_ids = list({c.external_post_id.strip() for c in comments if c.external_post_id and c.external_post_id.strip()})
    fb_posts = {}
    ig_posts = {}
    
    if ext_post_ids:
        from app.models.post import Post
        matched_posts = db.query(Post).filter(
            Post.user_id == current_user.id,
            (Post.fb_post_id.in_(ext_post_ids)) | (Post.ig_media_id.in_(ext_post_ids))
        ).all()
        
        for p in matched_posts:
            if p.fb_post_id:
                fb_posts[p.fb_post_id.strip()] = p
            if p.ig_media_id:
                ig_posts[p.ig_media_id.strip()] = p

    # Stage 2: In-Memory Request Cache for Meta Graph API Fallback Lookups
    meta_resolved_posts: dict = {}
    
    # Pre-fetch user's connected social accounts for Meta API fallback
    connected_accounts = db.query(SocialAccount).filter(
        SocialAccount.user_id == current_user.id,
        SocialAccount.status == "CONNECTED"
    ).all()
    
    fb_account = next((a for a in connected_accounts if (a.platform or "").lower() == "facebook"), None)
    ig_account = next((a for a in connected_accounts if (a.platform or "").lower() == "instagram"), None)

    res_list = []
    for c in comments:
        # Defensive Check: Skip if this comment is an owner reply echo
        if c.external_comment_id in owner_reply_ids:
            continue

        post_obj = None
        if c.external_post_id and c.external_post_id.strip():
            ext_pid = c.external_post_id.strip()
            c_platform = (c.platform or "").lower()
            matched_post = None

            if c_platform == "facebook":
                matched_post = fb_posts.get(ext_pid)
            elif c_platform == "instagram":
                matched_post = ig_posts.get(ext_pid)

            if matched_post:
                post_obj = {
                    "id": matched_post.id,
                    "title": matched_post.title,
                    "caption": matched_post.caption,
                    "image_url": matched_post.image_url,
                    "media_type": matched_post.media_type,
                    "thumbnail_url": matched_post.thumbnail_url,
                    "platform": c.platform,
                    "source": "local"
                }
            else:
                # Stage 2: Meta Graph API Fallback with Request-Level Caching
                cache_key = f"{c_platform}:{ext_pid}"
                if cache_key in meta_resolved_posts:
                    post_obj = meta_resolved_posts[cache_key]
                else:
                    try:
                        if c_platform == "facebook" and fb_account:
                            token = decrypt_token(fb_account.access_token)
                            if token:
                                fb_meta = meta_service.fetch_facebook_post_info(ext_pid, token)
                                if fb_meta and isinstance(fb_meta, dict):
                                    msg = fb_meta.get("message") or ""
                                    title_text = msg.split("\n")[0][:60] if msg else "Facebook Post"
                                    post_obj = {
                                        "id": str(fb_meta.get("id") or ext_pid),
                                        "title": title_text,
                                        "caption": msg,
                                        "image_url": fb_meta.get("full_picture") or fb_meta.get("picture"),
                                        "media_type": "image",
                                        "thumbnail_url": fb_meta.get("picture") or fb_meta.get("full_picture"),
                                        "platform": "facebook",
                                        "source": "meta"
                                    }
                        elif c_platform == "instagram" and ig_account:
                            token = decrypt_token(ig_account.access_token)
                            if token:
                                ig_meta = meta_service.fetch_instagram_media_info(ext_pid, token)
                                if ig_meta and isinstance(ig_meta, dict):
                                    cap = ig_meta.get("caption") or ""
                                    title_text = cap.split("\n")[0][:60] if cap else "Instagram Post"
                                    post_obj = {
                                        "id": str(ig_meta.get("id") or ext_pid),
                                        "title": title_text,
                                        "caption": cap,
                                        "image_url": ig_meta.get("media_url") or ig_meta.get("thumbnail_url"),
                                        "media_type": (ig_meta.get("media_type") or "IMAGE").lower(),
                                        "thumbnail_url": ig_meta.get("thumbnail_url") or ig_meta.get("media_url"),
                                        "platform": "instagram",
                                        "source": "meta"
                                    }
                    except Exception as meta_err:
                        # Graceful Fallback: Log warning and leave post_obj as None
                        pass
                    
                    meta_resolved_posts[cache_key] = post_obj

        # Sort replies chronologically (oldest first: Oldest reply -> Newest reply)
        sorted_replies = sorted(
            (c.replies or []),
            key=lambda r: r.created_at or datetime.min.replace(tzinfo=timezone.utc)
        )

        res_list.append({
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
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "post": post_obj,
            "replies": [
                {
                    "id": r.id,
                    "message": r.message,
                    "status": r.status,
                    "error_message": r.error_message,
                    "external_reply_id": r.external_reply_id,
                    "created_at": r.created_at.isoformat() if r.created_at else None
                }
                for r in sorted_replies
            ]
        })
    return res_list

@router.post("/{comment_id}/reply", response_model=dict)
def reply_to_social_comment(
    comment_id: int,
    payload: CommentReplyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually reply to an ingested Facebook or Instagram comment.
    Strictly verifies comment and account ownership for current_user.
    Decrypts page/account access token server-side only.
    Never accepts access tokens or credentials from the client.
    """
    raw_message = payload.message or ""
    message = raw_message.strip()

    # Reply Validation
    if not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reply message cannot be empty or whitespace-only."
        )

    if len(message) > MAX_REPLY_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Reply message exceeds maximum allowed length of {MAX_REPLY_LENGTH} characters."
        )

    # 1. Ownership & Comment Existence Check
    comment = social_comment_repo.get_by_id_and_user_id(db, comment_id=comment_id, user_id=current_user.id)
    if not comment:
        # Do not expose existence to unauthorized users
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found or access denied."
        )

    # 2. Associated SocialAccount Ownership & Status Verification
    social_account = db.query(SocialAccount).filter(
        SocialAccount.id == comment.social_account_id,
        SocialAccount.user_id == current_user.id
    ).first()

    if not social_account:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Associated social account not found or access denied."
        )

    if social_account.status != "CONNECTED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Social account is not active (status: {social_account.status}). Please reconnect your account."
        )

    # 3. Decrypt Token Server-Side
    decrypted_access_token = decrypt_token(social_account.access_token)
    if not decrypted_access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid access token available for social account."
        )

    # 4. Idempotency / Duplicate Protection Check
    now = datetime.now(timezone.utc)
    ten_seconds_ago = now - timedelta(seconds=10)
    existing_recent_reply = db.query(SocialCommentReply).filter(
        SocialCommentReply.comment_id == comment.id,
        SocialCommentReply.user_id == current_user.id,
        SocialCommentReply.message == message,
        SocialCommentReply.status == "SUCCESS",
        SocialCommentReply.created_at >= ten_seconds_ago
    ).first()

    if existing_recent_reply:
        return {
            "status": "success",
            "platform": comment.platform,
            "comment_id": comment.id,
            "external_reply_id": existing_recent_reply.external_reply_id,
            "message": "Duplicate reply detected and prevented."
        }

    # 5. Send Reply via Meta Graph API Service
    platform = (comment.platform or "").lower()
    try:
        if platform == "facebook":
            res = meta_service.reply_to_facebook_comment(
                comment_id=comment.external_comment_id,
                access_token=decrypted_access_token,
                message=message
            )
        elif platform == "instagram":
            res = meta_service.reply_to_instagram_comment(
                comment_id=comment.external_comment_id,
                access_token=decrypted_access_token,
                message=message
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported platform '{comment.platform}' for comment replies."
            )

        external_reply_id = str(res.get("id", ""))

        # Record Successful Audit Entry
        social_comment_repo.create_reply_audit(
            db=db,
            comment_id=comment.id,
            user_id=current_user.id,
            platform=platform,
            message=message,
            external_reply_id=external_reply_id,
            status="SUCCESS"
        )

        return {
            "status": "success",
            "platform": platform,
            "comment_id": comment.id,
            "external_reply_id": external_reply_id,
            "message": "Reply published successfully."
        }

    except Exception as e:
        # Audit Log Failure
        safe_error_msg = str(e)
        social_comment_repo.create_reply_audit(
            db=db,
            comment_id=comment.id,
            user_id=current_user.id,
            platform=platform,
            message=message,
            status="FAILED",
            error_message=safe_error_msg
        )

        return {
            "status": "failed",
            "message": "Unable to publish reply. Please try again."
        }


@router.delete("/{comment_id}", response_model=dict)
def delete_social_comment(
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Production-safe deletion of a social comment from Meta Graph API and local DB.
    Strictly verifies ownership for current_user.
    Decrypts token server-side only.
    Only marks local comment deleted after Meta confirms successful deletion.
    """
    # 1. Ownership & Comment Existence Check
    comment = social_comment_repo.get_by_id_and_user_id(db, comment_id=comment_id, user_id=current_user.id)
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found or access denied."
        )

    if comment.is_deleted:
        return {
            "status": "success",
            "message": "Comment is already deleted.",
            "comment_id": comment.id
        }

    # 2. Associated SocialAccount Ownership & Status Verification
    social_account = db.query(SocialAccount).filter(
        SocialAccount.id == comment.social_account_id,
        SocialAccount.user_id == current_user.id
    ).first()

    if not social_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated social account not found or access denied."
        )

    if social_account.status != "CONNECTED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Social account is not active (status: {social_account.status}). Please reconnect your account."
        )

    # 3. Decrypt Token Server-Side
    decrypted_access_token = decrypt_token(social_account.access_token)
    if not decrypted_access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to decrypt social account credentials. Please reconnect your account."
        )

    # 4. Meta Graph API Deletion
    platform = (comment.platform or "").lower()
    try:
        if platform == "facebook":
            meta_service.delete_facebook_comment(
                external_comment_id=comment.external_comment_id,
                access_token=decrypted_access_token
            )
        elif platform == "instagram":
            meta_service.delete_instagram_comment(
                external_comment_id=comment.external_comment_id,
                access_token=decrypted_access_token
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported platform '{comment.platform}' for comment deletion."
            )
    except HTTPException:
        raise
    except Exception as meta_err:
        logger.error(f"[COMMENT_DELETE_ERROR] Failed to delete comment {comment_id} on {platform}: {meta_err}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to delete this comment from {platform.capitalize()}. Please check account permissions or try again."
        )

    # 5. Update Local Database State Only After Meta Deletion Success
    social_comment_repo.mark_as_deleted(db, comment_id=comment.id, user_id=current_user.id)

    return {
        "status": "success",
        "message": f"Comment deleted from {platform.capitalize()} successfully.",
        "comment_id": comment.id
    }


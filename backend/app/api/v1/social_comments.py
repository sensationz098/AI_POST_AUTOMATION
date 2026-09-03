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
    meta_ad_id: Optional[int] = Query(None, description="Filter by Meta Ad DB ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve ingested social comments for the authenticated user only.
    Enforces user isolation and excludes any sensitive credentials.
    Supports filtering by specific social_account_id owned by current_user and meta_ad_id.
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
        social_account_id=social_account_id,
        meta_ad_id=meta_ad_id
    )

    ad_count = sum(1 for c in comments if c.meta_ad_id is not None)
    organic_count = len(comments) - ad_count
    logger.info(
        f"[COMMENTS_API] user_id={current_user.id} total_retrieved={len(comments)} "
        f"organic_count={organic_count} ad_comment_count={ad_count}"
    )
    
    # Defensive Protection: Fetch external_reply_ids for current_user to exclude any webhook echoes
    owner_reply_ids = {
        r[0] for r in db.query(SocialCommentReply.external_reply_id).filter(
            SocialCommentReply.user_id == current_user.id,
            SocialCommentReply.external_reply_id.isnot(None)
        ).all() if r[0]
    }

    # Tier 1: Batch lookup matching posts in local DB for current_user
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

    # Tier 2: Batch lookup in ExternalPostContext database cache table
    remaining_comments = [
        c for c in comments
        if c.external_post_id and c.external_post_id.strip() and
        c.external_post_id.strip() not in fb_posts and
        c.external_post_id.strip() not in ig_posts
    ]

    cached_ext_posts = {}
    if remaining_comments:
        from app.models.external_post_context import ExternalPostContext
        req_acc_ids = {c.social_account_id for c in remaining_comments if c.social_account_id}
        req_pids = {c.external_post_id.strip() for c in remaining_comments}

        if req_acc_ids and req_pids:
            ext_contexts = db.query(ExternalPostContext).filter(
                ExternalPostContext.social_account_id.in_(req_acc_ids),
                ExternalPostContext.external_post_id.in_(req_pids)
            ).all()
            for ctx in ext_contexts:
                key = (ctx.social_account_id, (ctx.platform or "").lower(), ctx.external_post_id.strip())
                cached_ext_posts[key] = ctx

    # Tier 3: Fetch missing post context from Meta Graph API using specific connected SocialAccount token & persist
    missing_tuples = []
    for c in comments:
        if c.external_post_id and c.external_post_id.strip():
            pid = c.external_post_id.strip()
            c_plat = (c.platform or "").lower()
            acc_id = c.social_account_id
            if pid not in fb_posts and pid not in ig_posts:
                key = (acc_id, c_plat, pid)
                if key not in cached_ext_posts:
                    missing_tuples.append((c_plat, acc_id, pid))

    unique_missing = list(dict.fromkeys(missing_tuples))
    if unique_missing:
        from app.models.external_post_context import ExternalPostContext
        account_ids = {item[1] for item in unique_missing if item[1]}
        social_acc_map = {}
        if account_ids:
            accs = db.query(SocialAccount).filter(
                SocialAccount.id.in_(account_ids),
                SocialAccount.user_id == current_user.id
            ).all()
            social_acc_map = {a.id: a for a in accs}

        new_contexts_to_add = []
        for c_platform, acc_id, pid in unique_missing:
            acc = social_acc_map.get(acc_id)
            if not acc:
                acc = db.query(SocialAccount).filter(
                    SocialAccount.user_id == current_user.id,
                    SocialAccount.platform == c_platform,
                    SocialAccount.status == "CONNECTED"
                ).first()
                if acc:
                    acc_id = acc.id

            token = decrypt_token(acc.access_token) if (acc and acc.access_token) else None
            meta_data = None
            if token:
                try:
                    if c_platform == "facebook":
                        meta_data = meta_service.fetch_facebook_post_info(pid, token)
                    elif c_platform == "instagram":
                        meta_data = meta_service.fetch_instagram_media_info(pid, token)
                except Exception as fetch_err:
                    logger.warning(f"[COMMENTS_API] Error fetching post {pid} for platform {c_platform}: {fetch_err}")

            if acc_id:
                if meta_data and isinstance(meta_data, dict):
                    cap = meta_data.get("caption") or meta_data.get("message") or ""
                    media_url = meta_data.get("media_url") or meta_data.get("full_picture") or meta_data.get("picture")
                    thumb_url = meta_data.get("thumbnail_url") or meta_data.get("picture") or media_url
                    permalink = meta_data.get("permalink") or meta_data.get("permalink_url")
                    media_type = (meta_data.get("media_type") or "IMAGE").upper()

                    ctx = ExternalPostContext(
                        platform=c_platform,
                        social_account_id=acc_id,
                        external_post_id=pid,
                        caption=cap,
                        media_type=media_type,
                        media_url=media_url,
                        thumbnail_url=thumb_url,
                        permalink=permalink,
                        status="ACTIVE",
                        metadata_json=meta_data
                    )
                else:
                    # Save placeholder status='UNAVAILABLE' so subsequent loads hit Tier 2 cache directly
                    ctx = ExternalPostContext(
                        platform=c_platform,
                        social_account_id=acc_id,
                        external_post_id=pid,
                        status="UNAVAILABLE"
                    )
                new_contexts_to_add.append(ctx)

        if new_contexts_to_add:
            try:
                db.add_all(new_contexts_to_add)
                db.commit()
                for ctx in new_contexts_to_add:
                    key = (ctx.social_account_id, (ctx.platform or "").lower(), ctx.external_post_id.strip())
                    cached_ext_posts[key] = ctx
            except Exception as commit_err:
                db.rollback()
                logger.error(f"[COMMENTS_API] Exception committing external post contexts: {commit_err}")

    # Build final response list with account context & resolved post context
    res_list = []
    for c in comments:
        # Defensive Check: Skip if this comment is an owner reply echo
        if c.external_comment_id in owner_reply_ids:
            continue

        # Account Context Resolution
        acc_obj = None
        sa = c.social_account
        if sa:
            is_ig = (sa.platform or "").lower() == "instagram"
            acc_obj = {
                "id": sa.id,
                "account_id": sa.account_id,
                "account_name": sa.account_name,
                "username": sa.account_name if is_ig else None,
                "display_name": sa.account_name,
                "platform": sa.platform,
                "logo_url": sa.logo_url
            }
        else:
            acc_obj = {
                "id": c.social_account_id,
                "account_id": "unknown",
                "account_name": f"{c.platform.capitalize()} Account #{c.social_account_id}",
                "username": None,
                "display_name": f"{c.platform.capitalize()} Account #{c.social_account_id}",
                "platform": c.platform,
                "logo_url": None
            }

        # Post Context Resolution
        post_obj = None
        if c.external_post_id and c.external_post_id.strip():
            ext_pid = c.external_post_id.strip()
            c_platform = (c.platform or "").lower()

            matched_local = fb_posts.get(ext_pid) if c_platform == "facebook" else ig_posts.get(ext_pid)
            if matched_local:
                title_txt = matched_local.title or (matched_local.caption[:60] if matched_local.caption else "Social Post")
                post_obj = {
                    "id": matched_local.id,
                    "title": title_txt,
                    "caption": matched_local.caption,
                    "image_url": matched_local.image_url,
                    "media_type": matched_local.media_type,
                    "thumbnail_url": matched_local.thumbnail_url,
                    "permalink": None,
                    "platform": c.platform,
                    "source": "local"
                }
            else:
                key = (c.social_account_id, c_platform, ext_pid)
                ext_ctx = cached_ext_posts.get(key)
                if ext_ctx and ext_ctx.status == "ACTIVE":
                    title_txt = ext_ctx.caption.split("\n")[0][:60] if ext_ctx.caption else f"{c.platform.capitalize()} Post"
                    post_obj = {
                        "id": ext_ctx.external_post_id,
                        "title": title_txt,
                        "caption": ext_ctx.caption,
                        "image_url": ext_ctx.media_url,
                        "media_type": (ext_ctx.media_type or "IMAGE").lower(),
                        "thumbnail_url": ext_ctx.thumbnail_url or ext_ctx.media_url,
                        "permalink": ext_ctx.permalink,
                        "platform": c.platform,
                        "source": "meta"
                    }

        # Sort replies chronologically (oldest first: Oldest reply -> Newest reply)
        sorted_replies = sorted(
            (c.replies or []),
            key=lambda r: r.created_at or datetime.min.replace(tzinfo=timezone.utc)
        )

        meta_ad_obj = None
        if c.meta_ad:
            meta_ad_obj = {
                "id": c.meta_ad.id,
                "meta_ad_id": c.meta_ad.meta_ad_id,
                "name": c.meta_ad.name,
                "campaign_name": c.meta_ad.campaign_name,
                "adset_name": c.meta_ad.adset_name,
                "effective_status": c.meta_ad.effective_status
            }

        logger.debug(
            f"[META_COMMENT_API_IDENTITY] comment_id={c.external_comment_id} "
            f"commenter_name={c.commenter_name or 'NONE'} commenter_id_present={bool(c.commenter_id)}"
        )

        res_list.append({
            "id": c.id,
            "social_account_id": c.social_account_id,
            "meta_ad_id": c.meta_ad_id,
            "meta_ad": meta_ad_obj,
            "account": acc_obj,
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


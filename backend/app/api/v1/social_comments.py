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
from app.models.social_comment import SocialComment
from app.models.social_comment_reply import SocialCommentReply
from app.repositories.social_comment_repository import social_comment_repo
from app.core.security_encryption import decrypt_token
from app.services.meta_service import meta_service, MetaPublishException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/social-comments", tags=["Social Comments"])

class CommentReplyRequest(BaseModel):
    message: str = Field(..., description="Manual reply text message")

MAX_REPLY_LENGTH = 2000

def _resolve_ad_permalink(ad: Optional[Any], db: Session, ctx_map: Optional[dict] = None) -> Optional[str]:
    """
    Resolves the canonical external permalink for a Meta Ad using existing ExternalPostContext records,
    creative metadata, or platform post IDs. Uses ctx_map to avoid N+1 DB queries.
    """
    if not ad:
        return None

    meta_json = ad.metadata_json or {}
    if isinstance(meta_json, dict):
        p_url = meta_json.get("permalink_url") or meta_json.get("permalink") or meta_json.get("instagram_permalink_url")
        if p_url and isinstance(p_url, str) and (p_url.startswith("http://") or p_url.startswith("https://")):
            return p_url

    if ad.facebook_post_id and ad.facebook_post_id.strip():
        fb_pid = ad.facebook_post_id.strip()
        if ctx_map is not None:
            ctx = ctx_map.get(fb_pid)
            if ctx and ctx.permalink:
                return ctx.permalink
        else:
            from app.models.external_post_context import ExternalPostContext
            ctx = db.query(ExternalPostContext).filter(ExternalPostContext.external_post_id == fb_pid).first()
            if ctx and ctx.permalink:
                return ctx.permalink
        return f"https://www.facebook.com/{fb_pid}"

    ig_mid = ad.instagram_media_id or (ad.engagement_object_id if ad.engagement_object_type == "INSTAGRAM_MEDIA" else None)
    if ig_mid and ig_mid.strip():
        ig_mid = ig_mid.strip()
        if ctx_map is not None:
            ctx = ctx_map.get(ig_mid)
            if ctx and ctx.permalink:
                return ctx.permalink
        else:
            from app.models.external_post_context import ExternalPostContext
            ctx = db.query(ExternalPostContext).filter(ExternalPostContext.external_post_id == ig_mid).first()
            if ctx and ctx.permalink:
                return ctx.permalink
        return f"https://www.instagram.com/p/{ig_mid}"

    return None


def _resolve_post_permalink(ext_pid: Optional[str], platform: str, db: Session, local_post: Optional[Any] = None, ctx_map: Optional[dict] = None) -> Optional[str]:
    """
    Resolves the canonical external permalink for an organic post using ExternalPostContext,
    local post identifiers, or standard platform URL structures. Uses ctx_map to avoid N+1 DB queries.
    """
    c_platform = (platform or "").lower()

    if local_post:
        if local_post.fb_post_id and local_post.fb_post_id.strip():
            fb_pid = local_post.fb_post_id.strip()
            if ctx_map is not None:
                ctx = ctx_map.get(fb_pid)
                if ctx and ctx.permalink:
                    return ctx.permalink
            else:
                from app.models.external_post_context import ExternalPostContext
                ctx = db.query(ExternalPostContext).filter(ExternalPostContext.external_post_id == fb_pid).first()
                if ctx and ctx.permalink:
                    return ctx.permalink
            return f"https://www.facebook.com/{fb_pid}"
        elif local_post.ig_media_id and local_post.ig_media_id.strip():
            ig_mid = local_post.ig_media_id.strip()
            if ctx_map is not None:
                ctx = ctx_map.get(ig_mid)
                if ctx and ctx.permalink:
                    return ctx.permalink
            else:
                from app.models.external_post_context import ExternalPostContext
                ctx = db.query(ExternalPostContext).filter(ExternalPostContext.external_post_id == ig_mid).first()
                if ctx and ctx.permalink:
                    return ctx.permalink
            return f"https://www.instagram.com/p/{ig_mid}"

    if not ext_pid or not ext_pid.strip():
        return None

    clean_pid = ext_pid.strip()
    if ctx_map is not None:
        ctx = ctx_map.get(clean_pid)
        if ctx and ctx.permalink:
            return ctx.permalink
    else:
        from app.models.external_post_context import ExternalPostContext
        ctx = db.query(ExternalPostContext).filter(ExternalPostContext.external_post_id == clean_pid).first()
        if ctx and ctx.permalink:
            return ctx.permalink

    if "facebook" in c_platform:
        return f"https://www.facebook.com/{clean_pid}"
    elif "instagram" in c_platform:
        return f"https://www.instagram.com/p/{clean_pid}"

    return None


def _format_comments_response_list(comments: List[SocialComment], current_user: User, db: Session) -> List[dict]:
    """Helper function to cleanly format a list of SocialComment DB models into API response objects with resolved post, account, and reply metadata."""
    if not comments:
        return []

    # Defensive Protection: Fetch external_reply_ids for current_user to exclude any webhook echoes
    owner_reply_ids = {
        r[0] for r in db.query(SocialCommentReply.external_reply_id).filter(
            SocialCommentReply.user_id == current_user.id,
            SocialCommentReply.external_reply_id.isnot(None)
        ).all() if r[0]
    }

    # Collect all post/ad IDs for batch lookup in ExternalPostContext and Post
    ext_post_ids = set()
    for c in comments:
        if c.external_post_id and c.external_post_id.strip():
            ext_post_ids.add(c.external_post_id.strip())
        if c.meta_ad:
            if c.meta_ad.facebook_post_id and c.meta_ad.facebook_post_id.strip():
                ext_post_ids.add(c.meta_ad.facebook_post_id.strip())
            if c.meta_ad.instagram_media_id and c.meta_ad.instagram_media_id.strip():
                ext_post_ids.add(c.meta_ad.instagram_media_id.strip())
            if c.meta_ad.engagement_object_id and c.meta_ad.engagement_object_id.strip():
                ext_post_ids.add(c.meta_ad.engagement_object_id.strip())

    ext_post_ids_list = list(ext_post_ids)
    fb_posts = {}
    ig_posts = {}

    if ext_post_ids_list:
        from app.models.post import Post
        matched_posts = db.query(Post).filter(
            Post.user_id == current_user.id,
            (Post.fb_post_id.in_(ext_post_ids_list)) | (Post.ig_media_id.in_(ext_post_ids_list))
        ).all()

        for p in matched_posts:
            if p.fb_post_id:
                fb_posts[p.fb_post_id.strip()] = p
            if p.ig_media_id:
                ig_posts[p.ig_media_id.strip()] = p

    # Batch lookup ALL relevant ExternalPostContext records in 1 query
    cached_ext_posts = {}
    ctx_map_by_ext_id = {}
    if ext_post_ids_list:
        from app.models.external_post_context import ExternalPostContext
        ext_contexts = db.query(ExternalPostContext).filter(
            ExternalPostContext.external_post_id.in_(ext_post_ids_list)
        ).all()
        for ctx in ext_contexts:
            ctx_map_by_ext_id[ctx.external_post_id.strip()] = ctx
            if ctx.social_account_id:
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
                    ctx_map_by_ext_id[ctx.external_post_id.strip()] = ctx
            except Exception as commit_err:
                db.rollback()
                logger.error(f"[COMMENTS_API] Exception committing external post contexts: {commit_err}")

    # Batch lookup child SocialComment records (Meta-ingested replies) for top-level comments
    parent_ext_ids = {c.external_comment_id for c in comments if c.external_comment_id}
    parent_int_ids = {str(c.id) for c in comments if c.id}
    all_parent_ids = parent_ext_ids.union(parent_int_ids)

    child_comments_map = {}
    if all_parent_ids:
        child_comments = db.query(SocialComment).filter(
            SocialComment.user_id == current_user.id,
            SocialComment.is_deleted.isnot(True),
            SocialComment.parent_comment_id.in_(all_parent_ids)
        ).all()
        for child in child_comments:
            if child.external_comment_id and child.external_comment_id in owner_reply_ids:
                continue
            p_id = child.parent_comment_id
            if p_id not in child_comments_map:
                child_comments_map[p_id] = []
            child_comments_map[p_id].append(child)

    # Build final response list with account context & resolved post context
    res_list = []
    for c in comments:
        if c.external_comment_id in owner_reply_ids:
            continue

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
                    "permalink": _resolve_post_permalink(ext_pid, c.platform, db, local_post=matched_local, ctx_map=ctx_map_by_ext_id),
                    "platform": c.platform,
                    "source": "local"
                }
            else:
                key = (c.social_account_id, c_platform, ext_pid)
                ext_ctx = cached_ext_posts.get(key) or ctx_map_by_ext_id.get(ext_pid)
                if ext_ctx and ext_ctx.status == "ACTIVE":
                    title_txt = ext_ctx.caption.split("\n")[0][:60] if ext_ctx.caption else f"{c.platform.capitalize()} Post"
                    post_obj = {
                        "id": ext_ctx.external_post_id,
                        "title": title_txt,
                        "caption": ext_ctx.caption,
                        "image_url": ext_ctx.media_url,
                        "media_type": (ext_ctx.media_type or "IMAGE").lower(),
                        "thumbnail_url": ext_ctx.thumbnail_url or ext_ctx.media_url,
                        "permalink": ext_ctx.permalink or _resolve_post_permalink(ext_pid, c.platform, db, ctx_map=ctx_map_by_ext_id),
                        "platform": c.platform,
                        "source": "meta"
                    }

        # Combine SocialCommentReply records and child SocialComment records (Meta replies)
        formatted_replies = []
        for r in (c.replies or []):
            formatted_replies.append({
                "id": r.id,
                "message": r.message,
                "status": r.status,
                "error_message": r.error_message,
                "external_reply_id": r.external_reply_id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "commenter_name": None,
                "source": "owner"
            })

        meta_child_comments = child_comments_map.get(c.external_comment_id, []) + child_comments_map.get(str(c.id), [])
        for child in meta_child_comments:
            formatted_replies.append({
                "id": child.id,
                "message": child.comment_text,
                "status": "SUCCESS",
                "error_message": None,
                "external_reply_id": child.external_comment_id,
                "created_at": child.created_at.isoformat() if child.created_at else None,
                "commenter_name": child.commenter_name,
                "commenter_id": child.commenter_id,
                "source": "meta"
            })

        formatted_replies.sort(key=lambda r: r.get("created_at") or "")

        meta_ad_obj = None
        if c.meta_ad:
            meta_ad_obj = {
                "id": c.meta_ad.id,
                "meta_ad_id": c.meta_ad.meta_ad_id,
                "name": c.meta_ad.name,
                "campaign_name": c.meta_ad.campaign_name,
                "adset_name": c.meta_ad.adset_name,
                "effective_status": c.meta_ad.effective_status,
                "permalink": _resolve_ad_permalink(c.meta_ad, db, ctx_map=ctx_map_by_ext_id),
                "platform": "facebook" if (not c.meta_ad.engagement_object_type or c.meta_ad.engagement_object_type == "FACEBOOK_POST") else "instagram"
            }

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
            "replies": formatted_replies
        })
    return res_list


@router.get("/", response_model=List[dict])
def get_user_social_comments(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    platform: Optional[str] = Query(None, description="Filter by platform ('facebook' or 'instagram')"),
    social_account_id: Optional[int] = Query(None, description="Filter by connected social account ID"),
    meta_ad_id: Optional[int] = Query(None, description="Filter by Meta Ad DB ID"),
    external_post_id: Optional[str] = Query(None, description="Filter by external post ID"),
    is_ad: Optional[bool] = Query(None, description="Filter ad vs organic comments"),
    reply_status: Optional[str] = Query(None, description="Filter by reply status: 'all', 'replied', or 'unreplied'"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve ingested social comments for the authenticated user only.
    Enforces user isolation and excludes any sensitive credentials.
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
        meta_ad_id=meta_ad_id,
        external_post_id=external_post_id,
        is_ad=is_ad,
        top_level_only=True,
        reply_status=reply_status
    )

    return _format_comments_response_list(comments, current_user, db)


@router.get("/overview", response_model=dict)
def get_engagement_overview(
    social_account_id: Optional[int] = Query(None, description="Filter by connected social account ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve high-level Engagement metrics and recent top Ads & Posts with clear comment counts.
    Strictly scoped to social_account_id if provided.
    """
    if social_account_id is not None:
        account = db.query(SocialAccount).filter(
            SocialAccount.id == social_account_id,
            SocialAccount.user_id == current_user.id
        ).first()
        if not account:
            raise HTTPException(status_code=404, detail="Social account not found")

    top_level_comment_count = social_comment_repo.count_by_user_id(db, current_user.id, social_account_id=social_account_id, top_level_only=True)
    reply_count = social_comment_repo.count_replies_by_user_id(db, current_user.id, social_account_id=social_account_id)
    total_interaction_count = top_level_comment_count + reply_count

    total_ad_comments = social_comment_repo.count_by_user_id(db, current_user.id, social_account_id=social_account_id, is_ad=True, top_level_only=True)
    total_post_comments = social_comment_repo.count_by_user_id(db, current_user.id, social_account_id=social_account_id, is_ad=False, top_level_only=True)

    from app.models.social_comment import SocialComment
    from app.models.social_comment_reply import SocialCommentReply
    from app.models.meta_ad import MetaAd
    from sqlalchemy import func, or_

    # Top-level comment counts per MetaAd
    ad_top_q = db.query(
        SocialComment.meta_ad_id,
        func.count(SocialComment.id)
    ).filter(
        SocialComment.user_id == current_user.id,
        SocialComment.is_deleted.isnot(True),
        SocialComment.meta_ad_id.isnot(None),
        or_(SocialComment.parent_comment_id.is_(None), SocialComment.parent_comment_id == "")
    )
    if social_account_id:
        ad_top_q = ad_top_q.filter(SocialComment.social_account_id == social_account_id)
    ad_top_counts_raw = ad_top_q.group_by(SocialComment.meta_ad_id).all()

    ad_top_map = {row[0]: row[1] for row in ad_top_counts_raw if row[0]}

    # Meta child replies per MetaAd
    ad_meta_reply_q = db.query(
        SocialComment.meta_ad_id,
        func.count(SocialComment.id)
    ).filter(
        SocialComment.user_id == current_user.id,
        SocialComment.is_deleted.isnot(True),
        SocialComment.meta_ad_id.isnot(None),
        SocialComment.parent_comment_id.isnot(None),
        SocialComment.parent_comment_id != ""
    )
    if social_account_id:
        ad_meta_reply_q = ad_meta_reply_q.filter(SocialComment.social_account_id == social_account_id)
    ad_meta_reply_raw = ad_meta_reply_q.group_by(SocialComment.meta_ad_id).all()
    ad_meta_reply_map = {row[0]: row[1] for row in ad_meta_reply_raw if row[0]}

    # Manual owner replies per MetaAd
    ad_manual_reply_q = db.query(
        SocialComment.meta_ad_id,
        func.count(SocialCommentReply.id)
    ).join(
        SocialCommentReply, SocialCommentReply.comment_id == SocialComment.id
    ).filter(
        SocialCommentReply.user_id == current_user.id,
        SocialCommentReply.status == "SUCCESS",
        SocialComment.is_deleted.isnot(True),
        SocialComment.meta_ad_id.isnot(None)
    )
    if social_account_id:
        ad_manual_reply_q = ad_manual_reply_q.filter(SocialComment.social_account_id == social_account_id)
    ad_manual_reply_raw = ad_manual_reply_q.group_by(SocialComment.meta_ad_id).all()
    ad_manual_reply_map = {row[0]: row[1] for row in ad_manual_reply_raw if row[0]}

    # Top recent Ads with comments
    recent_ads_db = db.query(MetaAd).filter(
        MetaAd.user_id == current_user.id,
        MetaAd.id.in_(list(ad_top_map.keys()))
    ).order_by(MetaAd.updated_at.desc()).limit(6).all() if ad_top_map else []

    recent_ads = []
    for ad in recent_ads_db:
        t_cnt = ad_top_map.get(ad.id, 0)
        r_cnt = ad_meta_reply_map.get(ad.id, 0) + ad_manual_reply_map.get(ad.id, 0)
        recent_ads.append({
            "id": ad.id,
            "meta_ad_id": ad.meta_ad_id,
            "name": ad.name,
            "campaign_name": ad.campaign_name,
            "adset_name": ad.adset_name,
            "effective_status": ad.effective_status,
            "facebook_page_id": ad.facebook_page_id,
            "meta_ad_account_id": ad.meta_ad_account_id,
            "top_level_comment_count": t_cnt,
            "reply_count": r_cnt,
            "total_interaction_count": t_cnt + r_cnt,
            "comment_count": t_cnt
        })

    # Top-level comment counts per organic external_post_id
    post_top_q = db.query(
        SocialComment.external_post_id,
        func.count(SocialComment.id)
    ).filter(
        SocialComment.user_id == current_user.id,
        SocialComment.is_deleted.isnot(True),
        SocialComment.meta_ad_id.is_(None),
        SocialComment.external_post_id.isnot(None),
        or_(SocialComment.parent_comment_id.is_(None), SocialComment.parent_comment_id == "")
    )
    if social_account_id:
        post_top_q = post_top_q.filter(SocialComment.social_account_id == social_account_id)
    post_top_raw = post_top_q.group_by(SocialComment.external_post_id).all()

    post_top_map = {row[0]: row[1] for row in post_top_raw if row[0]}

    from app.models.post import Post
    from app.models.external_post_context import ExternalPostContext

    recent_posts = []
    if post_top_map:
        matched_local_posts = db.query(Post).filter(
            Post.user_id == current_user.id,
            (Post.fb_post_id.in_(list(post_top_map.keys()))) | (Post.ig_media_id.in_(list(post_top_map.keys())))
        ).limit(6).all()

        added_pids = set()
        for p in matched_local_posts:
            ext_id = p.fb_post_id or p.ig_media_id or str(p.id)
            c_cnt = post_top_map.get(p.fb_post_id, 0) or post_top_map.get(p.ig_media_id, 0) or 0
            recent_posts.append({
                "id": p.id,
                "external_post_id": ext_id,
                "title": p.title or (p.caption[:60] if p.caption else "Organic Post"),
                "caption": p.caption,
                "image_url": p.image_url,
                "media_type": p.media_type,
                "platform": "facebook" if p.fb_post_id else "instagram",
                "published_at": p.published_at.isoformat() if p.published_at else p.created_at.isoformat(),
                "top_level_comment_count": c_cnt,
                "comment_count": c_cnt
            })
            if p.fb_post_id: added_pids.add(p.fb_post_id)
            if p.ig_media_id: added_pids.add(p.ig_media_id)

        # External cached posts fallback
        remaining_pids = [pid for pid in post_top_map.keys() if pid not in added_pids]
        if remaining_pids and len(recent_posts) < 6:
            ext_ctx_q = db.query(ExternalPostContext).filter(
                ExternalPostContext.external_post_id.in_(remaining_pids)
            )
            if social_account_id:
                ext_ctx_q = ext_ctx_q.filter(ExternalPostContext.social_account_id == social_account_id)
            ext_ctxs = ext_ctx_q.limit(6 - len(recent_posts)).all()

            for ctx in ext_ctxs:
                c_cnt = post_top_map.get(ctx.external_post_id, 0)
                recent_posts.append({
                    "id": ctx.external_post_id,
                    "external_post_id": ctx.external_post_id,
                    "title": ctx.caption.split("\n")[0][:60] if ctx.caption else f"{ctx.platform.capitalize()} Post",
                    "caption": ctx.caption,
                    "image_url": ctx.media_url,
                    "media_type": ctx.media_type,
                    "platform": ctx.platform,
                    "published_at": ctx.created_at.isoformat() if ctx.created_at else None,
                    "top_level_comment_count": c_cnt,
                    "comment_count": c_cnt
                })

    return {
        "top_level_comment_count": top_level_comment_count,
        "reply_count": reply_count,
        "total_interaction_count": total_interaction_count,
        "total_comments": top_level_comment_count,
        "total_ad_comments": total_ad_comments,
        "total_post_comments": total_post_comments,
        "recent_ads": recent_ads,
        "recent_posts": recent_posts
    }


@router.get("/ads", response_model=List[dict])
def get_meta_ads_with_comments(
    status: Optional[str] = Query(None, description="Filter by ad status ('ACTIVE', 'PAUSED', 'ALL')"),
    ad_account_id: Optional[str] = Query(None, description="Filter by Meta Ad Account ID"),
    social_account_id: Optional[int] = Query(None, description="Filter by connected social account ID"),
    q: Optional[str] = Query(None, description="Search ad name, campaign, or adset"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve all Meta Ads for authenticated user with exact non-deleted comment & reply metrics.
    Optionally scoped to a specific social_account_id.
    """
    if social_account_id is not None:
        account = db.query(SocialAccount).filter(
            SocialAccount.id == social_account_id,
            SocialAccount.user_id == current_user.id
        ).first()
        if not account:
            raise HTTPException(status_code=404, detail="Social account not found")
    else:
        account = None

    from app.models.meta_ad import MetaAd
    from app.models.social_comment import SocialComment
    from app.models.social_comment_reply import SocialCommentReply
    from sqlalchemy import func, or_

    # Top-level comment counts per MetaAd
    ad_top_q = db.query(
        SocialComment.meta_ad_id,
        func.count(SocialComment.id)
    ).filter(
        SocialComment.user_id == current_user.id,
        SocialComment.is_deleted.isnot(True),
        SocialComment.meta_ad_id.isnot(None),
        or_(SocialComment.parent_comment_id.is_(None), SocialComment.parent_comment_id == "")
    )
    if social_account_id:
        ad_top_q = ad_top_q.filter(SocialComment.social_account_id == social_account_id)
    ad_top_counts_raw = ad_top_q.group_by(SocialComment.meta_ad_id).all()
    ad_top_map = {row[0]: row[1] for row in ad_top_counts_raw if row[0]}

    # Meta child replies per MetaAd
    ad_meta_reply_q = db.query(
        SocialComment.meta_ad_id,
        func.count(SocialComment.id)
    ).filter(
        SocialComment.user_id == current_user.id,
        SocialComment.is_deleted.isnot(True),
        SocialComment.meta_ad_id.isnot(None),
        SocialComment.parent_comment_id.isnot(None),
        SocialComment.parent_comment_id != ""
    )
    if social_account_id:
        ad_meta_reply_q = ad_meta_reply_q.filter(SocialComment.social_account_id == social_account_id)
    ad_meta_reply_raw = ad_meta_reply_q.group_by(SocialComment.meta_ad_id).all()
    ad_meta_reply_map = {row[0]: row[1] for row in ad_meta_reply_raw if row[0]}

    # Manual owner replies per MetaAd
    ad_manual_reply_q = db.query(
        SocialComment.meta_ad_id,
        func.count(SocialCommentReply.id)
    ).join(
        SocialCommentReply, SocialCommentReply.comment_id == SocialComment.id
    ).filter(
        SocialCommentReply.user_id == current_user.id,
        SocialCommentReply.status == "SUCCESS",
        SocialComment.is_deleted.isnot(True),
        SocialComment.meta_ad_id.isnot(None)
    )
    if social_account_id:
        ad_manual_reply_q = ad_manual_reply_q.filter(SocialComment.social_account_id == social_account_id)
    ad_manual_reply_raw = ad_manual_reply_q.group_by(SocialComment.meta_ad_id).all()
    ad_manual_reply_map = {row[0]: row[1] for row in ad_manual_reply_raw if row[0]}

    query = db.query(MetaAd).filter(MetaAd.user_id == current_user.id)

    if social_account_id and account:
        acc_ext_id = account.account_id
        ad_ids_with_comments = set(ad_top_map.keys()).union(set(ad_meta_reply_map.keys())).union(set(ad_manual_reply_map.keys()))
        query = query.filter(
            or_(
                MetaAd.facebook_page_id == acc_ext_id,
                MetaAd.instagram_account_id == acc_ext_id,
                MetaAd.id.in_(list(ad_ids_with_comments)) if ad_ids_with_comments else False
            )
        )

    if ad_account_id:
        raw_id = str(ad_account_id).strip()
        prefixed = raw_id if raw_id.startswith("act_") else f"act_{raw_id}"
        unprefixed = raw_id.replace("act_", "")
        query = query.filter(MetaAd.meta_ad_account_id.in_([prefixed, unprefixed]))

    if status and status.upper() != "ALL":
        target_st = status.upper()
        if target_st == "ACTIVE":
            query = query.filter(or_(MetaAd.effective_status == "ACTIVE", MetaAd.effective_status.is_(None)))
        else:
            query = query.filter(MetaAd.effective_status == target_st)

    if q and q.strip():
        search_term = f"%{q.strip().lower()}%"
        query = query.filter(
            or_(
                func.lower(MetaAd.name).like(search_term),
                func.lower(MetaAd.campaign_name).like(search_term),
                func.lower(MetaAd.adset_name).like(search_term),
                func.lower(MetaAd.meta_ad_id).like(search_term)
            )
        )

    all_ads = query.order_by(MetaAd.updated_at.desc()).all()

    # Pre-fetch ExternalPostContext map for permalinks to avoid N+1 queries
    all_fb_pids = [ad.facebook_post_id.strip() for ad in all_ads if ad.facebook_post_id and ad.facebook_post_id.strip()]
    all_ig_mids = [ad.instagram_media_id.strip() for ad in all_ads if ad.instagram_media_id and ad.instagram_media_id.strip()]
    all_ext_ids = list(set(all_fb_pids + all_ig_mids))
    ctx_map = {}
    if all_ext_ids:
        from app.models.external_post_context import ExternalPostContext
        ext_ctxs = db.query(ExternalPostContext).filter(ExternalPostContext.external_post_id.in_(all_ext_ids)).all()
        ctx_map = {c.external_post_id.strip(): c for c in ext_ctxs}

    res = []
    for ad in all_ads:
        t_cnt = ad_top_map.get(ad.id, 0)
        r_cnt = ad_meta_reply_map.get(ad.id, 0) + ad_manual_reply_map.get(ad.id, 0)
        res.append({
            "id": ad.id,
            "meta_ad_id": ad.meta_ad_id,
            "name": ad.name,
            "campaign_name": ad.campaign_name,
            "adset_name": ad.adset_name,
            "effective_status": ad.effective_status,
            "facebook_page_id": ad.facebook_page_id,
            "facebook_post_id": ad.facebook_post_id,
            "meta_ad_account_id": ad.meta_ad_account_id,
            "created_at": ad.created_at.isoformat() if ad.created_at else None,
            "top_level_comment_count": t_cnt,
            "reply_count": r_cnt,
            "total_interaction_count": t_cnt + r_cnt,
            "comment_count": t_cnt,
            "permalink": _resolve_ad_permalink(ad, db, ctx_map=ctx_map),
            "platform": "facebook" if (not ad.engagement_object_type or ad.engagement_object_type == "FACEBOOK_POST") else "instagram"
        })
    return res


@router.get("/ads/{meta_ad_identifier}", response_model=dict)
def get_comments_for_specific_ad(
    meta_ad_identifier: str,
    skip: int = Query(0, ge=0),
    page: Optional[int] = Query(None, ge=1),
    limit: int = Query(50, ge=1, le=100),
    social_account_id: Optional[int] = Query(None, description="Filter by connected social account ID"),
    reply_status: Optional[str] = Query(None, description="Filter by reply status ('all', 'replied', 'unreplied')"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve single Meta Ad details + paginated comments for THAT specific Ad only.
    Supports looking up meta_ad by numeric database ID or string meta_ad_id.
    Returns explicit top-level comment, reply, and total interaction metrics alongside filtered counts.
    """
    if social_account_id is not None:
        account = db.query(SocialAccount).filter(
            SocialAccount.id == social_account_id,
            SocialAccount.user_id == current_user.id
        ).first()
        if not account:
            raise HTTPException(status_code=404, detail="Social account not found")

    from app.models.meta_ad import MetaAd

    if page is not None and page > 0 and skip == 0:
        skip = (page - 1) * limit

    ad = None
    if meta_ad_identifier.isdigit() and len(meta_ad_identifier) <= 9:
        try:
            ad = db.query(MetaAd).filter(MetaAd.id == int(meta_ad_identifier), MetaAd.user_id == current_user.id).first()
        except Exception:
            ad = None

    if not ad:
        ad = db.query(MetaAd).filter(MetaAd.meta_ad_id == str(meta_ad_identifier), MetaAd.user_id == current_user.id).first()

    if not ad:
        logger.warning(f"[GET_AD_COMMENTS_API] Meta Ad not found for identifier={meta_ad_identifier} user_id={current_user.id}")
        raise HTTPException(status_code=404, detail="Meta Ad not found or access denied")

    import time
    t0 = time.time()

    top_level_comment_count = social_comment_repo.count_by_user_id(
        db, current_user.id, social_account_id=social_account_id, meta_ad_id=ad.id, top_level_only=True
    )
    reply_count = social_comment_repo.count_replies_by_user_id(
        db, current_user.id, social_account_id=social_account_id, meta_ad_id=ad.id
    )
    total_interaction_count = top_level_comment_count + reply_count

    filtered_top_level_count = social_comment_repo.count_by_user_id(
        db, current_user.id, social_account_id=social_account_id, meta_ad_id=ad.id, top_level_only=True, reply_status=reply_status
    )
    raw_comments = social_comment_repo.get_by_user_id(
        db, current_user.id, skip=skip, limit=limit, social_account_id=social_account_id, meta_ad_id=ad.id, top_level_only=True, reply_status=reply_status
    )

    formatted_comments = _format_comments_response_list(raw_comments, current_user, db)

    duration_ms = int((time.time() - t0) * 1000)
    has_next = (skip + len(formatted_comments)) < filtered_top_level_count
    current_page_num = (skip // limit) + 1 if limit > 0 else 1

    logger.info(
        f"[AD_COMMENTS_PERF] ad_identifier={meta_ad_identifier} ad_id={ad.id} "
        f"meta_ad_id={ad.meta_ad_id} user_id={current_user.id} "
        f"top_level_comment_count={top_level_comment_count} reply_count={reply_count} "
        f"total_interaction_count={total_interaction_count} filtered_count={filtered_top_level_count} "
        f"returned_comments={len(formatted_comments)} skip={skip} limit={limit} "
        f"page={current_page_num} has_next={has_next} duration_ms={duration_ms}"
    )

    return {
        "ad": {
            "id": ad.id,
            "meta_ad_id": ad.meta_ad_id,
            "name": ad.name,
            "campaign_name": ad.campaign_name,
            "adset_name": ad.adset_name,
            "effective_status": ad.effective_status,
            "facebook_page_id": ad.facebook_page_id,
            "facebook_post_id": ad.facebook_post_id,
            "meta_ad_account_id": ad.meta_ad_account_id,
            "permalink": _resolve_ad_permalink(ad, db),
            "platform": "facebook" if (not ad.engagement_object_type or ad.engagement_object_type == "FACEBOOK_POST") else "instagram"
        },
        "top_level_comment_count": top_level_comment_count,
        "reply_count": reply_count,
        "total_interaction_count": total_interaction_count,
        "total_comments": top_level_comment_count,
        "filtered_top_level_count": filtered_top_level_count,
        "skip": skip,
        "limit": limit,
        "page": current_page_num,
        "has_next": has_next,
        "comments": formatted_comments
    }


@router.get("/posts", response_model=List[dict])
def get_posts_with_comments(
    q: Optional[str] = Query(None, description="Search post caption or title"),
    platform: Optional[str] = Query(None, description="Filter by platform ('facebook' or 'instagram')"),
    social_account_id: Optional[int] = Query(None, description="Filter by connected social account ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve all organic posts with exact non-deleted comment counts for current user.
    Optionally scoped to a specific social_account_id.
    """
    if social_account_id is not None:
        account = db.query(SocialAccount).filter(
            SocialAccount.id == social_account_id,
            SocialAccount.user_id == current_user.id
        ).first()
        if not account:
            raise HTTPException(status_code=404, detail="Social account not found")

    from app.models.social_comment import SocialComment
    from app.models.post import Post
    from app.models.external_post_context import ExternalPostContext
    from app.models.meta_ad import MetaAd
    from sqlalchemy import func, or_

    # Collect all post IDs that belong to Meta Ads to exclude them from organic posts
    ad_post_ids_q = db.query(MetaAd.facebook_post_id).filter(
        MetaAd.user_id == current_user.id,
        MetaAd.facebook_post_id.isnot(None)
    ).union(
        db.query(MetaAd.instagram_media_id).filter(
            MetaAd.user_id == current_user.id,
            MetaAd.instagram_media_id.isnot(None)
        )
    ).union(
        db.query(MetaAd.engagement_object_id).filter(
            MetaAd.user_id == current_user.id,
            MetaAd.engagement_object_id.isnot(None)
        )
    )
    ad_post_ids = {row[0].strip() for row in ad_post_ids_q.all() if row[0] and row[0].strip()}

    query_counts = db.query(
        SocialComment.external_post_id,
        SocialComment.platform,
        func.count(SocialComment.id)
    ).filter(
        SocialComment.user_id == current_user.id,
        SocialComment.is_deleted.isnot(True),
        SocialComment.meta_ad_id.is_(None),
        SocialComment.external_post_id.isnot(None),
        or_(SocialComment.parent_comment_id.is_(None), SocialComment.parent_comment_id == "")
    )
    if ad_post_ids:
        query_counts = query_counts.filter(~SocialComment.external_post_id.in_(list(ad_post_ids)))
    if platform:
        query_counts = query_counts.filter(SocialComment.platform == platform)
    if social_account_id:
        query_counts = query_counts.filter(SocialComment.social_account_id == social_account_id)

    post_counts_raw = query_counts.group_by(SocialComment.external_post_id, SocialComment.platform).all()
    post_count_map = {row[0]: row[2] for row in post_counts_raw if row[0]}

    res_posts = []
    added_pids = set()

    if post_count_map:
        pids = list(post_count_map.keys())
        local_posts = db.query(Post).filter(
            Post.user_id == current_user.id,
            (Post.fb_post_id.in_(pids)) | (Post.ig_media_id.in_(pids))
        ).all()

        for p in local_posts:
            ext_id = p.fb_post_id or p.ig_media_id or str(p.id)
            c_cnt = post_count_map.get(p.fb_post_id, 0) or post_count_map.get(p.ig_media_id, 0) or 0

            if q and q.strip():
                term = q.strip().lower()
                title_match = p.title and term in p.title.lower()
                cap_match = p.caption and term in p.caption.lower()
                if not title_match and not cap_match:
                    continue

            p_platform = "facebook" if p.fb_post_id else "instagram"
            res_posts.append({
                "id": p.id,
                "external_post_id": ext_id,
                "title": p.title or (p.caption[:60] if p.caption else "Organic Post"),
                "caption": p.caption,
                "image_url": p.image_url,
                "media_type": p.media_type,
                "platform": p_platform,
                "published_at": p.published_at.isoformat() if p.published_at else p.created_at.isoformat(),
                "top_level_comment_count": c_cnt,
                "comment_count": c_cnt,
                "permalink": _resolve_post_permalink(ext_id, p_platform, db, local_post=p)
            })
            if p.fb_post_id: added_pids.add(p.fb_post_id)
            if p.ig_media_id: added_pids.add(p.ig_media_id)

        remaining = [pid for pid in post_count_map.keys() if pid not in added_pids]
        ext_found_pids = set()
        if remaining:
            ext_ctx_q = db.query(ExternalPostContext).filter(
                ExternalPostContext.external_post_id.in_(remaining)
            )
            if social_account_id:
                ext_ctx_q = ext_ctx_q.filter(ExternalPostContext.social_account_id == social_account_id)
            ext_ctxs = ext_ctx_q.all()

            for ctx in ext_ctxs:
                ext_found_pids.add(ctx.external_post_id)
                if q and q.strip():
                    term = q.strip().lower()
                    if ctx.caption and term not in ctx.caption.lower():
                        continue
                c_cnt = post_count_map.get(ctx.external_post_id, 0)
                res_posts.append({
                    "id": ctx.external_post_id,
                    "external_post_id": ctx.external_post_id,
                    "title": ctx.caption.split("\n")[0][:60] if ctx.caption else f"{ctx.platform.capitalize()} Post",
                    "caption": ctx.caption,
                    "image_url": ctx.media_url,
                    "media_type": ctx.media_type,
                    "platform": ctx.platform,
                    "published_at": ctx.created_at.isoformat() if ctx.created_at else None,
                    "top_level_comment_count": c_cnt,
                    "comment_count": c_cnt,
                    "permalink": ctx.permalink or _resolve_post_permalink(ctx.external_post_id, ctx.platform, db)
                })

        for pid in remaining:
            if pid not in ext_found_pids:
                c_cnt = post_count_map.get(pid, 0)
                res_posts.append({
                    "id": pid,
                    "external_post_id": pid,
                    "title": f"Post {pid}",
                    "caption": None,
                    "image_url": None,
                    "media_type": "IMAGE",
                    "platform": "facebook",
                    "published_at": None,
                    "top_level_comment_count": c_cnt,
                    "comment_count": c_cnt,
                    "permalink": _resolve_post_permalink(pid, "facebook", db)
                })

    return res_posts


@router.get("/posts/{post_identifier}", response_model=dict)
def get_comments_for_specific_post(
    post_identifier: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    social_account_id: Optional[int] = Query(None, description="Filter by connected social account ID"),
    reply_status: Optional[str] = Query(None, description="Filter by reply status ('all', 'replied', 'unreplied')"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve single Organic Post details + paginated comments for THAT specific Post only.
    """
    if social_account_id is not None:
        account = db.query(SocialAccount).filter(
            SocialAccount.id == social_account_id,
            SocialAccount.user_id == current_user.id
        ).first()
        if not account:
            raise HTTPException(status_code=404, detail="Social account not found")

    from app.models.post import Post
    from app.models.external_post_context import ExternalPostContext

    post_meta = None
    ext_pid = post_identifier

    if post_identifier.isdigit():
        p_db = db.query(Post).filter(Post.id == int(post_identifier), Post.user_id == current_user.id).first()
        if p_db:
            ext_pid = p_db.fb_post_id or p_db.ig_media_id or str(p_db.id)
            post_meta = {
                "id": p_db.id,
                "external_post_id": ext_pid,
                "title": p_db.title or (p_db.caption[:60] if p_db.caption else "Organic Post"),
                "caption": p_db.caption,
                "image_url": p_db.image_url,
                "media_type": p_db.media_type,
                "platform": "facebook" if p_db.fb_post_id else "instagram",
                "published_at": p_db.published_at.isoformat() if p_db.published_at else p_db.created_at.isoformat(),
                "permalink": _resolve_post_permalink(ext_pid, "facebook" if p_db.fb_post_id else "instagram", db, local_post=p_db)
            }

    if not post_meta:
        ctx_q = db.query(ExternalPostContext).filter(
            ExternalPostContext.external_post_id == str(post_identifier)
        )
        if social_account_id:
            ctx_q = ctx_q.filter(ExternalPostContext.social_account_id == social_account_id)
        ctx = ctx_q.first()

        if ctx:
            ext_pid = ctx.external_post_id
            post_meta = {
                "id": ctx.external_post_id,
                "external_post_id": ctx.external_post_id,
                "title": ctx.caption.split("\n")[0][:60] if ctx.caption else f"{ctx.platform.capitalize()} Post",
                "caption": ctx.caption,
                "image_url": ctx.media_url,
                "media_type": ctx.media_type,
                "platform": ctx.platform,
                "published_at": ctx.created_at.isoformat() if ctx.created_at else None,
                "permalink": ctx.permalink or _resolve_post_permalink(ctx.external_post_id, ctx.platform, db)
            }

    if not post_meta:
        post_meta = {
            "id": post_identifier,
            "external_post_id": post_identifier,
            "title": f"Post {post_identifier}",
            "caption": None,
            "image_url": None,
            "media_type": "IMAGE",
            "platform": "facebook",
            "published_at": None,
            "permalink": _resolve_post_permalink(post_identifier, "facebook", db)
        }

    top_level_comment_count = social_comment_repo.count_by_user_id(
        db, current_user.id, social_account_id=social_account_id, external_post_id=ext_pid, is_ad=False, top_level_only=True
    )
    reply_count = social_comment_repo.count_replies_by_user_id(
        db, current_user.id, social_account_id=social_account_id, external_post_id=ext_pid, is_ad=False
    )
    total_interaction_count = top_level_comment_count + reply_count

    filtered_top_level_count = social_comment_repo.count_by_user_id(
        db, current_user.id, social_account_id=social_account_id, external_post_id=ext_pid, is_ad=False, top_level_only=True, reply_status=reply_status
    )
    raw_comments = social_comment_repo.get_by_user_id(
        db, current_user.id, skip=skip, limit=limit, social_account_id=social_account_id, external_post_id=ext_pid, is_ad=False, top_level_only=True, reply_status=reply_status
    )

    formatted_comments = _format_comments_response_list(raw_comments, current_user, db)

    return {
        "post": post_meta,
        "top_level_comment_count": top_level_comment_count,
        "reply_count": reply_count,
        "total_interaction_count": total_interaction_count,
        "total_comments": top_level_comment_count,
        "filtered_top_level_count": filtered_top_level_count,
        "skip": skip,
        "limit": limit,
        "comments": formatted_comments
    }

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


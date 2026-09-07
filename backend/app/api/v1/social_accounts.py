from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.schemas.social_account import (
    SocialAccountConnectRequest,
    SocialAccountResponse
)
from app.repositories.social_account_repository import social_account_repo
from app.api.v1.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/social-accounts", tags=["Connected Social Accounts"])

@router.get("/", response_model=List[SocialAccountResponse])
def get_connected_social_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve list of connected Facebook Pages & Instagram accounts (excluding sensitive access tokens)."""
    accounts = social_account_repo.get_by_user(db, current_user.id)
    fake_ids = {"109823471029", "17841400928371", "17841400928372", "17841400928373", "109823471030", "sandbox"}
    real_accounts = [
        a for a in accounts
        if a.account_id not in fake_ids and not (a.access_token and ("sandbox" in a.access_token or "mock" in a.access_token))
    ]
    return real_accounts

@router.get("/diagnostics")
def get_social_accounts_diagnostics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Inspect connected Facebook social accounts, stored creation/update timestamps,
    granted scopes, and token health safely WITHOUT exposing raw access tokens.
    """
    from app.services.meta_service import meta_service
    accounts = social_account_repo.get_by_user(db, current_user.id)
    fake_ids = {"109823471029", "17841400928371", "17841400928372", "17841400928373", "109823471030", "sandbox"}
    real_accounts = [
        a for a in accounts
        if a.account_id not in fake_ids and not (a.access_token and ("sandbox" in a.access_token or "mock" in a.access_token))
    ]

    diagnostics = []
    for acc in real_accounts:
        if acc.platform == "facebook":
            health = meta_service.evaluate_social_account_token_health(acc)
            diagnostics.append(health)

    return {
        "user_id": current_user.id,
        "configured_oauth_scopes": meta_service.REQUIRED_META_OAUTH_SCOPES,
        "facebook_accounts": diagnostics
    }

@router.get("/comment-automation/readiness")
def get_comment_automation_readiness(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Inspect granted Meta permissions & comment automation capability readiness for current authenticated user's connected social accounts.
    Strictly isolated per user. NEVER exposes tokens, secrets, or decrypted credentials.
    """
    from app.core.security_encryption import decrypt_token
    from app.services.meta_service import meta_service
    from datetime import datetime, timezone

    accounts = social_account_repo.get_by_user(db, current_user.id)
    fake_ids = {"109823471029", "17841400928371", "17841400928372", "17841400928373", "109823471030", "sandbox"}
    real_accounts = [
        a for a in accounts
        if a.account_id not in fake_ids and not (a.access_token and ("sandbox" in a.access_token or "mock" in a.access_token))
    ]

    readiness_list = []
    for acc in real_accounts:
        decrypted_tok = decrypt_token(acc.access_token) or ""
        readiness = meta_service.evaluate_account_comment_automation_readiness(acc, decrypted_tok)

        # Update namespaced metadata_json["comment_automation"] while preserving all existing metadata fields
        current_meta = dict(acc.metadata_json or {})
        current_meta["comment_automation"] = {
            "last_checked_at": datetime.now(timezone.utc).isoformat(),
            "inspection_status": readiness.get("inspection_status"),
            "oauth_permissions_ready": readiness.get("oauth_permissions_ready"),
            "comment_read_ready": readiness.get("comment_read_ready"),
            "comment_reply_ready": readiness.get("comment_reply_ready"),
            "webhook_prerequisites_ready": readiness.get("webhook_prerequisites_ready"),
            "missing_permissions": readiness.get("missing_permissions")
        }
        acc.metadata_json = current_meta
        db.commit()

        readiness_list.append(readiness)

    return {"accounts": readiness_list}

@router.post("/connect", response_model=SocialAccountResponse, status_code=status.HTTP_201_CREATED)
def connect_social_account(
    request: SocialAccountConnectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Link a Facebook Page or Instagram Business account independently to user workspace."""
    logo = request.logo_url
    if not logo and request.platform == "facebook":
        logo = f"https://graph.facebook.com/v19.0/{request.account_id}/picture?type=large"
    if not logo:
        logo = "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=120&auto=format&fit=crop&q=80"

    from app.repositories.brand_repository import brand_repo
    brand_repo.ensure_brand_profile_exists(db, current_user.id, request.account_name, logo)

    account = social_account_repo.create_or_update(
        db=db,
        user_id=current_user.id,
        platform=request.platform.lower(),
        account_id=request.account_id,
        account_name=request.account_name,
        access_token=request.access_token,
        brand_id=request.brand_id,
        token_type=request.token_type or "page_access_token",
        expires_at=request.expires_at,
        logo_url=logo,
        metadata_json=request.metadata_json
    )
    return account

@router.delete("/disconnect-all", status_code=status.HTTP_200_OK)
@router.delete("/all", status_code=status.HTTP_200_OK)
def disconnect_all_social_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Disconnect and remove all connected social accounts for the user."""
    count = social_account_repo.delete_all_for_user(db, current_user.id)
    return {"message": f"Successfully disconnected {count} social account(s).", "count": count}

@router.get("/{social_account_id}/platform-posts")
def get_social_account_platform_posts(
    social_account_id: int,
    limit: int = 25,
    after: str = None,
    q: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Fetch real platform posts directly from connected Instagram Business Account or Facebook Page.
    Strictly isolated to the specified SocialAccount belonging to current user.
    Optionally correlates external post IDs with local Post records.
    """
    from app.core.security_encryption import decrypt_token
    from app.services.meta_service import meta_service
    from app.models.post import Post

    account = social_account_repo.get_by_id(db, social_account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Social account not found or access denied."
        )

    if account.status and account.status.upper() in ["TOKEN_EXPIRED", "REVOKED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Social account is disconnected or has expired token ({account.status}). Please reconnect."
        )

    decrypted_token = decrypt_token(account.access_token)
    if not decrypted_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valid access token not found for this social account."
        )

    limit = max(1, min(limit, 100))
    platform = account.platform.lower()

    if platform == "instagram":
        result = meta_service.fetch_instagram_account_posts(
            instagram_account_id=account.account_id,
            access_token=decrypted_token,
            limit=limit,
            after=after
        )
    elif platform == "facebook":
        result = meta_service.fetch_facebook_page_posts(
            page_id=account.account_id,
            access_token=decrypted_token,
            limit=limit,
            after=after
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Platform '{account.platform}' does not support platform post fetching."
        )

    items = result.get("items", [])
    paging = result.get("paging", {})

    # Correlate with local Post table (Optional metadata only)
    if items:
        external_ids = [item["id"] for item in items if "id" in item]
        if platform == "instagram":
            matched_posts = db.query(Post).filter(
                Post.user_id == current_user.id,
                Post.ig_media_id.in_(external_ids)
            ).all()
            id_to_internal = {p.ig_media_id: p.id for p in matched_posts if p.ig_media_id}
        else:
            matched_posts = db.query(Post).filter(
                Post.user_id == current_user.id,
                Post.fb_post_id.in_(external_ids)
            ).all()
            id_to_internal = {p.fb_post_id: p.id for p in matched_posts if p.fb_post_id}

        for item in items:
            item["internal_post_id"] = id_to_internal.get(item["id"], None)

    # Optional search query filter by caption or ID
    if q and q.strip():
        search_lower = q.strip().lower()
        items = [
            item for item in items
            if search_lower in (item.get("caption") or "").lower() or search_lower in item.get("id", "").lower()
        ]

    return {
        "items": items,
        "paging": paging
    }


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def disconnect_social_account(
    account_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Disconnect and delete a connected social account by ID (database ID or account_id string)."""
    try:
        # Convert numeric string to int only if within standard 32-bit integer bounds
        parsed_id = int(account_id) if (account_id.isdigit() and int(account_id) <= 2147483647) else account_id
    except Exception:
        parsed_id = account_id

    success = social_account_repo.delete(db, parsed_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Social account not found or access denied"
        )
    return None



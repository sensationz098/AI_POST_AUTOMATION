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

@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def disconnect_social_account(
    account_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Disconnect and delete a connected social account by ID (database ID or account_id string)."""
    try:
        # Convert numeric string to int if possible
        parsed_id = int(account_id) if account_id.isdigit() else account_id
    except Exception:
        parsed_id = account_id

    success = social_account_repo.delete(db, parsed_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Social account not found or access denied"
        )
    return None


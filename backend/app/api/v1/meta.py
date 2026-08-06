from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.meta import MetaConnectRequest, MetaAccountResponse
from app.repositories.brand_repository import brand_repo
from app.api.v1.deps import get_current_user
from app.models.user import User
from datetime import datetime

router = APIRouter(prefix="/meta", tags=["Meta Graph Integration"])

@router.post("/connect", response_model=MetaAccountResponse)
def connect_meta_account(
    request: MetaConnectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Link Facebook Page & Instagram Business account to a Brand Profile."""
    data = {
        "access_token": request.access_token,
        "facebook_page_id": request.facebook_page_id or "109823471029",
        "facebook_page_name": request.facebook_page_name or "Official Facebook Page",
        "instagram_account_id": request.instagram_account_id or "17841400928371",
        "instagram_username": request.instagram_username or "brand_official",
        "is_connected": True,
        "last_synced_at": datetime.utcnow()
    }
    meta_acc = brand_repo.create_or_update_meta(db, request.brand_id, data)
    return meta_acc

@router.get("/account/{brand_id}", response_model=MetaAccountResponse)
def get_meta_account(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get linked Meta account status for a brand."""
    meta = brand_repo.get_meta_account(db, brand_id)
    if not meta:
        # Return un-connected default
        return MetaAccountResponse(
            id=0,
            brand_id=brand_id,
            facebook_page_id=None,
            facebook_page_name=None,
            instagram_account_id=None,
            instagram_username=None,
            is_connected=False,
            last_synced_at=None,
            created_at=datetime.utcnow()
        )
    return meta

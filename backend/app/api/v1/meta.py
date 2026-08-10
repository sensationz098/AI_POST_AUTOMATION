from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.meta import MetaConnectRequest, MetaAccountResponse
from app.repositories.brand_repository import brand_repo
from app.api.v1.deps import get_current_user
from app.models.user import User
from datetime import datetime

from app.models.brand import BrandProfile

router = APIRouter(prefix="/meta", tags=["Meta Graph Integration"])

@router.post("/connect", response_model=MetaAccountResponse)
def connect_meta_account(
    request: MetaConnectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Link Facebook Page & Instagram Business account to a Brand Profile."""
    # Determine Meta brand name & profile picture URL
    brand_name = request.facebook_page_name or (f"@{request.instagram_username}" if request.instagram_username else "Meta Connected Brand")
    
    brand_logo_url = request.logo_url
    if not brand_logo_url and request.facebook_page_id:
        brand_logo_url = f"https://graph.facebook.com/v19.0/{request.facebook_page_id}/picture?type=large"
    if not brand_logo_url:
        brand_logo_url = "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=120&auto=format&fit=crop&q=80"

    # 1. Check if specific brand_id was requested
    if request.brand_id and not request.create_new_brand:
        target_brand = db.query(BrandProfile).filter(
            BrandProfile.id == request.brand_id,
            BrandProfile.user_id == current_user.id
        ).first()

    # 2. If create_new_brand or brand not found, check existing user brands or create new brand
    if not target_brand:
        if request.create_new_brand:
            target_brand = BrandProfile(
                name=brand_name,
                logo_url=brand_logo_url,
                brand_colors=["#6366F1", "#06B6D4"],
                tone_of_voice="Professional & Engaging",
                target_audience="Facebook & Instagram Audience",
                cta_style="Direct & Value-driven",
                industry="Social Media Brand",
                user_id=current_user.id
            )
            db.add(target_brand)
            db.commit()
            db.refresh(target_brand)
        else:
            # Pick first existing brand profile for user or create one
            user_brands = brand_repo.get_by_user(db, current_user.id)
            if user_brands:
                target_brand = user_brands[0]
            else:
                target_brand = BrandProfile(
                    name=brand_name,
                    logo_url=brand_logo_url,
                    brand_colors=["#6366F1", "#06B6D4"],
                    tone_of_voice="Professional & Engaging",
                    target_audience="Facebook & Instagram Audience",
                    cta_style="Direct & Value-driven",
                    industry="Social Media Brand",
                    user_id=current_user.id
                )
                db.add(target_brand)
                db.commit()
                db.refresh(target_brand)

    # 3. Always update brand profile name and logo_url to match Meta Account details
    if target_brand:
        if request.facebook_page_name or request.instagram_username:
            target_brand.name = brand_name
        if brand_logo_url:
            target_brand.logo_url = brand_logo_url
        db.commit()
        db.refresh(target_brand)

    data = {
        "access_token": request.access_token,
        "facebook_page_id": request.facebook_page_id or "109823471029",
        "facebook_page_name": request.facebook_page_name or "Official Facebook Page",
        "instagram_account_id": request.instagram_account_id or "17841400928371",
        "instagram_username": request.instagram_username or "brand_official",
        "logo_url": brand_logo_url,
        "is_connected": True,
        "last_synced_at": datetime.utcnow()
    }
    meta_acc = brand_repo.create_or_update_meta(db, target_brand.id, data)
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

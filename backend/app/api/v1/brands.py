from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.schemas.brand import BrandCreate, BrandUpdate, BrandResponse
from app.services.brand_service import brand_service
from app.api.v1.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/brands", tags=["Brand Profiles"])

@router.post("/", response_model=BrandResponse, status_code=status.HTTP_201_CREATED)
def create_brand(
    brand_in: BrandCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new brand profile with voice tone, colors, and target audience."""
    return brand_service.create_brand(db, current_user.id, brand_in)

@router.get("/", response_model=List[BrandResponse])
def get_user_brands(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all brand profiles owned by authenticated user."""
    return brand_service.get_user_brands(db, current_user.id)

@router.get("/{brand_id}", response_model=BrandResponse)
def get_brand(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get specific brand profile details."""
    return brand_service.get_brand(db, brand_id, current_user.id)

@router.put("/{brand_id}", response_model=BrandResponse)
def update_brand(
    brand_id: int,
    brand_in: BrandUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update brand profile settings."""
    return brand_service.update_brand(db, brand_id, current_user.id, brand_in)

@router.delete("/{brand_id}")
def delete_brand(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a brand profile."""
    brand_service.delete_brand(db, brand_id, current_user.id)
    return {"message": "Brand deleted successfully"}

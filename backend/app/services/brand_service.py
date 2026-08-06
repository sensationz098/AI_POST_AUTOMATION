from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import List, Optional
from app.repositories.brand_repository import brand_repo
from app.schemas.brand import BrandCreate, BrandUpdate
from app.models.brand import BrandProfile

class BrandService:
    def create_brand(self, db: Session, user_id: int, brand_in: BrandCreate) -> BrandProfile:
        data = brand_in.model_dump()
        data["user_id"] = user_id
        return brand_repo.create(db, data)

    def get_user_brands(self, db: Session, user_id: int) -> List[BrandProfile]:
        return brand_repo.get_by_user(db, user_id)

    def get_brand(self, db: Session, brand_id: int) -> BrandProfile:
        brand = brand_repo.get(db, brand_id)
        if not brand:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Brand profile not found"
            )
        return brand

    def update_brand(self, db: Session, brand_id: int, brand_in: BrandUpdate) -> BrandProfile:
        brand = self.get_brand(db, brand_id)
        return brand_repo.update(db, brand, brand_in.model_dump(exclude_unset=True))

    def delete_brand(self, db: Session, brand_id: int) -> Optional[BrandProfile]:
        self.get_brand(db, brand_id)
        return brand_repo.delete(db, brand_id)

brand_service = BrandService()

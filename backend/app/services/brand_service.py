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
        from app.repositories.social_account_repository import social_account_repo
        brand_repo.deduplicate_brand_profiles(db, user_id)
        all_accounts = social_account_repo.get_by_user(db, user_id)
        fake_ids = {"109823471029", "17841400928371", "17841400928372", "17841400928373", "109823471030", "sandbox"}
        for acc in all_accounts:
            if acc.account_id not in fake_ids and not (acc.access_token and ("sandbox" in acc.access_token or "mock" in acc.access_token)):
                brand_repo.ensure_brand_profile_exists(db, user_id, acc.account_name, acc.logo_url)
        brand_repo.deduplicate_brand_profiles(db, user_id)
        return brand_repo.get_by_user(db, user_id)

    def get_brand(self, db: Session, brand_id: int, user_id: int) -> BrandProfile:
        brand = brand_repo.get(db, brand_id)
        if not brand or brand.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Brand profile not found or access denied"
            )
        return brand

    def update_brand(self, db: Session, brand_id: int, user_id: int, brand_in: BrandUpdate) -> BrandProfile:
        brand = self.get_brand(db, brand_id, user_id)
        return brand_repo.update(db, brand, brand_in.model_dump(exclude_unset=True))

    def delete_brand(self, db: Session, brand_id: int, user_id: int) -> Optional[BrandProfile]:
        self.get_brand(db, brand_id, user_id)
        return brand_repo.delete(db, brand_id)

brand_service = BrandService()

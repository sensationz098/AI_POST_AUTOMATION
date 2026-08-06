from typing import List, Optional
from sqlalchemy.orm import Session
from app.repositories.base import BaseRepository
from app.models.brand import BrandProfile
from app.models.meta_account import MetaAccount

class BrandRepository(BaseRepository[BrandProfile]):
    def __init__(self):
        super().__init__(BrandProfile)

    def get_by_user(self, db: Session, user_id: int) -> List[BrandProfile]:
        return db.query(BrandProfile).filter(BrandProfile.user_id == user_id).all()

    def get_meta_account(self, db: Session, brand_id: int) -> Optional[MetaAccount]:
        return db.query(MetaAccount).filter(MetaAccount.brand_id == brand_id).first()

    def create_or_update_meta(self, db: Session, brand_id: int, data: dict) -> MetaAccount:
        meta = db.query(MetaAccount).filter(MetaAccount.brand_id == brand_id).first()
        if not meta:
            meta = MetaAccount(brand_id=brand_id, **data)
            db.add(meta)
        else:
            for k, v in data.items():
                if v is not None:
                    setattr(meta, k, v)
        db.commit()
        db.refresh(meta)
        return meta

brand_repo = BrandRepository()

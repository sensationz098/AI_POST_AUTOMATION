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

    def ensure_brand_profile_exists(self, db: Session, user_id: int, account_name: str, logo_url: Optional[str] = None) -> BrandProfile:
        """Check if a BrandProfile exists for this user and account_name; if not, create a new BrandProfile with the same name and logo."""
        clean_name = account_name.strip()
        brand = db.query(BrandProfile).filter(
            BrandProfile.user_id == user_id,
            BrandProfile.name == clean_name
        ).first()

        if not brand:
            brand = BrandProfile(
                name=clean_name,
                logo_url=logo_url or "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=120&auto=format&fit=crop&q=80",
                user_id=user_id,
                brand_colors=["#6366F1", "#38BDF8"],
                tone_of_voice="Professional, Engaging & Visionary",
                target_audience="Target Audience & Followers",
                cta_style="Value-driven Call to Action",
                industry="Social Media & Brand"
            )
            db.add(brand)
            db.commit()
            db.refresh(brand)
        else:
            if logo_url and brand.logo_url != logo_url:
                brand.logo_url = logo_url
                db.commit()
                db.refresh(brand)
        return brand

    def deduplicate_brand_profiles(self, db: Session, user_id: int):
        """Purge duplicate BrandProfiles with the exact same name for a user, keeping only the earliest created record."""
        all_brands = db.query(BrandProfile).filter(BrandProfile.user_id == user_id).order_by(BrandProfile.id.asc()).all()
        seen_names = set()
        for b in all_brands:
            clean_name = b.name.strip().lower()
            if clean_name in seen_names:
                db.delete(b)
            else:
                seen_names.add(clean_name)
        db.commit()

brand_repo = BrandRepository()

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from app.schemas.meta import MetaAccountResponse

class BrandBase(BaseModel):
    name: str
    logo_url: Optional[str] = None
    brand_colors: List[str] = Field(default_factory=lambda: ["#4F46E5", "#06B6D4"])
    tone_of_voice: str = "Professional & Engaging"
    target_audience: Optional[str] = "Tech-savvy professionals and entrepreneurs aged 22-45"
    cta_style: str = "Direct & Urgency-driven"
    industry: Optional[str] = "Software & Tech"

class BrandCreate(BrandBase):
    pass

class BrandUpdate(BaseModel):
    name: Optional[str] = None
    logo_url: Optional[str] = None
    brand_colors: Optional[List[str]] = None
    tone_of_voice: Optional[str] = None
    target_audience: Optional[str] = None
    cta_style: Optional[str] = None
    industry: Optional[str] = None

class BrandResponse(BrandBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    meta_account: Optional[MetaAccountResponse] = None

    class Config:
        from_attributes = True

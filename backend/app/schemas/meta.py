from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class MetaConnectRequest(BaseModel):
    brand_id: Optional[int] = 1
    access_token: str
    facebook_page_id: Optional[str] = None
    facebook_page_name: Optional[str] = None
    instagram_account_id: Optional[str] = None
    instagram_username: Optional[str] = None
    logo_url: Optional[str] = None
    create_new_brand: Optional[bool] = False

class MetaAccountResponse(BaseModel):
    id: int
    brand_id: int
    facebook_page_id: Optional[str]
    facebook_page_name: Optional[str]
    instagram_account_id: Optional[str]
    instagram_username: Optional[str]
    logo_url: Optional[str] = None
    is_connected: bool
    last_synced_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True

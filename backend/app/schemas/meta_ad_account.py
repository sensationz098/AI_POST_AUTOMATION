from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class MetaAdAccountResponse(BaseModel):
    id: int
    user_id: int
    meta_ad_account_id: str = Field(..., description="Meta Ad Account ID string (e.g. 'act_123456789')")
    name: Optional[str] = None
    account_status: Optional[int] = None
    status_label: Optional[str] = None
    currency: Optional[str] = None
    timezone_name: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class MetaAdAccountSyncResponse(BaseModel):
    success: bool
    message: str
    synced_count: int
    accounts: List[MetaAdAccountResponse]

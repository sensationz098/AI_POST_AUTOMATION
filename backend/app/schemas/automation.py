from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from app.models.automation import AutomationStatus, TriggerType, PostTargetType


class TriggerConfig(BaseModel):
    keywords: Optional[List[str]] = Field(default_factory=list, description="List of keywords for KEYWORD trigger")


class PublicReplyConfig(BaseModel):
    enabled: bool = Field(default=False, description="Whether public reply is enabled")
    variations: List[str] = Field(default_factory=list, description="Variations of public replies for randomization")


class PrivateMessageConfig(BaseModel):
    enabled: bool = Field(default=False, description="Whether private DM is enabled")
    message: Optional[str] = Field(default=None, description="Direct message text content")


class ActionConfig(BaseModel):
    public_reply: Optional[PublicReplyConfig] = Field(default_factory=PublicReplyConfig)
    private_message: Optional[PrivateMessageConfig] = Field(default_factory=PrivateMessageConfig)


class AutomationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Descriptive name for the automation")
    platform: str = Field(..., description="'facebook' or 'instagram'")
    social_account_id: int = Field(..., description="Target social account ID")
    post_target_type: Optional[str] = Field(default=PostTargetType.SPECIFIC_POST.value, description="Post targeting strategy")
    internal_post_id: Optional[int] = Field(default=None, description="Internal post ID (if applicable)")
    external_post_id: Optional[str] = Field(default=None, description="External Meta post/media ID")
    trigger_type: str = Field(default=TriggerType.ANY_COMMENT.value, description="'ANY_COMMENT' or 'KEYWORD'")
    trigger_config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Trigger parameters (e.g. keywords)")
    action_config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Actions configuration (public_reply, private_message)")
    metadata_json: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional metadata")


class AutomationUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    platform: Optional[str] = Field(default=None)
    social_account_id: Optional[int] = Field(default=None)
    post_target_type: Optional[str] = Field(default=None)
    internal_post_id: Optional[int] = Field(default=None)
    external_post_id: Optional[str] = Field(default=None)
    trigger_type: Optional[str] = Field(default=None)
    trigger_config: Optional[Dict[str, Any]] = Field(default=None)
    action_config: Optional[Dict[str, Any]] = Field(default=None)
    metadata_json: Optional[Dict[str, Any]] = Field(default=None)


class AutomationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    social_account_id: int
    name: str
    platform: str
    status: str
    post_target_type: str
    external_post_id: Optional[str] = None
    internal_post_id: Optional[int] = None
    trigger_type: str
    trigger_config: Dict[str, Any]
    action_config: Dict[str, Any]
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class AutomationDeleteResponse(BaseModel):
    success: bool
    message: str
    automation_id: int

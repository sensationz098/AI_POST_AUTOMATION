from pydantic import BaseModel, Field
from typing import List, Optional

class AIGenerateRequest(BaseModel):
    brand_id: int
    topic: str = Field(..., description="Main topic or promo idea for the post")
    campaign_goal: Optional[str] = "Brand Awareness & Lead Generation"
    platform: Optional[str] = "all"  # "facebook", "instagram", or "all"
    custom_instructions: Optional[str] = None

class AIGenerateResponse(BaseModel):
    caption: str
    hashtags: List[str]
    cta: str
    seo_keywords: List[str]
    image_prompt: str

class AIImageGenerateRequest(BaseModel):
    image_prompt: str
    style: Optional[str] = "photorealistic"  # "photorealistic", "illustration", "3d render", "minimalist"
    aspect_ratio: Optional[str] = "1080x1080"  # "1080x1080" (IG Square), "1080x1350" (IG Portrait)

class AIImageGenerateResponse(BaseModel):
    image_url: str
    provider: str

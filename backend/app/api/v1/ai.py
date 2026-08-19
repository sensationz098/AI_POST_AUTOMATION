from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.schemas.ai import AIGenerateRequest, AIGenerateResponse, AIImageGenerateRequest, AIImageGenerateResponse
from app.services.ai_service import ai_service
from app.services.brand_service import brand_service
from app.api.v1.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/ai", tags=["AI Generation Engine"])

class GenericAIPromptRequest(BaseModel):
    prompt: Optional[str] = None
    topic: Optional[str] = None
    brand_id: Optional[int] = 1
    platform: Optional[str] = "facebook"

class HashtagSuggestRequest(BaseModel):
    topic: Optional[str] = "Social AI"

@router.post("/generate", response_model=AIGenerateResponse)
@router.post("/generate-content", response_model=AIGenerateResponse)
def generate_ai_content(
    request: GenericAIPromptRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate caption, hashtags, CTA, SEO keywords, and visual image prompt using OpenAI GPT or intelligent fallback."""
    try:
        brand = None
        if request.brand_id:
            try:
                brand = brand_service.get_brand(db, request.brand_id, current_user.id)
            except Exception:
                pass
        
        if not brand:
            # Fallback to user's first brand or mock brand profile
            user_brands = brand_service.get_user_brands(db, current_user.id)
            brand = user_brands[0] if user_brands else None

        req_schema = AIGenerateRequest(
            brand_id=request.brand_id or 1,
            topic=request.topic or request.prompt or "Introducing Sensationz AI Social Platform",
            campaign_goal="Engagement",
            custom_instructions=request.prompt
        )
        
        if brand:
            return ai_service.generate_content(brand, req_schema)
        else:
            # Mock brand object fallback
            class DummyBrand:
                name = "Sensationz Brand"
                tone_of_voice = "Professional & Modern"
                target_audience = "Social Media Marketers"
                cta_style = "Direct"
                industry = "Software"
                brand_colors = ["#6366F1", "#06B6D4"]
            return ai_service.generate_content(DummyBrand(), req_schema)
    except Exception as e:
        return AIGenerateResponse(
            caption=f"🚀 {request.topic or 'Streamline your social presence'}! Automated content generation made effortless with Sensationz.",
            hashtags=["#SocialAI", "#MetaAutomation", "#ContentCreator"],
            cta="👉 Click link in bio to learn more!",
            seo_keywords=["social media", "ai", "automation"],
            image_prompt=request.prompt or "Modern tech workspace editorial typography"
        )

@router.post("/generate-image", response_model=AIImageGenerateResponse)
def generate_ai_image(
    request: AIImageGenerateRequest,
    current_user: User = Depends(get_current_user)
):
    """Generate high-resolution social graphic using DALL-E, Pollinations.ai or curated visual engine."""
    try:
        if not request.image_prompt:
            request.image_prompt = "Modern minimal tech workspace editorial style"
        return ai_service.generate_image(request)
    except Exception as e:
        return AIImageGenerateResponse(
            image_url="https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=1200&q=80",
            provider="Unsplash Fallback Engine"
        )

@router.post("/suggest-hashtags")
def suggest_hashtags(
    request: HashtagSuggestRequest,
    current_user: User = Depends(get_current_user)
):
    """Suggest viral hashtags tailored to a topic or caption."""
    try:
        topic_clean = (request.topic or "Social AI").replace(" ", "").replace("#", "")
        return {
            "hashtags": [
                f"#{topic_clean}",
                "#MetaGraphAPI",
                "#ContentStrategy",
                "#DigitalMarketing",
                "#SensationzAI"
            ]
        }
    except Exception:
        return {
            "hashtags": ["#SocialAI", "#MetaAutomation", "#DigitalMarketing", "#ContentCreator"]
        }

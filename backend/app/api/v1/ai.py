from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.ai import AIGenerateRequest, AIGenerateResponse, AIImageGenerateRequest, AIImageGenerateResponse
from app.services.ai_service import ai_service
from app.services.brand_service import brand_service
from app.api.v1.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/ai", tags=["AI Generation Engine"])

@router.post("/generate-content", response_model=AIGenerateResponse)
def generate_ai_content(
    request: AIGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate caption, hashtags, CTA, SEO keywords, and visual image prompt using OpenAI GPT."""
    brand = brand_service.get_brand(db, request.brand_id)
    return ai_service.generate_content(brand, request)

@router.post("/generate-image", response_model=AIImageGenerateResponse)
def generate_ai_image(
    request: AIImageGenerateRequest,
    current_user: User = Depends(get_current_user)
):
    """Generate high-resolution social graphic using OpenAI DALL-E or pluggable visual engine."""
    return ai_service.generate_image(request)

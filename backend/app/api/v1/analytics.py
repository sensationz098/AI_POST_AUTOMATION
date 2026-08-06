from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.analytics import DashboardAnalyticsResponse
from app.services.analytics_service import analytics_service
from app.api.v1.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/analytics", tags=["Analytics & Growth"])

@router.get("/brand/{brand_id}", response_model=DashboardAnalyticsResponse)
def get_brand_analytics(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve reach, impressions, engagement rates, and trend metrics for brand analytics dashboard."""
    return analytics_service.get_brand_dashboard(db, brand_id)

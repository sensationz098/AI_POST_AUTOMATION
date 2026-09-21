from typing import Optional
from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.analytics import (
    DashboardAnalyticsResponse,
    AccountAnalyticsResponse,
    OverviewReportResponse,
    PlatformBreakdownResponse,
    PostPerformanceListResponse,
    LiveAnalyticsResponse,
)
from app.services.analytics_service import analytics_service
from app.services.live_analytics_service import live_analytics_service
from app.api.v1.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/analytics", tags=["Analytics & Growth"])

# ==============================================================================
# Phase A5-DATA-01: Live Real-Time Platform Analytics Endpoint
# ==============================================================================

@router.get("/live", response_model=LiveAnalyticsResponse)
def get_live_platform_analytics(
    brand_id: Optional[int] = Query(None, description="Optional brand filter"),
    social_account_id: Optional[int] = Query(None, description="Optional social account filter"),
    platform: Optional[str] = Query(None, description="Optional platform filter (e.g. instagram, facebook, youtube)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Fetch CURRENT real-time platform metrics directly from connected social accounts (Meta / YouTube),
    idempotently update today's historical snapshot row, and return normalized analytics with capabilities.
    Does NOT require pre-existing historical snapshots.
    """
    return live_analytics_service.get_live_analytics(
        db=db,
        user_id=current_user.id,
        brand_id=brand_id,
        social_account_id=social_account_id,
        platform=platform
    )


# ==============================================================================
# Backward-Compatible Legacy Overview Endpoints
# ==============================================================================

@router.get("/overview", response_model=DashboardAnalyticsResponse)
def get_user_overview_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve aggregated insights across ALL connected Facebook Pages & Instagram accounts for current user."""
    return analytics_service.get_user_overview_dashboard(db, current_user.id)

@router.get("/brand/{brand_id}", response_model=DashboardAnalyticsResponse)
def get_brand_analytics(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve reach, impressions, engagement rates, and trend metrics for brand analytics dashboard."""
    return analytics_service.get_brand_dashboard(db, brand_id, current_user.id)

# ==============================================================================
# Phase 2B.5-A3: Read-Only Aggregation & Performance Endpoints
# ==============================================================================

@router.get("/accounts/snapshots", response_model=AccountAnalyticsResponse)
def get_account_snapshots(
    brand_id: Optional[int] = Query(None, description="Optional brand filter"),
    social_account_id: Optional[int] = Query(None, description="Optional social account filter"),
    platform: Optional[str] = Query(None, description="Optional platform filter (e.g. instagram, facebook, youtube)"),
    start_date: Optional[date] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date filter (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve chronological daily snapshots and growth metrics for connected social accounts.
    Strictly read-only from persisted snapshots.
    """
    return analytics_service.get_account_historical_analytics(
        db=db,
        user_id=current_user.id,
        brand_id=brand_id,
        social_account_id=social_account_id,
        platform=platform,
        start_date=start_date,
        end_date=end_date
    )

@router.get("/overview-report", response_model=OverviewReportResponse)
def get_overview_report(
    brand_id: Optional[int] = Query(None, description="Optional brand filter"),
    social_account_id: Optional[int] = Query(None, description="Optional social account filter"),
    platform: Optional[str] = Query(None, description="Optional platform filter"),
    start_date: Optional[date] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date filter (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve aggregated overview report metrics (total followers, posts count, likes, comments, shares,
    saves, reach, impressions, and aggregate engagement rate) strictly from persisted records.
    total_followers is the arithmetic sum of platform followers (not deduplicated audience).
    """
    return analytics_service.get_overview_report(
        db=db,
        user_id=current_user.id,
        brand_id=brand_id,
        social_account_id=social_account_id,
        platform=platform,
        start_date=start_date,
        end_date=end_date
    )

@router.get("/platforms", response_model=PlatformBreakdownResponse)
def get_platform_breakdown(
    brand_id: Optional[int] = Query(None, description="Optional brand filter"),
    start_date: Optional[date] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date filter (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve metrics breakdown across Instagram, Facebook, and YouTube within user/brand scope.
    """
    return analytics_service.get_platform_breakdown(
        db=db,
        user_id=current_user.id,
        brand_id=brand_id,
        start_date=start_date,
        end_date=end_date
    )

@router.get("/posts", response_model=PostPerformanceListResponse)
def get_posts_performance(
    brand_id: Optional[int] = Query(None, description="Optional brand filter"),
    social_account_id: Optional[int] = Query(None, description="Optional social account filter"),
    platform: Optional[str] = Query(None, description="Optional platform filter"),
    start_date: Optional[date] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date filter (YYYY-MM-DD)"),
    order_by: str = Query(
        "published_at",
        pattern="^(published_at|created_at|likes|comments|shares|saves|reach|impressions|engagement_rate)$",
        description="Metric or field to sort by"
    ),
    order_dir: str = Query("desc", pattern="^(asc|desc)$", description="Sort direction (asc/desc)"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Offset index"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve paginated post performance listing with deterministic NULL-safe sorting and filtering.
    """
    return analytics_service.get_posts_performance_list(
        db=db,
        user_id=current_user.id,
        brand_id=brand_id,
        social_account_id=social_account_id,
        platform=platform,
        start_date=start_date,
        end_date=end_date,
        order_by=order_by,
        order_dir=order_dir,
        limit=limit,
        offset=offset
    )


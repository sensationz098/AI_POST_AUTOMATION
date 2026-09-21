from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional, Dict, Any
from datetime import date, datetime

class PostAnalyticsResponse(BaseModel):
    id: int
    post_id: int
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    saves: Optional[int] = None
    reach: Optional[int] = None
    impressions: Optional[int] = None
    engagement_rate: Optional[float] = None
    follower_growth: Optional[int] = 0
    updated_at: datetime

    class Config:
        from_attributes = True

class FacebookPageMetrics(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = "Connected Facebook Page"
    followers_count: int = 0
    fan_count: int = 0
    category: Optional[str] = "Meta Page"
    picture_url: Optional[str] = None
    link: Optional[str] = None
    is_sandbox: bool = True

class InstagramAccountMetrics(BaseModel):
    id: Optional[str] = None
    username: Optional[str] = "instagram_account"
    name: Optional[str] = "Instagram Business"
    followers_count: int = 0
    follows_count: int = 0
    media_count: int = 0
    profile_picture_url: Optional[str] = None
    is_sandbox: bool = True

class MetricOverview(BaseModel):
    total_posts: int
    published_posts: int
    scheduled_posts: int
    failed_posts: int
    total_likes: int
    total_comments: int
    total_shares: int
    total_reach: int
    total_impressions: int
    avg_engagement_rate: float

class DailyMetricPoint(BaseModel):
    date: str
    reach: int
    impressions: int
    engagement: int

class DashboardAnalyticsResponse(BaseModel):
    overview: MetricOverview
    daily_trends: List[DailyMetricPoint]
    facebook_page: Optional[FacebookPageMetrics] = None
    instagram_account: Optional[InstagramAccountMetrics] = None
    accounts_list: Optional[List[dict]] = None
    is_live_meta: bool = False

# ==============================================================================
# Phase 2B.5-A3 Schemas: Account Snapshots, Aggregations, Breakdown, Post Metrics
# ==============================================================================

class AccountSnapshotPoint(BaseModel):
    id: int
    social_account_id: int
    platform: str
    account_name: Optional[str] = None
    snapshot_date: date
    followers_count: Optional[int] = None
    following_count: Optional[int] = None
    media_count: Optional[int] = None
    views_count: Optional[int] = None
    reach: Optional[int] = None
    impressions: Optional[int] = None
    engagement_rate: Optional[float] = None
    metadata_json: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

class GrowthMetrics(BaseModel):
    initial_followers: Optional[int] = None
    current_followers: Optional[int] = None
    follower_change: Optional[int] = None
    follower_growth_rate: Optional[float] = None  # Percentage e.g. 5.25%
    initial_media_count: Optional[int] = None
    current_media_count: Optional[int] = None
    media_count_change: Optional[int] = None
    initial_views: Optional[int] = None
    current_views: Optional[int] = None
    views_change: Optional[int] = None

class AccountAnalyticsResponse(BaseModel):
    snapshots: List[AccountSnapshotPoint]
    growth: GrowthMetrics
    total_records: int

class OverviewReportResponse(BaseModel):
    total_followers: Optional[int] = Field(
        default=None,
        description="Arithmetic sum of available platform/account follower counts. NOT a deduplicated cross-platform audience."
    )
    total_posts: int = Field(default=0, description="Distinct count of logical posts within scope.")
    published_posts: int = 0
    scheduled_posts: int = 0
    failed_posts: int = 0
    total_likes: Optional[int] = None
    total_comments: Optional[int] = None
    total_shares: Optional[int] = None
    total_saves: Optional[int] = None
    total_reach: Optional[int] = None
    total_impressions: Optional[int] = None
    aggregate_engagement_rate: Optional[float] = Field(
        default=None,
        description="Calculated from aggregate interactions over aggregate impressions (or reach). Rounded to 2 decimal places."
    )
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class PlatformBreakdownItem(BaseModel):
    platform: str
    connected_accounts_count: int = 0
    total_followers: Optional[int] = Field(
        default=None,
        description="Arithmetic sum of platform followers. NOT deduplicated."
    )
    total_posts: int = 0
    total_likes: Optional[int] = None
    total_comments: Optional[int] = None
    total_shares: Optional[int] = None
    total_saves: Optional[int] = None
    total_reach: Optional[int] = None
    total_impressions: Optional[int] = None
    total_views: Optional[int] = None
    aggregate_engagement_rate: Optional[float] = None

class PlatformBreakdownResponse(BaseModel):
    platforms: List[PlatformBreakdownItem]

class PostPerformanceItem(BaseModel):
    post_id: int
    title: Optional[str] = None
    caption: Optional[str] = None
    status: str
    platforms: List[str] = []
    media_type: Optional[str] = None
    thumbnail_url: Optional[str] = None
    image_url: Optional[str] = None
    published_at: Optional[datetime] = None
    created_at: datetime
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    saves: Optional[int] = None
    reach: Optional[int] = None
    impressions: Optional[int] = None
    engagement_rate: Optional[float] = None
    analytics_updated_at: Optional[datetime] = None

class PostPerformanceListResponse(BaseModel):
    items: List[PostPerformanceItem]
    total: int
    limit: int
    offset: int


# ==============================================================================
# Phase A5-DATA-01 Schemas: Normalized Live Platform Analytics
# ==============================================================================

class LiveAccountMetrics(BaseModel):
    followers: Optional[int] = None
    following: Optional[int] = None
    media_count: Optional[int] = None
    views_count: Optional[int] = None


class LiveAnalyticsMetrics(BaseModel):
    reach: Optional[int] = None
    impressions: Optional[int] = None
    engagement_rate: Optional[float] = None


class LiveAccountCapabilities(BaseModel):
    followers: bool = False
    following: bool = False
    media_count: bool = False
    views_count: bool = False
    reach: bool = False
    impressions: bool = False
    engagement_rate: bool = False


class LiveAccountAnalyticsItem(BaseModel):
    social_account_id: int
    platform: str
    account_name: Optional[str] = None
    account_id: str
    logo_url: Optional[str] = None
    status: str = "CONNECTED"
    account: LiveAccountMetrics
    analytics: LiveAnalyticsMetrics
    capabilities: LiveAccountCapabilities
    source: str = "live_platform_api"
    fetched_at: str
    error_message: Optional[str] = None


class LiveAnalyticsSummary(BaseModel):
    total_followers: Optional[int] = Field(
        default=None,
        description="Arithmetic sum of live platform followers across connected accounts. Not deduplicated."
    )
    total_reach: Optional[int] = None
    total_impressions: Optional[int] = None
    aggregate_engagement_rate: Optional[float] = None


class LiveAnalyticsResponse(BaseModel):
    accounts: List[LiveAccountAnalyticsItem]
    summary: LiveAnalyticsSummary
    fetched_at: str


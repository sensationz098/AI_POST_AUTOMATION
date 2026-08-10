from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class PostAnalyticsResponse(BaseModel):
    id: int
    post_id: int
    likes: int
    comments: int
    shares: int
    saves: int
    reach: int
    impressions: int
    engagement_rate: float
    follower_growth: int
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
    is_live_meta: bool = False

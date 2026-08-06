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

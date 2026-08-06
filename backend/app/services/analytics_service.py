from sqlalchemy.orm import Session
from app.repositories.analytics_repository import analytics_repo
from app.schemas.analytics import DashboardAnalyticsResponse, MetricOverview, DailyMetricPoint

class AnalyticsService:
    def get_brand_dashboard(self, db: Session, brand_id: int) -> DashboardAnalyticsResponse:
        summary = analytics_repo.get_brand_summary(db, brand_id)
        
        overview = MetricOverview(**summary)
        
        # Generated trend data for line charts
        daily_trends = [
            DailyMetricPoint(date="Mon", reach=1200, impressions=1800, engagement=140),
            DailyMetricPoint(date="Tue", reach=1450, impressions=2100, engagement=165),
            DailyMetricPoint(date="Wed", reach=1900, impressions=2600, engagement=210),
            DailyMetricPoint(date="Thu", reach=2400, impressions=3100, engagement=280),
            DailyMetricPoint(date="Fri", reach=2850, impressions=3700, engagement=340),
            DailyMetricPoint(date="Sat", reach=3200, impressions=4200, engagement=410),
            DailyMetricPoint(date="Sun", reach=3800, impressions=4900, engagement=490),
        ]
        
        return DashboardAnalyticsResponse(overview=overview, daily_trends=daily_trends)

analytics_service = AnalyticsService()

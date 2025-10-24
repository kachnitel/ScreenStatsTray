"""Service for statistics aggregations."""
import datetime
from typing import Dict, List, Tuple
from ..config import IDLE_THRESHOLD_MS
from .activity_service import ActivityService

IDLE_THRESHOLD_SEC = IDLE_THRESHOLD_MS // 1000


class StatsService:
    """Handles statistics calculations for a given day."""
    
    def __init__(self) -> None:
        self.activity_service = ActivityService()
    
    def get_daily_totals(self, day: str) -> Dict[str, float]:
        """
        Get total active/inactive seconds for a day (YYYY-MM-DD format).
        
        Returns:
            Dict with 'active' and 'inactive' seconds
        """
        day_date = datetime.date.fromisoformat(day)
        periods = self.activity_service.get_activity_periods_for_day(day_date)
        
        totals: Dict[str, float] = {"active": 0.0, "inactive": 0.0}
        
        for period in periods:
            duration = period["duration_seconds"]
            # Short inactive periods count as active (minor pauses)
            if period["state"] == "inactive" and duration < IDLE_THRESHOLD_SEC:
                totals["active"] += duration
            else:
                totals[period["state"]] += duration
        
        return totals
    
    def get_top_apps(self, day: str, limit: int = 10) -> List[Tuple[str, float]]:
        """
        Get top applications by active time for a day.
        
        Returns:
            List of (app_name, seconds) tuples sorted by usage
        """
        day_date = datetime.date.fromisoformat(day)
        app_times = self.activity_service.get_app_usage_for_day(day_date)
        
        # Sort and limit
        sorted_apps = sorted(app_times.items(), key=lambda x: x[1], reverse=True)
        return sorted_apps[:limit]

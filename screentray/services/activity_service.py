"""Service for activity period calculations."""
import datetime
from typing import List, Dict, Tuple
from ..db.event_repository import EventRepository
from ..models import Event


class ActivityService:
    """Handles activity period analysis."""
    
    def __init__(self) -> None:
        self.repo = EventRepository()
    
    def get_activity_periods_for_day(self, day: datetime.date) -> List[Dict[str, any]]:
        """
        Get all activity periods for a specific day.
        
        Returns:
            List of dicts with 'start', 'end', 'state', 'duration_seconds'
        """
        start = datetime.datetime.combine(day, datetime.time.min)
        end = datetime.datetime.combine(day, datetime.time.max)
        
        events = self.repo.find_events_in_period(start, end)
        return self._build_periods(events, start, end)
    
    def get_activity_periods_last_24h(self) -> List[Dict[str, any]]:
        """Get activity periods for the last 24 hours."""
        end = datetime.datetime.now()
        start = end - datetime.timedelta(hours=24)
        
        events = self.repo.find_events_in_period(start, end)
        return self._build_periods(events, start, end)
    
    def _build_periods(self, events: List[Event], period_start: datetime.datetime, 
                       period_end: datetime.datetime) -> List[Dict[str, any]]:
        """Build activity periods from events."""
        if not events:
            # No events = entire period is inactive
            duration = (period_end - period_start).total_seconds()
            return [{
                "start": period_start,
                "end": period_end,
                "state": "inactive",
                "duration_seconds": duration
            }]
        
        periods: List[Dict[str, any]] = []
        last_ts = period_start
        last_state = "inactive"  # Default to inactive
        
        for event in events:
            event_ts = datetime.datetime.fromisoformat(event.timestamp)
            
            # Determine state based on event type
            if event.type in EventRepository.INACTIVE_EVENTS:
                new_state = "inactive"
            else:
                new_state = "active"
            
            # State change - close previous period
            if new_state != last_state:
                duration = (event_ts - last_ts).total_seconds()
                if duration > 0:
                    periods.append({
                        "start": last_ts,
                        "end": event_ts,
                        "state": last_state,
                        "duration_seconds": duration
                    })
                last_ts = event_ts
                last_state = new_state
        
        # Add final period up to period_end
        duration = (period_end - last_ts).total_seconds()
        if duration > 0:
            periods.append({
                "start": last_ts,
                "end": period_end,
                "state": last_state,
                "duration_seconds": duration
            })
        
        return periods
    
    def get_app_usage_for_day(self, day: datetime.date) -> Dict[str, float]:
        """
        Calculate time spent per app for a specific day.
        
        Returns:
            Dict mapping app names to seconds of active usage
        """
        start = datetime.datetime.combine(day, datetime.time.min)
        end = datetime.datetime.combine(day, datetime.time.max)
        
        # Get app_switch events
        events = self.repo.find_events_in_period(start, end, types=('app_switch',))
        
        if not events:
            return {}
        
        app_times: Dict[str, float] = {}
        
        # Get the app before first switch (if exists)
        first_event = events[0]
        prev_app = self._extract_app_from_detail(first_event.detail, is_target=False)
        prev_ts = datetime.datetime.fromisoformat(first_event.timestamp)
        
        for event in events:
            event_ts = datetime.datetime.fromisoformat(event.timestamp)
            current_app = self._extract_app_from_detail(event.detail, is_target=True)
            
            # Credit time to previous app
            if prev_app:
                duration = (event_ts - prev_ts).total_seconds()
                
                # Check if session was interrupted by inactive event
                inactive_event = self.repo.find_last_by_types(
                    EventRepository.INACTIVE_EVENTS,
                    before=event_ts
                )
                
                if inactive_event:
                    inactive_ts = datetime.datetime.fromisoformat(inactive_event.timestamp)
                    # Only count time up to inactive event if it occurred during this period
                    if inactive_ts > prev_ts and inactive_ts < event_ts:
                        duration = (inactive_ts - prev_ts).total_seconds()
                
                if duration > 0:
                    app_times[prev_app] = app_times.get(prev_app, 0.0) + duration
            
            prev_app = current_app
            prev_ts = event_ts
        
        # Handle last app until end of day or inactive event
        if prev_app:
            # Find if there was an inactive event after last switch
            last_inactive = self.repo.find_last_by_types(
                EventRepository.INACTIVE_EVENTS,
                before=end
            )
            
            if last_inactive:
                last_inactive_ts = datetime.datetime.fromisoformat(last_inactive.timestamp)
                if last_inactive_ts > prev_ts:
                    duration = (last_inactive_ts - prev_ts).total_seconds()
                else:
                    duration = (end - prev_ts).total_seconds()
            else:
                duration = (end - prev_ts).total_seconds()
            
            if duration > 0:
                app_times[prev_app] = app_times.get(prev_app, 0.0) + duration
        
        return app_times
    
    @staticmethod
    def _extract_app_from_detail(detail: str, is_target: bool = True) -> str:
        """
        Extract app name from app_switch detail string.
        
        Args:
            detail: String like "app1 → app2"
            is_target: If True, return app2; if False, return app1
        """
        if not detail or '→' not in detail:
            return "unknown"
        
        parts = detail.split('→')
        if len(parts) != 2:
            return "unknown"
        
        if is_target:
            return parts[1].strip()
        else:
            return parts[0].strip()

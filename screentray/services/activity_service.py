"""Service for activity period calculations."""
import datetime
from typing import Any, List, Dict
from ..db.event_repository import EventRepository
from ..models import Event


class ActivityService:
    """Handles activity period analysis."""

    def __init__(self) -> None:
        self.repo = EventRepository()

    def get_activity_periods_for_day(self, day: datetime.date) -> List[Dict[str, Any]]:
        """
        Get all activity periods for a specific day.

        Returns:
            List of dicts with 'start', 'end', 'state', 'duration_seconds'
        """
        start = datetime.datetime.combine(day, datetime.time.min)
        end = datetime.datetime.combine(day, datetime.time.max)

        events = self.repo.find_events_in_period(start, end)
        return self._build_periods(events, start, end)

    def get_activity_periods_last_24h(self) -> List[Dict[str, Any]]:
        """Get activity periods for the last 24 hours."""
        end = datetime.datetime.now()
        start = end - datetime.timedelta(hours=24)

        events = self.repo.find_events_in_period(start, end)
        return self._build_periods(events, start, end)

    def _build_periods(self, events: List[Event], period_start: datetime.datetime,
                       period_end: datetime.datetime) -> List[Dict[str, Any]]:
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

        periods: List[Dict[str, Any]] = []
        last_ts = period_start
        last_state = "inactive"  # Default to inactive

        for event in events:
            event_ts = datetime.datetime.fromisoformat(event.timestamp)

            # Determine state based on event type
            if event.type in EventRepository.INACTIVE_EVENTS:
                new_state = "inactive"
            elif event.type in EventRepository.ACTIVE_EVENTS:
                new_state = "active"
            else:
                # Non-state events don't trigger state changes
                continue

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

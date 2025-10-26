"""Service for session-related calculations (single source of truth)."""
import datetime
from typing import Tuple, List, Dict, Any
from ..config import IDLE_THRESHOLD_MS
from ..db.event_repository import EventRepository

MAX_NO_EVENT_GAP = IDLE_THRESHOLD_MS // 1000


class SessionService:
    """Handles all session-related calculations using period reconstruction."""

    def __init__(self) -> None:
        self.repo = EventRepository()

    def _build_recent_periods(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Build activity periods from events, same logic as web interface."""
        now = datetime.datetime.now()
        since = now - datetime.timedelta(hours=hours)

        events = self.repo.find_events_in_period(since, now)

        if not events:
            return [{
                "start": since,
                "end": now,
                "state": "inactive",
                "duration": (now - since).total_seconds()
            }]

        periods: List[Dict[str, Any]] = []
        last_ts = since
        last_state = "inactive"  # Assume inactive before first event
        last_event_ts = since

        for event in events:
            ts = datetime.datetime.fromisoformat(event.timestamp)

            # Check for gaps (no events > threshold = inactive)
            gap = (ts - last_event_ts).total_seconds()
            if gap > MAX_NO_EVENT_GAP:
                # Gap detected - insert inactive period
                if last_state == "active":
                    # Close active period, add gap
                    periods.append({
                        "start": last_ts,
                        "end": last_event_ts,
                        "state": last_state,
                        "duration": (last_event_ts - last_ts).total_seconds()
                    })
                    periods.append({
                        "start": last_event_ts,
                        "end": ts,
                        "state": "inactive",
                        "duration": gap
                    })
                    last_ts = ts
                    last_state = "inactive"
                else:
                    # Already inactive, just extend the gap
                    pass

            # Determine state from event type
            if event.type in EventRepository.INACTIVE_EVENTS:
                new_state = "inactive"
            elif event.type in EventRepository.ACTIVE_EVENTS:
                new_state = "active"
            elif event.type == "poll" and event.detail:
                # Poll events contain state info - use them to infer state
                if "state=active" in event.detail:
                    new_state = "active"
                elif "state=inactive" in event.detail:
                    new_state = "inactive"
                else:
                    last_event_ts = ts
                    continue
            else:
                # Non-state events don't change state
                last_event_ts = ts
                continue

            # State changed - close previous period
            if new_state != last_state:
                periods.append({
                    "start": last_ts,
                    "end": ts,
                    "state": last_state,
                    "duration": (ts - last_ts).total_seconds()
                })
                last_ts = ts
                last_state = new_state

            last_event_ts = ts

        # Check for gap at end
        gap = (now - last_event_ts).total_seconds()
        if gap > MAX_NO_EVENT_GAP:
            # Large gap at end - force inactive
            if last_state == "active":
                periods.append({
                    "start": last_ts,
                    "end": last_event_ts,
                    "state": last_state,
                    "duration": (last_event_ts - last_ts).total_seconds()
                })
                periods.append({
                    "start": last_event_ts,
                    "end": now,
                    "state": "inactive",
                    "duration": gap
                })
            else:
                # Already inactive, extend to now
                periods.append({
                    "start": last_ts,
                    "end": now,
                    "state": last_state,
                    "duration": (now - last_ts).total_seconds()
                })
        else:
            # Normal final period
            periods.append({
                "start": last_ts,
                "end": now,
                "state": last_state,
                "duration": (now - last_ts).total_seconds()
            })

        return periods

    def get_current_session(self) -> Tuple[datetime.datetime | None, float]:
        """
        Get current active session start time and duration.

        Returns:
            Tuple of (start_datetime, duration_seconds)
            Returns (None, 0.0) if no active session
        """
        periods = self._build_recent_periods(hours=24)

        # Last period is current state
        if not periods:
            return (None, 0.0)

        current = periods[-1]

        if current["state"] == "active":
            return (current["start"], current["duration"])
        else:
            return (None, 0.0)

    def get_current_session_seconds(self) -> float:
        """Get duration of current session in seconds."""
        _, duration = self.get_current_session()
        return duration

    def get_last_break(self) -> Tuple[datetime.datetime | None, datetime.datetime | None, float]:
        """
        Get the last break period (inactive time).

        Returns:
            Tuple of (break_start, break_end, duration_seconds)
            Returns (None, None, 0.0) if no recent break found
        """
        periods = self._build_recent_periods(hours=24)

        if not periods:
            return (None, None, 0.0)

        current = periods[-1]

        # If currently inactive, return current period as ongoing break
        if current["state"] == "inactive":
            return (current["start"], None, current["duration"])

        # Otherwise find last inactive period
        for period in reversed(periods[:-1]):
            if period["state"] == "inactive":
                return (period["start"], period["end"], period["duration"])

        return (None, None, 0.0)

    def get_last_break_seconds(self) -> float:
        """Get duration of last break in seconds."""
        _, _, duration = self.get_last_break()
        return duration

    def is_currently_active(self) -> bool:
        """Check if there's an active session right now."""
        _, duration = self.get_current_session()
        return duration > 0
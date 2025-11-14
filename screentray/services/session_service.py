"""Service for session-related calculations (single source of truth)."""
import datetime
from typing import Tuple, List, Dict, Any
from ..db.event_repository import EventRepository
# --- MODIFIED: Import ActivityService ---
from .activity_service import ActivityService


class SessionService:
    """Handles all session-related calculations by delegating to ActivityService."""

    def __init__(self) -> None:
        self.repo = EventRepository()
        # --- MODIFIED: Create an ActivityService instance ---
        self.activity_service = ActivityService()

    # --- MODIFIED: _build_recent_periods is REMOVED ---
    # We now call self.activity_service.get_detailed_activity_periods()

    def _get_periods_for_session(self) -> List[Dict[str, Any]]:
        """
        Helper to get detailed periods, converting string timestamps to datetimes.
        """
        # Call the consolidated method from ActivityService
        periods_raw = self.activity_service.get_detailed_activity_periods(hours=24)

        # Convert timestamps for internal use
        for p in periods_raw:
            p["start"] = datetime.datetime.fromisoformat(p["start"])
            p["end"] = datetime.datetime.fromisoformat(p["end"])
            p["duration"] = p["duration_sec"] # alias for consistency

        return periods_raw

    def get_current_session(self) -> Tuple[datetime.datetime | None, float]:
        """
        Get current active session start time and duration.
        """
        periods = self._get_periods_for_session()

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
        """
        periods = self._get_periods_for_session()

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

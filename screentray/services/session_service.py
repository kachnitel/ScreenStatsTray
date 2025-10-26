"""Service for session-related calculations (single source of truth)."""
import datetime
from typing import Optional, Tuple
from ..config import IDLE_THRESHOLD_MS
from ..db.event_repository import EventRepository

MAX_NO_EVENT_GAP = IDLE_THRESHOLD_MS // 1000


class SessionService:
    """Handles all session-related calculations."""

    def __init__(self) -> None:
        self.repo = EventRepository()

    def get_current_session(self) -> Tuple[datetime.datetime | None, float]:
        """
        Get current active session start time and duration.
        Uses same logic as web interface: find last state-changing event.

        Returns:
            Tuple of (start_datetime, duration_seconds)
            Returns (None, 0.0) if no active session
        """
        now = datetime.datetime.now()

        # Get the most recent event of any state-changing type
        last_active = self.repo.find_last_active()
        last_inactive = self.repo.find_last_inactive()

        # Determine current state based on most recent event
        if last_active and last_inactive:
            active_ts = datetime.datetime.fromisoformat(last_active.timestamp)
            inactive_ts = datetime.datetime.fromisoformat(last_inactive.timestamp)

            if active_ts > inactive_ts:
                # Most recent event was active - we're in an active session
                duration = (now - active_ts).total_seconds()

                # Safety check: if too much time passed, consider inactive
                if duration > MAX_NO_EVENT_GAP:
                    return (None, 0.0)

                return (active_ts, duration)
            else:
                # Most recent event was inactive
                return (None, 0.0)

        elif last_active:
            # Only active events exist - we're active since that event
            active_ts = datetime.datetime.fromisoformat(last_active.timestamp)
            duration = (now - active_ts).total_seconds()

            if duration > MAX_NO_EVENT_GAP:
                return (None, 0.0)

            return (active_ts, duration)

        else:
            # No events at all
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
        now = datetime.datetime.now()

        last_active = self.repo.find_last_active()
        last_inactive = self.repo.find_last_inactive()

        if not last_inactive:
            return (None, None, 0.0)

        inactive_ts = datetime.datetime.fromisoformat(last_inactive.timestamp)

        if last_active:
            active_ts = datetime.datetime.fromisoformat(last_active.timestamp)

            if active_ts > inactive_ts:
                # Break ended - return the completed break
                duration = (active_ts - inactive_ts).total_seconds()
                return (inactive_ts, active_ts, duration)
            else:
                # Still in break
                duration = (now - inactive_ts).total_seconds()
                return (inactive_ts, None, duration)
        else:
            # No active events, still in break
            duration = (now - inactive_ts).total_seconds()
            return (inactive_ts, None, duration)

    def get_last_break_seconds(self) -> float:
        """Get duration of last break in seconds."""
        _, _, duration = self.get_last_break()
        return duration

    def is_currently_active(self) -> bool:
        """Check if there's an active session right now."""
        _, duration = self.get_current_session()
        return duration > 0
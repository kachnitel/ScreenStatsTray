"""Service for session-related calculations (single source of truth)."""
import datetime
from typing import Optional, Tuple
from ..config import IDLE_THRESHOLD_MS
from ..db.event_repository import EventRepository

# Convert to seconds
MAX_NO_EVENT_GAP = IDLE_THRESHOLD_MS // 1000


class SessionService:
    """Handles all session-related calculations."""
    
    def __init__(self) -> None:
        self.repo = EventRepository()
    
    def get_current_session(self) -> Tuple[datetime.datetime | None, float]:
        """
        Get current active session start time and duration.
        
        Returns:
            Tuple of (start_datetime, duration_seconds)
            Returns (None, 0.0) if no active session
        """
        now = datetime.datetime.now()
        
        # Find last active event (session start candidate)
        last_active = self.repo.find_last_active()
        if not last_active:
            return (None, 0.0)
        
        start = datetime.datetime.fromisoformat(last_active.timestamp)
        
        # Check if any inactive event occurred after session start
        last_inactive_after = self.repo.find_last_inactive_after(start)
        if last_inactive_after:
            # Session was interrupted
            return (None, 0.0)
        
        # Check if session exceeded max gap (no events = inactive)
        duration = (now - start).total_seconds()
        if duration > MAX_NO_EVENT_GAP:
            return (None, 0.0)
        
        return (start, duration)
    
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
        
        # Find most recent inactive->active transition
        transition = self.repo.find_last_inactive_to_active_transition()
        if transition:
            inactive_event, active_event = transition
            start = datetime.datetime.fromisoformat(inactive_event.timestamp)
            end = datetime.datetime.fromisoformat(active_event.timestamp)
            duration = (end - start).total_seconds()
            
            # Only count as a break if it exceeds the threshold
            if duration >= MAX_NO_EVENT_GAP:
                return (start, end, duration)
        
        # Check if currently in an inactive state
        last_inactive = self.repo.find_last_inactive()
        if last_inactive:
            inactive_ts = datetime.datetime.fromisoformat(last_inactive.timestamp)
            
            # Verify no active event came after
            last_active = self.repo.find_last_active()
            if not last_active or datetime.datetime.fromisoformat(last_active.timestamp) < inactive_ts:
                # Still inactive
                duration = (now - inactive_ts).total_seconds()
                if duration >= MAX_NO_EVENT_GAP:
                    return (inactive_ts, None, duration)
        
        return (None, None, 0.0)
    
    def get_last_break_seconds(self) -> float:
        """Get duration of last break in seconds."""
        _, _, duration = self.get_last_break()
        return duration
    
    def is_currently_active(self) -> bool:
        """Check if there's an active session right now."""
        _, duration = self.get_current_session()
        return duration > 0

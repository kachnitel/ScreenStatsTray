"""Service for activity period calculations."""
import datetime
from typing import Any, List, Dict
from ..db.event_repository import EventRepository
from ..models import Event
from ..config import MAX_NO_EVENT_GAP


class ActivityService:
    """Handles activity period analysis."""

    def __init__(self) -> None:
        self.repo = EventRepository()

    def get_activity_periods_for_day(self, day: datetime.date) -> List[Dict[str, Any]]:
        """
        Get all *simple* activity periods for a specific day.
        Used by StatsService for historical totals.
        """
        start = datetime.datetime.combine(day, datetime.time.min)
        end = datetime.datetime.combine(day, datetime.time.max)

        events = self.repo.find_events_in_period(start, end)
        return self._build_simple_periods(events, start, end)

    def get_activity_periods_last_24h(self) -> List[Dict[str, Any]]:
        """Get *simple* activity periods for the last 24 hours."""
        end = datetime.datetime.now()
        start = end - datetime.timedelta(hours=24)

        events = self.repo.find_events_in_period(start, end)
        return self._build_simple_periods(events, start, end)

    def _build_simple_periods(self, events: List[Event], period_start: datetime.datetime,
                              period_end: datetime.datetime) -> List[Dict[str, Any]]:
        """
        Build simple activity periods from state-changing events only.
        This method does NOT do gap detection.
        """
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

        # For today, 'now' is earlier than 'period_end', so 'now' is used.
        now = datetime.datetime.now()
        effective_end = min(period_end, now)

        # Add final period up to the effective_end
        if last_ts < effective_end:
            duration = (effective_end - last_ts).total_seconds()
            if duration > 0:
                periods.append({
                    "start": last_ts,
                    "end": effective_end,
                    "state": last_state,
                    "duration_seconds": duration
                })

        return periods

    def get_detailed_activity_periods(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get detailed activity periods, including gap detection and raw events.
        This is the consolidated logic previously in SessionService and core_routes.
        """
        now = datetime.datetime.now()
        since = now - datetime.timedelta(hours=hours)

        events = self.repo.find_events_in_period(since, now)

        if not events:
            return [{
                "start": since.isoformat(),
                "end": now.isoformat(),
                "state": "inactive",
                "duration_sec": (now - since).total_seconds(),
                "trigger_event": None,
                "events": []
            }]

        periods: List[Dict[str, Any]] = []
        last_ts = since
        last_state = "inactive"  # Assume inactive before first event
        last_event_ts = since
        current_events: List[Dict[str, Any]] = []

        for event in events:
            ts = datetime.datetime.fromisoformat(event.timestamp)
            typ = event.type

            event_dict: Dict[str, Any] = {
                "id": event.id,
                "timestamp": event.timestamp,
                "type": typ,
                "detail": event.detail or ""
            }

            # Check for gaps (no events > threshold = inactive)
            gap = (ts - last_event_ts).total_seconds()
            if gap > MAX_NO_EVENT_GAP:
                # Gap detected - insert inactive period
                if last_state == "active":
                    # Close active period, add gap
                    periods.append({
                        "start": last_ts.isoformat(),
                        "end": last_event_ts.isoformat(),
                        "state": last_state,
                        "duration_sec": (last_event_ts - last_ts).total_seconds(),
                        "trigger_event": None,
                        "events": current_events.copy()
                    })
                    periods.append({
                        "start": last_event_ts.isoformat(),
                        "end": ts.isoformat(),
                        "state": "inactive",
                        "duration_sec": gap,
                        "trigger_event": {"type": "gap", "detail": f"{gap:.0f}s gap"},
                        "events": []
                    })
                    last_ts = ts
                    last_state = "inactive"
                    current_events = []
                else:
                    # Already inactive, just extend the gap
                    pass # We'll handle this when the state *changes*

            # Determine state from event type
            if typ in EventRepository.INACTIVE_EVENTS:
                new_state = "inactive"
            elif typ in EventRepository.ACTIVE_EVENTS:
                new_state = "active"
            elif typ == "poll" and event.detail:
                # Poll events contain state info
                if "state=active" in event.detail:
                    new_state = "active"
                elif "state=inactive" in event.detail:
                    new_state = "inactive"
                else:
                    # Non-state poll - add to current period
                    current_events.append(event_dict)
                    last_event_ts = ts
                    continue
            else:
                # Non-state event (tracker_start, tracker_stop) - add to current period
                current_events.append(event_dict)
                last_event_ts = ts
                continue

            # State changed - close previous period
            if new_state != last_state:
                periods.append({
                    "start": last_ts.isoformat(),
                    "end": ts.isoformat(),
                    "state": last_state,
                    "duration_sec": (ts - last_ts).total_seconds(),
                    "trigger_event": event_dict,
                    "events": current_events.copy()
                })
                current_events = [event_dict]
                last_ts = ts
                last_state = new_state
            else:
                current_events.append(event_dict)

            last_event_ts = ts

        # Check for gap at end
        gap = (now - last_event_ts).total_seconds()
        if gap > MAX_NO_EVENT_GAP:
            # Large gap at end - force inactive
            if last_state == "active":
                periods.append({
                    "start": last_ts.isoformat(),
                    "end": last_event_ts.isoformat(),
                    "state": last_state,
                    "duration_sec": (last_event_ts - last_ts).total_seconds(),
                    "trigger_event": None,
                    "events": current_events
                })
                periods.append({
                    "start": last_event_ts.isoformat(),
                    "end": now.isoformat(),
                    "state": "inactive",
                    "duration_sec": gap,
                    "trigger_event": {"type": "gap", "detail": f"{gap:.0f}s gap"},
                    "events": []
                })
            else:
                # Already inactive, extend to now
                periods.append({
                    "start": last_ts.isoformat(),
                    "end": now.isoformat(),
                    "state": last_state,
                    "duration_sec": (now - last_ts).total_seconds(),
                    "trigger_event": None,
                    "events": current_events
                })
        else:
            # Normal final period
            periods.append({
                "start": last_ts.isoformat(),
                "end": now.isoformat(),
                "state": last_state,
                "duration_sec": (now - last_ts).total_seconds(),
                "trigger_event": None,
                "events": current_events
            })

        # REVIEW: Filter out zero-duration periods (tracker restart artifacts)
        periods = [p for p in periods if p["duration_sec"] > 0]

        return periods

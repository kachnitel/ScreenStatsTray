"""Repository for event data access."""
import datetime
from typing import List, Optional, Tuple
from ..models import Event
from .connection import get_cursor


class EventRepository:
    """Repository for event CRUD operations."""

    # Event type constants - simplified to only track screen and idle states
    ACTIVE_EVENTS = ('screen_on', 'idle_end')
    INACTIVE_EVENTS = ('idle_start', 'screen_off')

    @staticmethod
    def insert(type_: str, detail: str = "", timestamp: Optional[datetime.datetime] = None) -> None:
        """Insert a new event."""
        if timestamp is None:
            timestamp = datetime.datetime.now()
        ts_str = timestamp.isoformat(timespec="seconds")

        with get_cursor() as cur:
            cur.execute(
                "INSERT INTO events (timestamp, type, detail) VALUES (?, ?, ?)",
                (ts_str, type_, detail)
            )

    @staticmethod
    def find_last_by_types(types: Tuple[str, ...], before: Optional[datetime.datetime] = None) -> Optional[Event]:
        """Find the most recent event of given types."""
        with get_cursor() as cur:
            if before:
                cur.execute("""
                    SELECT id, timestamp, type, detail
                    FROM events
                    WHERE type IN ({})
                      AND timestamp < ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                """.format(','.join('?' * len(types))), types + (before.isoformat(),))
            else:
                cur.execute("""
                    SELECT id, timestamp, type, detail
                    FROM events
                    WHERE type IN ({})
                    ORDER BY timestamp DESC
                    LIMIT 1
                """.format(','.join('?' * len(types))), types)

            row = cur.fetchone()
            if row:
                return Event(id=row[0], timestamp=row[1], type=row[2], detail=row[3])
            return None

    @staticmethod
    def find_last_active() -> Optional[Event]:
        """Find the most recent active event."""
        return EventRepository.find_last_by_types(EventRepository.ACTIVE_EVENTS)

    @staticmethod
    def find_last_inactive() -> Optional[Event]:
        """Find the most recent inactive event."""
        return EventRepository.find_last_by_types(EventRepository.INACTIVE_EVENTS)

    @staticmethod
    def find_last_inactive_after(after: datetime.datetime) -> Optional[Event]:
        """Find the most recent inactive event after a given time."""
        with get_cursor() as cur:
            cur.execute("""
                SELECT id, timestamp, type, detail
                FROM events
                WHERE type IN ({})
                  AND timestamp > ?
                ORDER BY timestamp DESC
                LIMIT 1
            """.format(','.join('?' * len(EventRepository.INACTIVE_EVENTS))),
            EventRepository.INACTIVE_EVENTS + (after.isoformat(),))

            row = cur.fetchone()
            if row:
                return Event(id=row[0], timestamp=row[1], type=row[2], detail=row[3])
            return None

    @staticmethod
    def find_events_in_period(start: datetime.datetime, end: datetime.datetime,
                              types: Optional[Tuple[str, ...]] = None) -> List[Event]:
        """Find all events in a time period, optionally filtered by type."""
        with get_cursor() as cur:
            if types:
                cur.execute("""
                    SELECT id, timestamp, type, detail
                    FROM events
                    WHERE timestamp >= ? AND timestamp <= ?
                      AND type IN ({})
                    ORDER BY timestamp ASC
                """.format(','.join('?' * len(types))),
                (start.isoformat(), end.isoformat()) + types)
            else:
                cur.execute("""
                    SELECT id, timestamp, type, detail
                    FROM events
                    WHERE timestamp >= ? AND timestamp <= ?
                    ORDER BY timestamp ASC
                """, (start.isoformat(), end.isoformat()))

            return [Event(id=r[0], timestamp=r[1], type=r[2], detail=r[3])
                    for r in cur.fetchall()]

    @staticmethod
    def find_last_inactive_to_active_transition() -> Optional[Tuple[Event, Event]]:
        """Find the most recent inactive->active transition pair."""
        with get_cursor() as cur:
            cur.execute("""
                WITH inactive_starts AS (
                    SELECT id, timestamp, type
                    FROM events
                    WHERE type IN ({})
                ),
                active_starts AS (
                    SELECT id, timestamp, type
                    FROM events
                    WHERE type IN ({})
                )
                SELECT
                    i.id, i.timestamp, i.type,
                    a.id, a.timestamp, a.type
                FROM inactive_starts i
                INNER JOIN active_starts a ON a.timestamp > i.timestamp
                ORDER BY i.timestamp DESC
                LIMIT 1
            """.format(
                ','.join('?' * len(EventRepository.INACTIVE_EVENTS)),
                ','.join('?' * len(EventRepository.ACTIVE_EVENTS))
            ), EventRepository.INACTIVE_EVENTS + EventRepository.ACTIVE_EVENTS)

            row = cur.fetchone()
            if row:
                inactive = Event(id=row[0], timestamp=row[1], type=row[2], detail="")
                active = Event(id=row[3], timestamp=row[4], type=row[5], detail="")
                return (inactive, active)
            return None
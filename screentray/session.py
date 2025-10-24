import sqlite3
import os
import datetime
from typing import Optional, Tuple

from .config import MAX_NO_EVENT_GAP

DB_PATH: str = os.path.expanduser("~/.local/share/screentracker.db")

def get_last_active_time() -> Optional[datetime.datetime]:
    """
    Return the timestamp of the last 'screen_on' or 'idle_end' event.

    Returns:
        datetime.datetime if found, else None
    """
    if not os.path.exists(DB_PATH):
        return None

    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT timestamp
            FROM events
            WHERE type IN ('screen_on', 'idle_end')
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        row = cur.fetchone()
        return datetime.datetime.fromisoformat(row[0]) if row else None


def current_session_seconds() -> float:
    """
    Return the number of seconds since the last active start
    (last 'screen_on' or 'idle_end' event).

    Returns:
        float: seconds of current session, 0 if no previous active event
    """
    last: Optional[datetime.datetime] = get_last_active_time()
    if not last:
        return 0.0
    return (datetime.datetime.now() - last).total_seconds()

def get_current_session() -> Tuple[float, float]:
    """
    Return start timestamp and duration (seconds) of the current session.
    Session ends if any 'inactive' event is the last: idle_start, screen_off, lid_closed, system_suspend.
    Uses timestamp ordering to handle out-of-order events.
    """
    now = datetime.datetime.now()
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        # last activity event by timestamp
        cur.execute("""
            SELECT timestamp, type
            FROM events
            WHERE type IN ('idle_end','screen_on','system_resume','lid_open')
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        row = cur.fetchone()
        if not row:
            return 0.0, 0.0
        start = datetime.datetime.fromisoformat(row[0])

        # Check if any inactive event occurred after this start time
        cur.execute("""
            SELECT timestamp, type
            FROM events
            WHERE type IN ('idle_start', 'screen_off', 'lid_closed', 'system_suspend')
              AND timestamp > ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (start.isoformat(),))
        inactive_row = cur.fetchone()

        if inactive_row:
            # Session ended at this inactive event
            return 0.0, 0.0

        # If no activity for > MAX_NO_EVENT_GAP, session ended
        if (now - start).total_seconds() > MAX_NO_EVENT_GAP:
            return 0.0, 0.0

        duration = (now - start).total_seconds()
        return start.timestamp(), duration

def get_last_break_seconds() -> float:
    """
    Return duration of last idle period, considering idle, screen_off, lid_closed, suspend.
    Uses timestamp ordering to handle out-of-order events.
    """
    now = datetime.datetime.now()
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()

        # Find the most recent inactive->active transition by timestamp
        cur.execute("""
            WITH inactive_starts AS (
                SELECT timestamp, type
                FROM events
                WHERE type IN ('idle_start','screen_off','lid_closed','system_suspend')
            ),
            active_starts AS (
                SELECT timestamp, type
                FROM events
                WHERE type IN ('idle_end','screen_on','lid_open','system_resume')
            )
            SELECT
                i.timestamp as start_ts,
                a.timestamp as end_ts,
                a.type as end_type
            FROM inactive_starts i
            LEFT JOIN active_starts a ON a.timestamp > i.timestamp
            WHERE a.timestamp IS NOT NULL
            ORDER BY i.timestamp DESC
            LIMIT 1
        """)
        row = cur.fetchone()

        if row:
            start_dt = datetime.datetime.fromisoformat(row[0])
            end_dt = datetime.datetime.fromisoformat(row[1])
            return (end_dt - start_dt).total_seconds()

        # Check if currently in an inactive state
        cur.execute("""
            SELECT timestamp, type
            FROM events
            WHERE type IN ('idle_start','screen_off','lid_closed','system_suspend')
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        inactive_row = cur.fetchone()

        if inactive_row:
            # Check if there's been an active event since
            inactive_ts = datetime.datetime.fromisoformat(inactive_row[0])
            cur.execute("""
                SELECT timestamp
                FROM events
                WHERE type IN ('idle_end','screen_on','lid_open','system_resume')
                  AND timestamp > ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (inactive_row[0],))
            active_after = cur.fetchone()

            if not active_after:
                # Still inactive since that event
                return (now - inactive_ts).total_seconds()

        return 0.0

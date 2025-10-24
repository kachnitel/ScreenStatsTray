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
            ORDER BY id DESC
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
    """
    now = datetime.datetime.now()
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        # last activity event
        cur.execute("""
            SELECT timestamp, type
            FROM events
            WHERE type IN ('idle_end','screen_on')
               OR type='system_resume'
               OR type='lid_open'
            ORDER BY id DESC
            LIMIT 1
        """)
        row = cur.fetchone()
        if not row:
            return 0, 0
        start = datetime.datetime.fromisoformat(row[0])

        # last event of any type
        cur.execute("SELECT type, timestamp FROM events ORDER BY id DESC LIMIT 1")
        last_type, _ = cur.fetchone()
        if last_type in ("idle_start", "screen_off", "lid_closed", "system_suspend"):
            return 0, 0

        # If no activity for > IDLE_THRESHOLD_MS, mark session ended
        if (datetime.datetime.now() - start).total_seconds() > MAX_NO_EVENT_GAP:
            return 0, 0

        duration = (now - start).total_seconds()
        return start.timestamp(), duration

def get_last_break_seconds() -> float:
    """
    Return duration of last idle period, considering idle, screen_off, lid_closed, suspend.
    """
    now = datetime.datetime.now()
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT prev.timestamp, curr.timestamp, curr.type
            FROM events AS curr
            JOIN events AS prev ON prev.id = curr.id - 1
            WHERE prev.type IN ('idle_start','screen_off','lid_closed','system_suspend')
              AND curr.type IN ('idle_end','screen_on','lid_open','system_resume',
                                'idle_start','screen_off','lid_closed','system_suspend')
            ORDER BY curr.id DESC
            LIMIT 1
        """)
        row = cur.fetchone()
        if not row:
            return 0
        start, end, curr_type = row
        start_dt = datetime.datetime.fromisoformat(start)
        if curr_type in ("idle_end","screen_on","lid_open","system_resume"):
            end_dt = datetime.datetime.fromisoformat(end)
        else:
            end_dt = now  # still inactive
        return (end_dt - start_dt).total_seconds()


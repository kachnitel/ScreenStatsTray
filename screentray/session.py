import sqlite3
import os
import datetime
from typing import Optional

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

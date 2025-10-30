"""
screentray/plugins/app_tracker/db.py

Database operations for application tracking.
"""
import sqlite3
import datetime
from typing import Optional
from ...db.connection import get_cursor, DB_PATH


def ensure_tables() -> None:
    """Create app_usage table if it doesn't exist."""
    with get_cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS app_usage (
                id INTEGER PRIMARY KEY,
                timestamp TEXT NOT NULL,
                app_name TEXT NOT NULL,
                window_title TEXT,
                event_type TEXT NOT NULL
            )
        """)
        # Index for efficient queries
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_app_usage_timestamp
            ON app_usage(timestamp)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_app_usage_app_name
            ON app_usage(app_name)
        """)


def drop_tables() -> None:
    """Remove app_usage table (used during uninstall)."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS app_usage")
    cur.execute("DROP INDEX IF EXISTS idx_app_usage_timestamp")
    cur.execute("DROP INDEX IF EXISTS idx_app_usage_app_name")
    conn.commit()
    conn.close()


def insert_app_event(
    app_name: str,
    event_type: str,
    window_title: Optional[str] = None,
    timestamp: Optional[datetime.datetime] = None
) -> None:
    """
    Insert an application event.

    Args:
        app_name: Name of the application
        event_type: 'switch_to' or 'switch_from'
        window_title: Optional window title
        timestamp: Event timestamp (default: now)
    """
    if timestamp is None:
        timestamp = datetime.datetime.now()

    ts_str = timestamp.isoformat(timespec="seconds")

    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO app_usage (timestamp, app_name, window_title, event_type)
            VALUES (?, ?, ?, ?)
        """, (ts_str, app_name, window_title or "", event_type))


def get_last_app_switch() -> Optional[tuple[str, str]]:
    """
    Get the last app that was switched to.

    Returns:
        Tuple of (app_name, timestamp) or None
    """
    with get_cursor() as cur:
        cur.execute("""
            SELECT app_name, timestamp
            FROM app_usage
            WHERE event_type = 'switch_to'
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        row = cur.fetchone()
        if row:
            return (row[0], row[1])
        return None

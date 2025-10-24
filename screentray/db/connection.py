"""Database connection management."""
import sqlite3
import os
from contextlib import contextmanager
from typing import Iterator

DB_PATH: str = os.path.expanduser("~/.local/share/screentracker.db")


def get_connection() -> sqlite3.Connection:
    """Create and return a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_cursor() -> Iterator[sqlite3.Cursor]:
    """Context manager for database operations."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def ensure_db_exists() -> None:
    """Ensure database directory and table exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY,
                timestamp TEXT NOT NULL,
                type TEXT NOT NULL,
                detail TEXT DEFAULT ''
            )
        """)
        # Create index for timestamp-based queries
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_timestamp 
            ON events(timestamp)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_type 
            ON events(type)
        """)

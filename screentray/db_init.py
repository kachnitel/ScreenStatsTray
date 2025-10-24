#!/usr/bin/env python3
"""
Initialize or update the SQLite database schema from the Event dataclass.
"""

import sqlite3
import os
from dataclasses import fields, MISSING
from typing import Any, Set
from screentray.models import Event
from screentray.config import DB_PATH

# Ensure directory exists
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# Map Python types to SQLite types and default conversions
TYPE_MAP: dict[Any, str] = {
    int: "INTEGER",
    str: "TEXT",
    float: "REAL",
    bool: "INTEGER",  # store bool as 0/1
}

def convert_default(value: Any) -> str:
    """Convert Python default value to SQL-safe string."""
    if isinstance(value, str):
        return f"'{value}'"
    elif isinstance(value, bool):
        return "1" if value else "0"
    else:
        return str(value)

def init_db() -> None:
    """Initialize or update the database schema."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='events';")
    table_exists = cursor.fetchone() is not None

    # Existing columns
    existing_cols: Set[str] = set()
    if table_exists:
        cursor.execute("PRAGMA table_info(events);")
        existing_cols = {row[1] for row in cursor.fetchall()}

    # Build column definitions
    columns_list: list[str] = []
    for f in fields(Event):
        if f.name in existing_cols:
            continue  # skip existing column
        sql_type = TYPE_MAP.get(f.type, "TEXT")
        col_def = f"{f.name} {sql_type}"

        # Primary key
        if f.name == "id":
            col_def += " PRIMARY KEY"
        # Default value
        elif f.default is not MISSING:
            col_def += f" DEFAULT {convert_default(f.default)}"
        elif f.default_factory is not MISSING:
            pass  # leave nullable
        else:
            col_def += " NOT NULL"

        if table_exists:
            print(f"Adding column: {f.name}...")
            cursor.execute(f"ALTER TABLE events ADD COLUMN {col_def};")
        else:
            columns_list.append(col_def)

    # Create table if not exists
    if not table_exists:
        create_table_sql = f"CREATE TABLE events ({', '.join(columns_list)});"
        print("Creating new 'events' table...")
        cursor.execute(create_table_sql)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print(f"Database initialized/updated at {DB_PATH}")

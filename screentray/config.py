# import os
from pathlib import Path

HOME = Path.home()
DB_PATH = HOME / ".local" / "share" / "screentracker.db"
UPDATE_INTERVAL_MS = 5000
SWITCH_MIN_DURATION = 5  # seconds
IDLE_THRESHOLD_MS = 300_000

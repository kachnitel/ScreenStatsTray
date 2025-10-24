import os

DB_PATH: str = os.path.expanduser("~/.local/share/screentracker.db")
LOG_INTERVAL: int = 2
IDLE_THRESHOLD_MS: int = 600_000  # 10 minutes
SWITCH_MIN_DURATION: int = 5  # seconds
MAX_NO_EVENT_GAP: int = IDLE_THRESHOLD_MS // 1000  # 10 minutes
import os

DB_PATH: str = os.path.expanduser(os.environ.get("SCREENTRACKER_DB", "~/.local/share/screentracker.db"))
LOG_INTERVAL: int = 2
IDLE_THRESHOLD_MS: int = 600_000  # 10 minutes
SWITCH_MIN_DURATION: int = 5  # seconds
MAX_NO_EVENT_GAP: int = IDLE_THRESHOLD_MS // 1000  # 10 minutes

# Tray session alert threshold (minutes)
ALERT_SESSION_MINUTES: int = 30

# Action buttons on notification
NOTIFY_BUTTONS = {
    "suspend": True,
    "screen_off": True,
    "lock_screen": True,
}

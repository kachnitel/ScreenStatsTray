import os
import json
from typing import Any, Dict

DB_PATH: str = os.path.expanduser(os.environ.get("SCREENTRACKER_DB", "~/.local/share/screentracker.db"))
LOG_INTERVAL: int = 2
IDLE_THRESHOLD_MS: int = 600_000  # 10 minutes
SWITCH_MIN_DURATION: int = 5  # seconds
MAX_NO_EVENT_GAP: int = IDLE_THRESHOLD_MS // 1000  # 10 minutes
ICON_PULSE_INTERVAL = 10000

# User configuration file path
USER_CONFIG_PATH: str = os.path.expanduser("~/.config/screentray/settings.json")

# Action buttons on notification
NOTIFY_BUTTONS = {
    "suspend": True,
    "screen_off": True,
    "lock_screen": True,
    "snooze": True,
}

# Debug mode - logs detailed tracking information
DEBUG_MODE: bool = os.environ.get("SCREENTRACKER_DEBUG", "0") == "1"
DEBUG_LOG_PATH: str = os.path.expanduser("~/.local/share/screentracker_debug.log")


# --- Dynamic Configuration Class ---

class Config:
    """
    Manages dynamic application settings loaded from the user's JSON file.

    This class holds settings that can be reloaded at runtime.
    """
    # Default values are defined as class attributes
    DEFAULT_ALERT_SESSION_MINUTES: int = 30
    DEFAULT_SNOOZE_MINUTES: int = 10

    def __init__(self, config_path: str = USER_CONFIG_PATH):
        """
        Initializes the configuration object and loads initial values.
        """
        self.config_path = config_path
        self._user_config: Dict[str, Any] = {}

        # Initialize instance attributes with defaults
        # These will be updated by self.reload()
        self.alert_session_minutes: int = self.DEFAULT_ALERT_SESSION_MINUTES
        self.snooze_minutes: int = self.DEFAULT_SNOOZE_MINUTES

        # Load the actual values from the config file
        self.reload()

    def _load_user_config(self) -> Dict[str, Any]:
        """Load user configuration from file."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                # You could add logging here to notify of a broken config file
                pass
        return {}

    def reload(self) -> None:
        """
        Reload configuration from disk, updating this object's attributes.
        """
        self._user_config = self._load_user_config()

        # Update instance attributes from the loaded config,
        # falling back to the class defaults.
        self.alert_session_minutes = self._user_config.get(
            'alert_session_minutes', self.DEFAULT_ALERT_SESSION_MINUTES
        )
        self.snooze_minutes = self._user_config.get(
            'snooze_minutes', self.DEFAULT_SNOOZE_MINUTES
        )


# --- Singleton Instance ---
# This is the single, shared instance of the Config class that
# the rest of your application will import and use.
settings = Config()

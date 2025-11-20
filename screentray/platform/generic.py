"""Generic X11/Wayland fallback implementation."""
import subprocess
from typing import Optional, Tuple
from .base import PlatformBase


class GenericPlatform(PlatformBase):
    """Fallback for unknown desktop environments."""

    IDLE_COMMANDS = [["xprintidle"]]
    SCREEN_STATE_COMMAND = ["xset", "-q"]
    WINDOW_COMMANDS = {
        "get_id": ["xdotool", "getactivewindow"],
        "get_class": ["xdotool", "getwindowclassname"],
        "get_title": ["xdotool", "getwindowname"]
    }
    SCREEN_OFF_COMMAND = ["xset", "dpms", "force", "off"]
    LOCK_COMMAND = ["loginctl", "lock-session"]

    @property
    def name(self) -> str:
        return "Generic"

    @property
    def supports_window_tracking(self) -> bool:
        return self._is_x11() and self._check_command("xdotool")

    def get_idle_seconds(self) -> float:
        """Try xprintidle, fallback to 0."""
        try:
            idle_ms = int(subprocess.check_output(self.IDLE_COMMANDS[0]).strip())
            return idle_ms / 1000.0
        except (FileNotFoundError, subprocess.CalledProcessError):
            return 0.0

    def is_screen_on(self) -> bool:
        """Try xset, assume on if unavailable."""
        try:
            out = subprocess.check_output(self.SCREEN_STATE_COMMAND).decode()
            return "Monitor is On" in out
        except (FileNotFoundError, subprocess.CalledProcessError):
            return True

    def get_active_window_info(self) -> Optional[Tuple[str, str]]:
        """Only works with xdotool on X11."""
        if not self._is_x11() or not self.WINDOW_COMMANDS:
            return None

        try:
            window_id = subprocess.check_output(
                self.WINDOW_COMMANDS["get_id"],
                stderr=subprocess.DEVNULL
            ).decode().strip()

            app_name = subprocess.check_output(
                self.WINDOW_COMMANDS["get_class"] + [window_id],
                stderr=subprocess.DEVNULL
            ).decode().strip()

            window_title = subprocess.check_output(
                self.WINDOW_COMMANDS["get_title"] + [window_id],
                stderr=subprocess.DEVNULL
            ).decode().strip()

            return (app_name, window_title)
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

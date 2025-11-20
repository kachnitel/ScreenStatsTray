"""KDE Plasma platform implementation."""
import subprocess
from typing import Optional, Tuple
from .base import PlatformBase


class KDEPlatform(PlatformBase):
    """KDE Plasma-specific implementation."""

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
        return "KDE Plasma"

    @property
    def supports_window_tracking(self) -> bool:
        return self._check_command("xdotool")

    def get_idle_seconds(self) -> float:
        """Use xprintidle (X11)."""
        try:
            idle_ms = int(subprocess.check_output(self.IDLE_COMMANDS[0]).strip())
            return idle_ms / 1000.0
        except (FileNotFoundError, subprocess.CalledProcessError):
            return 0.0

    def is_screen_on(self) -> bool:
        """Use xset for DPMS state."""
        try:
            out: bytes = subprocess.check_output(self.SCREEN_STATE_COMMAND)
            return "Monitor is On" in out.decode()
        except (FileNotFoundError, subprocess.CalledProcessError):
            return True

    def get_active_window_info(self) -> Optional[Tuple[str, str]]:
        """Use xdotool for window info."""
        if not self.WINDOW_COMMANDS:
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

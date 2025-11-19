"""Generic X11/Wayland fallback implementation."""
import subprocess
import os
from typing import Optional, Tuple
from .base import PlatformBase


class GenericPlatform(PlatformBase):
    """Fallback for unknown desktop environments."""

    @property
    def name(self) -> str:
        return "Generic"

    @property
    def supports_window_tracking(self) -> bool:
        return self._is_x11() and self._check_command("xdotool")

    def get_idle_seconds(self) -> float:
        """Try xprintidle, fallback to 0."""
        try:
            idle_ms = int(subprocess.check_output(["xprintidle"]).strip())
            return idle_ms / 1000.0
        except (FileNotFoundError, subprocess.CalledProcessError):
            return 0.0

    def is_screen_on(self) -> bool:
        """Try xset, assume on if unavailable."""
        try:
            out = subprocess.check_output(["xset", "-q"]).decode()
            return "Monitor is On" in out
        except (FileNotFoundError, subprocess.CalledProcessError):
            return True

    def get_active_window_info(self) -> Optional[Tuple[str, str]]:
        """Only works with xdotool on X11."""
        if not self._is_x11():
            return None

        try:
            window_id = subprocess.check_output(
                ["xdotool", "getactivewindow"],
                stderr=subprocess.DEVNULL
            ).decode().strip()

            app_name = subprocess.check_output(
                ["xdotool", "getwindowclassname", window_id],
                stderr=subprocess.DEVNULL
            ).decode().strip()

            window_title = subprocess.check_output(
                ["xdotool", "getwindowname", window_id],
                stderr=subprocess.DEVNULL
            ).decode().strip()

            return (app_name, window_title)
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    def suspend(self) -> bool:
        """Try systemctl."""
        if not self._check_command("systemctl"):
            return False
        subprocess.run(["systemctl", "suspend", "--check-inhibitors=no"], check=False)
        return True

    def screen_off(self) -> bool:
        """Try xset if on X11."""
        if not self._is_x11():
            return False
        if not self._check_command("xset"):
            return False
        subprocess.run(["xset", "dpms", "force", "off"], check=False)
        return True

    def lock_screen(self) -> bool:
        """Try loginctl."""
        if not self._check_command("loginctl"):
            return False
        subprocess.run(["loginctl", "lock-session"], check=False)
        return True

    def _is_x11(self) -> bool:
        """Check if running on X11."""
        session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
        return session_type == "x11" or os.environ.get("DISPLAY") is not None

    def _check_command(self, cmd: str) -> bool:
        """Check if command exists."""
        try:
            subprocess.run(["which", cmd], capture_output=True, check=True)
            return True
        except subprocess.CalledProcessError:
            return False


"""KDE Plasma platform implementation."""
import subprocess
from typing import Optional, Tuple
from .base import PlatformBase


class KDEPlatform(PlatformBase):
    """KDE Plasma-specific implementation."""

    @property
    def name(self) -> str:
        return "KDE Plasma"

    @property
    def supports_window_tracking(self) -> bool:
        return self._check_command("xdotool")

    def get_idle_seconds(self) -> float:
        """Use xprintidle (works on X11)."""
        try:
            idle_ms = int(subprocess.check_output(["xprintidle"]).strip())
            return idle_ms / 1000.0
        except (FileNotFoundError, subprocess.CalledProcessError):
            return 0.0

    def is_screen_on(self) -> bool:
        """Use xset for DPMS state."""
        try:
            out = subprocess.check_output(["xset", "-q"]).decode()
            return "Monitor is On" in out
        except (FileNotFoundError, subprocess.CalledProcessError):
            return True

    def get_active_window_info(self) -> Optional[Tuple[str, str]]:
        """Use xdotool for window info."""
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
        """Use systemctl suspend."""
        if not self._check_command("systemctl"):
            return False
        subprocess.run(["systemctl", "suspend", "--check-inhibitors=no"], check=False)
        return True

    def screen_off(self) -> bool:
        """Use xset dpms force off."""
        if not self._check_command("xset"):
            return False
        subprocess.run(["xset", "dpms", "force", "off"], check=False)
        return True

    def lock_screen(self) -> bool:
        """Use loginctl lock-session."""
        if not self._check_command("loginctl"):
            return False
        subprocess.run(["loginctl", "lock-session"], check=False)
        return True

    def _check_command(self, cmd: str) -> bool:
        """Check if command exists."""
        try:
            subprocess.run(["which", cmd], capture_output=True, check=True)
            return True
        except subprocess.CalledProcessError:
            return False


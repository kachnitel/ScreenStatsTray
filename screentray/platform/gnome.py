"""GNOME platform implementation."""
import subprocess
from typing import Optional, Tuple
from .base import PlatformBase


class GNOMEPlatform(PlatformBase):
    """GNOME-specific implementation."""

    @property
    def name(self) -> str:
        return "GNOME"

    @property
    def supports_window_tracking(self) -> bool:
        # GNOME on Wayland doesn't expose window info by default
        return self._is_x11() and self._check_command("xdotool")

    def get_idle_seconds(self) -> float:
        """
        Try multiple methods:
        1. xprintidle on X11
        2. gdbus query to Mutter (Wayland)
        3. Fallback to 0
        """
        # Try xprintidle first (X11)
        try:
            idle_ms = int(subprocess.check_output(["xprintidle"]).strip())
            return idle_ms / 1000.0
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass

        # Try gdbus for Wayland
        try:
            result = subprocess.check_output([
                "gdbus", "call", "--session",
                "--dest", "org.gnome.Mutter.IdleMonitor",
                "--object-path", "/org/gnome/Mutter/IdleMonitor/Core",
                "--method", "org.gnome.Mutter.IdleMonitor.GetIdletime"
            ]).decode().strip()
            # Parse result like "(uint64 12345,)"
            idle_ms = int(result.strip("(),").split()[1])
            return idle_ms / 1000.0
        except (FileNotFoundError, subprocess.CalledProcessError, ValueError):
            pass

        return 0.0

    def is_screen_on(self) -> bool:
        """
        Check screen state via gdbus or xset.
        """
        # Try xset on X11
        if self._is_x11():
            try:
                out = subprocess.check_output(["xset", "-q"]).decode()
                return "Monitor is On" in out
            except (FileNotFoundError, subprocess.CalledProcessError):
                pass

        # GNOME Wayland: assume on (no reliable detection)
        return True

    def get_active_window_info(self) -> Optional[Tuple[str, str]]:
        """Only works on X11 with xdotool."""
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
        """Use systemctl suspend."""
        if not self._check_command("systemctl"):
            return False
        subprocess.run(["systemctl", "suspend", "--check-inhibitors=no"], check=False)
        return True

    def screen_off(self) -> bool:
        """Use xset on X11, no reliable method on Wayland."""
        if not self._is_x11():
            return False
        if not self._check_command("xset"):
            return False
        subprocess.run(["xset", "dpms", "force", "off"], check=False)
        return True

    def lock_screen(self) -> bool:
        """Use gnome-screensaver-command or loginctl."""
        if self._check_command("gnome-screensaver-command"):
            subprocess.run(["gnome-screensaver-command", "-l"], check=False)
            return True
        elif self._check_command("loginctl"):
            subprocess.run(["loginctl", "lock-session"], check=False)
            return True
        return False

    def _is_x11(self) -> bool:
        """Check if running on X11."""
        import os
        session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
        return session_type == "x11" or os.environ.get("DISPLAY") is not None

    def _check_command(self, cmd: str) -> bool:
        """Check if command exists."""
        try:
            subprocess.run(["which", cmd], capture_output=True, check=True)
            return True
        except subprocess.CalledProcessError:
            return False


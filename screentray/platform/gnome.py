"""GNOME platform implementation."""
import subprocess
from typing import Optional, Tuple
from .base import PlatformBase


class GNOMEPlatform(PlatformBase):
    """GNOME-specific implementation."""

    IDLE_COMMANDS = [
        ["xprintidle"],  # X11 fallback
        ["gdbus", "call", "--session",
         "--dest", "org.gnome.Mutter.IdleMonitor",
         "--object-path", "/org/gnome/Mutter/IdleMonitor/Core",
         "--method", "org.gnome.Mutter.IdleMonitor.GetIdletime"]  # Wayland
    ]
    SCREEN_STATE_COMMAND = ["xset", "-q"]  # X11 only
    WINDOW_COMMANDS = {  # X11 only
        "get_id": ["xdotool", "getactivewindow"],
        "get_class": ["xdotool", "getwindowclassname"],
        "get_title": ["xdotool", "getwindowname"]
    }
    SCREEN_OFF_COMMAND = ["xset", "dpms", "force", "off"]  # X11 only
    LOCK_COMMAND = ["gnome-screensaver-command", "-l"]

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
            idle_ms = int(subprocess.check_output(self.IDLE_COMMANDS[0]).strip())
            return idle_ms / 1000.0
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass

        # Try gdbus for Wayland
        try:
            result = subprocess.check_output(self.IDLE_COMMANDS[1]).decode().strip()
            idle_ms = int(result.strip("(),").split()[1])
            return idle_ms / 1000.0
        except (FileNotFoundError, subprocess.CalledProcessError, ValueError):
            pass

        return 0.0

    def is_screen_on(self) -> bool:
        """Check via xset on X11, assume on for Wayland."""

        # GNOME Wayland: assume on (no reliable detection)
        if not self._is_x11():
            return True

        try:
            out = subprocess.check_output(self.SCREEN_STATE_COMMAND).decode()
            return "Monitor is On" in out
        except (FileNotFoundError, subprocess.CalledProcessError):
            return True

    def get_active_window_info(self) -> Optional[Tuple[str, str]]:
        """Only works on X11 with xdotool."""
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

    def lock_screen(self) -> bool:
        """Try gnome-screensaver-command or loginctl."""
        if self._check_command("gnome-screensaver-command"):
            try:
                subprocess.run(["gnome-screensaver-command", "-l"], check=False)
                return True
            except FileNotFoundError:
                pass
        return super().lock_screen()  # Try loginctl fallback

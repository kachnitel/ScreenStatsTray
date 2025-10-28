"""
screentray/plugins/app_tracker/tracker.py

Active window monitoring for application tracking.
"""
import subprocess
from typing import Optional


def get_active_window_info() -> Optional[tuple[str, str]]:
    """
    Get the currently active window's application name and title.

    Uses xdotool to query X11 window information.

    Returns:
        Tuple of (app_name, window_title) or None on error
    """
    try:
        # Get active window ID
        window_id = subprocess.check_output(
            ["xdotool", "getactivewindow"],
            stderr=subprocess.DEVNULL
        ).decode().strip()

        # Get window class (application name)
        app_name = subprocess.check_output(
            ["xdotool", "getwindowclassname", window_id],
            stderr=subprocess.DEVNULL
        ).decode().strip()

        # Get window title
        window_title = subprocess.check_output(
            ["xdotool", "getwindowname", window_id],
            stderr=subprocess.DEVNULL
        ).decode().strip()

        return (app_name, window_title)

    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


class AppTracker:
    """
    Tracks application switches and records them to the database.

    This class is instantiated by the plugin and polled regularly
    by the screentracker service.
    """

    def __init__(self) -> None:
        self.current_app: Optional[str] = None
        self.is_tracking: bool = False

    def start(self) -> None:
        """Begin tracking (called when user becomes active)."""
        self.is_tracking = True
        # Record initial state
        self._check_and_record()

    def stop(self) -> None:
        """Stop tracking (called when user becomes inactive)."""
        if self.current_app and self.is_tracking:
            # Record switch_from for current app
            from .db import insert_app_event
            insert_app_event(self.current_app, "switch_from")
            self.current_app = None
        self.is_tracking = False

    def poll(self) -> None:
        """
        Check for application changes.
        Should be called regularly (e.g., every 2 seconds) by screentracker.
        """
        if not self.is_tracking:
            return

        self._check_and_record()

    def _check_and_record(self) -> None:
        """Internal: check current window and record changes."""
        info = get_active_window_info()

        if info is None:
            return

        app_name, window_title = info

        # Ignore empty/invalid app names
        if not app_name or app_name == "":
            return

        # Check if app changed
        if app_name != self.current_app:
            from .db import insert_app_event

            # Record switch_from for previous app
            if self.current_app:
                insert_app_event(self.current_app, "switch_from")

            # Record switch_to for new app
            insert_app_event(app_name, "switch_to", window_title)

            self.current_app = app_name
            print(f"App switch: {app_name}")
"""
screentray/plugins/app_tracker/tracker.py

Active window monitoring for application tracking.
"""
from typing import Optional, Tuple
from ...platform import get_platform


def get_active_window_info() -> Optional[Tuple[str, str]]:
    """
    Get the currently active window's application name and title.

    Delegates to platform implementation.

    Returns:
        Tuple of (app_name, window_title) or None on error
    """
    platform = get_platform()
    return platform.get_active_window_info()

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

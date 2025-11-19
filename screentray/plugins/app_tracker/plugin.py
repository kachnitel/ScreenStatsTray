"""
screentray/plugins/app_tracker/plugin.py

Main plugin implementation for application tracking.
"""
from typing import Any, Dict, Optional
from PyQt5.QtWidgets import QWidget
from ..base import PluginBase
from . import PLUGIN_INFO
from .tracker import AppTracker
from . import db


class AppTrackerPlugin(PluginBase):
    """
    Application usage tracking plugin.

    Monitors which application has focus and records time spent.
    Only tracks during active periods (not when idle/screen off).
    """

    def __init__(self) -> None:
        self.tracker = AppTracker()

    def get_info(self) -> dict[str, Any]:
        """Return plugin metadata."""
        return PLUGIN_INFO

    def install(self) -> None:
        """Create database tables for app tracking."""
        print("Creating app_usage table...")
        db.ensure_tables()

    def uninstall(self) -> None:
        """Remove database tables."""
        print("Removing app_usage table...")
        db.drop_tables()

    def start(self) -> None:
        """Begin tracking (called by screentracker on startup)."""
        # Check platform compatibility
        from ...platform import get_platform
        platform = get_platform()

        if not platform.supports_window_tracking:
            print(f"Warning: App tracking unavailable on {platform.name} "
                f"(window tracking not supported)")
            return

        # Don't start tracking yet - wait for on_active()
        pass

    def stop(self) -> None:
        """Stop tracking and cleanup."""
        self.tracker.stop()

    def poll(self) -> None:
        """
        Called regularly by screentracker to check for app changes.
        This is the main entry point for the tracking loop.
        """
        self.tracker.poll()

    # State awareness hooks

    def on_active(self) -> None:
        """User became active - start tracking apps."""
        self.tracker.start()

    def on_inactive(self) -> None:
        """User became inactive - stop tracking apps."""
        self.tracker.stop()

    # UI Integration

    def get_popup_widget(self) -> Optional[QWidget]:
        """Return widget for tray popup showing app usage."""
        from .widget import AppUsageWidget
        return AppUsageWidget()

    def get_web_routes(self) -> list[tuple[str, Any]]:
        """Return Flask routes for web interface."""
        try:
            from .web import AppTrackerWeb
            web = AppTrackerWeb()
            return web.get_routes()
        except ImportError as e:
            # Web dependencies not installed
            print(f"Web integration not available: {e}")
            return []
        except Exception as e:
            print(f"Error loading web routes: {e}")
            return []

    def get_web_content(self) -> Dict[str, Any]:
        """Return web UI content for injection into main interface."""
        try:
            from .web import AppTrackerWeb
            web = AppTrackerWeb()
            return web.get_content()
        except ImportError as e:
            # Web dependencies not installed
            print(f"Web integration not available: {e}")
            return {'slots': {}, 'javascript': ''}
        except Exception as e:
            print(f"Error loading web content: {e}")
            import traceback
            traceback.print_exc()
            return {'slots': {}, 'javascript': ''}

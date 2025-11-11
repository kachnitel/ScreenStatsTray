"""
screentray/plugins/base.py

Base plugin interface that all plugins must implement.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from PyQt5.QtWidgets import QWidget


class PluginBase(ABC):
    """
    Base class for all ScreenTray plugins.

    Plugins extend functionality by:
    - Adding their own database tables
    - Contributing widgets to the UI
    - Providing web API endpoints
    """

    @abstractmethod
    def get_info(self) -> dict[str, Any]:
        """
        Return plugin metadata.

        Required keys:
            name: str - Unique plugin identifier
            version: str - Plugin version
            requires_install: bool - Whether plugin needs DB setup
        """
        pass

    @abstractmethod
    def install(self) -> None:
        """
        One-time setup: create database tables, initialize config.
        Called when plugin is first enabled.
        """
        pass

    @abstractmethod
    def uninstall(self) -> None:
        """
        Cleanup: remove database tables, delete config.
        Called when plugin is disabled/removed.
        """
        pass

    @abstractmethod
    def start(self) -> None:
        """
        Begin plugin operation.
        Called when screentracker service starts.
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """
        Stop plugin operation, cleanup resources.
        Called when screentracker service stops.
        """
        pass

    # UI Integration (optional - return None if not implemented)

    def get_popup_widget(self) -> Optional[QWidget]:
        """
        Return a Qt widget to display in the tray popup.

        Returns:
            QWidget or None if no UI component
        """
        return None

    def get_web_routes(self) -> list[tuple[str, Any]]:
        """
        Return Flask route definitions for web interface.

        Returns:
            List of (route_path, view_function) tuples
            Example: [("/api/plugin/data", self.api_data)]
        """
        return []

    def get_web_content(self) -> Dict[str, Any]:
        """
        Return web UI content for injection into main interface.

        Returns:
            Dict with keys:
                'slots': Dict mapping slot names to HTML content
                       Available slots: 'overview_bottom', 'daily_bottom', 'weekly_bottom', 'events_bottom'
                'javascript': JavaScript code to inject into page
                'new_tab': Optional dict with 'id', 'title', and 'content' for a new tab
        """
        return {
            'slots': {},
            'javascript': '',
        }

    # State awareness (plugins can override to react to state changes)

    def on_active(self) -> None:
        """Called when system becomes active (user present)."""
        pass

    def on_inactive(self) -> None:
        """Called when system becomes inactive (idle/screen off)."""
        pass
    # Plugin manager access (optional)
    
    def set_plugin_manager(self, manager: Any) -> None:
        """
        Receive plugin manager reference (optional).
        
        Useful for plugins that need to discover other plugins.
        """
        pass

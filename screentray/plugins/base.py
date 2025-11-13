"""
Base plugin interface with event system integration.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QWidget
    from .manager import PluginManager


class PluginBase(ABC):
    """
    Base class for all ScreenTray plugins.

    Plugins extend functionality through:
    - Database operations (install/uninstall)
    - Event handlers (register_events)
    - State awareness (on_active/on_inactive)
    - Optional UI/web extensions

    Event System:
        Plugins register handlers for lifecycle and UI events through
        register_events(). Core components emit events that plugins
        respond to, avoiding hardcoded coupling.

    Example:
        class MyPlugin(PluginBase):
            def register_events(self, manager: PluginManager) -> None:
                manager.events.subscribe(
                    Event.TRAY_READY,
                    self._on_tray_ready
                )

            def _on_tray_ready(self, ctx: EventContext) -> None:
                ctx.menu.addAction("My Action", self.my_handler)
    """

    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
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

    # Event System Integration

    def register_events(self, manager: 'PluginManager') -> None:
        """
        Register event handlers with the plugin manager.

        Called during initialization to let plugins subscribe to
        UI and lifecycle events without coupling core to plugin
        implementations.

        Args:
            manager: PluginManager with event dispatcher

        Example:
            def register_events(self, manager: PluginManager) -> None:
                # Register for tray menu event
                manager.events.subscribe(
                    Event.TRAY_READY,
                    self._handle_tray_menu
                )

            def _handle_tray_menu(self, ctx: EventContext) -> None:
                action = ctx.menu.addAction("My Action")
                action.triggered.connect(self.my_handler)
        """
        pass

    # State Awareness (Direct Callbacks)

    def on_active(self) -> None:
        """Called when system becomes active (user present)."""
        pass

    def on_inactive(self) -> None:
        """Called when system becomes inactive (idle/screen off)."""
        pass

    # Optional UI Extensions

    def get_popup_widget(self) -> Optional['QWidget']:
        """
        Return a Qt widget to display in the tray popup.

        DEPRECATED: Use register_events() with POPUP_READY event instead.
        Maintained for backward compatibility.

        Returns:
            QWidget or None if no UI component
        """
        return None

    # Web Extensions (for web plugin and extenders)

    def get_web_routes(self) -> list[tuple[str, Any]]:
        """
        Return Flask route definitions for web interface.

        Only used by plugins that extend the web plugin.

        Returns:
            List of (route_path, view_function) tuples
        """
        return []

    def get_web_content(self) -> Dict[str, Any]:
        """
        Return web UI content for injection into main interface.

        Only used by plugins that extend the web plugin.

        Returns:
            Dict with 'slots', 'javascript', and optional 'new_tab'
        """
        return {
            'slots': {},
            'javascript': '',
        }

    # Plugin Manager Access

    def set_plugin_manager(self, manager: 'PluginManager') -> None:
        """
        Receive plugin manager reference.

        Allows plugins to:
        - Access event dispatcher
        - Discover other plugins
        - Query system state

        Args:
            manager: PluginManager instance
        """
        pass

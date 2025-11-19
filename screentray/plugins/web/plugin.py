"""
Web Dashboard Plugin with event-driven UI integration.
"""
import threading
import webbrowser
import os
from typing import Any, Optional
from PyQt5.QtWidgets import QAction, QPushButton
from ..base import PluginBase
from ..manager import PluginManager
from ...events import Event, TrayReadyContext, PopupReadyContext
from . import PLUGIN_INFO


PORT_FILE = os.path.expanduser("~/.local/share/screentray_web_port")

class WebPlugin(PluginBase):
    """
    Web dashboard plugin using event system for UI integration.

    Registers handlers for tray menu and popup events to add
    UI elements without coupling core components to this plugin.
    """

    def __init__(self) -> None:
        self.server_thread: Optional[threading.Thread] = None
        self.server_port: Optional[int] = None
        self.plugin_manager: Optional[PluginManager] = None
        self.flask_app: Optional[Any] = None
        self.tray_action: Optional[QAction] = None
        self.popup_button: Optional[QPushButton] = None

    def get_info(self) -> dict[str, Any]:
        """Return plugin metadata."""
        return PLUGIN_INFO

    def set_plugin_manager(self, manager: PluginManager) -> None:
        """Receive plugin manager reference."""
        self.plugin_manager = manager

    def register_events(self, manager: PluginManager) -> None:
        """
        Register event handlers for UI integration.

        Subscribes to:
        - TRAY_MENU_READY: Add "Open Web Dashboard" menu item
        - POPUP_READY: Add "Open Web Dashboard" button
        """
        manager.events.subscribe(Event.TRAY_READY, self._on_tray_menu_ready)
        manager.events.subscribe(Event.POPUP_READY, self._on_popup_ready)

    def install(self) -> None:
        """No installation needed."""
        pass

    def uninstall(self) -> None:
        """No cleanup needed."""
        pass

    def start(self) -> None:
        """No-op - server starts in tray process."""
        pass

    def stop(self) -> None:
        """Stop Flask server (daemon thread stops with main process)."""
        pass

    def _run_server(self) -> None:
        """Run Flask server (executed in thread)."""
        if self.flask_app and self.server_port:
            self.flask_app.run(
                host="127.0.0.1",
                port=self.server_port,
                debug=False,
                use_reloader=False
            )

    def _on_tray_menu_ready(self, ctx: TrayReadyContext) -> None:
        """Create menu items, check server async."""
        menu = ctx.menu

        # Create disabled menu item immediately
        first_action = menu.actions()[0] if menu.actions() else None
        self.tray_action = QAction("Open Web Dashboard", menu)
        self.tray_action.triggered.connect(self._open_dashboard)
        self.tray_action.setEnabled(False)
        self.tray_action.setToolTip("Starting...")

        if first_action:
            menu.insertAction(first_action, self.tray_action)
            menu.insertSeparator(menu.actions()[1])
        else:
            menu.addAction(self.tray_action) # pyright: ignore[reportUnknownMemberType]
            menu.addSeparator()

        # Start server in background
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(0, self._start_server_async)

    def _on_popup_ready(self, ctx: PopupReadyContext) -> None:
        """
        Handle POPUP_READY event.

        Adds "Open Web Dashboard" button at the bottom of popup.
        Initially hidden until server starts.
        """
        layout = ctx.layout

        self.popup_button = QPushButton("Open Web Dashboard")
        self.popup_button.clicked.connect(self._open_dashboard)
        self.popup_button.setVisible(False)
        layout.addWidget(self.popup_button)

        # Update state if server already running
        self._update_ui_state()

    def _update_ui_state(self) -> None:
        """Update UI elements based on server state."""
        if not self.server_port:
            return

        url = self.get_url()
        tooltip = f"Open {url}"

        if self.tray_action:
            self.tray_action.setEnabled(True)
            self.tray_action.setToolTip(tooltip)

        if self.popup_button:
            self.popup_button.setVisible(True)
            self.popup_button.setToolTip(tooltip)

    def _open_dashboard(self) -> None:
        """Open web dashboard in default browser."""
        if self.server_port:
            webbrowser.open(self.get_url())

    def get_url(self) -> str:
        """Return the web dashboard URL."""
        return f"http://127.0.0.1:{self.server_port or 5050}"

    def get_port(self) -> Optional[int]:
        """Return the server port if running."""
        return self.server_port

    def _start_server_async(self) -> None:
        """Start server and update menu state."""
        if self.server_port:
            return  # Already started

        from .server import create_app, find_free_port

        try:
            plugins_with_web: list[PluginBase] = []
            if self.plugin_manager:
                for plugin in self.plugin_manager.get_all_plugins():
                    if plugin is self:
                        continue
                    if hasattr(plugin, 'get_web_routes') or hasattr(plugin, 'get_web_content'):
                        plugins_with_web.append(plugin)

            self.flask_app = create_app(plugins_with_web)
            self.server_port = find_free_port()

            threading.Thread(target=self._run_server, daemon=True).start()

            # Update menu
            if self.tray_action:
                self.tray_action.setEnabled(True)
                self.tray_action.setToolTip(f"http://127.0.0.1:{self.server_port}")

            print(f"Web dashboard at http://127.0.0.1:{self.server_port}")
        except Exception as e:
            print(f"Web server failed: {e}")
            if self.tray_action:
                self.tray_action.setToolTip("Failed to start")

        self._update_ui_state()

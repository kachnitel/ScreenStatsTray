"""
Web Dashboard Plugin - provides web interface for ScreenTracker.
"""
import threading
from typing import Any, Optional
from ..base import PluginBase
from ..manager import PluginManager
from . import PLUGIN_INFO


class WebPlugin(PluginBase):
    """Web dashboard plugin with extension support for other plugins."""

    def __init__(self) -> None:
        self.server_thread: Optional[threading.Thread] = None
        self.server_port: Optional[int] = None
        self.plugin_manager: Optional[PluginManager] = None
        self.flask_app: Optional[Any] = None

    def get_info(self) -> dict[str, Any]:
        """Return plugin metadata."""
        return PLUGIN_INFO

    def set_plugin_manager(self, manager: PluginManager) -> None:
        """Receive plugin manager reference for discovering other plugins."""
        self.plugin_manager = manager

    def install(self) -> None:
        """No installation needed - no database tables."""
        pass

    def uninstall(self) -> None:
        """No cleanup needed."""
        pass

    def start(self) -> None:
        """Start Flask server in background thread."""
        from .server import create_app, find_free_port

        # Discover plugins that provide web content
        plugins_with_web: list[PluginBase] = []
        if self.plugin_manager:
            for plugin in self.plugin_manager.get_all_plugins():
                # Skip self
                if plugin is self:
                    continue
                # Check if plugin has web content
                if hasattr(plugin, 'get_web_routes') or hasattr(plugin, 'get_web_content'):
                    plugins_with_web.append(plugin)

        self.flask_app = create_app(plugins_with_web)
        self.server_port = find_free_port()

        # Start server in daemon thread
        self.server_thread = threading.Thread(
            target=self._run_server,
            daemon=True
        )
        self.server_thread.start()

        print(f"Web dashboard started at http://127.0.0.1:{self.server_port}")

    def stop(self) -> None:
        """Stop Flask server."""
        # Flask in daemon thread will stop when main process exits
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

    def get_url(self) -> str:
        """Return the web dashboard URL."""
        return f"http://127.0.0.1:{self.server_port or 5050}"

    def get_port(self) -> Optional[int]:
        """Return the server port if running."""
        return self.server_port

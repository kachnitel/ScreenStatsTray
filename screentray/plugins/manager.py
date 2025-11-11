"""
screentray/plugins/manager.py

Plugin discovery and lifecycle management.
"""
import os
import importlib
from typing import Optional
from .base import PluginBase


class PluginManager:
    """
    Discovers and manages plugins in the screentray/plugins directory.

    Usage:
        manager = PluginManager()
        manager.discover_plugins()
        manager.install_all()
        manager.start_all()
    """

    def __init__(self) -> None:
        self.plugins: dict[str, PluginBase] = {}
        self._active_state: str = "inactive"

    def discover_plugins(self) -> None:
        """
        Scan plugins/ directory and load all valid plugins.

        A valid plugin is a directory containing:
        - __init__.py with PLUGIN_INFO dict
        - plugin.py with a class implementing PluginBase
        """
        plugins_dir = os.path.dirname(__file__)

        for item in os.listdir(plugins_dir):
            item_path = os.path.join(plugins_dir, item)

            # Skip non-directories and special files
            if not os.path.isdir(item_path) or item.startswith('_'):
                continue

            try:
                # Import the plugin module
                module = importlib.import_module(f"screentray.plugins.{item}")

                # Check for required PLUGIN_INFO
                if not hasattr(module, 'PLUGIN_INFO'):
                    print(f"Warning: Plugin '{item}' missing PLUGIN_INFO, skipping")
                    continue

                # Load plugin class from plugin.py
                plugin_module = importlib.import_module(f"screentray.plugins.{item}.plugin")

                # Find class that inherits from PluginBase
                plugin_class = None
                for attr_name in dir(plugin_module):
                    attr = getattr(plugin_module, attr_name)
                    if (isinstance(attr, type) and
                        issubclass(attr, PluginBase) and
                        attr is not PluginBase):
                        plugin_class = attr
                        break

                if plugin_class is None:
                    print(f"Warning: Plugin '{item}' has no PluginBase class, skipping")
                    continue

                # Instantiate plugin
                plugin_instance = plugin_class()
                info = plugin_instance.get_info()
                plugin_name = info['name']

                self.plugins[plugin_name] = plugin_instance
                print(f"Discovered plugin: {plugin_name} v{info['version']}")

            except Exception as e:
                print(f"Error loading plugin '{item}': {e}")

    def install_plugin(self, name: str) -> None:
        """Install a specific plugin (create DB tables, etc)."""
        if name not in self.plugins:
            raise ValueError(f"Plugin '{name}' not found")

        plugin = self.plugins[name]
        info = plugin.get_info()

        if info.get('requires_install'):
            print(f"Installing plugin: {name}")
            plugin.install()

    def install_all(self) -> None:
        """Install all discovered plugins that require installation."""
        for name, plugin in self.plugins.items():
            info = plugin.get_info()
            if info.get('requires_install'):
                try:
                    self.install_plugin(name)
                except Exception as e:
                    print(f"Failed to install plugin '{name}': {e}")

    def start_all(self) -> None:
        """Start all plugins (begin tracking/operation)."""
        for name, plugin in self.plugins.items():
            try:
                print(f"Starting plugin: {name}")
                plugin.start()
            except Exception as e:
                print(f"Failed to start plugin '{name}': {e}")

    def stop_all(self) -> None:
        """Stop all plugins (cleanup resources)."""
        for name, plugin in self.plugins.items():
            try:
                print(f"Stopping plugin: {name}")
                plugin.stop()
            except Exception as e:
                print(f"Failed to stop plugin '{name}': {e}")

    def uninstall_plugin(self, name: str) -> None:
        """Uninstall a specific plugin (remove DB tables, etc)."""
        if name not in self.plugins:
            raise ValueError(f"Plugin '{name}' not found")

        plugin = self.plugins[name]
        print(f"Uninstalling plugin: {name}")
        plugin.uninstall()

    # State propagation to plugins

    def notify_active(self) -> None:
        """Notify all plugins that system became active."""
        self._active_state = "active"
        for plugin in self.plugins.values():
            try:
                plugin.on_active()
            except Exception as e:
                print(f"Plugin error on_active: {e}")

    def notify_inactive(self) -> None:
        """Notify all plugins that system became inactive."""
        self._active_state = "inactive"
        for plugin in self.plugins.values():
            try:
                plugin.on_inactive()
            except Exception as e:
                print(f"Plugin error on_inactive: {e}")

    def is_active(self) -> bool:
        """Check current activity state."""
        return self._active_state == "active"

    def get_plugin(self, name: str) -> Optional[PluginBase]:
        """Get a specific plugin by name."""
        return self.plugins.get(name)

    def get_all_plugins(self) -> list[PluginBase]:
        """Get all loaded plugins."""
        return list(self.plugins.values())

    def set_plugin_manager_for_all(self) -> None:
        """Pass plugin manager reference to plugins that need it."""
        for plugin in self.plugins.values():
            if hasattr(plugin, 'set_plugin_manager'):
                plugin.set_plugin_manager(self)  # type: ignore

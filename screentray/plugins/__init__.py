"""
Plugin system for ScreenTray with event-driven architecture.
"""
from .base import PluginBase
from .manager import PluginManager
from .events import PluginEvent, EventContext, EventDispatcher

__all__ = ['PluginBase', 'PluginManager', 'PluginEvent', 'EventContext', 'EventDispatcher']
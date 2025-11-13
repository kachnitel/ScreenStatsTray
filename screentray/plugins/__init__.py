"""
Plugin system for ScreenTray with event-driven architecture.
"""
from .base import PluginBase
from .manager import PluginManager
from ..events import Event, EventContext, EventBus

__all__ = ['PluginBase', 'PluginManager', 'Event', 'EventContext', 'EventBus']
"""
Plugin system for ScreenTray with event-driven architecture.
"""
from .base import PluginBase
from .manager import PluginManager
from ..events import Event, EventContext, EventBus, TrayReadyContext, PopupReadyContext

__all__ = ["PluginBase", "PluginManager", "Event", "EventContext", "TrayReadyContext", "PopupReadyContext", "EventBus"]

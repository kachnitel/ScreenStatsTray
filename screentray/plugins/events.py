"""
Plugin event system for UI and lifecycle hooks.

Provides a clean API for plugins to extend core functionality without
coupling core components to specific plugin implementations.
"""
from typing import Any, Callable, Dict, List, Optional
from enum import Enum


class PluginEvent(Enum):
    """Events that plugins can subscribe to."""

    # UI Events
    TRAY_MENU_READY = "tray_menu_ready"
    POPUP_READY = "popup_ready"

    # Lifecycle Events
    APP_READY = "app_ready"
    APP_SHUTDOWN = "app_shutdown"


class EventContext:
    """Context passed to event handlers with relevant objects."""

    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self) -> str:
        attrs = ', '.join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"EventContext({attrs})"


EventHandler = Callable[[EventContext], None]


class EventDispatcher:
    """
    Central event dispatcher for plugin system.

    Plugins register handlers for specific events. Core components
    emit events at key lifecycle points. This decouples core from
    plugin implementations.

    Example:
        # Plugin registers handler
        dispatcher.register(PluginEvent.TRAY_MENU_READY, my_handler)

        # Core emits event
        dispatcher.emit(PluginEvent.TRAY_MENU_READY,
                       EventContext(menu=menu, tray=self))
    """

    def __init__(self) -> None:
        self._handlers: Dict[PluginEvent, List[EventHandler]] = {}

    def register(self, event: PluginEvent, handler: EventHandler) -> None:
        """
        Register a handler for an event.

        Args:
            event: The event to listen for
            handler: Callback function(context: EventContext) -> None
        """
        if event not in self._handlers:
            self._handlers[event] = []
        self._handlers[event].append(handler)

    def emit(self, event: PluginEvent, context: EventContext) -> None:
        """
        Emit an event to all registered handlers.

        Args:
            event: The event being emitted
            context: Context object with event-specific data
        """
        handlers = self._handlers.get(event, [])
        for handler in handlers:
            try:
                handler(context)
            except Exception as e:
                print(f"Error in event handler for {event.value}: {e}")

    def unregister(self, event: PluginEvent, handler: EventHandler) -> None:
        """
        Unregister a specific handler.

        Args:
            event: The event to stop listening to
            handler: The handler to remove
        """
        if event in self._handlers:
            try:
                self._handlers[event].remove(handler)
            except ValueError:
                pass

    def clear(self, event: Optional[PluginEvent] = None) -> None:
        """
        Clear handlers for an event, or all events if none specified.

        Args:
            event: Optional specific event to clear
        """
        if event:
            self._handlers.pop(event, None)
        else:
            self._handlers.clear()

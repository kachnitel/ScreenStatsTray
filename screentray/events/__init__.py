"""Global event system for ScreenTray."""
from enum import Enum
from typing import Callable, Any, Dict, List

class Event(Enum):
    """Application-wide events."""
    ACTIVITY_CHANGED = "activity_changed"
    SESSION_ALERT = "session_alert"
    TRACKER_READY = "tracker_ready"
    TRAY_READY = "tray_ready"
    POPUP_READY = "popup_ready"

# class Event(Enum):
#     """Events that plugins can subscribe to."""

#     # UI Events
#     TRAY_MENU_READY = "tray_menu_ready"
#     POPUP_READY = "popup_ready"

#     # Lifecycle Events
#     APP_READY = "app_ready"
#     APP_SHUTDOWN = "app_shutdown"


class EventContext:
    """Context passed to event handlers with relevant objects."""

    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self) -> str:
        attrs = ', '.join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"EventContext({attrs})"

class EventBus:
    """Central event dispatcher."""

    def __init__(self) -> None:
        self._handlers: Dict[Event, List[Callable[[EventContext], None]]] = {}

    def subscribe(self, event: Event, handler: Callable[[Any], None]) -> None:
        """Subscribe to an event."""
        if event not in self._handlers:
            self._handlers[event] = []
        self._handlers[event].append(handler)

    def emit(self, event: Event, data: Any = None) -> None:
        """Emit an event to all subscribers."""
        for handler in self._handlers.get(event, []):
            try:
                handler(data)
            except Exception as e:
                print(f"Event handler error ({event.value}): {e}")

# Global instance
event_bus = EventBus()

"""Global event system for ScreenTray."""
from enum import Enum
from typing import Callable, Any, Dict, List, TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QMenu, QVBoxLayout
    from ..tray.tray import TrayApp
    from ..tray.popup import StatsPopup

class Event(Enum):
    """Application-wide events."""
    ACTIVITY_CHANGED = "activity_changed"
    SESSION_ALERT = "session_alert"
    TRACKER_READY = "tracker_ready"
    TRAY_READY = "tray_ready"
    POPUP_READY = "popup_ready"


class EventContext:
    """Base context for event handlers."""
    pass


class TrayReadyContext(EventContext):
    """Context passed to TRAY_READY event handlers."""
    def __init__(self, menu: 'QMenu', tray: 'TrayApp', position: str = 'top') -> None:
        self.menu = menu
        self.tray = tray
        self.position = position


class PopupReadyContext(EventContext):
    """Context passed to POPUP_READY event handlers."""
    def __init__(self, popup: 'StatsPopup', layout: 'QVBoxLayout') -> None:
        self.popup = popup
        self.layout = layout


ContextT = TypeVar('ContextT', bound=EventContext)


class EventBus:
    """Central event dispatcher."""

    def __init__(self) -> None:
        # Store handlers with Any type to allow different context subtypes
        self._handlers: Dict[Event, List[Callable[[Any], None]]] = {}

    def subscribe(self, event: Event, handler: Callable[[ContextT], None]) -> None:
        """Subscribe to an event with a typed handler."""
        if event not in self._handlers:
            self._handlers[event] = []
        self._handlers[event].append(handler)  # type: ignore[arg-type]

    def emit(self, event: Event, context: EventContext) -> None:
        """Emit an event to all subscribers."""
        for handler in self._handlers.get(event, []):
            try:
                handler(context)
            except Exception as e:
                print(f"Event handler error ({event.value}): {e}")


# Global instance
event_bus = EventBus()

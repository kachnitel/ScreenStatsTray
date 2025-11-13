"""Desktop notification service."""
from typing import List, Tuple, Callable, Optional, Dict

class NotificationService:
    """Handles desktop notifications with action support."""

    def __init__(self) -> None:
        self._dbus_handler: Optional[Callable[[int, str], None]] = None

    def notify(self, title: str, message: str, icon: str = "dialog-information",
               actions: Optional[List[Tuple[str, Callable[[], None]]]] = None,
               timeout: int = 0) -> bool:
        """
        Send desktop notification.

        Args:
            title: Notification title
            message: Notification message
            icon: Icon name (theme icon)
            actions: List of (label, callback) tuples
            timeout: Timeout in ms (0 = no timeout)

        Returns:
            True if DBus notification succeeded, False otherwise
        """
        try:
            import dbus  # type: ignore[import-untyped]
            import dbus.mainloop.glib  # type: ignore[import-untyped]

            dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)  # type: ignore[reportUnknownMemberType]
            bus: dbus.SessionBus = dbus.SessionBus()  # type: ignore[reportUnknownMemberType]
            obj = bus.get_object("org.freedesktop.Notifications",  # type: ignore[reportUnknownMemberType]
                               "/org/freedesktop/Notifications")
            interface = dbus.Interface(obj, "org.freedesktop.Notifications")  # type: ignore[reportUnknownMemberType]

            action_list: List[str] = []
            action_callbacks: Dict[str, Callable[[], None]] = {}

            if actions:
                for label, callback in actions:
                    key = label.lower().replace(" ", "_")
                    action_list += [key, label]
                    action_callbacks[key] = callback

            def on_action_invoked(nid: int, action_key: str) -> None:
                if action_key in action_callbacks:
                    action_callbacks[action_key]()

            bus.add_signal_receiver(on_action_invoked, signal_name="ActionInvoked",  # type: ignore[reportUnknownMemberType]
                                  dbus_interface="org.freedesktop.Notifications")
            self._dbus_handler = on_action_invoked

            interface.Notify("ScreenTracker", 0, icon, title, message,  # type: ignore[reportUnknownMemberType]
                           action_list, {}, timeout)
            return True
        except Exception as e:
            print(f"DBus notification failed: {e}")
            return False

    def notify_session_alert(self, minutes: int, on_snooze: Callable[[], None],
                           on_suspend: Optional[Callable[[], None]] = None,
                           on_screen_off: Optional[Callable[[], None]] = None,
                           on_lock: Optional[Callable[[], None]] = None,
                           snooze_minutes: int = 10) -> bool:
        """Send session alert notification with action buttons."""
        title = "ScreenTracker Alert"
        message = f"Session exceeded {minutes} minutes! Take a break."

        actions: List[Tuple[str, Callable[[], None]]] = [
            (f"Snooze {snooze_minutes}m", on_snooze)
        ]

        if on_suspend:
            actions.append(("Suspend", on_suspend))
        if on_screen_off:
            actions.append(("Screen Off", on_screen_off))
        if on_lock:
            actions.append(("Lock Screen", on_lock))

        return self.notify(title, message, "chronometer-pause-symbolic", actions)

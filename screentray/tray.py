from typing import Optional, List, Tuple, Callable, Dict
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QTimer, QDate
from .popup import StatsPopup
from .session import current_session_seconds
from .db import query_totals
import subprocess
from . import config

ICON_NORMAL: str = "preferences-desktop"
ICON_ALERT: str = "chronometer-pause-symbolic" #"dialog-warning"

class TrayApp:
    def __init__(self) -> None:
        self.tray: QSystemTrayIcon = QSystemTrayIcon(QIcon.fromTheme(ICON_NORMAL))
        self.tray.setToolTip("ScreenTracker")
        self.tray.show()

        # Keep popup reference
        self.popup: Optional[StatsPopup] = None
        self.notified_threshold: bool = False

        self.tray.activated.connect(self.on_tray_activated)

        # Context menu
        menu: QMenu = QMenu()
        exit_action: QAction = menu.addAction("Exit") # type: ignore[reportUnknownMemberType, reportAssignmentType]
        exit_action.triggered.connect(self.exit)
        self.tray.setContextMenu(menu)

        # Timer to refresh tooltip and icon
        self.timer: QTimer = QTimer()
        self.timer.timeout.connect(self.update_tooltip)
        self.timer.start(10_000)  # every 10 seconds

        # Initial tooltip
        self.update_tooltip()

    def on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.Trigger: # type: ignore[reportUnknownMemberType, reportAttributeAccessIssue]
            if self.popup is None:
                self.popup = StatsPopup()

            if self.popup.isVisible():
                self.popup.hide()
            else:
                self.popup.show()
                self.popup.raise_()
                self.popup.activateWindow()


    def update_tooltip(self) -> None:
        today: str = QDate.currentDate().toString("yyyy-MM-dd")
        totals = query_totals(today)
        active_sec: float = totals.get("active", 0)
        inactive_sec: float = totals.get("inactive", 0)
        session_sec: float = current_session_seconds()

        # Tooltip text
        h_s, rem = divmod(int(session_sec), 3600)
        m_s, s_s = divmod(rem, 60)
        h_a, m_a, s_a = int(active_sec // 3600), int((active_sec % 3600) // 60), int(active_sec % 60)
        h_i, m_i, s_i = int(inactive_sec // 3600), int((inactive_sec % 3600) // 60), int(inactive_sec % 60)

        tooltip: str = (
            f"Active: {h_a:02d}:{m_a:02d}:{s_a:02d}  "
            f"Inactive: {h_i:02d}:{m_i:02d}:{s_i:02d}\n"
            f"Current session: {h_s:02d}:{m_s:02d}:{s_s:02d}"
        )
        self.tray.setToolTip(tooltip)

        # Change icon if session exceeds threshold
        if session_sec / 60 >= config.ALERT_SESSION_MINUTES:
            self.tray.setIcon(QIcon.fromTheme(ICON_ALERT))
            if not self.notified_threshold:
                self.notify_threshold()
                self.notified_threshold = True
        else:
            self.tray.setIcon(QIcon.fromTheme(ICON_NORMAL))
            self.notified_threshold = False

    def notify_threshold(self) -> None:
        """Show KDE Plasma native notification (non-blocking)."""
        title: str = "ScreenTracker Alert"
        message: str = f"Session exceeded {config.ALERT_SESSION_MINUTES} minutes!"
        actions: List[Tuple[str, Callable[[], None]]] = []

        if config.NOTIFY_BUTTONS.get("suspend", False):
            actions.append(("Suspend", self.system_suspend))
        if config.NOTIFY_BUTTONS.get("screen_off", False):
            actions.append(("Screen Off", self.screen_off))
        if config.NOTIFY_BUTTONS.get("lock_screen", False):
            actions.append(("Lock Screen", self.lock_screen))

        if not self._notify_plasma(title, message, ICON_ALERT, actions):
            # Fallback to Qt tray balloon
            self.tray.showMessage(title, message, QIcon.fromTheme(ICON_ALERT))

        if len(actions) == 1:
            _label, _action = actions[0]

    def _notify_plasma(self, title: str, message: str, icon: str, actions: Optional[List[Tuple[str, Callable[[], None]]]] = None) -> bool:
        """Send KDE Plasma native notification over DBus with optional working actions (sticky)."""
        try:
            import dbus  # type: ignore[import-untyped]
            import dbus.mainloop.glib  # type: ignore[import-untyped]
            from gi.repository import GLib  # type: ignore[import-untyped]

            dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)  # type: ignore[reportUnknownMemberType]
            bus: dbus.SessionBus = dbus.SessionBus()
            obj: dbus.proxies.ProxyObject = bus.get_object("org.freedesktop.Notifications", "/org/freedesktop/Notifications")  # type: ignore[reportUnknownMemberType]
            interface: dbus.Interface = dbus.Interface(obj, "org.freedesktop.Notifications")  # type: ignore[reportUnknownMemberType]

            action_list: List[str] = []
            action_callbacks: Dict[str, Callable[[], None]] = {}

            if actions:
                for label, callback in actions:
                    key = label.lower().replace(" ", "_")
                    action_list += [key, label]
                    action_callbacks[key] = callback

            # Define signal handler as persistent attribute to keep it alive
            def on_action_invoked(nid: int, action_key: str) -> None:
                if action_key in action_callbacks:
                    action_callbacks[action_key]()

            bus.add_signal_receiver(  # type: ignore[reportUnknownMemberType]
                on_action_invoked,
                signal_name="ActionInvoked",
                dbus_interface="org.freedesktop.Notifications",
            )
            self._dbus_signal_handler = on_action_invoked  # keep alive

            interface.Notify(  # type: ignore[reportUnknownMemberType]
                "ScreenTracker",
                0,
                icon,
                title,
                message,
                action_list,
                {},
                0,  # sticky
            )

            return True

        except Exception as e:
            if self.tray:
                self.tray.showMessage(title, message, QIcon.fromTheme(icon))
            else:
                print(f"Notification failed: {e}")
            return False

    def system_suspend(self) -> None:
        subprocess.run(["systemctl", "suspend"], check=False)

    def screen_off(self) -> None:
        subprocess.run(["xset", "dpms", "force", "off"], check=False)

    def lock_screen(self) -> None:
        subprocess.run(["loginctl", "lock-session"], check=False)

    def exit(self) -> None:
        self.tray.hide()
        QApplication.quit()

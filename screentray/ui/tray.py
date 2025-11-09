"""Main system tray application."""
import subprocess
import datetime
import socket
import webbrowser
import os
from typing import Optional, List, Tuple, Callable, Dict
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction, QApplication
from PyQt5.QtGui import QIcon, QPainter, QColor, QPixmap, QCursor
from PyQt5.QtCore import QTimer, Qt
from .popup import StatsPopup
from ..config import settings, NOTIFY_BUTTONS
from ..services.session_service import SessionService
from . import config_dialog

ICON_NORMAL = "preferences-desktop"
ICON_ALERT = "chronometer-pause-symbolic"
TEST_NOTIFICATION_TRIGGER = os.path.expanduser("~/.local/share/screentracker_test_notify")


class TrayApp:
    """Main application class for the system tray icon."""

    def __init__(self) -> None:
        self.session_service = SessionService()
        self.popup: StatsPopup = StatsPopup()
        self.notified_threshold = False
        self.snooze_until: Optional[datetime.datetime] = None
        self.web_port: Optional[int] = None
        self._dbus_signal_handler: Optional[Callable[[int, str], None]] = None

        # Create tray icon
        self.tray_icon = QSystemTrayIcon(QIcon.fromTheme(ICON_NORMAL))
        self.tray_icon.setToolTip("ScreenTray")

        # Context menu
        self.create_context_menu()

        # Connect notification message clicked signal (fallback)
        self.tray_icon.messageClicked.connect(self.on_notification_clicked)  # pyright: ignore[reportGeneralTypeIssues]

        # Connect tray activation
        self.tray_icon.activated.connect(self.on_tray_activated)  # pyright: ignore[reportGeneralTypeIssues]

        # Timer for updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status)  # pyright: ignore[reportGeneralTypeIssues]
        self.timer.start(2000)

        # Check web service status
        self.check_web_service()

        # Initial update and check
        self.update_status()
        self.tray_icon.show()

    def create_context_menu(self) -> None:
        """Create the context menu with all actions."""
        self.menu = QMenu()

        # Web Dashboard action (will be enabled/disabled based on service status)
        self.web_action: Optional[QAction] = self.menu.addAction("Open Web Dashboard")  # pyright: ignore[reportUnknownMemberType]
        if self.web_action:
            self.web_action.triggered.connect(self.open_web_dashboard)
            self.web_action.setEnabled(False)  # Disabled until we confirm service is running
        self.menu.addSeparator()

        # Settings action
        settings_action: QAction = self.menu.addAction("Settings...")  # pyright: ignore[reportUnknownMemberType, reportAssignmentType]
        settings_action.triggered.connect(self.open_settings)
        self.menu.addSeparator()

        # Quick Actions submenu
        actions_menu = QMenu("Quick Actions", self.menu)
        actions_added = False

        if NOTIFY_BUTTONS.get("suspend", False):
            suspend_action: QAction = actions_menu.addAction("Suspend")  # pyright: ignore[reportUnknownMemberType, reportAssignmentType]
            suspend_action.triggered.connect(self.system_suspend)
            actions_added = True

        if NOTIFY_BUTTONS.get("screen_off", False):
            screen_off_action: QAction = actions_menu.addAction("Screen Off")  # pyright: ignore[reportUnknownMemberType, reportAssignmentType]
            screen_off_action.triggered.connect(self.screen_off)
            actions_added = True

        if NOTIFY_BUTTONS.get("lock_screen", False):
            lock_action: QAction = actions_menu.addAction("Lock Screen")  # pyright: ignore[reportUnknownMemberType, reportAssignmentType]
            lock_action.triggered.connect(self.lock_screen)
            actions_added = True

        # Only add submenu if it has actions
        if actions_added:
            self.menu.addMenu(actions_menu)
            self.menu.addSeparator()

        # Exit action
        exit_action: QAction = self.menu.addAction("Exit")  # type: ignore[reportUnknownMemberType, reportAssignmentType]
        exit_action.triggered.connect(self.quit_app)

        # Set context menu
        self.tray_icon.setContextMenu(self.menu)

    def show_popup(self) -> None:
        """Show the statistics popup window."""
        self.popup.show()
        self.popup.activateWindow()

    def hide_popup(self) -> None:
        """Hide the statistics popup window."""
        self.popup.hide()

    def on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon click: toggle on left-click, show menu on right-click."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.popup.isVisible():
                self.hide_popup()
            else:
                self.show_popup()
        elif reason == QSystemTrayIcon.ActivationReason.Context:
            # Explicitly show menu at cursor position
            self.menu.popup(QCursor.pos())

    def on_notification_clicked(self) -> None:
        """Handle notification click - show actions menu (fallback if DBus actions don't work)."""
        self.menu.popup(QCursor.pos())

    def update_status(self) -> None:
        """Update tray icon and tooltip based on activity."""
        # Check for test notification trigger
        if os.path.exists(TEST_NOTIFICATION_TRIGGER):
            os.remove(TEST_NOTIFICATION_TRIGGER)
            self.send_test_notification()
            return

        is_active = self.session_service.is_currently_active()

        if is_active:
            # Currently active - show session time
            _, session_s = self.session_service.get_current_session()
            _, break_end, break_s = self.session_service.get_last_break()

            session_m = session_s / 60.0
            tooltip = f"Active: {int(session_m)}m"

            if break_end:
                # Last break ended
                tooltip += f"\nLast Break: {int(break_s / 60)}m"

            # Check if we should notify
            if session_m >= settings.alert_session_minutes:
                self.tray_icon.setIcon(QIcon.fromTheme(ICON_ALERT))

                # Check if we should send notification
                should_notify = not self.notified_threshold

                # Check snooze
                if self.snooze_until:
                    if datetime.datetime.now() < self.snooze_until:
                        should_notify = False
                    else:
                        # Snooze expired
                        self.snooze_until = None
                        should_notify = True

                if should_notify:
                    self.notify_threshold()
                    self.notified_threshold = True
            else:
                self.tray_icon.setIcon(self._create_icon("green"))
                self.notified_threshold = False
                self.snooze_until = None
        else:
            # Currently inactive - show break time
            _, break_end, break_s = self.session_service.get_last_break()

            if break_end is None:
                # Still in break
                tooltip = f"Idle: {int(break_s / 60)}m"
            else:
                # Break ended, but not active yet
                tooltip = "Idle"

            self.tray_icon.setIcon(self._create_icon("gray"))
            # Reset notification flag when inactive
            self.notified_threshold = False
            self.snooze_until = None

        self.tray_icon.setToolTip(tooltip)

    def _create_icon(self, color_name: str) -> QIcon:
        """Create a 16x16 colored circular icon."""
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.transparent) # pyright: ignore[reportUnknownArgumentType, reportUnknownMemberType, reportAttributeAccessIssue]
        painter = QPainter(pixmap)
        painter.setBrush(QColor(color_name))
        painter.setPen(Qt.NoPen) # pyright: ignore[reportUnknownArgumentType, reportUnknownMemberType, reportAttributeAccessIssue]
        painter.setRenderHint(QPainter.Antialiasing) # pyright: ignore[reportUnknownArgumentType, reportUnknownMemberType]
        painter.drawEllipse(2, 2, 12, 12)
        painter.end()
        return QIcon(pixmap)

    def notify_threshold(self) -> None:
        """Show a desktop notification when threshold exceeded with action buttons."""
        title = "ScreenTracker Alert"
        message = f"Session exceeded {settings.alert_session_minutes} minutes! Take a break."

        # Build actions list - include snooze in notification
        actions: List[Tuple[str, Callable[[], None]]] = []

        if NOTIFY_BUTTONS.get("snooze", False):
            actions.append((f"Snooze {settings.snooze_minutes}m", self.snooze_notification))

        if NOTIFY_BUTTONS.get("suspend", False):
            actions.append(("Suspend", self.system_suspend))

        if NOTIFY_BUTTONS.get("screen_off", False):
            actions.append(("Screen Off", self.screen_off))

        if NOTIFY_BUTTONS.get("lock_screen", False):
            actions.append(("Lock Screen", self.lock_screen))

        # Try DBus notification first, fallback to Qt
        if not self._notify_plasma(title, message, ICON_ALERT, actions):
            # Fallback: Qt notification with click handler
            self.tray_icon.showMessage(
                title,
                message + "\n\nClick for actions.",
                QIcon.fromTheme(ICON_ALERT),
                0
            )

    def send_test_notification(self) -> None:
        """Send a test notification with all configured actions."""
        title = "ScreenTracker Test"
        message = "This is a test notification. Try the action buttons!"

        actions: List[Tuple[str, Callable[[], None]]] = []

        if NOTIFY_BUTTONS.get("snooze", False):
            actions.append((f"Test Snooze {settings.snooze_minutes}m", lambda: print("Test: Snooze clicked")))

        if NOTIFY_BUTTONS.get("suspend", False):
            actions.append(("Test Suspend", lambda: print("Test: Suspend clicked")))

        if NOTIFY_BUTTONS.get("screen_off", False):
            actions.append(("Test Screen Off", lambda: print("Test: Screen Off clicked")))

        if NOTIFY_BUTTONS.get("lock_screen", False):
            actions.append(("Test Lock", lambda: print("Test: Lock clicked")))

        if not self._notify_plasma(title, message, ICON_NORMAL, actions):
            self.tray_icon.showMessage(title, message, QIcon.fromTheme(ICON_NORMAL), 5000)

    def _notify_plasma(
        self,
        title: str,
        message: str,
        icon: str,
        actions: Optional[List[Tuple[str, Callable[[], None]]]] = None
    ) -> bool:
        """Send KDE Plasma native notification over DBus with action buttons."""
        try:
            import dbus  # type: ignore[import-untyped]
            import dbus.mainloop.glib  # type: ignore[import-untyped]
            from gi.repository import GLib  # type: ignore[import-untyped]

            dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)  # type: ignore[reportUnknownMemberType]
            bus: dbus.SessionBus = dbus.SessionBus()  # type: ignore[reportUnknownMemberType]
            obj = bus.get_object("org.freedesktop.Notifications", "/org/freedesktop/Notifications")  # type: ignore[reportUnknownMemberType]
            interface = dbus.Interface(obj, "org.freedesktop.Notifications")  # type: ignore[reportUnknownMemberType]

            action_list: List[str] = []
            action_callbacks: Dict[str, Callable[[], None]] = {}

            if actions:
                for label, callback in actions:
                    key = label.lower().replace(" ", "_")
                    action_list += [key, label]
                    action_callbacks[key] = callback

            # Define signal handler
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
                0,  # sticky (no timeout)
            )

            return True

        except Exception as e:
            print(f"DBus notification failed: {e}")
            return False

    def snooze_notification(self) -> None:
        """Snooze the notification for configured duration."""
        self.snooze_until = datetime.datetime.now() + datetime.timedelta(minutes=settings.snooze_minutes)
        print(f"Snoozed until {self.snooze_until.isoformat()}")
        # Send confirmation
        self.tray_icon.showMessage(
            "Snoozed",
            f"Alert snoozed for {settings.snooze_minutes} minutes",
            QIcon.fromTheme(ICON_NORMAL),
            3000
        )

    def system_suspend(self) -> None:
        """Suspend the system."""
        subprocess.run(["systemctl", "suspend", "--check-inhibitors=no"], check=False)

    def screen_off(self) -> None:
        """Turn off the screen."""
        subprocess.run(["xset", "dpms", "force", "off"], check=False)

    def lock_screen(self) -> None:
        """Lock the screen."""
        subprocess.run(["loginctl", "lock-session"], check=False)

    def quit_app(self) -> None:
        """Quit the application."""
        self.tray_icon.hide()
        app_instance = QApplication.instance()
        if app_instance:
            app_instance.quit()

    def check_web_service(self) -> None:
        """Check if web service is running and on which port."""
        try:
            # Check if service is active
            result = subprocess.run(
                ["systemctl", "--user", "is-active", "screenstats-web.service"],
                capture_output=True,
                text=True,
                timeout=1
            )

            if result.returncode != 0:
                self.web_port = None
                if self.web_action:
                    self.web_action.setEnabled(False)
                return

            # Get port from recent journal entries
            journal_result = subprocess.run(
                ["journalctl", "--user", "-u", "screenstats-web.service", "-n", "50", "--no-pager"],
                capture_output=True,
                text=True,
                timeout=2
            )

            # Look for "Starting server on http://127.0.0.1:XXXX" in output
            for line in journal_result.stdout.split('\n'):
                if "127.0.0.1:" in line and "Starting server" in line:
                    # Extract port number
                    parts = line.split("127.0.0.1:")
                    if len(parts) > 1:
                        port_str = parts[1].split()[0].rstrip('.,;')
                        try:
                            self.web_port = int(port_str)
                            if self.web_action:
                                self.web_action.setEnabled(True)
                            return
                        except ValueError:
                            pass

            # Fallback: try common ports
            for port in [5050, 8080, 5000]:
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(0.1)
                        if s.connect_ex(("127.0.0.1", port)) == 0:
                            self.web_port = port
                            if self.web_action:
                                self.web_action.setEnabled(True)
                            return
                except (socket.error, OSError):
                    continue

        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        self.web_port = None
        if self.web_action:
            self.web_action.setEnabled(False)

    def open_web_dashboard(self) -> None:
        """Open the web dashboard in default browser."""
        if self.web_port:
            url = f"http://127.0.0.1:{self.web_port}"
            webbrowser.open(url)

    def open_settings(self) -> None:
        """Open the settings dialog."""
        dialog = config_dialog.ConfigDialog()
        if dialog.exec_():  # Returns True if user clicked OK
            # Reload config to pick up new values
            settings.reload()
            # Reset notification state so new threshold takes effect
            self.notified_threshold = False
            self.snooze_until = None
            # Immediately update status to reflect new threshold
            self.update_status()

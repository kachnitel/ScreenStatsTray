"""Main system tray application."""
import subprocess
import datetime
from typing import Optional
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction, QApplication
from PyQt5.QtGui import QIcon, QPainter, QColor, QPixmap, QCursor
from PyQt5.QtCore import QTimer, Qt, QRect
from .popup import StatsPopup
from ..services.session_service import SessionService
from ..config import ALERT_SESSION_MINUTES, NOTIFY_BUTTONS, SNOOZE_MINUTES

ICON_NORMAL = "preferences-desktop"
ICON_ALERT = "chronometer-pause-symbolic"

class TrayApp:
    """Main application class for the system tray icon."""

    def __init__(self) -> None:
        self.session_service = SessionService()
        self.popup: StatsPopup = StatsPopup()
        self.notified_threshold = False
        self.snooze_until: Optional[datetime.datetime] = None

        # Create tray icon
        self.tray_icon = QSystemTrayIcon(QIcon.fromTheme(ICON_NORMAL))
        self.tray_icon.setToolTip("ScreenTray")

        # Context menu - always create it
        self.create_context_menu()

        # Connect notification message clicked signal
        self.tray_icon.messageClicked.connect(self.on_notification_clicked)  # pyright: ignore[reportGeneralTypeIssues]

        # Connect tray activation
        self.tray_icon.activated.connect(self.on_tray_activated)  # pyright: ignore[reportGeneralTypeIssues]

        # Timer for updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status)  # pyright: ignore[reportGeneralTypeIssues]
        self.timer.start(2000)

        # Initial update and check
        self.update_status()
        self.tray_icon.show()

    def create_context_menu(self) -> None:
        """Create the context menu with all actions."""
        self.menu = QMenu()

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

        if NOTIFY_BUTTONS.get("snooze", False):
            snooze_action: QAction = actions_menu.addAction(f"Snooze {SNOOZE_MINUTES}m")  # pyright: ignore[reportUnknownMemberType, reportAssignmentType]
            snooze_action.triggered.connect(self.snooze_notification)
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
        """Show popup near cursor as fallback for tray positioning."""
        # Try to get tray geometry
        tray_geometry: QRect = self.tray_icon.geometry()

        if tray_geometry.isValid() and not tray_geometry.isNull():
            # Position near tray icon
            self.popup.adjustSize()
            popup_size = self.popup.size()

            x = tray_geometry.center().x() - popup_size.width() // 2
            y = tray_geometry.top() - popup_size.height() - 5

            screen = QApplication.primaryScreen()
            if screen:
                screen_geometry = screen.availableGeometry()
                if y < screen_geometry.top():
                    y = tray_geometry.bottom() + 5
                if x < screen_geometry.left():
                    x = screen_geometry.left() + 5
                elif x + popup_size.width() > screen_geometry.right():
                    x = screen_geometry.right() - popup_size.width() - 5
        else:
            # Fallback: show near cursor (common for KDE)
            cursor_pos = QCursor.pos()
            self.popup.adjustSize()
            x = cursor_pos.x() - self.popup.width() // 2
            y = cursor_pos.y() - self.popup.height() - 10

        self.popup.move(x, y)
        self.popup.show()
        self.popup.activateWindow()
        self.popup.raise_()

    def hide_popup(self) -> None:
        """Hide the statistics popup window."""
        self.popup.hide()

    def on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """
        Handle tray icon interactions.

        Left-click: Toggle popup visibility
        Right-click: Show context menu
        """
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.popup.isVisible():
                self.hide_popup()
            else:
                self.show_popup()
        elif reason == QSystemTrayIcon.ActivationReason.Context:
            # Explicitly show menu at cursor position
            self.menu.popup(QCursor.pos())

    def on_notification_clicked(self) -> None:
        """Handle notification click - show actions menu."""
        # Show the quick actions menu when notification is clicked
        self.menu.popup(QCursor.pos())

    def update_status(self) -> None:
        """
        Update tray icon appearance and tooltip based on current activity state.

        Updates every 2 seconds via timer to reflect:
        - Active session duration
        - Idle/break duration
        - Alert state when session exceeds threshold
        """
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
            if session_m >= ALERT_SESSION_MINUTES:
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
        """
        Create a simple colored circular icon.

        Args:
            color_name: Qt color name (e.g., "green", "gray", "red")

        Returns:
            QIcon suitable for system tray display
        """
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
        """Show a desktop notification when session threshold is exceeded."""
        title = "ScreenTracker Alert"
        message = f"Session exceeded {ALERT_SESSION_MINUTES} minutes! Take a break.\n\nClick for actions."
        self.tray_icon.showMessage(title, message, QIcon.fromTheme(ICON_ALERT), 0)

    def snooze_notification(self) -> None:
        """Snooze the notification for configured duration."""
        self.snooze_until = datetime.datetime.now() + datetime.timedelta(minutes=SNOOZE_MINUTES)
        self.tray_icon.showMessage(
            "Snoozed",
            f"Alert snoozed for {SNOOZE_MINUTES} minutes",
            QIcon.fromTheme(ICON_NORMAL),
            3000
        )
        print(f"Snoozed until {self.snooze_until.isoformat()}")

    def system_suspend(self) -> None:
        """Suspend the system."""
        subprocess.run(["systemctl", "suspend"], check=False)

    def screen_off(self) -> None:
        """Turn off the screen."""
        subprocess.run(["xset", "dpms", "force", "off"], check=False)

    def lock_screen(self) -> None:
        """Lock the current session."""
        subprocess.run(["loginctl", "lock-session"], check=False)

    def quit_app(self) -> None:
        """Clean up and exit the application."""
        self.tray_icon.hide()
        app_instance = QApplication.instance()
        if app_instance:
            app_instance.quit()

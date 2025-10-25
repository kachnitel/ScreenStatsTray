"""Main system tray application."""
import subprocess
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction, QApplication
from PyQt5.QtGui import QIcon, QPainter, QColor, QPixmap, QCursor
from PyQt5.QtCore import QTimer, Qt
from .popup import StatsPopup
from ..services.session_service import SessionService
from ..config import ALERT_SESSION_MINUTES, NOTIFY_BUTTONS # <-- FIXME

ICON_NORMAL = "preferences-desktop"
ICON_ALERT = "chronometer-pause-symbolic"

class TrayApp:
    """Main application class for the system tray icon."""

    def __init__(self) -> None:
        self.session_service = SessionService()
        self.popup: StatsPopup = StatsPopup()
        self.notified_threshold = False

        # Create tray icon
        self.tray_icon = QSystemTrayIcon(QIcon.fromTheme(ICON_NORMAL))
        self.tray_icon.setToolTip("ScreenTray")

        # Context menu
        self.menu: QMenu = QMenu()

        # --- FIXME: Conditionally build the Quick Actions menu ---
        actions_menu = QMenu("Quick Actions")
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

        # Only add the "Quick Actions" menu and separator if any actions were added
        if actions_added:
            self.menu.addMenu(actions_menu)
            self.menu.addSeparator()
        # --- END FIXME ---


        exit_action: QAction = self.menu.addAction("Exit")  # type: ignore[reportUnknownMemberType, reportAssignmentType]
        exit_action.triggered.connect(self.quit_app)
        self.tray_icon.setContextMenu(self.menu)

        self.tray_icon.activated.connect(self.on_tray_activated)  # pyright: ignore[reportGeneralTypeIssues]

        # Timer for updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status)  # pyright: ignore[reportGeneralTypeIssues]
        self.timer.start(2000)

        self.update_status()
        self.tray_icon.show()

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
            # Show menu explicitly on right-click for compatibility
            self.menu.exec_(QCursor.pos()) # pyright: ignore[reportUnknownMemberType]

    def update_status(self) -> None:
        """Update tray icon and tooltip based on activity."""
        is_active = self.session_service.is_currently_active()
        session_s = self.session_service.get_current_session_seconds()
        break_s = self.session_service.get_last_break_seconds()

        if is_active:
            session_m = session_s / 60.0
            tooltip = f"Active: {int(session_m)}m\nLast Break: {int(break_s / 60)}m"
            if session_m >= ALERT_SESSION_MINUTES:
                self.tray_icon.setIcon(QIcon.fromTheme(ICON_ALERT))
                if not self.notified_threshold:
                    self.notify_threshold()
                    self.notified_threshold = True
            else:
                self.tray_icon.setIcon(self._create_icon("green"))
                self.notified_threshold = False
        else:
            tooltip = f"Idle: {int(break_s / 60)}m\nLast Session: {int(session_s / 60)}m"
            self.tray_icon.setIcon(self._create_icon("gray"))
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
        """Show a desktop notification when threshold exceeded."""
        title = "ScreenTracker Alert"
        message = f"Session exceeded {ALERT_SESSION_MINUTES} minutes!"
        self.tray_icon.showMessage(title, message, QIcon.fromTheme(ICON_ALERT))

    def system_suspend(self) -> None:
        subprocess.run(["systemctl", "suspend"], check=False)

    def screen_off(self) -> None:
        subprocess.run(["xset", "dpms", "force", "off"], check=False)

    def lock_screen(self) -> None:
        subprocess.run(["loginctl", "lock-session"], check=False)

    def quit_app(self) -> None:
        """Quit the application."""
        self.tray_icon.hide()
        app_instance = QApplication.instance()
        if app_instance:
            app_instance.quit()

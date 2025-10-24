"""Main system tray application."""
import sys
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QIcon, QPainter, QColor, QPixmap
from PyQt5.QtCore import QTimer, Qt
from .popup import StatsPopup
from ..services.session_service import SessionService
from ..config import ALERT_SESSION_MINUTES, IDLE_THRESHOLD_MS

# Simple icon paths (replace with real .ico or .png)
# We will generate simple pixmaps instead for portability

class TrayApp:
    """Main application class."""

    def __init__(self) -> None:
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.session_service = SessionService()

        # Create popup window (hidden by default)
        self.popup = StatsPopup()

        # Create tray icon
        self.tray_icon = QSystemTrayIcon()
        self.tray_icon.setToolTip("ScreenTray")

        # Create tray menu
        menu = QMenu()
        show_action = QAction("Show Stats")
        show_action.triggered.connect(self.show_popup)
        menu.addAction(show_action)

        menu.addSeparator()

        quit_action = QAction("Quit")
        quit_action.triggered.connect(self.quit_app)
        menu.addAction(quit_action)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self.on_tray_activated)

        # Timer for icon/tooltip updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status)
        self.timer.start(2000)  # Update every 2 seconds

        self.update_status()  # Initial update
        self.tray_icon.show()

    def run(self) -> int:
        """Start the application event loop."""
        return self.app.exec_()

    def show_popup(self) -> None:
        """Show the statistics popup window."""
        self.popup.show()
        self.popup.activateWindow()

    def on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon click."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:  # Left click
            self.show_popup()

    def update_status(self) -> None:
        """Update tray icon and tooltip based on activity."""
        is_active = self.session_service.is_currently_active()
        session_s = self.session_service.get_current_session_seconds()
        break_s = self.session_service.get_last_break_seconds()

        if is_active:
            session_m = session_s / 60.0
            tooltip = f"Active: {int(session_m)}m\nLast Break: {int(break_s / 60)}m"
            
            if session_m >= ALERT_SESSION_MINUTES:
                icon = self._create_icon("red")  # Alert
            else:
                icon = self._create_icon("green") # Active
        else:
            tooltip = f"Idle: {int(break_s / 60)}m\nLast Session: {int(session_s / 60)}m"
            icon = self._create_icon("gray")  # Inactive

        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip(tooltip)

    def _create_icon(self, color_name: str) -> QIcon:
        """Create a 16x16 pixmap icon of a specific color."""
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        color = QColor(color_name)
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(2, 2, 12, 12)  # Draw a circle
        painter.end()
        
        return QIcon(pixmap)

    def quit_app(self) -> None:
        """Quit the application."""
        self.tray_icon.hide()
        self.app.quit()

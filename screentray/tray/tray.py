"""Main system tray application with event-driven plugin system."""
import datetime
import os
from typing import Optional, List, Tuple, Callable, Dict, Any
from ..services.notification_service import NotificationService
from ..services.system_service import SystemService
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction, QApplication
from PyQt5.QtGui import QIcon, QPainter, QColor, QPixmap, QCursor, QPalette
from PyQt5.QtCore import (
    QTimer, Qt, QPropertyAnimation, QEasingCurve, QObject, pyqtProperty, pyqtSignal, QRect # type: ignore
)
from .popup import StatsPopup
from ..config import ICON_PULSE_INTERVAL, settings, NOTIFY_BUTTONS
from ..services.session_service import SessionService
from ..events import Event, EventContext
from . import config_dialog

ICON_NORMAL = "preferences-desktop-display-randr-symbolic"
ICON_ALERT = "chronometer-pause-symbolic"

# Centralized configuration for all visual states
_STATE_CONFIG: Dict[str, Dict[str, Any]] = {
    "idle": {
        "icon": ICON_NORMAL,
        "static_color": None, # Use native theme icon
        "animation": False
    },
    "active": {
        "icon": ICON_NORMAL,
        "static_color": None, # Use native theme icon
        "animation": False
    },
    "alert": {
        "icon": ICON_ALERT,
        "static_color": QColor("red"),
        "animation": False
    },
    "snooze": {
        "icon": ICON_ALERT,
        "start_color": QColor("orange"), # Animation end color
        "animation": True
    }
}

TEST_NOTIFICATION_TRIGGER = os.path.expanduser("~/.local/share/screentracker_test_notify")


def get_system_color(role: str = "normal") -> QColor:
    """Get color from system palette."""
    app: Optional[QApplication] = QApplication.instance() # pyright: ignore[reportAssignmentType]
    # Fallback colors if no QApplication or if running in a headless environment
    if not app:
        return {"normal": QColor("#3daee9"), "inactive": QColor("#7f8c8d")}.get(role, QColor("#3daee9"))

    palette: QPalette = app.palette()
    if role == "inactive":
        return palette.color(QPalette.ColorRole.Mid)
    else:  # normal/active
        return palette.color(QPalette.ColorRole.HighlightedText)


class IconColor(QObject):
    """Holds the color property for QPropertyAnimation."""
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._color: QColor = get_system_color("normal")

    def get_color(self) -> QColor:
        return self._color

    def set_color(self, color: QColor) -> None:
        self._color = color

    color: QColor = pyqtProperty(QColor, get_color, set_color)


class TrayIconVisuals(QObject):
    """
    Manages the visual state and animation of the tray icon.
    (Single Responsibility: Visual Management)
    """
    icon_updated: pyqtSignal = pyqtSignal(QIcon)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.current_state: str = "idle"
        self.icon_color_object: IconColor = IconColor()
        self.animation: QPropertyAnimation = QPropertyAnimation(self.icon_color_object, b"color")
        self.animation.setDuration(ICON_PULSE_INTERVAL)
        self.animation.setLoopCount(-1)
        self.animation.setEasingCurve(QEasingCurve.InBounce) # pyright: ignore[reportUnknownArgumentType, reportUnknownMemberType]
        self.animation.valueChanged.connect(self._emit_animated_icon)

        # Initialize with the base idle icon
        self.icon_updated.emit(QIcon.fromTheme(ICON_NORMAL))

    def _emit_animated_icon(self, color: QColor) -> None:
        """Slot called by animation. Emits the icon based on the current state."""
        # Get the icon name from the centralized config
        icon_name: str = _STATE_CONFIG.get(self.current_state, {}).get("icon", ICON_NORMAL)
        self.icon_updated.emit(self._create_colored_icon(icon_name, color))

    def _create_colored_icon(self, icon_name: str, color: QColor) -> QIcon:
        """Creates a colored version of the KDE icon."""
        pixmap: QPixmap = QPixmap(16, 16)
        pixmap.fill(Qt.transparent) # pyright: ignore[reportAttributeAccessIssue, reportUnknownArgumentType, reportUnknownMemberType]

        # Load the original icon from the theme
        original_icon: QIcon = QIcon.fromTheme(icon_name)
        painter: QPainter = QPainter(pixmap)

        # Draw the original icon onto the pixmap
        original_icon.paint(painter, QRect(0, 0, 16, 16))

        # Apply the color overlay (SourceIn ensures only existing pixels are colored)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn) # pyright: ignore[reportUnknownArgumentType, reportUnknownMemberType]
        painter.fillRect(pixmap.rect(), color)
        painter.end()

        return QIcon(pixmap)

    def _get_theme_highlight_color(self) -> QColor:
        """Helper to safely get the theme's highlight color."""
        app: Optional[QApplication] = QApplication.instance() # pyright: ignore[reportAssignmentType]
        if app:
            # Use HighlightedText color for the pulse effect
            return app.palette().color(QPalette.ColorRole.HighlightedText)
        return QColor("#3daee9") # Fallback for no QApplication

    def set_state(self, state: str) -> None:
        """Sets the visual state of the icon (active, idle, alert, snooze)."""
        if state == self.current_state:
            return  # No change

        self.animation.stop()
        self.current_state = state

        config: Dict[str, Any] = _STATE_CONFIG.get(state, _STATE_CONFIG["idle"])

        if config.get("animation"):
            # 1. Setup Animation (DRY: uses centralized config)
            start_color: QColor = self._get_theme_highlight_color() # Always start from the theme accent
            end_color: QColor = config["start_color"] # The color to pulse to (e.g., Orange)

            self.animation.setStartValue(start_color)
            self.animation.setEndValue(end_color)
            self.animation.start()

        elif config.get("static_color"):
            # 2. Static Colored Icon (DRY: uses centralized config)
            icon: QIcon = self._create_colored_icon(config["icon"], config["static_color"])
            self.icon_updated.emit(icon)

        else:
            # 3. Native Themed Icon (idle/active)
            self.icon_updated.emit(QIcon.fromTheme(config["icon"]))

    def get_static_icon(self, state: str) -> QIcon:
        """
        Provides a static QIcon for use in synchronous operations like QSystemTrayIcon.showMessage().
        Uses the centralized _STATE_CONFIG.
        """
        config: Dict[str, Any] = _STATE_CONFIG.get(state, _STATE_CONFIG["idle"])

        if config.get("static_color"):
            # Return a colored icon for alert/snooze states
            return self._create_colored_icon(config["icon"], config["static_color"])

        # Return the native themed icon for idle/active states
        return QIcon.fromTheme(config["icon"])

class TrayApp:
    """
    Main system tray application.
    Provides base tray functionality and emits events for plugins.
    """

    def __init__(self) -> None:
        self.notification_service = NotificationService()
        self.system_service = SystemService()
        self.session_service = SessionService()
        self.popup: StatsPopup = StatsPopup()
        self.notified_threshold = False
        self.snooze_until: Optional[datetime.datetime] = None
        self._dbus_signal_handler: Optional[Callable[[int, str], None]] = None

        self.visuals = TrayIconVisuals()

        # Create tray icon
        self.tray_icon = QSystemTrayIcon()
        # Connect the visual class signal to the tray icon's setIcon method
        self.visuals.icon_updated.connect(self.tray_icon.setIcon) # pyright: ignore[reportGeneralTypeIssues]
        # Set initial state
        self.visuals.set_state("idle")
        self.tray_icon.setToolTip("ScreenTray")

        # Context menu
        self.create_context_menu()

        # Connect notification message clicked signal
        self.tray_icon.messageClicked.connect(self.on_notification_clicked)  # pyright: ignore[reportGeneralTypeIssues]

        # Connect tray activation
        self.tray_icon.activated.connect(self.on_tray_activated)  # pyright: ignore[reportGeneralTypeIssues]

        # Timer for updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status)  # pyright: ignore[reportGeneralTypeIssues]
        self.timer.start(2000)

        self.update_status()
        self.tray_icon.show()

    def create_context_menu(self) -> None:
        """
        Create the context menu and emit event for plugins to extend it.
        """
        self.menu = QMenu()

        # Emit event for plugins to add items at the top
        self.popup.plugin_manager.events.emit(
            Event.TRAY_READY,
            EventContext(menu=self.menu, tray=self, position='top')
        )

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
        # --- Use new position-aware method ---
        # icon_geom = self.tray_icon.geometry()
        # self.popup.show_at_tray(icon_geom)
        self.popup.show()
        self.popup.activateWindow()

    def hide_popup(self) -> None:
        """Hide the statistics popup window."""
        self.popup.hide()

    def on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.popup.isVisible():
                self.hide_popup()
            else:
                self.show_popup()
        elif reason == QSystemTrayIcon.ActivationReason.Context:
            self.menu.popup(QCursor.pos())

    def on_notification_clicked(self) -> None:
        """Handle notification click."""
        self.menu.popup(QCursor.pos())

    def is_snoozed(self) -> bool:
        """Helper to check if we are in a snooze period."""
        if self.snooze_until:
            return datetime.datetime.now() < self.snooze_until
        return False

    def update_status(self) -> None:
        """Update tray icon and tooltip based on activity."""
        # Check for test notification trigger
        if os.path.exists(TEST_NOTIFICATION_TRIGGER):
            os.remove(TEST_NOTIFICATION_TRIGGER)
            self.send_test_notification()
            return

        is_active = self.session_service.is_currently_active()
        is_snoozing = self.is_snoozed()

        if is_active:
            _, session_s = self.session_service.get_current_session()
            _, break_end, break_s = self.session_service.get_last_break()

            session_m = session_s / 60.0
            tooltip = f"Active: {int(session_m)}m"

            if break_end:
                tooltip += f"\nLast Break: {int(break_s / 60)}m"

            if is_snoozing:
                self.visuals.set_state("snooze")
                self.notified_threshold = True  # Don't send notifications
                snooze_left = (self.snooze_until - datetime.datetime.now()).total_seconds() / 60 # pyright: ignore[reportUnknownMemberType, reportOptionalOperand, reportUnknownVariableType] Covered in is_snoozed
                tooltip += f"\nStatus: Snoozed ({int(snooze_left)} min left)" # pyright: ignore[reportUnknownArgumentType]

            elif session_m >= settings.alert_session_minutes:
                self.visuals.set_state("alert")

                if not self.notified_threshold:
                    self.notify_threshold()
                    self.notified_threshold = True

            else:  # Active but under threshold
                self.visuals.set_state("active")
                self.notified_threshold = False
                # No need to reset snooze_until here, only when we become inactive

        else:  # Not active (idle)
            _, break_end, break_s = self.session_service.get_last_break()
            if break_end is None:
                tooltip = f"Idle: {int(break_s / 60)}m"
            else:
                tooltip = "Idle"

            self.visuals.set_state("idle")
            self.notified_threshold = False
            self.snooze_until = None  # Reset snooze when idle

        self.tray_icon.setToolTip(tooltip)

    def notify_threshold(self) -> None:
        """Show desktop notification when threshold exceeded."""
        title = "ScreenTracker Alert"
        message = f"Session exceeded {settings.alert_session_minutes} minutes! Take a break."

        actions: List[Tuple[str, Callable[[], None]]] = []

        if NOTIFY_BUTTONS.get("snooze", False):
            actions.append((f"Snooze {settings.snooze_minutes}m", self.snooze_notification))
        if NOTIFY_BUTTONS.get("suspend", False):
            actions.append(("Suspend", self.system_suspend))
        if NOTIFY_BUTTONS.get("screen_off", False):
            actions.append(("Screen Off", self.screen_off))
        if NOTIFY_BUTTONS.get("lock_screen", False):
            actions.append(("Lock Screen", self.lock_screen))

        # --- UPDATE: Use state name, as the logic for color/icon name is internal ---
        alert_icon = self.visuals.get_static_icon("alert")

        # Use theme icon name for DBus. The colored version is for the QSystemTrayIcon fallback.
        if not self._notify_plasma(title, message, ICON_ALERT, actions):
            self.tray_icon.showMessage(title, message + "\n\nClick for actions.",
                                      alert_icon, 0)

    def send_test_notification(self) -> None:
        """Send test notification."""
        title = "ScreenTracker Test"
        message = "Test notification with action buttons."

        actions: List[Tuple[str, Callable[[], None]]] = []
        if NOTIFY_BUTTONS.get("snooze", False):
            actions.append((f"Test Snooze {settings.snooze_minutes}m",
                          lambda: print("Test: Snooze clicked")))
        if NOTIFY_BUTTONS.get("suspend", False):
            actions.append(("Test Suspend", lambda: print("Test: Suspend clicked")))
        if NOTIFY_BUTTONS.get("screen_off", False):
            actions.append(("Test Screen Off", lambda: print("Test: Screen Off clicked")))
        if NOTIFY_BUTTONS.get("lock_screen", False):
            actions.append(("Test Lock", lambda: print("Test: Lock clicked")))

        # --- UPDATE: Use state name, remove color argument ---
        active_icon = self.visuals.get_static_icon("active")

        if not self._notify_plasma(title, message, ICON_NORMAL, actions):
            self.tray_icon.showMessage(title, message, active_icon, 5000)

    def _notify_plasma(self, title: str, message: str, icon: str,
                      actions: Optional[List[Tuple[str, Callable[[], None]]]] = None) -> bool:
        """Send KDE Plasma notification via DBus."""

        if not self.notification_service.notify(title, message,
                                                icon=icon, # Use the icon string passed
                                                actions=actions, timeout=5000):
            # Fallback to standard tray message
            # --- UPDATE: Use state name, remove color argument ---
            fallback_icon = self.visuals.get_static_icon("active")
            self.tray_icon.showMessage(title, message, fallback_icon, 5000)
            return False

        return True

    def snooze_notification(self) -> None:
        """Snooze notification for configured duration."""
        self.snooze_until = datetime.datetime.now() + datetime.timedelta(
            minutes=settings.snooze_minutes)
        print(f"Snoozed until {self.snooze_until.isoformat()}")
        self.update_status() # Immediately update to "snooze" state

        # --- UPDATE: Use state name, remove color argument ---
        self.tray_icon.showMessage("Snoozed",
                                  f"Alert snoozed for {settings.snooze_minutes} minutes",
                                  self.visuals.get_static_icon("snooze"), 3000)

    def system_suspend(self) -> None:
        """Suspend the system."""
        self.system_service.suspend()

    def screen_off(self) -> None:
        """Turn off the screen."""
        self.system_service.screen_off()

    def lock_screen(self) -> None:
        """Lock the screen."""
        self.system_service.lock_screen()

    def quit_app(self) -> None:
        """Quit the application."""
        self.tray_icon.hide()
        app_instance = QApplication.instance()
        if app_instance:
            app_instance.quit()

    def open_settings(self) -> None:
        """Open settings dialog."""
        dialog = config_dialog.ConfigDialog()
        if dialog.exec_():
            settings.reload()
            self.notified_threshold = False
            self.snooze_until = None
            self.update_status()

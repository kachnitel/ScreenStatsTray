# file: tray.py
from typing import Optional #, TYPE_CHECKING
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QTimer, QDate
from .popup import StatsPopup
from .session import current_session_seconds
from .db import query_totals

# Configurable session alert threshold (minutes)
ALERT_SESSION_MINUTES: int = 30

# System theme icons
ICON_NORMAL: str = "preferences-desktop"
ICON_ALERT: str = "chronometer-pause-symbolic" #"dialog-warning"

# if TYPE_CHECKING:
#     Trigger = QSystemTrayIcon.ActivationReason.Trigger  # hint for type checker

class TrayApp:
    def __init__(self) -> None:
        # Initialize tray
        self.tray: QSystemTrayIcon = QSystemTrayIcon(QIcon.fromTheme(ICON_NORMAL))
        self.tray.setToolTip("ScreenTracker")
        self.tray.show()

        # Keep popup reference
        self.popup: Optional[StatsPopup] = None

        # Connect left-click
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
            self.popup.show()
            self.popup.raise_()
            self.popup.activateWindow()

    def update_tooltip(self) -> None:
        today: str = QDate.currentDate().toString("yyyy-MM-dd")
        totals = query_totals(today)
        active_sec: float = totals.get("active", 0)
        inactive_sec: float = totals.get("inactive", 0)

        # Current session
        session_sec: float = current_session_seconds()
        h_s, rem = divmod(int(session_sec), 3600)
        m_s, s_s = divmod(rem, 60)

        # Tooltip text
        h_a, m_a, s_a = int(active_sec // 3600), int((active_sec % 3600) // 60), int(active_sec % 60)
        h_i, m_i, s_i = int(inactive_sec // 3600), int((inactive_sec % 3600) // 60), int(inactive_sec % 60)
        tooltip: str = (
            f"Active: {h_a:02d}:{m_a:02d}:{s_a:02d}  "
            f"Inactive: {h_i:02d}:{m_i:02d}:{s_i:02d}\n"
            f"Current session: {h_s:02d}:{m_s:02d}:{s_s:02d}"
        )
        self.tray.setToolTip(tooltip)

        # Change icon if session exceeds threshold
        if session_sec / 60 >= ALERT_SESSION_MINUTES:
            self.tray.setIcon(QIcon.fromTheme(ICON_ALERT))
        else:
            self.tray.setIcon(QIcon.fromTheme(ICON_NORMAL))

    def exit(self) -> None:
        self.tray.hide()
        QApplication.quit()

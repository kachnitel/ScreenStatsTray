"""Statistics popup window."""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QTabWidget
)
from PyQt5.QtGui import QShowEvent
from PyQt5.QtCore import QTimer, Qt, QEvent
import datetime
import socket
import subprocess
import webbrowser
from typing import List, Optional
from .activity_bar import ActivityBar
from ..services.stats_service import StatsService
from ..services.session_service import SessionService
from ..plugins import PluginManager


class StatsPopup(QWidget):
    """
    Statistics popup widget with native tray popup behavior.

    Displays activity statistics in a compact, tray-anchored window
    that automatically hides when focus is lost, mimicking KDE's
    native tray popups like network manager.
    """

    def __init__(self) -> None:
        super().__init__()
        self.date = datetime.date.today()
        self.stats_service = StatsService()
        self.session_service = SessionService()
        self.web_port: Optional[int] = None

        # Configure as native popup window
        self.setWindowTitle("ScreenTray Statistics")
        self.setWindowFlags(
            Qt.Popup |  # Popup window that auto-hides on focus loss # pyright: ignore[reportAttributeAccessIssue,reportUnknownArgumentType,reportUnknownMemberType]
            Qt.FramelessWindowHint  # No window decorations # pyright: ignore[reportUnknownArgumentType,reportAttributeAccessIssue,reportUnknownMemberType]
        )
        self.setAttribute(Qt.WA_TranslucentBackground, False) # pyright: ignore[reportAttributeAccessIssue, reportUnknownArgumentType, reportUnknownMemberType]

        # Set reasonable size constraints
        self.setMinimumWidth(320)
        self.setMaximumWidth(450)
        self.setMaximumHeight(600)

        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.setLayout(self.main_layout)

        # Initialize plugin manager and collect widgets
        self.plugin_manager = PluginManager()
        self.plugin_manager.discover_plugins()
        self.plugin_widgets: List[QWidget] = []

        for plugin in self.plugin_manager.plugins.values():
            widget = plugin.get_popup_widget()
            if widget:
                self.plugin_widgets.append(widget)

        # Create tabbed interface
        self.tab_widget = QTabWidget()
        self.main_layout.addWidget(self.tab_widget)

        self.create_now_tab()
        self.create_daily_tab()

        # Web dashboard button (if service is running)
        self.check_web_service()
        if self.web_port:
            self.web_button = QPushButton("Open Web Dashboard")
            self.web_button.clicked.connect(self.open_web_dashboard)
            self.main_layout.addWidget(self.web_button)

        # Update timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_all_stats)
        self.timer.start(5000)

        self.update_all_stats()

    def create_now_tab(self) -> None:
        """Create the 'Now' tab showing live session and 24h activity."""
        now_tab = QWidget()
        now_layout = QVBoxLayout()
        now_layout.setContentsMargins(5, 10, 5, 5)
        now_tab.setLayout(now_layout)

        # Current session stats
        now_layout.addWidget(QLabel("<b>Current Status:</b>"))
        self.session_label = QLabel("Session: ...")
        self.break_label = QLabel("Last Break: ...")
        now_layout.addWidget(self.session_label)
        now_layout.addWidget(self.break_label)

        now_layout.addSpacing(15)

        # 24h activity bar
        now_layout.addWidget(QLabel("<b>Last 24h Activity:</b>"))
        self.activity_bar = ActivityBar()
        now_layout.addWidget(self.activity_bar)

        now_layout.addStretch()
        self.tab_widget.addTab(now_tab, "Now")

    def create_daily_tab(self) -> None:
        """Create the 'Daily Stats' tab with historical data."""
        daily_tab = QWidget()
        daily_layout = QVBoxLayout()
        daily_layout.setContentsMargins(5, 10, 5, 5)
        daily_tab.setLayout(daily_layout)

        # Date navigation
        self.date_layout = QHBoxLayout()
        self.prev_button = QPushButton("< Prev")
        self.prev_button.clicked.connect(self.prev_day)
        self.date_label = QLabel()
        self.next_button = QPushButton("Next >")
        self.next_button.clicked.connect(self.next_day)

        self.date_layout.addWidget(self.prev_button)
        self.date_layout.addWidget(self.date_label)
        self.date_layout.addWidget(self.next_button)
        daily_layout.addLayout(self.date_layout)

        daily_layout.addSpacing(15)

        # Daily totals
        daily_layout.addWidget(QLabel("<b>Daily Totals:</b>"))
        self.active_label = QLabel("Active: ...")
        self.inactive_label = QLabel("Inactive: ...")
        daily_layout.addWidget(self.active_label)
        daily_layout.addWidget(self.inactive_label)

        # Plugin widgets
        if self.plugin_widgets:
            daily_layout.addSpacing(15)
            for widget in self.plugin_widgets:
                daily_layout.addWidget(widget)

        daily_layout.addStretch()
        self.tab_widget.addTab(daily_tab, "Daily Stats")

    def update_all_stats(self) -> None:
        """Update statistics for all tabs."""
        self.update_live_stats()
        self.update_historical_stats()

    def update_live_stats(self) -> None:
        """Update live statistics on the 'Now' tab."""
        self.activity_bar.update_data()

        is_active = self.session_service.is_currently_active()

        if is_active:
            _, session_s = self.session_service.get_current_session()
            _, break_end, break_s = self.session_service.get_last_break()

            self.session_label.setText(f"Session: {self._format_seconds(session_s)}")
            if break_end:
                self.break_label.setText(f"Last Break: {self._format_seconds(break_s)}")
            else:
                self.break_label.setText("Last Break: (no recent break)")
        else:
            _, break_end, break_s = self.session_service.get_last_break()

            if break_end is None:
                self.session_label.setText("Session: Idle")
                self.break_label.setText(f"Idle Duration: {self._format_seconds(break_s)}")
            else:
                self.session_label.setText("Session: No active session")
                self.break_label.setText(f"Last Break: {self._format_seconds(break_s)}")

    def update_historical_stats(self) -> None:
        """Update historical statistics on the 'Daily Stats' tab."""
        self.date_label.setText(f"<b>{self.date.isoformat()}</b>")
        self.next_button.setEnabled(self.date < datetime.date.today())

        day_str = self.date.isoformat()
        totals = self.stats_service.get_daily_totals(day_str)
        self.active_label.setText(f"Active: {self._format_seconds(totals['active'])}")
        self.inactive_label.setText(f"Inactive: {self._format_seconds(totals['inactive'])}")

        # Update plugin widgets with selected date
        for widget in self.plugin_widgets:
            if hasattr(widget, 'update_data'):
                widget.update_data(self.date) # pyright: ignore[reportUnknownMemberType]

    def prev_day(self) -> None:
        """Navigate to previous day."""
        self.date -= datetime.timedelta(days=1)
        self.update_historical_stats()

    def next_day(self) -> None:
        """Navigate to next day."""
        if self.date < datetime.date.today():
            self.date += datetime.timedelta(days=1)
            self.update_historical_stats()

    def _format_seconds(self, seconds: float) -> str:
        """
        Format seconds into human-readable duration.

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted string (e.g., "2h 15m 30s", "45m 12s", "23s")
        """
        total_s = int(seconds)
        h = total_s // 3600
        m = (total_s % 3600) // 60
        s = total_s % 60
        if h > 0:
            return f"{h}h {m}m {s}s"
        elif m > 0:
            return f"{m}m {s}s"
        else:
            return f"{s}s"

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
                            return
                except (socket.error, OSError):
                    continue
                    
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        self.web_port = None

    def open_web_dashboard(self) -> None:
        """Open the web dashboard in default browser."""
        if self.web_port:
            url = f"http://127.0.0.1:{self.web_port}"
            webbrowser.open(url)


    def showEvent(self, a0: QShowEvent | None) -> None:
        """
        Handle popup display event.

        Resets to today's date and refreshes all statistics
        when the popup is shown.
        """
        self.date = datetime.date.today()
        self.update_all_stats()
        super().showEvent(a0)

    def event(self, a0: QEvent|None) -> bool:
        """
        Handle window events.

        Specifically handles WindowDeactivate to hide the popup
        when it loses focus, matching native KDE popup behavior.
        """
        if a0 == None:
            return super().event(a0)

        if a0.type() == QEvent.WindowDeactivate: # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]
            # Auto-hide when focus is lost (native popup behavior)
            self.hide()
        return super().event(a0)

"""Statistics popup window."""
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton
from PyQt5.QtGui import QPaintEvent
from PyQt5.QtCore import QTimer
import datetime
from typing import List, Tuple
from .activity_bar import ActivityBar
from ..services.stats_service import StatsService
from ..services.session_service import SessionService


class StatsPopup(QWidget):
    """Main statistics popup window."""

    def __init__(self) -> None:
        super().__init__()
        self.date = datetime.date.today()
        self.stats_service = StatsService()
        self.session_service = SessionService()

        self.setWindowTitle("ScreenTray Statistics")
        self.setMinimumWidth(300)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # --- Date Navigation ---
        self.date_layout = QHBoxLayout()
        self.prev_button = QPushButton("< Prev")
        self.prev_button.clicked.connect(self.prev_day)
        self.date_label = QLabel()
        self.next_button = QPushButton("Next >")
        self.next_button.clicked.connect(self.next_day)
        
        self.date_layout.addWidget(self.prev_button)
        self.date_layout.addStretch()
        self.date_layout.addWidget(self.date_label)
        self.date_layout.addStretch()
        self.date_layout.addWidget(self.next_button)
        self.layout.addLayout(self.date_layout)

        # --- 24h Activity Bar ---
        self.layout.addWidget(QLabel("<b>Last 24h Activity:</b>"))
        self.activity_bar = ActivityBar()
        self.layout.addWidget(self.activity_bar)

        # --- Current Session Stats ---
        self.layout.addWidget(QLabel("<b>Current Status:</b>"))
        self.session_label = QLabel("Session: ...")
        self.break_label = QLabel("Last Break: ...")
        self.layout.addWidget(self.session_label)
        self.layout.addWidget(self.break_label)

        # --- Daily Stats ---
        self.layout.addWidget(QLabel("<b>Daily Totals:</b>"))
        self.active_label = QLabel("Active: ...")
        self.inactive_label = QLabel("Inactive: ...")
        self.layout.addWidget(self.active_label)
        self.layout.addWidget(self.inactive_label)

        # --- Top Apps ---
        self.layout.addWidget(QLabel("<b>Top Apps:</b>"))
        self.app_labels: List[QLabel] = []
        for _ in range(5):  # Show top 5
            label = QLabel("...")
            self.layout.addWidget(label)
            self.app_labels.append(label)

        # --- Timer for updates ---
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(5000)  # Update every 5 seconds

        self.update_stats()

    def update_stats(self) -> None:
        """Reload all statistics and update labels."""
        self.date_label.setText(f"<b>{self.date.isoformat()}</b>")
        
        # Check if "Next" button should be enabled
        self.next_button.setEnabled(self.date < datetime.date.today())

        # Update 24h bar
        self.activity_bar.update_data()

        # Update current session/break
        session_s = self.session_service.get_current_session_seconds()
        break_s = self.session_service.get_last_break_seconds()
        self.session_label.setText(f"Session: {self._format_seconds(session_s)}")
        self.break_label.setText(f"Last Break: {self._format_seconds(break_s)}")

        # Update daily totals
        day_str = self.date.isoformat()
        totals = self.stats_service.get_daily_totals(day_str)
        self.active_label.setText(f"Active: {self._format_seconds(totals['active'])}")
        self.inactive_label.setText(f"Inactive: {self._format_seconds(totals['inactive'])}")

        # Update top apps
        top_apps = self.stats_service.get_top_apps(day_str, limit=5)
        for i in range(5):
            if i < len(top_apps):
                app, seconds = top_apps[i]
                self.app_labels[i].setText(f"{i+1}. {app}: {self._format_seconds(seconds)}")
            else:
                self.app_labels[i].setText(f"{i+1}. ...")

    def prev_day(self) -> None:
        """Go to the previous day."""
        self.date -= datetime.timedelta(days=1)
        self.update_stats()

    def next_day(self) -> None:
        """Go to the next day."""
        if self.date < datetime.date.today():
            self.date += datetime.timedelta(days=1)
            self.update_stats()

    def _format_seconds(self, seconds: float) -> str:
        """Format seconds into H:M:S string."""
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

    def showEvent(self, event: QPaintEvent) -> None:
        """Trigger update when window is shown."""
        self.update_stats()
        super().showEvent(event)

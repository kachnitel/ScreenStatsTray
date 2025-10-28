"""
screentray/plugins/app_tracker/widget.py

Qt widget for displaying app usage statistics in the tray popup.
"""
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt
from typing import List, Tuple
from .service import AppUsageService


class AppUsageWidget(QWidget):
    """
    Widget showing top applications by usage time.

    Displays top 5 apps by default, expandable to show all.
    Updates automatically when parent calls update_data().
    """

    def __init__(self) -> None:
        super().__init__()
        self.service = AppUsageService()
        self.expanded = False
        self.limit_collapsed = 5  # Show 5 apps when collapsed

        # Layout
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

        # Header
        self.header = QLabel("<b>App Usage Today:</b>")
        self.layout.addWidget(self.header)

        # App list container
        self.app_list_widget = QWidget()
        self.app_list_layout = QVBoxLayout()
        self.app_list_layout.setContentsMargins(10, 0, 0, 0)
        self.app_list_widget.setLayout(self.app_list_layout)
        self.layout.addWidget(self.app_list_widget)

        # Expand/collapse button
        self.toggle_button = QPushButton("Show More")
        self.toggle_button.clicked.connect(self.toggle_expanded)
        self.layout.addWidget(self.toggle_button)

        # Initial data load
        self.update_data()

    def update_data(self) -> None:
        """Refresh app usage data and update display."""
        # Get today's usage
        usage = self.service.get_app_usage_today()

        # Sort by time spent (descending)
        sorted_apps = sorted(usage.items(), key=lambda x: x[1], reverse=True)

        # Clear existing labels
        while self.app_list_layout.count():
            child = self.app_list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Determine how many to show
        limit = len(sorted_apps) if self.expanded else self.limit_collapsed
        apps_to_show = sorted_apps[:limit]

        if not apps_to_show:
            # No data yet
            no_data_label = QLabel("<i>No app usage recorded yet</i>")
            no_data_label.setStyleSheet("color: gray;")
            self.app_list_layout.addWidget(no_data_label)
            self.toggle_button.hide()
        else:
            # Display apps
            for app_name, seconds in apps_to_show:
                time_str = self._format_duration(seconds)
                label = QLabel(f"{app_name}: {time_str}")
                self.app_list_layout.addWidget(label)

            # Update toggle button
            if len(sorted_apps) > self.limit_collapsed:
                self.toggle_button.show()
                remaining = len(sorted_apps) - limit
                if self.expanded:
                    self.toggle_button.setText("Show Less")
                else:
                    self.toggle_button.setText(f"Show More ({remaining} more)")
            else:
                self.toggle_button.hide()

    def toggle_expanded(self) -> None:
        """Toggle between showing 5 apps and showing all apps."""
        self.expanded = not self.expanded
        self.update_data()

    def _format_duration(self, seconds: float) -> str:
        """
        Format seconds into readable duration.

        Examples:
            65 seconds -> "1m 5s"
            3661 seconds -> "1h 1m"
        """
        total_s = int(seconds)
        h = total_s // 3600
        m = (total_s % 3600) // 60
        s = total_s % 60

        if h > 0:
            return f"{h}h {m}m"
        elif m > 0:
            return f"{m}m {s}s"
        else:
            return f"{s}s"

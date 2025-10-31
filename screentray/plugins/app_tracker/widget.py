"""
screentray/plugins/app_tracker/widget.py

Qt widget for displaying app usage statistics in the tray popup.
"""
import datetime
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QLayoutItem
from .service import AppUsageService


class AppUsageWidget(QWidget):
    """
    Widget showing top applications by usage time.

    This widget is now date-aware and receives the date to display
    from its parent (StatsPopup) via the update_data method.
    """

    def __init__(self) -> None:
        super().__init__()
        # Service methods are static, so we can call them directly
        self.service = AppUsageService()
        self.expanded = False
        self.limit_collapsed = 5  # Show 5 apps when collapsed
        self.current_date = datetime.date.today()

        # Layout
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0, 5, 0, 0) # Added top margin
        self.setLayout(self.main_layout)

        # Header (will be set by update_data)
        self.header = QLabel("<b>App Usage:</b>")
        self.main_layout.addWidget(self.header)

        # App list container
        self.app_list_widget = QWidget()
        self.app_list_layout = QVBoxLayout()
        self.app_list_layout.setContentsMargins(10, 0, 0, 0)
        self.app_list_widget.setLayout(self.app_list_layout)
        self.main_layout.addWidget(self.app_list_widget)

        # Expand/collapse button
        self.toggle_button = QPushButton("Show More")
        self.toggle_button.clicked.connect(self.toggle_expanded)
        self.main_layout.addWidget(self.toggle_button)

        # Initial data load (will be triggered by parent)
        # self.update_data(self.current_date) # No need, parent calls it

    def update_data(self, date_to_show: datetime.date) -> None:
        """
        Refresh app usage data for the specified date.
        This method is called by the parent StatsPopup.
        """
        self.current_date = date_to_show

        # Update header to reflect the selected date
        date_str = "Today" if date_to_show == datetime.date.today() else date_to_show.isoformat()
        self.header.setText(f"<b>App Usage ({date_str}):</b>")

        # Get usage for the specified day
        now = datetime.datetime.now()
        start_of_day = datetime.datetime.combine(date_to_show, datetime.time.min)

        # If the date is today, only show data up to 'now'
        if date_to_show == now.date():
            end_of_day = now
        else:
            end_of_day = datetime.datetime.combine(date_to_show, datetime.time.max)

        usage = self.service.get_app_usage_for_period(start_of_day, end_of_day)

        # Sort by time spent (descending)
        sorted_apps = sorted(usage.items(), key=lambda x: x[1], reverse=True)

        # Clear existing labels
        while self.app_list_layout.count():
            child: QLayoutItem | None = self.app_list_layout.takeAt(0)
            if child:
                w = child.widget()
                if w:
                    w.deleteLater()

        # Determine how many to show
        limit = len(sorted_apps) if self.expanded else self.limit_collapsed
        apps_to_show = sorted_apps[:limit]

        if not apps_to_show:
            # No data yet
            no_data_label = QLabel(f"<i>No app usage recorded for {date_str}</i>")
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
        # Re-run update with the same date
        self.update_data(self.current_date)

    def _format_duration(self, seconds: float) -> str:
        """
        Format seconds into readable duration.
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

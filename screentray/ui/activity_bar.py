"""24h activity bar widget."""
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QColor, QPaintEvent
from PyQt5.QtCore import Qt
import datetime
from typing import List, Dict
from ..services.activity_service import ActivityService
from ..services.session_service import SessionService
from ..config import ALERT_SESSION_MINUTES


class ActivityBar(QWidget):
    """Visual 24h rolling activity bar with session overlay."""

    def __init__(self) -> None:
        super().__init__()
        self.setFixedHeight(20)
        self.activity_service = ActivityService()
        self.session_service = SessionService()
        self.periods: List[Dict[str, any]] = []
        self.setMouseTracking(True)

    def update_data(self) -> None:
        """Refresh activity data from service."""
        self.periods = self.activity_service.get_activity_periods_last_24h()
        self.update()

    def paintEvent(self, event: QPaintEvent | None = None) -> None:
        """Draw the activity bar."""
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("lightgray"))

        width = self.width()
        height = self.height()
        total_seconds = 24 * 3600

        # Draw activity periods
        for period in self.periods:
            start = period["start"]
            end = period["end"]
            state = period["state"]

            # Calculate relative position in 24h window
            now = datetime.datetime.now()
            window_start = now - datetime.timedelta(hours=24)

            start_offset = (start - window_start).total_seconds()
            end_offset = (end - window_start).total_seconds()

            # Convert to pixel coordinates
            x = int((start_offset / total_seconds) * width)
            w = max(1, int(((end_offset - start_offset) / total_seconds) * width))

            color = QColor("green") if state == "active" else QColor("gray")
            painter.fillRect(x, 0, w, height, color)

        # Draw current session overlay
        session_start, session_duration = self.session_service.get_current_session()
        if session_start and session_duration > 0:
            now = datetime.datetime.now()
            window_start = now - datetime.timedelta(hours=24)

            if session_start >= window_start:
                start_offset = (session_start - window_start).total_seconds()
                session_x = int((start_offset / total_seconds) * width)
                session_w = max(2, int((session_duration / total_seconds) * width))

                # Color based on duration threshold
                if session_duration / 60 < ALERT_SESSION_MINUTES:
                    session_color = QColor("yellow")
                else:
                    session_color = QColor("red")

                painter.fillRect(session_x, 0, session_w, height, session_color)

        painter.end()

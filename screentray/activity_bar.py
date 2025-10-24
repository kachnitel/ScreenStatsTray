from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QColor, QPaintEvent
import datetime
import sqlite3
from typing import List, Tuple
from .db import DB_PATH
from .session import get_current_session
from .config import ALERT_SESSION_MINUTES

class ActivityBar(QWidget):
    """24h rolling activity bar with active/inactive + session overlay."""
    def __init__(self) -> None:
        super().__init__()
        self.setFixedHeight(20)
        self.segments: List[Tuple[float, float, str]] = []  # start_sec, end_sec, state
        self.setMouseTracking(True)

    def update_segments(self) -> None:
        """Load last 24h periods and merge consecutive same states."""
        now = datetime.datetime.now()
        since = now - datetime.timedelta(hours=24)
        rows: List[Tuple[str, str]] = []

        try:
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT timestamp, type
                    FROM events
                    WHERE timestamp >= ?
                    ORDER BY timestamp ASC
                """, (since.isoformat(),))
                rows = cur.fetchall()
        except sqlite3.Error:
            rows = []

        if not rows:
            self.segments = [(0.0, 24*3600.0, "inactive")]
            self.update()
            return

        self.segments = []
        last_ts = since
        last_state = "inactive"

        for ts_str, typ in rows:
            ts = datetime.datetime.fromisoformat(ts_str)
            # Determine state - include all inactive event types
            state = "inactive" if typ in ("idle_start", "screen_off", "lid_closed", "system_suspend") else "active"
            if state != last_state:
                # Append segment for previous state
                self.segments.append(((last_ts - since).total_seconds(),
                                    (ts - since).total_seconds(),
                                    last_state))
                last_ts = ts
                last_state = state
            # else: same state, continue without appending → merges adjacent identical states

        # Append the last segment up to now
        self.segments.append(((last_ts - since).total_seconds(),
                            (now - since).total_seconds(),
                            last_state))
        self.update()


    def paintEvent(self, a0: QPaintEvent | None = None) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("lightgray"))
        width, height = self.width(), self.height()
        for start_sec, end_sec, state in self.segments:
            x = int(start_sec / (24*3600) * width)
            w = max(1, int((end_sec - start_sec) / (24*3600) * width))
            color = QColor("green") if state == "active" else QColor("gray")
            painter.fillRect(x, 0, w, height, color)

        start_ts, session_sec = get_current_session()
        if session_sec > 0:
            # Calculate position in 24h window
            session_start_dt = datetime.datetime.fromtimestamp(start_ts)
            now = datetime.datetime.now()
            since = now - datetime.timedelta(hours=24)

            # Only show if session started within last 24h
            if session_start_dt >= since:
                session_start_x = int((session_start_dt - since).total_seconds() / (24*3600) * width)
                session_w = max(2, int(session_sec / (24*3600) * width))
                session_color = QColor("yellow") if session_sec / 60 < ALERT_SESSION_MINUTES else QColor("red")
                painter.fillRect(session_start_x, 0, session_w, height, session_color)

        painter.end()
from PyQt5.QtWidgets import QWidget#, QToolTip
from PyQt5.QtGui import QPainter, QColor, QPaintEvent#, QMouseEvent
import datetime
import sqlite3
from typing import List, Tuple
from .db import DB_PATH
from .session import get_current_session

ALERT_SESSION_MINUTES: int = 30

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
            self.segments = [(0, 24*3600, "inactive")]
            self.update()
            return

        self.segments = []
        last_ts = since
        last_state = "inactive"

        for ts_str, typ in rows:
            ts = datetime.datetime.fromisoformat(ts_str)
            # Determine state
            state = "inactive" if typ in ("idle_start", "screen_off") else "active"
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
            session_start_x = int((start_ts % (24*3600)) / (24*3600) * width)
            session_w = max(2, int(session_sec / (24*3600) * width))
            session_color = QColor("yellow") if session_sec / 60 < ALERT_SESSION_MINUTES else QColor("red")
            painter.fillRect(session_start_x, 0, session_w, height, session_color)

        painter.end()

    # def mouseMoveEvent(self, a0: QMouseEvent | None = None) -> None:
    #     if a0 is None:
    #         return
    #     width = self.width()
    #     pos_sec = a0.x() / width * 24*3600
    #     for start_sec, end_sec, state in self.segments:
    #         if start_sec <= pos_sec <= end_sec:
    #             duration_sec = end_sec - start_sec
    #             h, rem = divmod(int(duration_sec), 3600)
    #             m, s = divmod(rem, 60)
    #             QToolTip.showText(a0.globalPos(), f"{state.capitalize()}: {h:02d}:{m:02d}:{s:02d}\n{start_sec:.0f}-{end_sec:.0f}")
    #             return
    #     QToolTip.hideText()

    # def mousePressEvent(self, a0: QMouseEvent | None = None) -> None:
    #     """Debug: show exact start/end timestamp for clicked segment."""
    #     width = self.width()
    #     pos_sec = a0.x() / width * 24*3600
    #     for start_sec, end_sec, state in self.segments:
    #         if start_sec <= pos_sec <= end_sec:
    #             QToolTip.showText(a0.globalPos(), f"DEBUG: {state}\nstart={start_sec:.0f}s end={end_sec:.0f}s")
    #             return

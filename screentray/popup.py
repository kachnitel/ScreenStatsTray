from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton#, QToolTip
from PyQt5.QtCore import QTimer
# from PyQt5.QtGui import QPainter, QColor, QMouseEvent, QPaintEvent
import datetime
# import time
from typing import List, Tuple#, Optional
import sqlite3
from .activity_bar import ActivityBar

from .db import query_totals, query_top_apps, DB_PATH
# from .session import current_session_seconds

ALERT_SESSION_MINUTES: int = 30


# --- session calculations ---
def get_current_session() -> Tuple[float, float]:
    """
    Return start timestamp and duration (seconds) of the current session.
    Current session = time since last 'idle_end' or 'screen_on' until now,
    0 if currently idle or screen off.
    """
    now = datetime.datetime.now()
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT timestamp, type
            FROM events
            WHERE type IN ('idle_end','screen_on')
            ORDER BY id DESC
            LIMIT 1
        """)
        row = cur.fetchone()
        if not row:
            return 0, 0
        start = datetime.datetime.fromisoformat(row[0])

        # check if currently idle or screen off
        cur.execute("SELECT type FROM events ORDER BY id DESC LIMIT 1")
        last_type = cur.fetchone()[0]
        if last_type in ("idle_start", "screen_off"):
            return 0, 0

        duration = (now - start).total_seconds()
        return start.timestamp(), duration


def get_last_break_seconds() -> float:
    """Return duration of last idle period, including ongoing idle."""
    now = datetime.datetime.now()
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT prev.timestamp, curr.timestamp, curr.type
            FROM events AS curr
            JOIN events AS prev ON prev.id = curr.id - 1
            WHERE prev.type='idle_start' AND curr.type IN ('idle_end','idle_start')
            ORDER BY curr.id DESC
            LIMIT 1
        """)
        row = cur.fetchone()
        if not row:
            return 0
        start, end, curr_type = row
        start_dt = datetime.datetime.fromisoformat(start)
        if curr_type == "idle_end":
            end_dt = datetime.datetime.fromisoformat(end)
        else:
            end_dt = now  # still idle
        return (end_dt - start_dt).total_seconds()


class StatsPopup(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.date: datetime.date = datetime.date.today()
        self.setWindowTitle("ScreenTracker Stats")
        self.main_layout: QVBoxLayout = QVBoxLayout()
        self.setLayout(self.main_layout)

        # Session + last break
        self.label: QLabel = QLabel()
        self.main_layout.addWidget(self.label)

        # 24h activity graph
        self.activity_bar: ActivityBar = ActivityBar()
        self.main_layout.addWidget(self.activity_bar)

        # Navigation
        nav: QHBoxLayout = QHBoxLayout()
        self.prev_btn: QPushButton = QPushButton("← Previous")
        self.prev_btn.clicked.connect(self.prev_day)
        self.next_btn: QPushButton = QPushButton("Next →")
        self.next_btn.clicked.connect(self.next_day)
        nav.addWidget(self.prev_btn)
        nav.addWidget(self.next_btn)
        self.main_layout.addLayout(nav)

        # Auto-refresh timer for session & graph
        self.timer: QTimer = QTimer()
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1000)

        self.refresh()

    def refresh(self) -> None:
        totals: dict[str, float] = query_totals(self.date.isoformat())
        apps: List[Tuple[str, float]] = query_top_apps(self.date.isoformat())

        # Current session
        _, session_sec = get_current_session()
        h_s, rem = divmod(int(session_sec), 3600)
        m_s, s_s = divmod(rem, 60)
        session_time: str = f"{h_s:02d}:{m_s:02d}:{s_s:02d}"

        # Last break
        last_break_sec: float = get_last_break_seconds()
        last_break_from: str = ""
        last_break_to: str = ""
        if last_break_sec > 0:
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT prev.timestamp, curr.timestamp, curr.type
                    FROM events AS curr
                    JOIN events AS prev ON prev.id = curr.id - 1
                    WHERE prev.type='idle_start' AND curr.type IN ('idle_end','idle_start')
                    ORDER BY curr.id DESC
                    LIMIT 1
                """)
                row = cur.fetchone()
                if row:
                    start_dt = datetime.datetime.fromisoformat(row[0])
                    if row[2] == "idle_end":
                        end_dt = datetime.datetime.fromisoformat(row[1])
                    else:
                        end_dt = datetime.datetime.now()
                    last_break_from = start_dt.strftime("%H:%M:%S")
                    last_break_to = end_dt.strftime("%H:%M:%S")

            h_b, rem = divmod(int(last_break_sec), 3600)
            m_b, s_b = divmod(rem, 60)
            last_break_time: str = f"{h_b:02d}:{m_b:02d}:{s_b:02d}"
        else:
            last_break_time = "–"
            last_break_from = "-"
            last_break_to = "-"

        # Build HTML
        html: str = f"""
        <div style="text-align:center; margin-bottom:10px;">
            <span style="font-size:10pt; color:gray;">Current session</span><br>
            <span style="font-size:18pt; font-weight:bold;">{session_time}</span><br>
            <span style="font-size:10pt; color:gray;">Last break</span><br>
            <span style="font-size:14pt;">{last_break_time}</span><br>
            <span style="font-size:8pt;">({last_break_from} - {last_break_to})</span>
        </div>
        <hr>
        <b>{self.date}</b><br>
        """

        for state in ["active", "inactive"]:
            sec: float = totals.get(state, 0)
            h, m, s = int(sec // 3600), int((sec % 3600) // 60), int(sec % 60)
            html += f"{state.capitalize()}: {h:02d}:{m:02d}:{s:02d}<br>"

        html += "<br><b>Top apps:</b><br>"
        for app, sec in apps:
            h, m, s = int(sec // 3600), int((sec % 3600) // 60), int(sec % 60)
            html += f"{app}: {h:02d}:{m:02d}:{s:02d}<br>"

        self.label.setText(html)
        self.activity_bar.update_segments()


    def prev_day(self) -> None:
        self.date -= datetime.timedelta(days=1)
        self.refresh()

    def next_day(self) -> None:
        self.date += datetime.timedelta(days=1)
        self.refresh()

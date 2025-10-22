from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton
import datetime
from typing import List, Tuple
from .db import query_totals, query_top_apps
from .session import current_session_seconds


class StatsPopup(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.date: datetime.date = datetime.date.today()
        self.setWindowTitle("ScreenTracker Stats")
        self.main_layout: QVBoxLayout = QVBoxLayout()
        self.setLayout(self.main_layout)

        self.label: QLabel = QLabel()
        self.main_layout.addWidget(self.label)

        # Navigation
        nav: QHBoxLayout = QHBoxLayout()
        self.prev_btn: QPushButton = QPushButton("← Previous")
        self.prev_btn.clicked.connect(self.prev_day)
        self.next_btn: QPushButton = QPushButton("Next →")
        self.next_btn.clicked.connect(self.next_day)
        nav.addWidget(self.prev_btn)
        nav.addWidget(self.next_btn)
        self.main_layout.addLayout(nav)

        self.refresh()

    def refresh(self) -> None:
        totals: dict[str, float] = query_totals(self.date.isoformat())
        apps: List[Tuple[str, float]] = query_top_apps(self.date.isoformat())

        # Current session
        session_sec: float = current_session_seconds()
        h_s, rem = divmod(int(session_sec), 3600)
        m_s, s_s = divmod(rem, 60)
        session_time: str = f"{h_s:02d}:{m_s:02d}:{s_s:02d}"

        # Build HTML
        html: str = f"""
        <div style="text-align:center; margin-bottom:10px;">
            <span style="font-size:10pt; color:gray;">Current session</span><br>
            <span style="font-size:18pt; font-weight:bold;">{session_time}</span>
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

    def prev_day(self) -> None:
        self.date -= datetime.timedelta(days=1)
        self.refresh()

    def next_day(self) -> None:
        self.date += datetime.timedelta(days=1)
        self.refresh()

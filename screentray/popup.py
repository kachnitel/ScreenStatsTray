from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton
import datetime
from .db import query_totals, query_top_apps

class StatsPopup(QWidget):
    def __init__(self):
        super().__init__()
        self.date = datetime.date.today()
        self.setWindowTitle("ScreenTracker Stats")
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.label = QLabel()
        self.layout.addWidget(self.label)

        # Navigation
        nav = QHBoxLayout()
        self.prev_btn = QPushButton("← Previous")
        self.prev_btn.clicked.connect(self.prev_day)
        self.next_btn = QPushButton("Next →")
        self.next_btn.clicked.connect(self.next_day)
        nav.addWidget(self.prev_btn)
        nav.addWidget(self.next_btn)
        self.layout.addLayout(nav)

        self.refresh()

    def refresh(self):
        totals = query_totals(self.date.isoformat())
        apps = query_top_apps(self.date.isoformat())

        text = f"<b>{self.date}</b><br>"
        for state in ["active", "inactive"]:
            sec = totals.get(state, 0)
            h, m, s = int(sec//3600), int((sec%3600)//60), int(sec%60)
            text += f"{state.capitalize()}: {h:02d}:{m:02d}:{s:02d}<br>"
        text += "<br><b>Top apps:</b><br>"
        for app, sec in apps:
            h, m, s = int(sec//3600), int((sec%3600)//60), int(sec%60)
            text += f"{app}: {h:02d}:{m:02d}:{s:02d}<br>"
        self.label.setText(text)

    def prev_day(self):
        self.date -= datetime.timedelta(days=1)
        self.refresh()

    def next_day(self):
        self.date += datetime.timedelta(days=1)
        self.refresh()

from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction, QApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QTimer, QDate
from .popup import StatsPopup
from .db import query_totals
from .config import UPDATE_INTERVAL_MS

class TrayApp(QSystemTrayIcon):
    def __init__(self, icon: QIcon):
        super().__init__(icon)
        self.menu = QMenu()
        self.popup = StatsPopup()

        show_action = QAction("Show Stats")
        show_action.triggered.connect(self.popup.show)
        self.menu.addAction(show_action)

        quit_action = QAction("Quit")
        quit_action.triggered.connect(QApplication.instance().quit)
        self.menu.addAction(quit_action)

        self.setContextMenu(self.menu)
        self.setToolTip("ScreenTracker")
        self.show()

        # auto-refresh tooltip
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_tooltip)
        self.timer.start(UPDATE_INTERVAL_MS)
        self.update_tooltip()

    def update_tooltip(self):
        totals = query_totals(QDate.currentDate().toString("yyyy-MM-dd"))
        active_sec = totals.get("active",0)
        inactive_sec = totals.get("inactive",0)
        h, m, s = int(active_sec//3600), int((active_sec%3600)//60), int(active_sec%60)
        h2, m2, s2 = int(inactive_sec//3600), int((inactive_sec%3600)//60), int(inactive_sec%60)
        self.setToolTip(f"Active: {h:02d}:{m:02d}:{s:02d}  Inactive: {h2:02d}:{m2:02d}:{s2:02d}")

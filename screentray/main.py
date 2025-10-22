#!/usr/bin/env python3
import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from .tray import TrayApp

if __name__ == "__main__":
    app = QApplication(sys.argv)
    tray_icon = TrayApp(QIcon.fromTheme("preferences-system-time"))
    sys.exit(app.exec_())

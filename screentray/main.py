#!/usr/bin/env python3
import sys
from PyQt5.QtWidgets import QApplication
from .tray import TrayApp

if __name__ == "__main__":
    app = QApplication(sys.argv)
    tray_icon = TrayApp()
    sys.exit(app.exec_())

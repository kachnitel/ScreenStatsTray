#!/usr/bin/env python3
"""
Main entrypoint for the ScreenTray UI application.
"""
import sys
from PyQt5.QtWidgets import QApplication
from .tray import TrayApp
from ..db import ensure_db_exists

if __name__ == "__main__":
    ensure_db_exists()
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    tray_icon = TrayApp()
    sys.exit(app.exec_())

#!/usr/bin/env python3
"""
Main entrypoint for the ScreenTray UI application.
"""
import sys
from PyQt5.QtWidgets import QApplication
from .ui.tray import TrayApp
from .db import ensure_db_exists

if __name__ == "__main__":
    # Ensure DB schema exists before launching UI
    # This is safe to run every time.
    ensure_db_exists()

    app = QApplication(sys.argv)
    tray_icon = TrayApp()
    sys.exit(app.exec_())

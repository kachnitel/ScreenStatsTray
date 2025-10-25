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
    ensure_db_exists()

    # 1. Initialize the global QApplication instance
    app = QApplication(sys.argv)

    # 2. CRUCIAL: Prevent the application from quitting when any popup window closes.
    # This keeps the tray icon alive.
    app.setQuitOnLastWindowClosed(False)

    # 3. Instantiate TrayApp (which creates the icon and timers)
    # The TrayApp constructor no longer creates its own QApplication.
    tray_icon = TrayApp()

    # 4. Start the Qt event loop
    sys.exit(app.exec_())
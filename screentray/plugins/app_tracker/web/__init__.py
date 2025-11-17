"""
screentray/plugins/app_tracker/web/__init__.py

Web interface integration - main entry point.
"""
import os
from typing import Any, Dict
# from flask import jsonify


class AppTrackerWeb:
    """Handles web interface integration for app tracker."""

    def __init__(self) -> None:
        from ..service import AppUsageService
        self.service = AppUsageService()
        self.web_dir = os.path.dirname(__file__)

    def _read_file(self, filename: str) -> str:
        """Read a file from the web directory."""
        filepath = os.path.join(self.web_dir, filename)
        try:
            with open(filepath, 'r') as f:
                return f.read()
        except FileNotFoundError:
            print(f"Warning: Could not find {filepath}")
            return ""

    # Public API for plugin system

    def get_routes(self) -> list[tuple[str, Any]]:
        """Return Flask routes."""
        from .routes import AppUsageRoutes
        routes_handler = AppUsageRoutes(self.service)
        return [
            ("/api/app_usage/today", routes_handler.api_today),
            ("/api/app_usage/top_apps", routes_handler.api_top_apps),
        ]

    def get_content(self) -> Dict[str, Any]:
        """Return web UI content for injection."""
        return {
            'slots': {
                # 'overview_bottom': self._read_file('templates/overview.html'),
                'daily_bottom': self._read_file('templates/daily.html'),
            },
            'javascript': self._read_file('static/app_usage.js'),
            'new_tab': {
                'id': 'apps',
                'title': 'Apps',
                'content': self._read_file('templates/apps_tab.html'),
            }
        }

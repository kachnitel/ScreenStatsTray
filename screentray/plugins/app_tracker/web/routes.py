"""
screentray/plugins/app_tracker/web/routes.py

Flask route handlers for app usage API.
"""
from flask import jsonify, request
from typing import Any
import datetime


class AppUsageRoutes:
    """Flask route handlers for app tracker."""

    def __init__(self, service: Any) -> None:
        self.service = service

    def api_today(self) -> Any:
        """Get today's app usage."""
        try:
            usage = self.service.get_app_usage_today()
            # Convert to list of dicts for JSON
            data = [
                {"app": app, "seconds": secs}
                for app, secs in sorted(usage.items(), key=lambda x: x[1], reverse=True)
            ]
            return jsonify(data)
        except Exception as e:
            print(f"Error in api_today: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500

    def api_top_apps(self) -> Any:
        """Get top apps for a date range."""
        try:
            # Parse date parameters
            start_str = request.args.get('start')
            end_str = request.args.get('end')
            limit = int(request.args.get('limit', '10'))

            if not start_str or not end_str:
                return jsonify({"error": "Missing start or end parameter"}), 400

            try:
                start = datetime.datetime.fromisoformat(start_str)
                end = datetime.datetime.fromisoformat(end_str)
            except ValueError:
                return jsonify({"error": "Invalid date format"}), 400

            top_apps = self.service.get_top_apps(start, end, limit)
            data = [
                {"app": app, "seconds": secs}
                for app, secs in top_apps
            ]
            return jsonify(data)
        except Exception as e:
            print(f"Error in api_top_apps: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500

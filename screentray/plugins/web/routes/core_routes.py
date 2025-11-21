"""
Core API routes for activity data.
"""
from flask import Flask, jsonify, request
import sqlite3
import datetime
import os
from typing import Any, List, Dict, Optional
from ....services import StatsService, ActivityService


DB_PATH = os.path.expanduser("~/.local/share/screentracker.db")

def register_routes(app: Flask) -> None:
    """Register core API routes with Flask app."""

    stats_service = StatsService()
    activity_service = ActivityService()

    @app.route("/api/events")
    def api_events() -> Any: # pyright: ignore[reportUnusedFunction]
        try:
            return jsonify(list_events(
                limit=int(request.args.get("limit", "200")),
                offset=int(request.args.get("offset", "0")),
                query=request.args.get("q")
            ))
        except FileNotFoundError as e:
            return jsonify({"error": str(e)}), 404

    @app.route("/api/periods")
    def api_periods() -> Any: # pyright: ignore[reportUnusedFunction]
        try:
            hours = int(request.args.get("hours", "24"))
            return jsonify(activity_service.get_detailed_activity_periods(hours))
        except FileNotFoundError as e:
            return jsonify({"error": str(e)}), 404

    @app.route("/api/stats/<day_str>")
    def api_daily_stats(day_str: str) -> Any: # pyright: ignore[reportUnusedFunction]
        try:
            return jsonify(get_daily_stats(stats_service, day_str))
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 400

    @app.route("/api/hourly/24h")
    def api_hourly_24h() -> Any: # pyright: ignore[reportUnusedFunction]
        """Get hourly breakdown for last 24 hours."""
        try:
            return jsonify(activity_service.get_hourly_breakdown_24h())
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500

    @app.route("/api/daily/range")
    def api_daily_range() -> Any: # pyright: ignore[reportUnusedFunction]
        """Get daily totals for date range."""
        try:
            start_str = request.args.get('start')
            end_str = request.args.get('end')

            if not start_str or not end_str:
                return jsonify({"error": "Missing start or end parameter"}), 400

            start_date = datetime.date.fromisoformat(start_str)
            end_date = datetime.date.fromisoformat(end_str)

            return jsonify(activity_service.get_daily_totals_range(start_date, end_date))
        except ValueError as e:
            return jsonify({"error": f"Invalid date format: {e}"}), 400
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500


def open_conn() -> sqlite3.Connection:
    """Open database connection."""
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"DB not found at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn


def list_events(limit: int = 200, offset: int = 0, query: Optional[str] = None) -> List[Dict[str, Any]]:
    """List recent events with optional search."""
    # This function is UI-specific (pagination/search) and can keep its own DB logic.
    with open_conn() as conn:
        cur = conn.cursor()
        if query:
            q = f"%{query}%"
            cur.execute("""
                SELECT id, timestamp, type, detail
                FROM events
                WHERE type LIKE ? OR detail LIKE ?
                ORDER BY timestamp DESC LIMIT ? OFFSET ?
            """, (q, q, limit, offset))
        else:
            cur.execute("""
                SELECT id, timestamp, type, detail
                FROM events ORDER BY timestamp DESC LIMIT ? OFFSET ?
            """, (limit, offset))
        return [dict(r) for r in cur.fetchall()]




def get_daily_stats(stats_service: StatsService, day_str: str) -> Dict[str, Any]:
    """Get statistics for a specific day."""
    day = datetime.date.fromisoformat(day_str)
    start = datetime.datetime.combine(day, datetime.time.min)
    end = datetime.datetime.combine(day, datetime.time.max)

    # This UI-specific count query is fine to keep here.
    with open_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT type, COUNT(*) as count
            FROM events
            WHERE timestamp >= ? AND timestamp <= ?
            GROUP BY type
        """, (start.isoformat(), end.isoformat()))

        event_counts = {row["type"]: row["count"] for row in cur.fetchall()}

    # This part already correctly uses the service
    totals = stats_service.get_daily_totals(day_str)
    active_sec = totals.get("active", 0.0)
    inactive_sec = totals.get("inactive", 0.0)

    return {
        "date": day_str,
        "event_counts": event_counts,
        "active_seconds": active_sec,
        "inactive_seconds": inactive_sec,
        "total_seconds": active_sec + inactive_sec
    }

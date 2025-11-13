"""
Core API routes for activity data.
"""
from flask import Flask, jsonify, request
import sqlite3
import datetime
import os
from typing import Any, List, Dict, Optional
from ....services import StatsService


DB_PATH = os.path.expanduser("~/.local/share/screentracker.db")
INACTIVE_TYPES = ("idle_start", "screen_off")
ACTIVE_TYPES = ("idle_end", "screen_on")


def register_routes(app: Flask) -> None:
    """Register core API routes with Flask app."""

    stats_service = StatsService()
    # activity_service = ActivityService()

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
            # REVIEW: This route uses its own custom logic from get_periods_with_events
            return jsonify(get_periods_with_events(hours))
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


def open_conn() -> sqlite3.Connection:
    """Open database connection."""
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"DB not found at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn


def list_events(limit: int = 200, offset: int = 0, query: Optional[str] = None) -> List[Dict[str, Any]]:
    """List recent events with optional search."""
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

#REVIEW: Deprecate
def get_periods_with_events(hours: int = 24) -> List[Dict[str, Any]]:
    """Get activity periods with all events within last 24hr period."""
    now = datetime.datetime.now()
    since = now - datetime.timedelta(hours=hours)

    with open_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, timestamp, type, detail
            FROM events
            WHERE timestamp >= ?
            ORDER BY id ASC
        """, (since.isoformat(),))
        rows = cur.fetchall()

    if not rows:
        return [{
            "start": since.isoformat(),
            "end": now.isoformat(),
            "state": "inactive",
            "duration_sec": (now - since).total_seconds(),
            "trigger_event": None,
            "events": []
        }]

    periods: List[Dict[str, Any]] = []
    last_ts = since
    last_state = "inactive"
    current_events: List[Dict[str, Any]] = []
    last_event_ts = since
    gap_threshold = 600  # 10 minutes

    for r in rows:
        ts = datetime.datetime.fromisoformat(r["timestamp"])
        typ = r["type"]

        event_dict: Dict[str, Any] = {
            "id": r["id"],
            "timestamp": r["timestamp"],
            "type": typ,
            "detail": r["detail"] or ""
        }

        # Check for gaps
        gap = (ts - last_event_ts).total_seconds()
        if gap > gap_threshold and last_state == "active":
            periods.append({
                "start": last_ts.isoformat(),
                "end": last_event_ts.isoformat(),
                "state": last_state,
                "duration_sec": (last_event_ts - last_ts).total_seconds(),
                "trigger_event": None,
                "events": current_events.copy()
            })
            periods.append({
                "start": last_event_ts.isoformat(),
                "end": ts.isoformat(),
                "state": "inactive",
                "duration_sec": gap,
                "trigger_event": {"type": "gap", "detail": f"{gap:.0f}s gap"},
                "events": []
            })
            last_ts = ts
            last_state = "inactive"
            current_events = []

        # Determine state
        if typ in INACTIVE_TYPES:
            state = "inactive"
        elif typ in ACTIVE_TYPES:
            state = "active"
        elif typ == "poll" and r["detail"]:
            if "state=active" in r["detail"]:
                state = "active"
            elif "state=inactive" in r["detail"]:
                state = "inactive"
            else:
                current_events.append(event_dict)
                last_event_ts = ts
                continue
        else:
            current_events.append(event_dict)
            last_event_ts = ts
            continue

        if state != last_state:
            periods.append({
                "start": last_ts.isoformat(),
                "end": ts.isoformat(),
                "state": last_state,
                "duration_sec": (ts - last_ts).total_seconds(),
                "trigger_event": event_dict,
                "events": current_events.copy()
            })
            current_events = [event_dict]
            last_ts = ts
            last_state = state
        else:
            current_events.append(event_dict)

        last_event_ts = ts

    # Final period
    gap = (now - last_event_ts).total_seconds()
    if gap > gap_threshold:
        if last_state == "active":
            periods.append({
                "start": last_ts.isoformat(),
                "end": last_event_ts.isoformat(),
                "state": last_state,
                "duration_sec": (last_event_ts - last_ts).total_seconds(),
                "trigger_event": None,
                "events": current_events
            })
            periods.append({
                "start": last_event_ts.isoformat(),
                "end": now.isoformat(),
                "state": "inactive",
                "duration_sec": gap,
                "trigger_event": {"type": "gap", "detail": f"{gap:.0f}s gap"},
                "events": []
            })
        else:
            periods.append({
                "start": last_ts.isoformat(),
                "end": now.isoformat(),
                "state": last_state,
                "duration_sec": (now - last_ts).total_seconds(),
                "trigger_event": None,
                "events": current_events
            })
    else:
        periods.append({
            "start": last_ts.isoformat(),
            "end": now.isoformat(),
            "state": last_state,
            "duration_sec": (now - last_ts).total_seconds(),
            "trigger_event": None,
            "events": current_events
        })

    return periods


def get_daily_stats(stats_service: StatsService, day_str: str) -> Dict[str, Any]:
    """Get statistics for a specific day."""
    day = datetime.date.fromisoformat(day_str)
    start = datetime.datetime.combine(day, datetime.time.min)
    end = datetime.datetime.combine(day, datetime.time.max)

    with open_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT type, COUNT(*) as count
            FROM events
            WHERE timestamp >= ? AND timestamp <= ?
            GROUP BY type
        """, (start.isoformat(), end.isoformat()))

        event_counts = {row["type"]: row["count"] for row in cur.fetchall()}

    # Call the StatsService to get the correct totals for the requested day.
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

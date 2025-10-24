#!/usr/bin/env python3
"""
ScreenTracker Web Interface with diagnostics.
"""

from __future__ import annotations
from flask import Flask, jsonify, request, send_file
import sqlite3, datetime, os, sys, traceback, socket
from typing import Any, List#, Tuple, Optional

APP = Flask(__name__, static_folder=".", static_url_path="")
DB_PATH = os.path.expanduser("~/.local/share/screentracker.db")
HOUR24 = datetime.timedelta(hours=24)

INACTIVE_TYPES = ("idle_start","screen_off","lid_closed","system_suspend")

# ---- Utilities ------------------------------------------------------------

def open_conn():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"DB not found at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn


def _extract_app(detail: str) -> str:
    if not detail:
        return "unknown"
    if "→" in detail:
        return detail.split("→", 1)[1].strip()
    return detail.strip()


# ---- Data Queries ---------------------------------------------------------

def list_events(limit=200, offset=0, query=None) -> List[dict]:
    with open_conn() as conn:
        cur = conn.cursor()
        if query:
            q = f"%{query}%"
            cur.execute("""
                SELECT id, timestamp, type, detail
                FROM events
                WHERE type LIKE ? OR detail LIKE ?
                ORDER BY id DESC LIMIT ? OFFSET ?
            """, (q, q, limit, offset))
        else:
            cur.execute("""
                SELECT id, timestamp, type, detail
                FROM events ORDER BY id DESC LIMIT ? OFFSET ?
            """, (limit, offset))
        return [dict(r) for r in cur.fetchall()]

def merged_periods_past_24h() -> list[dict]:
    """Merge consecutive events into active/inactive periods for the past 24h."""
    now = datetime.datetime.now()
    since = now - datetime.timedelta(hours=24)
    with open_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT timestamp, type, id FROM events WHERE timestamp >= ? ORDER BY id ASC", (since.isoformat(),))
        rows = cur.fetchall()

    # No events → single inactive period
    if not rows:
        return [{"start": since.isoformat(), "end": now.isoformat(), "state": "inactive"}]

    periods: list[Any] = []
    last_ts = since
    last_state = "inactive"

    for r in rows:
        ts = datetime.datetime.fromisoformat(r["timestamp"])
        typ = r["type"]
        state = "inactive" if typ in INACTIVE_TYPES else "active"
        if state != last_state:
            periods.append((last_ts, ts, last_state))
            last_ts = ts
            last_state = state
        # else continue, merge equal states

    # Final period up to now
    periods.append((last_ts, now, last_state))
    return [{"start": s.isoformat(), "end": e.isoformat(), "state": st} for s, e, st in periods]

def period_app_summary(start_iso: str, end_iso: str) -> List[dict]:
    start_dt, end_dt = datetime.datetime.fromisoformat(start_iso), datetime.datetime.fromisoformat(end_iso)
    with open_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, timestamp, detail FROM events
            WHERE timestamp >= ? AND timestamp <= ? AND type='app_switch'
            ORDER BY id ASC
        """, (start_dt.isoformat(), end_dt.isoformat()))
        rows = cur.fetchall()

    apps, prev_app, prev_ts = {}, None, start_dt
    if rows:
        first_id = rows[0]["id"]
        with open_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT detail FROM events WHERE type='app_switch' AND id < ? ORDER BY id DESC LIMIT 1", (first_id,))
            row = cur.fetchone()
            if row:
                prev_app = _extract_app(row["detail"])

    for r in rows:
        ts = datetime.datetime.fromisoformat(r["timestamp"])
        app = _extract_app(r["detail"])
        if prev_app:
            apps[prev_app] = apps.get(prev_app, 0) + max(0, (ts - prev_ts).total_seconds())
        prev_app, prev_ts = app, ts

    if prev_app:
        apps[prev_app] = apps.get(prev_app, 0) + max(0, (end_dt - prev_ts).total_seconds())

    return [{"app": a, "seconds": int(s)} for a, s in sorted(apps.items(), key=lambda kv: kv[1], reverse=True)]


# ---- Flask Routes ---------------------------------------------------------

@APP.route("/api/events")
def api_events():
    try:
        return jsonify(list_events(
            limit=int(request.args.get("limit", "200")),
            offset=int(request.args.get("offset", "0")),
            query=request.args.get("q")
        ))
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404


@APP.route("/api/periods")
def api_periods():
    try:
        return jsonify(merged_periods_past_24h())
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404


@APP.route("/api/periods/<start_iso>/<end_iso>/apps")
def api_period_apps(start_iso, end_iso):
    try:
        return jsonify(period_app_summary(start_iso, end_iso))
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 400


@APP.route("/")
def index():
    return send_file(os.path.join(os.path.dirname(__file__), "web_static_index.html"))


# ---- Diagnostics / Startup ------------------------------------------------

def find_free_port(preferred=5050):
    """Try preferred port, fall back if unavailable."""
    for port in (preferred, 8080, 5000):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("No free port found (5050/8080/5000 busy)")


def main():
    print("=== ScreenTracker Web ===")
    print(f"Python: {sys.executable}")
    print(f"Flask:  {APP.import_name}")
    print(f"DB path: {DB_PATH}")

    port = find_free_port()
    print(f"Starting server on http://127.0.0.1:{port} ...", flush=True)

    try:
        APP.run(host="127.0.0.1", port=port, debug=False)
    except Exception:
        print("!!! Flask failed to start:")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

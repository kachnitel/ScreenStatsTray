#!/usr/bin/env python3
"""
ScreenTracker Web Interface with plugin support.
"""

from __future__ import annotations
from flask import Flask, jsonify, request, Response
import sqlite3, datetime, os, sys, traceback, socket
from typing import Any, List

# Import plugin system
sys.path.insert(0, os.path.expanduser("~/.local/lib"))
from screentray.plugins import PluginManager

APP = Flask(__name__, static_folder=".", static_url_path="")
DB_PATH = os.path.expanduser("~/.local/share/screentracker.db")

INACTIVE_TYPES = ("idle_start", "screen_off")
ACTIVE_TYPES = ("idle_end", "screen_on")

# Initialize plugin system
plugin_manager = PluginManager()
plugin_manager.discover_plugins()

# Register plugin routes
for plugin in plugin_manager.plugins.values():
    for route, handler in plugin.get_web_routes():
        APP.add_url_rule(route, view_func=handler, methods=['GET', 'POST'])
        print(f"Registered plugin route: {route}")

# ---- Utilities ------------------------------------------------------------

def open_conn() -> sqlite3.Connection:
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"DB not found at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn


# ---- Data Queries ---------------------------------------------------------

def list_events(limit: int = 200, offset: int = 0, query: str | None = None) -> List[dict[str, Any]]:
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


def get_periods_with_events(hours: int = 24) -> list[dict[str, Any]]:
    """Get periods with all events that occurred within each period."""
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

    periods: list[dict[str, Any]] = []
    last_ts = since
    last_state = "inactive"
    current_events: list[dict[str, Any]] = []
    last_event_ts = since

    # Idle threshold in seconds
    gap_threshold = 600  # 10 minutes

    for r in rows:
        ts = datetime.datetime.fromisoformat(r["timestamp"])
        typ = r["type"]

        event_dict: dict[str, Any] = {
            "id": r["id"],
            "timestamp": r["timestamp"],
            "type": typ,
            "detail": r["detail"] or ""
        }

        # Check for gaps
        gap = (ts - last_event_ts).total_seconds()
        if gap > gap_threshold and last_state == "active":
            # Gap detected - insert inactive period
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
            # Poll events contain state info
            if "state=active" in r["detail"]:
                state = "active"
            elif "state=inactive" in r["detail"]:
                state = "inactive"
            else:
                current_events.append(event_dict)
                last_event_ts = ts
                continue
        else:
            # Non-state events
            current_events.append(event_dict)
            last_event_ts = ts
            continue

        if state != last_state:
            # State change - close previous period
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
            # Same state - add event to current period
            current_events.append(event_dict)

        last_event_ts = ts

    # Check for final gap
    gap = (now - last_event_ts).total_seconds()
    if gap > gap_threshold:
        # Large gap at end - force inactive
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
            # Already inactive, extend to now
            periods.append({
                "start": last_ts.isoformat(),
                "end": now.isoformat(),
                "state": last_state,
                "duration_sec": (now - last_ts).total_seconds(),
                "trigger_event": None,
                "events": current_events
            })
    else:
        # Normal final period
        periods.append({
            "start": last_ts.isoformat(),
            "end": now.isoformat(),
            "state": last_state,
            "duration_sec": (now - last_ts).total_seconds(),
            "trigger_event": None,
            "events": current_events
        })

    return periods


def get_daily_stats(day_str: str) -> dict[str, Any]:
    """Get statistics for a specific day (YYYY-MM-DD)."""
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

    # Calculate active/inactive time
    periods = get_periods_with_events(hours=24)
    active_sec = sum(p["duration_sec"] for p in periods if p["state"] == "active" and
                     start.isoformat() <= p["start"] <= end.isoformat())
    inactive_sec = sum(p["duration_sec"] for p in periods if p["state"] == "inactive" and
                       start.isoformat() <= p["start"] <= end.isoformat())

    return {
        "date": day_str,
        "event_counts": event_counts,
        "active_seconds": active_sec,
        "inactive_seconds": inactive_sec,
        "total_seconds": active_sec + inactive_sec
    }


# ---- Flask Routes ---------------------------------------------------------

@APP.route("/api/events")
def api_events() -> Any:
    try:
        return jsonify(list_events(
            limit=int(request.args.get("limit", "200")),
            offset=int(request.args.get("offset", "0")),
            query=request.args.get("q")
        ))
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404


@APP.route("/api/periods")
def api_periods() -> Any:
    try:
        hours = int(request.args.get("hours", "24"))
        return jsonify(get_periods_with_events(hours))
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404


@APP.route("/api/stats/<day_str>")
def api_daily_stats(day_str: str) -> Any:
    try:
        return jsonify(get_daily_stats(day_str))
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 400


@APP.route("/")
def index() -> Response:
    """Serve index.html with plugin content injected."""
    index_path = os.path.join(os.path.dirname(__file__), "web_static_index.html")

    with open(index_path, 'r') as f:
        html = f.read()

    # Collect plugin content
    plugin_slots: dict[str, list[str]] = {}
    plugin_js: list[str] = []
    plugin_tabs: list[dict[str, Any]] = []

    for plugin in plugin_manager.plugins.values():
        try:
            content = plugin.get_web_content()

            # Collect slot content
            for slot_name, slot_html in content.get('slots', {}).items():
                if slot_name not in plugin_slots:
                    plugin_slots[slot_name] = []
                plugin_slots[slot_name].append(slot_html)

            # Collect JavaScript
            if content.get('javascript'):
                plugin_js.append(content['javascript'])

            # Collect new tabs
            if content.get('new_tab'):
                plugin_tabs.append(content['new_tab'])

        except Exception as e:
            print(f"Error loading plugin content: {e}")
            traceback.print_exc()

    # Inject slot content
    for slot_name, slot_contents in plugin_slots.items():
        slot_marker = f"<!-- CONTENT_SLOT: {slot_name} -->"
        combined_html = '\n'.join(slot_contents)
        html = html.replace(slot_marker, combined_html)

    # Inject new tabs into navigation
    if plugin_tabs:
        tab_nav_html = ''
        tab_content_html = ''

        for tab in plugin_tabs:
            tab_id = tab['id']
            tab_title = tab['title']
            tab_nav_html += f'<li><a href="#" role="button" data-tab="{tab_id}">{tab_title}</a></li>\n'
            tab_content_html += f'<section class="tab-content" id="{tab_id}">\n{tab["content"]}\n</section>\n'

        # Inject navigation items before closing </ul>
        html = html.replace('</ul>\n</nav>', f'{tab_nav_html}</ul>\n</nav>')

        # Inject content sections before closing </main>
        html = html.replace('</main>', f'{tab_content_html}</main>')

    # Inject JavaScript before closing </body>
    if plugin_js:
        combined_js = '\n\n'.join(plugin_js)
        html = html.replace('</body>', f'<script>\n// Plugin JavaScript\n{combined_js}\n</script>\n</body>')

    return Response(html, mimetype='text/html')


# ---- Diagnostics / Startup ------------------------------------------------

def find_free_port(preferred: int = 5050) -> int:
    """Try preferred port, fall back if unavailable."""
    for port in (preferred, 8080, 5000):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("No free port found (5050/8080/5000 busy)")


def main() -> None:
    print("=== ScreenTracker Web ===")
    print(f"Python: {sys.executable}")
    print(f"Flask:  {APP.import_name}")
    print(f"DB path: {DB_PATH}")
    print(f"Discovered {len(plugin_manager.plugins)} plugins")

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

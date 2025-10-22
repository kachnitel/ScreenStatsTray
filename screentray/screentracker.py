#!/usr/bin/env python3
import os
import time
import subprocess
import sqlite3
import datetime
from typing import Optional, Tuple, Any

DB_PATH: str = os.path.expanduser("~/.local/share/screentracker.db")
LOG_INTERVAL: int = 2
IDLE_THRESHOLD_MS: int = 300_000
SWITCH_MIN_DURATION: int = 5  # seconds

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def db_exec(query: str, params: Tuple[Any, ...] = ()) -> None:
    """Execute a SQL query and commit."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, timestamp TEXT, type TEXT, detail TEXT)"
        )
        conn.execute(query, params)
        conn.commit()


def log_event(type_: str, detail: str = "") -> None:
    """Log an event to the database and stdout."""
    ts: str = datetime.datetime.now().isoformat(timespec="seconds")
    db_exec("INSERT INTO events (timestamp, type, detail) VALUES (?, ?, ?)", (ts, type_, detail))
    print(f"[{ts}] {type_} {detail}")


def get_idle_ms() -> int:
    """Return the current idle time in milliseconds."""
    return int(subprocess.check_output(["xprintidle"]).strip())


def get_active_window_name() -> Optional[str]:
    """Return the WM_CLASS name of the currently active window."""
    try:
        wid: bytes = subprocess.check_output(["xdotool", "getactivewindow"]).strip()
        name: str = subprocess.check_output(["xprop", "-id", wid, "WM_CLASS"]).decode()
        return name.split('"')[1]
    except subprocess.CalledProcessError:
        return None


def is_screen_on() -> bool:
    """Return True if monitor is on, False otherwise."""
    out: str = subprocess.check_output(["xset", "-q"]).decode()
    return "Monitor is On" in out


def main() -> None:
    last_app: Optional[str] = None
    last_app_time: float = time.time()
    was_idle: bool = False
    was_on: bool = is_screen_on()
    log_event("screen_on" if was_on else "screen_off")

    while True:
        idle_ms: int = get_idle_ms()
        idle: bool = idle_ms > IDLE_THRESHOLD_MS

        # Screen state
        on: bool = is_screen_on()
        if on != was_on:
            log_event("screen_on" if on else "screen_off")
            was_on = on

        # Idle state
        if idle != was_idle:
            if idle:
                log_event("idle_start", f"idle > {IDLE_THRESHOLD_MS / 1000}s")
            else:
                log_event("idle_end")
            was_idle = idle

        # Foreground app
        if on and not idle:
            app: Optional[str] = get_active_window_name()
            now: float = time.time()
            if app and app != last_app:
                if last_app and now - last_app_time > SWITCH_MIN_DURATION:
                    log_event("app_switch", f"{last_app} → {app}")
                last_app = app
                last_app_time = now

        time.sleep(LOG_INTERVAL)

if __name__ == "__main__":
    main()

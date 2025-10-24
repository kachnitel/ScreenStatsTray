#!/usr/bin/env python3
import os
import time
import subprocess
import sqlite3
import datetime
from typing import Optional, Tuple, Any
from .config import *

try:
    import dbus # pyright: ignore[reportMissingTypeStubs]
    import dbus.mainloop.glib # pyright: ignore[reportMissingTypeStubs]
    from gi.repository import GLib # pyright: ignore[reportMissingTypeStubs, reportUnknownVariableType, reportAttributeAccessIssue]
    DBUS_AVAILABLE = True
except ImportError:
    DBUS_AVAILABLE = False # pyright: ignore[reportConstantRedefinition]

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

def setup_dbus_listeners() -> None:
    """Subscribe to systemd logind signals for lid/suspend/resume."""
    if not DBUS_AVAILABLE:
        return

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True) # pyright: ignore[reportUnknownMemberType, reportPossiblyUnboundVariable]
    bus = dbus.SystemBus() # pyright: ignore[reportPossiblyUnboundVariable]

    def sleep_signal_handler(suspend: bool) -> None:
        log_event("system_suspend" if suspend else "system_resume")

    bus.add_signal_receiver( # pyright: ignore[reportUnknownMemberType]
        sleep_signal_handler,
        dbus_interface="org.freedesktop.login1.Manager",
        signal_name="PrepareForSleep"
    )

    # Listen to PropertiesChanged for lid
    def lid_signal_handler(interface: Any, changed: Any, invalidated: Any) -> None:
        if "LidClosed" in changed:
            closed: bool = changed["LidClosed"]
            log_event("lid_closed" if closed else "lid_open")

    bus.add_signal_receiver( # pyright: ignore[reportUnknownMemberType]
        lid_signal_handler,
        dbus_interface="org.freedesktop.DBus.Properties",
        signal_name="PropertiesChanged",
        path="/org/freedesktop/login1",
        arg0="org.freedesktop.login1.Manager"
    )

    # Start GLib loop in a separate thread or main thread
    from threading import Thread
    def loop() -> None:
        GLib.MainLoop().run() # pyright: ignore[reportPossiblyUnboundVariable, reportUnknownMemberType]
    Thread(target=loop, daemon=True).start()


def main() -> None:
    last_app: Optional[str] = None
    last_app_time = time.time()
    was_idle = False
    was_on = is_screen_on()
    last_event_time = time.time()
    last_activity_time = time.time()

    log_event("screen_on" if was_on else "screen_off")

    # Setup DBus listeners for suspend/lid
    setup_dbus_listeners()

    while True:
        now: float = time.time()
        idle_ms: int = get_idle_ms()
        idle: bool = idle_ms > IDLE_THRESHOLD_MS

        # Screen state handling
        on: bool = is_screen_on()
        if on != was_on:
            # Ignore spurious "screen_on" within threshold after last activity
            if on and (now - last_activity_time) < (IDLE_THRESHOLD_MS / 1000):
                pass
            else:
                log_event("screen_on" if on else "screen_off")
                was_on = on
                last_event_time = now
                if on:
                    last_activity_time = now

        # Idle detection
        if idle != was_idle:
            if idle:
                log_event("idle_start", f"idle > {IDLE_THRESHOLD_MS / 1000}s")
            else:
                log_event("idle_end")
                last_activity_time = now
            was_idle = idle
            last_event_time = now

        # Foreground window tracking
        if on and not idle:
            app: Optional[str] = get_active_window_name()
            if app and app != last_app:
                if last_app and now - last_app_time > SWITCH_MIN_DURATION:
                    log_event("app_switch", f"{last_app} → {app}")
                last_app = app
                last_app_time = now
                last_event_time = now
                last_activity_time = now

        # Fallback: no events for long period → assume inactive starting earlier
        if now - last_event_time > MAX_NO_EVENT_GAP:
            # Estimate that user became idle MAX_NO_EVENT_GAP seconds ago
            idle_start_time = datetime.datetime.fromtimestamp(now - MAX_NO_EVENT_GAP)
            db_exec(
                "INSERT INTO events (timestamp, type, detail) VALUES (?, ?, ?)",
                (idle_start_time.isoformat(timespec="seconds"), "idle_start", "no activity gap"),
            )
            print(f"[{idle_start_time.isoformat(timespec='seconds')}] idle_start (no activity gap)")
            last_event_time = now
            was_idle = True
            last_app = None

        time.sleep(LOG_INTERVAL)


if __name__ == "__main__":
    main()

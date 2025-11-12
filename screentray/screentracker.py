#!/usr/bin/env python3
"""
Background service to track user activity with event-driven plugin system.
"""
import os
import time
import subprocess
import datetime
from .config import (
    DB_PATH,
    LOG_INTERVAL,
    IDLE_THRESHOLD_MS,
    DEBUG_MODE,
    DEBUG_LOG_PATH
)
from .db import ensure_db_exists
from .db.event_repository import EventRepository
from .plugins import PluginManager

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
IDLE_THRESHOLD_SEC = IDLE_THRESHOLD_MS / 1000.0


def debug_log(message: str) -> None:
    """Write debug message to log file if debug mode is enabled."""
    if DEBUG_MODE:
        timestamp = datetime.datetime.now().isoformat(timespec='milliseconds')
        with open(DEBUG_LOG_PATH, 'a') as f:
            f.write(f"[{timestamp}] {message}\n")


def get_idle_seconds() -> float:
    """Return the current idle time in seconds."""
    try:
        idle_ms = int(subprocess.check_output(["xprintidle"]).strip())
        idle_sec = idle_ms / 1000.0
        if DEBUG_MODE:
            debug_log(f"xprintidle: {idle_ms}ms ({idle_sec:.1f}s)")
        return idle_sec
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        if DEBUG_MODE:
            debug_log(f"xprintidle error: {e}")
        return 0.0


def is_screen_on() -> bool:
    """Return True if monitor is on."""
    try:
        out = subprocess.check_output(["xset", "-q"]).decode()
        is_on = "Monitor is On" in out
        if DEBUG_MODE:
            dpms_line = [line for line in out.split('\n') if 'Monitor is' in line]
            debug_log(f"xset -q: {dpms_line[0].strip() if dpms_line else 'unknown'}")
        return is_on
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        if DEBUG_MODE:
            debug_log(f"xset error: {e}")
        return True


def get_active_window_info() -> str:
    """Get info about the currently active window for debug purposes."""
    try:
        window_id = subprocess.check_output(
            ["xdotool", "getactivewindow"],
            stderr=subprocess.DEVNULL
        ).decode().strip()

        app_name = subprocess.check_output(
            ["xdotool", "getwindowclassname", window_id],
            stderr=subprocess.DEVNULL
        ).decode().strip()

        window_title = subprocess.check_output(
            ["xdotool", "getwindowname", window_id],
            stderr=subprocess.DEVNULL
        ).decode().strip()

        if len(window_title) > 50:
            window_title = window_title[:47] + "..."

        return f"{app_name}: {window_title}"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def main() -> None:
    """Main tracking loop with event-driven plugin system."""
    ensure_db_exists()
    repo = EventRepository()

    # Initialize plugin system
    plugin_manager = PluginManager()
    plugin_manager.discover_plugins()
    plugin_manager.install_all()
    plugin_manager.set_plugin_manager_for_all()

    # Register plugin event handlers
    for plugin in plugin_manager.plugins.values():
        try:
            plugin.register_events(plugin_manager)
        except Exception as e:
            print(f"Error registering events for {plugin.get_info()['name']}: {e}")

    plugin_manager.start_all()

    # Track state
    current_state = "unknown"
    last_poll_log = datetime.datetime.now()
    last_idle_change_time = datetime.datetime.now()
    last_idle_value = 0.0

    if DEBUG_MODE:
        debug_log("="*80)
        debug_log("ScreenTracker started in DEBUG mode")
        debug_log(f"IDLE_THRESHOLD_SEC: {IDLE_THRESHOLD_SEC}")
        debug_log(f"LOG_INTERVAL: {LOG_INTERVAL}")
        debug_log("="*80)

    repo.insert("tracker_start")
    print(f"[{datetime.datetime.now().isoformat(timespec='seconds')}] tracker_start")
    print("Starting tracker main loop...")
    if DEBUG_MODE:
        print(f"Debug logging enabled: {DEBUG_LOG_PATH}")

    try:
        while True:
            now = datetime.datetime.now()
            idle_sec = get_idle_seconds()
            screen_on = is_screen_on()

            # Debug: Track idle changes
            if DEBUG_MODE:
                if idle_sec < last_idle_value:
                    time_since_last_change = (now - last_idle_change_time).total_seconds()
                    window_info = get_active_window_info()
                    debug_log(
                        f"IDLE RESET: {last_idle_value:.1f}s -> {idle_sec:.1f}s "
                        f"(after {time_since_last_change:.1f}s) | Window: {window_info}"
                    )
                    last_idle_change_time = now

                elif idle_sec - last_idle_value > 5.0:
                    debug_log(
                        f"IDLE INCREASE: {last_idle_value:.1f}s -> {idle_sec:.1f}s "
                        f"(+{idle_sec - last_idle_value:.1f}s)"
                    )

                last_idle_value = idle_sec

            # Determine actual state
            if screen_on and idle_sec < IDLE_THRESHOLD_SEC:
                new_state = "active"
            else:
                new_state = "inactive"

            if DEBUG_MODE and new_state == "active":
                window_info = get_active_window_info()
                debug_log(
                    f"STATE: {new_state} | idle={idle_sec:.1f}s | "
                    f"screen={'on' if screen_on else 'off'} | Window: {window_info}"
                )

            if current_state == "unknown":
                current_state = new_state

                if DEBUG_MODE:
                    debug_log(f"Initial state established: {new_state}")

                if new_state == "active":
                    plugin_manager.notify_active()
                    detail = f"state={new_state} idle={idle_sec:.0f}s screen={'on' if screen_on else 'off'}"
                    repo.insert("poll", detail)
                    print(f"[{now.isoformat(timespec='seconds')}] poll (initial): {detail}")
                    last_poll_log = now

                time.sleep(LOG_INTERVAL)
                continue

            # Log state transitions
            if new_state != current_state:
                if DEBUG_MODE:
                    debug_log(f"STATE CHANGE: {current_state} -> {new_state}")

                if new_state == "active":
                    repo.insert("idle_end", f"idle was {idle_sec:.0f}s")
                    print(f"[{now.isoformat(timespec='seconds')}] idle_end (idle was {idle_sec:.0f}s)")
                    plugin_manager.notify_active()
                else:
                    if not screen_on:
                        repo.insert("screen_off")
                        print(f"[{now.isoformat(timespec='seconds')}] screen_off")
                        if DEBUG_MODE:
                            debug_log("Inactive reason: screen off")
                    else:
                        idle_start_time = now - datetime.timedelta(seconds=idle_sec - IDLE_THRESHOLD_SEC)
                        repo.insert("idle_start", f"idle {idle_sec:.0f}s > {IDLE_THRESHOLD_SEC}s",
                                  timestamp=idle_start_time)
                        print(f"[{idle_start_time.isoformat(timespec='seconds')}] idle_start (idle {idle_sec:.0f}s)")
                        if DEBUG_MODE:
                            debug_log(f"Inactive reason: idle threshold exceeded ({idle_sec:.0f}s > {IDLE_THRESHOLD_SEC}s)")

                    plugin_manager.notify_inactive()

            # Poll plugins (only if active)
            if new_state == "active":
                for plugin in plugin_manager.plugins.values():
                    if hasattr(plugin, 'poll'):
                        try:
                            plugin.poll()  # type: ignore
                        except Exception as e:
                            print(f"Plugin poll error: {e}")
                            if DEBUG_MODE:
                                debug_log(f"Plugin poll error: {e}")

            # Log polling data periodically (every 60s)
            if (now - last_poll_log).total_seconds() >= 60:
                detail = f"state={new_state} idle={idle_sec:.0f}s screen={'on' if screen_on else 'off'}"
                repo.insert("poll", detail)
                print(f"[{now.isoformat(timespec='seconds')}] poll: {detail}")
                last_poll_log = now

            current_state = new_state
            time.sleep(LOG_INTERVAL)

    except KeyboardInterrupt:
        print("\nTracker stopping.")
        if DEBUG_MODE:
            debug_log("Tracker stopped by user (KeyboardInterrupt)")
        plugin_manager.stop_all()
        repo.insert("tracker_stop")
        print(f"[{datetime.datetime.now().isoformat(timespec='seconds')}] tracker_stop")


if __name__ == "__main__":
    main()

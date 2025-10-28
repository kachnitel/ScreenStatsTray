#!/usr/bin/env python3
"""
Background service to track user activity with plugin support.
"""
import os
import time
import subprocess
import datetime
from .config import DB_PATH, LOG_INTERVAL, IDLE_THRESHOLD_MS
from .db import ensure_db_exists
from .db.event_repository import EventRepository
from .plugins import PluginManager

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
IDLE_THRESHOLD_SEC = IDLE_THRESHOLD_MS / 1000.0


def get_idle_seconds() -> float:
    """Return the current idle time in seconds."""
    try:
        idle_ms = int(subprocess.check_output(["xprintidle"]).strip())
        return idle_ms / 1000.0
    except (FileNotFoundError, subprocess.CalledProcessError):
        return 0.0


def is_screen_on() -> bool:
    """Return True if monitor is on."""
    try:
        out = subprocess.check_output(["xset", "-q"]).decode()
        return "Monitor is On" in out
    except (FileNotFoundError, subprocess.CalledProcessError):
        return True


def main() -> None:
    """Main tracking loop with plugin support."""
    ensure_db_exists()
    repo = EventRepository()

    # Initialize plugin system
    plugin_manager = PluginManager()
    plugin_manager.discover_plugins()
    plugin_manager.install_all()
    plugin_manager.start_all()

    # Track state
    current_state = "unknown"
    last_poll_log = datetime.datetime.now()

    repo.insert("tracker_start")
    print(f"[{datetime.datetime.now().isoformat(timespec='seconds')}] tracker_start")
    print("Starting tracker main loop...")

    try:
        while True:
            now = datetime.datetime.now()
            idle_sec = get_idle_seconds()
            screen_on = is_screen_on()

            # Determine actual state
            if screen_on and idle_sec < IDLE_THRESHOLD_SEC:
                new_state = "active"
            else:
                new_state = "inactive"

            # Log state transitions
            if new_state != current_state and current_state != "unknown":
                if new_state == "active":
                    # Became active
                    repo.insert("idle_end", f"idle was {idle_sec:.0f}s")
                    print(f"[{now.isoformat(timespec='seconds')}] idle_end (idle was {idle_sec:.0f}s)")

                    # Notify plugins
                    plugin_manager.notify_active()

                else:
                    # Became inactive
                    if not screen_on:
                        repo.insert("screen_off")
                        print(f"[{now.isoformat(timespec='seconds')}] screen_off")
                    else:
                        idle_start_time = now - datetime.timedelta(seconds=idle_sec - IDLE_THRESHOLD_SEC)
                        repo.insert("idle_start", f"idle {idle_sec:.0f}s > {IDLE_THRESHOLD_SEC}s",
                                  timestamp=idle_start_time)
                        print(f"[{idle_start_time.isoformat(timespec='seconds')}] idle_start (idle {idle_sec:.0f}s)")

                    # Notify plugins
                    plugin_manager.notify_inactive()

            # Poll plugins (only if active)
            if new_state == "active":
                for plugin in plugin_manager.plugins.values():
                    if hasattr(plugin, 'poll'):
                        try:
                            plugin.poll()  # type: ignore
                        except Exception as e:
                            print(f"Plugin poll error: {e}")

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
        plugin_manager.stop_all()
        repo.insert("tracker_stop")
        print(f"[{datetime.datetime.now().isoformat(timespec='seconds')}] tracker_stop")


if __name__ == "__main__":
    main()

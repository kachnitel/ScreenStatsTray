#!/usr/bin/env python3
"""
Background service to track user activity (active/inactive periods)
and log events to the SQLite database.

Simplified approach:
- Polls xprintidle every 2 seconds
- Transitions to inactive after 10 minutes of idle
- Logs state changes only
"""
import os
import time
import subprocess
import datetime
from .config import DB_PATH, LOG_INTERVAL, IDLE_THRESHOLD_MS
from .db import ensure_db_exists
from .db.event_repository import EventRepository

# Ensure DB directory exists
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# Convert threshold to seconds for easier comparison
IDLE_THRESHOLD_SEC = IDLE_THRESHOLD_MS / 1000.0


def get_idle_seconds() -> float:
    """Return the current idle time in seconds."""
    try:
        idle_ms = int(subprocess.check_output(["xprintidle"]).strip())
        return idle_ms / 1000.0
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("Warning: 'xprintidle' not found. Defaulting to 0 idle.")
        return 0.0


def is_screen_on() -> bool:
    """Return True if monitor is on, False otherwise."""
    try:
        out = subprocess.check_output(["xset", "-q"]).decode()
        return "Monitor is On" in out
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("Warning: 'xset' not found. Assuming screen is always on.")
        return True


def main() -> None:
    """Main loop for the activity tracker daemon."""
    # Initialize database
    ensure_db_exists()
    repo = EventRepository()

    # Track current state
    is_active = True

    # Log startup
    repo.insert("tracker_start")
    print(f"[{datetime.datetime.now().isoformat(timespec='seconds')}] tracker_start")

    # Initial state
    screen_on = is_screen_on()
    if screen_on:
        repo.insert("screen_on")
        print(f"[{datetime.datetime.now().isoformat(timespec='seconds')}] screen_on")
    else:
        repo.insert("screen_off")
        print(f"[{datetime.datetime.now().isoformat(timespec='seconds')}] screen_off")
        is_active = False

    print("Starting tracker main loop...")

    try:
        while True:
            now = datetime.datetime.now()
            idle_sec = get_idle_seconds()
            screen_on = is_screen_on()

            # Determine if user should be considered active
            # Active means: screen is on AND idle time is below threshold
            should_be_active = screen_on and idle_sec < IDLE_THRESHOLD_SEC

            # Handle state transitions
            if should_be_active and not is_active:
                # Transition: inactive -> active
                transition_time = now - datetime.timedelta(seconds=idle_sec)
                repo.insert("idle_end", timestamp=transition_time)
                print(f"[{transition_time.isoformat(timespec='seconds')}] idle_end")
                is_active = True

            elif not should_be_active and is_active:
                # Transition: active -> inactive
                if not screen_on:
                    # Screen turned off
                    repo.insert("screen_off")
                    print(f"[{now.isoformat(timespec='seconds')}] screen_off")
                else:
                    # User went idle - log at the moment idleness started
                    idle_start_time = now - datetime.timedelta(seconds=idle_sec)
                    repo.insert("idle_start", f"idle > {IDLE_THRESHOLD_SEC}s", timestamp=idle_start_time)
                    print(f"[{idle_start_time.isoformat(timespec='seconds')}] idle_start idle > {IDLE_THRESHOLD_SEC}s")

                is_active = False

            # Also track screen state changes independently
            # This handles screen coming back on (from sleep/screensaver)
            elif screen_on and not is_active and idle_sec < IDLE_THRESHOLD_SEC:
                # Screen came back on with activity
                repo.insert("screen_on")
                print(f"[{now.isoformat(timespec='seconds')}] screen_on")

            time.sleep(LOG_INTERVAL)

    except KeyboardInterrupt:
        print("\nTracker stopping.")
        repo.insert("tracker_stop")
        print(f"[{datetime.datetime.now().isoformat(timespec='seconds')}] tracker_stop")


if __name__ == "__main__":
    main()

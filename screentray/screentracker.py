#!/usr/bin/env python3
import os, time, subprocess, sqlite3, datetime

DB_PATH = os.path.expanduser("~/.local/share/screentracker.db")
LOG_INTERVAL = 2
IDLE_THRESHOLD_MS = 300_000
SWITCH_MIN_DURATION = 5  # seconds

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def db_exec(query, params=()):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, timestamp TEXT, type TEXT, detail TEXT)")
        conn.execute(query, params)
        conn.commit()

def log_event(type_, detail=""):
    ts = datetime.datetime.now().isoformat(timespec='seconds')
    db_exec("INSERT INTO events (timestamp, type, detail) VALUES (?, ?, ?)", (ts, type_, detail))
    print(f"[{ts}] {type_} {detail}")

def get_idle_ms():
    return int(subprocess.check_output(["xprintidle"]).strip())

def get_active_window_name():
    try:
        wid = subprocess.check_output(["xdotool", "getactivewindow"]).strip()
        name = subprocess.check_output(["xprop", "-id", wid, "WM_CLASS"]).decode()
        return name.split('"')[1]
    except subprocess.CalledProcessError:
        return None

def is_screen_on():
    out = subprocess.check_output(["xset", "-q"]).decode()
    return "Monitor is On" in out

def main():
    last_app = None
    last_app_time = time.time()
    was_idle = False
    was_on = is_screen_on()
    log_event("screen_on" if was_on else "screen_off")

    while True:
        idle_ms = get_idle_ms()
        idle = idle_ms > IDLE_THRESHOLD_MS

        # Screen state
        on = is_screen_on()
        if on != was_on:
            log_event("screen_on" if on else "screen_off")
            was_on = on

        # Idle state
        if idle != was_idle:
            if idle:
                log_event("idle_start", f"idle > {IDLE_THRESHOLD_MS/1000}s")
            else:
                log_event("idle_end")
            was_idle = idle

        # Foreground app
        if on and not idle:
            app = get_active_window_name()
            if app and app != last_app:
                now = time.time()
                if last_app and now - last_app_time > SWITCH_MIN_DURATION:
                    log_event("app_switch", f"{last_app} → {app}")
                last_app = app
                last_app_time = now

        time.sleep(LOG_INTERVAL)

if __name__ == "__main__":
    main()

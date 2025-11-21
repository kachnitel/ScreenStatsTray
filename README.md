# ScreenTracker

This application helps you keep track of your screen usage and activity patterns throughout the day. By showing current session length, recent breaks, and the most-used applications, it provides clear insights into your daily computer habits and encourages healthier work rhythms.

**ScreenTracker** is a lightweight, user-space tool for tracking screen usage and application activity on Linux (X11/KDE). It logs when your screen is on, when your system is idle, and which application is in the foreground. All data is stored locally in a SQLite database.

This project is designed for personal use or auditing your own productivity and does **not transmit any data externally**. Transparency and user control are core principles.

---

## Features

- Tracks:
  - Screen on/off events
  - Idle periods (with configurable threshold; default: 10 minutes)
  - Foreground application switches
- Logs all events to `~/.local/share/screentracker.db`
- Provides a CLI summary tool (`screenstats`) for:
  - Event counts
  - Total active vs. inactive screen time
  - Active time per application
- Automatically detects X11 display and authentication (`XAUTHORITY`)
- Runs as a **systemd user service** — no root required
- Lightweight and relies only on standard Linux packages (`python3`, `xdotool`, `xprintidle`, `xset`, `sqlite3`)

---

## Installation (User-Space)

### Dependencies

Make sure the following are installed via your package manager:

- python3
- xdotool
- xprintidle
- xset
- sqlite3
- python3-inotify_simple (Python package)

On openSUSE Tumbleweed:

```
sudo zypper install python3 xdotool xprintidle xorg-x11-utils sqlite3 python3-inotify_simple
```

### Install

Run `./install.sh`

## Usage

- View today’s summary:

```bash
screenstats
```

- View summary for a specific date:

```bash
screenstats 2025-10-31
```

Output includes:

- Event counts per type
- Total active and inactive time (idle <5min counts as active)
- Per-application active durations

## Privacy

All logs are local (~/.local/share/screentracker.db)

No network activity is performed

You can safely inspect or remove the database at any time

## Development / Contributing

Pull requests for new features or bug fixes are welcome

## Uninstallation

To remove ScreenTracker: `./uninstall.sh`

# Known issues

## Service initialization

App may be started before UI is initiated and fails to communicate with DE

## Popup positioning

Clicking tray popup opens the window at 0:0

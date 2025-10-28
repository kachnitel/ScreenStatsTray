# ScreenTray Plugin System

## Overview

The plugin system allows extending ScreenTray functionality without modifying core code. Plugins are auto-discovered from the `screentray/plugins/` directory.

## Architecture

### Key Components

```
screentray/
├── plugins/
│   ├── __init__.py          # Plugin exports
│   ├── base.py              # PluginBase abstract class
│   ├── manager.py           # Plugin discovery & lifecycle
│   └── app_tracker/         # Example plugin
│       ├── __init__.py      # PLUGIN_INFO metadata
│       ├── plugin.py        # AppTrackerPlugin class
│       ├── tracker.py       # Window monitoring logic
│       ├── db.py            # Database operations
│       └── service.py       # Statistics calculations
```

### Plugin Lifecycle

1. **Discovery** - `PluginManager.discover_plugins()` scans `plugins/` directory
2. **Installation** - `plugin.install()` creates DB tables on first run
3. **Start** - `plugin.start()` begins operation when tracker starts
4. **Poll** - `plugin.poll()` called every 2 seconds during active state
5. **Stop** - `plugin.stop()` cleanup when tracker stops
6. **Uninstall** - `plugin.uninstall()` removes DB tables

### State Awareness

Plugins receive state notifications from the core tracker:
- `on_active()` - User is present and active
- `on_inactive()` - User is idle or screen is off

**Important**: App tracker only records time during `active` state, ensuring accurate usage statistics.

## Creating a New Plugin

### Step 1: Create Plugin Directory

```bash
mkdir screentray/plugins/my_plugin
```

### Step 2: Add PLUGIN_INFO

```python
# screentray/plugins/my_plugin/__init__.py
PLUGIN_INFO = {
    "name": "my_plugin",
    "display_name": "My Plugin",
    "version": "1.0.0",
    "description": "What this plugin does",
    "requires_install": True,  # If it needs DB tables
}
```

### Step 3: Implement PluginBase

```python
# screentray/plugins/my_plugin/plugin.py
from typing import Any
from ..base import PluginBase
from . import PLUGIN_INFO

class MyPlugin(PluginBase):
    def get_info(self) -> dict[str, Any]:
        return PLUGIN_INFO

    def install(self) -> None:
        # Create DB tables
        pass

    def uninstall(self) -> None:
        # Drop DB tables
        pass

    def start(self) -> None:
        # Initialize plugin
        pass

    def stop(self) -> None:
        # Cleanup resources
        pass

    # Optional: respond to state changes
    def on_active(self) -> None:
        print("User became active")

    def on_inactive(self) -> None:
        print("User became inactive")

    # Optional: regular polling
    def poll(self) -> None:
        # Called every 2 seconds when active
        pass
```

### Step 4: Database Operations

```python
# screentray/plugins/my_plugin/db.py
from ...db.connection import get_cursor, DB_PATH
import sqlite3

def ensure_tables() -> None:
    with get_cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS my_table (
                id INTEGER PRIMARY KEY,
                timestamp TEXT NOT NULL,
                data TEXT
            )
        """)

def drop_tables() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS my_table")
    conn.commit()
    conn.close()
```

## App Tracker Plugin

### What It Does

Monitors which application has window focus and records:
- Application switches (switch_to/switch_from events)
- Time spent in each application
- Window titles for context

### Database Schema

```sql
CREATE TABLE app_usage (
    id INTEGER PRIMARY KEY,
    timestamp TEXT NOT NULL,
    app_name TEXT NOT NULL,
    window_title TEXT,
    event_type TEXT NOT NULL  -- 'switch_to' or 'switch_from'
);
```

### Usage Example

```python
from screentray.plugins.app_tracker.service import AppUsageService
import datetime

# Get today's app usage
usage = AppUsageService.get_app_usage_today()
for app, seconds in sorted(usage.items(), key=lambda x: x[1], reverse=True):
    print(f"{app}: {seconds/60:.1f} minutes")

# Get top 5 apps for a specific period
start = datetime.datetime(2025, 10, 25, 9, 0)
end = datetime.datetime(2025, 10, 25, 17, 0)
top_apps = AppUsageService.get_top_apps(start, end, limit=5)
```

### How It Works

1. **Window Monitoring**: Uses `xdotool` to query active window
2. **State Awareness**: Only tracks during active periods
3. **Switch Detection**: Records when focus changes between apps
4. **Time Calculation**: Computes duration from switch_to → switch_from pairs

### Installation

```bash
./install.sh --with-app-tracker
# Or interactively during install
```

## Integration Points

### UI Integration (Planned)

Plugins can provide widgets for the tray popup:

```python
def get_popup_widget(self) -> Optional[QWidget]:
    from PyQt5.QtWidgets import QLabel
    return QLabel("Plugin UI")
```

### Web Integration (Planned)

Plugins can register Flask routes:

```python
def get_web_routes(self) -> list[tuple[str, Any]]:
    return [
        ("/api/myplugin/stats", self.api_stats),
    ]

def api_stats(self):
    from flask import jsonify
    return jsonify({"data": "value"})
```

## Configuration

Plugin state is tracked in `~/.config/screentray/enabled_plugins.txt`:

```
app_tracker
```

## Best Practices

1. **Minimal Impact**: Plugins should be lightweight and not block the main loop
2. **Error Handling**: Wrap plugin operations in try/except to prevent crashes
3. **State Awareness**: Respect active/inactive state for accurate tracking
4. **Database Isolation**: Use separate tables to avoid conflicts
5. **Clean Uninstall**: Properly cleanup tables and resources

## Troubleshooting

### Plugin Not Loading

Check plugin discovery output:
```bash
systemctl --user status screentracker.service
```

Look for "Discovered plugin: ..." messages.

### Database Errors

Manually run install:
```python
from screentray.plugins.app_tracker import db
db.ensure_tables()
```

### xdotool Issues

Test window detection:
```bash
xdotool getactivewindow getwindowclassname
```

Ensure `xdotool` is installed:
```bash
sudo zypper install xdotool  # openSUSE
```
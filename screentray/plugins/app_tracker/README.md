# Application Tracker Plugin

Digital wellbeing plugin that monitors time spent in each application.

## Installation

```bash
./install.sh --with-app-tracker
```

Or during interactive install, answer 'y' when prompted.

## What Gets Tracked

- **Application focus**: Which app has the active window
- **Time spent**: Duration in each application (only when user is active)
- **Window titles**: Context about what you're working on

## Data Privacy

- All data stored locally in `~/.local/share/screentracker.db`
- No network activity
- Only tracks during active use (not during idle/screen off)

## Database Structure

### Table: `app_usage`

| Column       | Type    | Description                    |
|--------------|---------|--------------------------------|
| id           | INTEGER | Primary key                    |
| timestamp    | TEXT    | ISO format timestamp           |
| app_name     | TEXT    | Application class name         |
| window_title | TEXT    | Window title (optional)        |
| event_type   | TEXT    | 'switch_to' or 'switch_from'   |

### Example Data

```
2025-10-25T14:30:00 | firefox     | GitHub - PR Review      | switch_to
2025-10-25T14:45:00 | firefox     | GitHub - PR Review      | switch_from
2025-10-25T14:45:00 | code        | plugin.py - VSCode      | switch_to
2025-10-25T15:00:00 | code        | plugin.py - VSCode      | switch_from
```

## Querying Usage Data

### Python API

```python
from screentray.plugins.app_tracker.service import AppUsageService
import datetime

# Today's usage
usage = AppUsageService.get_app_usage_today()
for app, seconds in usage.items():
    print(f"{app}: {seconds/60:.1f} minutes")

# Top 5 apps this week
now = datetime.datetime.now()
week_start = now - datetime.timedelta(days=7)
top_apps = AppUsageService.get_top_apps(week_start, now, limit=5)
```

### SQL Query

```sql
-- Time spent per app today
WITH app_sessions AS (
  SELECT
    app_name,
    timestamp AS switch_to_time,
    LEAD(timestamp) OVER (ORDER BY timestamp) AS switch_from_time
  FROM app_usage
  WHERE event_type = 'switch_to'
    AND date(timestamp) = date('now', 'localtime')
)
SELECT
  app_name,
  SUM(
    (strftime('%s', switch_from_time) - strftime('%s', switch_to_time))
  ) / 60.0 AS minutes
FROM app_sessions
WHERE switch_from_time IS NOT NULL
GROUP BY app_name
ORDER BY minutes DESC;
```

## How It Works

1. **Window Detection**: Uses `xdotool getactivewindow` every 2 seconds
2. **App Identification**: Extracts app class name (e.g., 'firefox', 'code')
3. **State Awareness**: Only tracks when user is active (not idle/screen off)
4. **Event Recording**: Logs switch_to/switch_from pairs for time calculation

## Future Features

- **Usage notifications**: Alert when app usage exceeds threshold
- **Daily reports**: Summary emails or desktop notifications
- **Web dashboard**: Visual charts in the web interface
- **App categories**: Group apps (work, entertainment, communication)

## Uninstallation

```bash
./uninstall.sh
# When prompted, choose to remove database if desired
```

Or manually:

```bash
python3 -c "from screentray.plugins.app_tracker import db; db.drop_tables()"
```

## Troubleshooting

### "xdotool: command not found"

Install xdotool:
```bash
sudo zypper install xdotool  # openSUSE
sudo apt install xdotool      # Debian/Ubuntu
```

### No data being recorded

Check if screentracker is running:
```bash
systemctl --user status screentracker.service
```

Check for errors in logs:
```bash
journalctl --user -u screentracker.service -f
```

### Duplicate entries

This may happen if screentracker restarts. The service calculates time from switch_to → switch_from pairs, so duplicates are handled correctly.

## Development

To modify the plugin:

1. Edit files in `screentray/plugins/app_tracker/`
2. If using dev mode: `./install.sh --dev`
3. Restart tracker: `systemctl --user restart screentracker.service`

Key files:
- `plugin.py` - Main plugin logic
- `tracker.py` - Window monitoring
- `db.py` - Database operations
- `service.py` - Usage statistics

## Privacy & Ethics

This plugin is designed for **personal use only**. It helps you:
- Understand your digital habits
- Identify time sinks
- Build healthier work patterns

**Never use this to monitor others without consent.**
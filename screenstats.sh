#!/usr/bin/env bash
set -e

# Optional date argument (YYYY-MM-DD), default = today
DAY="${1:-$(date +%F)}"

# Call Python services for stats
python3 -c "
import sys
import datetime
from screentray.services.stats_service import StatsService

day = '$DAY'
print(f'=== ScreenTracker summary for {day} ===\n')

# Daily totals
stats_service = StatsService()
totals = stats_service.get_daily_totals(day)

active_sec = totals.get('active', 0.0)
h, rem = divmod(int(active_sec), 3600)
m, s = divmod(rem, 60)
print(f'Active time: {h:02d}:{m:02d}:{s:02d} ({active_sec/60:.1f} minutes)')
print()
"

# Try app_tracker plugin if available
python3 -c "
import sys
import datetime

try:
    from screentray.plugins.app_tracker.service import AppUsageService

    day = '$DAY'
    day_date = datetime.date.fromisoformat(day)
    start = datetime.datetime.combine(day_date, datetime.time.min)

    # For today, end at now; for past days, end at midnight
    if day_date == datetime.date.today():
        end = datetime.datetime.now()
    else:
        end = datetime.datetime.combine(day_date, datetime.time.max)

    usage = AppUsageService.get_app_usage_for_period(start, end)

    if usage:
        print('Top applications:')
        sorted_apps = sorted(usage.items(), key=lambda x: x[1], reverse=True)[:10]

        for app, seconds in sorted_apps:
            h, rem = divmod(int(seconds), 3600)
            m, s = divmod(rem, 60)
            if h > 0:
                time_str = f'{h}h {m}m'
            elif m > 0:
                time_str = f'{m}m {s}s'
            else:
                time_str = f'{s}s'
            print(f'  {app}: {time_str}')
except ImportError:
    pass  # Plugin not installed
except Exception as e:
    print(f'App tracker error: {e}', file=sys.stderr)
"

# Current session info
python3 -c "
from screentray.services.session_service import SessionService

session_service = SessionService()
start, duration = session_service.get_current_session()

if start and duration > 0:
    h, rem = divmod(int(duration), 3600)
    m, s = divmod(rem, 60)
    print(f'\nCurrent session: {h:02d}:{m:02d}:{s:02d}')
else:
    print('\nNo active session')
"

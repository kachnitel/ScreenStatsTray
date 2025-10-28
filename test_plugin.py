from screentray.plugins.app_tracker.service import AppUsageService
import datetime

# Get today's usage
print("=== Today's App Usage ===")
usage = AppUsageService.get_app_usage_today()

for app, seconds in sorted(usage.items(), key=lambda x: x[1], reverse=True):
    minutes = seconds / 60
    if minutes >= 1:
        print(f"{app:20s} {minutes:6.1f} minutes")

# Get top 5 apps
print("\n=== Top 5 Apps (Last 24h) ===")
now = datetime.datetime.now()
start = now - datetime.timedelta(hours=24)
top_apps = AppUsageService.get_top_apps(start, now, limit=5)

for app, seconds in top_apps:
    print(f"{app:20s} {seconds/60:6.1f} minutes")

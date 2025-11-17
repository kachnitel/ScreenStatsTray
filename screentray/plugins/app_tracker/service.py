"""
screentray/plugins/app_tracker/service.py

Business logic for app usage statistics.
"""
import datetime
from typing import Dict, List, Tuple
from ...db.connection import get_cursor


class AppUsageService:
    """Provides statistics about application usage."""

    @staticmethod
    def get_app_usage_for_period(
        start: datetime.datetime,
        end: datetime.datetime
    ) -> Dict[str, float]:
        """
        Calculate time spent in each application during a period.

        Args:
            start: Period start time (timezone-aware or naive)
            end: Period end time (timezone-aware or naive)

        Returns:
            Dict mapping app_name to seconds spent
        """
        # Strip timezone info to match database timestamps (which are naive)
        if start.tzinfo is not None:
            start = start.replace(tzinfo=None)
        if end.tzinfo is not None:
            end = end.replace(tzinfo=None)

        with get_cursor() as cur:
            cur.execute("""
                SELECT app_name, timestamp, event_type
                FROM app_usage
                WHERE timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp ASC
            """, (start.isoformat(), end.isoformat()))

            events = cur.fetchall()

        if not events:
            return {}

        app_times: Dict[str, float] = {}
        current_app: str | None = None
        last_switch_time: datetime.datetime | None = None

        for row in events:
            app_name = row[0]
            timestamp = datetime.datetime.fromisoformat(row[1])
            event_type = row[2]

            if event_type == "switch_to":
                # Close previous app session if any
                if current_app and last_switch_time:
                    duration = (timestamp - last_switch_time).total_seconds()
                    app_times[current_app] = app_times.get(current_app, 0.0) + duration

                # Start new session
                current_app = app_name
                last_switch_time = timestamp

            elif event_type == "switch_from":
                # Close current app session
                if current_app and last_switch_time and current_app == app_name:
                    duration = (timestamp - last_switch_time).total_seconds()
                    app_times[current_app] = app_times.get(current_app, 0.0) + duration
                    current_app = None
                    last_switch_time = None

        # Handle case where last app is still active
        # IMPORTANT: Only count time up to 'end', not 'now'
        if current_app and last_switch_time:
            # Use the earlier of 'end' or 'now' to avoid counting future time
            effective_end = min(end, datetime.datetime.now())
            # Only add duration if last_switch_time is before effective_end
            if last_switch_time < effective_end:
                duration = (effective_end - last_switch_time).total_seconds()
                app_times[current_app] = app_times.get(current_app, 0.0) + duration

        return app_times

    @staticmethod
    def get_app_usage_today() -> Dict[str, float]:
        """Get app usage for today."""
        now = datetime.datetime.now()
        start = datetime.datetime.combine(now.date(), datetime.time.min)
        return AppUsageService.get_app_usage_for_period(start, now)

    @staticmethod
    def get_top_apps(
        start: datetime.datetime,
        end: datetime.datetime,
        limit: int = 10
    ) -> List[Tuple[str, float]]:
        """
        Get top N applications by usage time.

        Returns:
            List of (app_name, seconds) tuples sorted by usage
        """
        app_times = AppUsageService.get_app_usage_for_period(start, end)
        sorted_apps = sorted(app_times.items(), key=lambda x: x[1], reverse=True)
        return sorted_apps[:limit]

    @staticmethod
    def get_current_app() -> str | None:
        """Get the currently active application (last switch_to event)."""
        with get_cursor() as cur:
            cur.execute("""
                SELECT app_name
                FROM app_usage
                WHERE event_type = 'switch_to'
                ORDER BY timestamp DESC
                LIMIT 1
            """)
            row = cur.fetchone()
            return row[0] if row else None

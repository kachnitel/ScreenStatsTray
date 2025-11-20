"""Unit tests for ActivityService."""
import unittest
from unittest.mock import patch
import datetime
from screentray.services.activity_service import ActivityService
from screentray.models import Event


class TestActivityService(unittest.TestCase):
    """Test activity period calculations."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.service = ActivityService()
        # Use current time relative to the system to ensure service lookups (which use datetime.now())
        # find these events. We place base_time 1 hour ago.
        self.base_time = datetime.datetime.now().replace(microsecond=0) - datetime.timedelta(hours=1)

    def _create_event(self, offset_seconds: int, event_type: str, detail: str = "") -> Event:
        """Create a test event at base_time + offset."""
        timestamp = self.base_time + datetime.timedelta(seconds=offset_seconds)
        return Event(
            id=offset_seconds,
            timestamp=timestamp.isoformat(),
            type=event_type,
            detail=detail
        )

    def test_empty_period_returns_inactive(self) -> None:
        """No events = entire period is inactive."""
        start = self.base_time
        end = start + datetime.timedelta(hours=1)

        periods = self.service._build_simple_periods([], start, end) # pyright: ignore[reportPrivateUsage]

        self.assertEqual(len(periods), 1)
        self.assertEqual(periods[0]["state"], "inactive")
        self.assertEqual(periods[0]["duration_seconds"], 3600.0)

    def test_single_active_event_creates_active_period(self) -> None:
        """Single screen_on creates active period from event to end."""
        events = [self._create_event(0, "screen_on")]
        start = self.base_time
        end = start + datetime.timedelta(minutes=10)

        periods = self.service._build_simple_periods(events, start, end) # pyright: ignore[reportPrivateUsage]

        self.assertEqual(len(periods), 1)
        self.assertEqual(periods[0]["state"], "active")
        self.assertEqual(periods[0]["duration_seconds"], 600.0)

    def test_active_to_inactive_transition(self) -> None:
        """screen_on followed by idle_start creates two periods."""
        events = [
            self._create_event(0, "screen_on"),
            self._create_event(300, "idle_start")
        ]
        start = self.base_time
        end = start + datetime.timedelta(minutes=10)

        periods = self.service._build_simple_periods(events, start, end) # pyright: ignore[reportPrivateUsage]

        self.assertEqual(len(periods), 2)
        self.assertEqual(periods[0]["state"], "active")
        self.assertEqual(periods[0]["duration_seconds"], 300.0)
        self.assertEqual(periods[1]["state"], "inactive")
        self.assertEqual(periods[1]["duration_seconds"], 300.0)

    def test_ignores_non_state_events(self) -> None:
        """poll and tracker_start events don't change state."""
        events = [
            self._create_event(0, "tracker_start"),
            self._create_event(100, "poll", "state=active"),
            self._create_event(200, "screen_on")
        ]
        start = self.base_time
        end = start + datetime.timedelta(minutes=10)

        periods = self.service._build_simple_periods(events, start, end) # pyright: ignore[reportPrivateUsage]

        self.assertEqual(len(periods), 2)
        self.assertEqual(periods[0]["state"], "inactive")
        self.assertEqual(periods[1]["state"], "active")

    def test_clips_to_today(self) -> None:
        """For today, periods end at 'now' not end-of-day."""
        today = datetime.date.today()
        end = datetime.datetime.combine(today, datetime.time.max)

        # Note: If the test runs at midnight, base_time might be yesterday,
        # but find_events_in_period returns our mock events anyway.
        # _build_simple_periods calculates duration based on explicit range,
        # so logic holds as long as events are roughly valid timestamps.
        periods = self.service.get_activity_periods_for_day(today)

        last_period = periods[-1]
        end_dt = last_period["end"]
        if isinstance(end_dt, str):
            end_dt = datetime.datetime.fromisoformat(end_dt)
        self.assertLess(end_dt, end)

    def test_multiple_transitions(self) -> None:
        """Complex sequence of state changes."""
        events = [
            self._create_event(0, "screen_on"),
            self._create_event(300, "idle_start"),
            self._create_event(900, "idle_end"),
            self._create_event(1200, "screen_off")
        ]
        start = self.base_time
        end = start + datetime.timedelta(minutes=30)

        periods = self.service._build_simple_periods(events, start, end) # pyright: ignore[reportPrivateUsage]

        self.assertEqual(len(periods), 4)
        self.assertEqual(periods[0]["state"], "active")
        self.assertEqual(periods[1]["state"], "inactive")
        self.assertEqual(periods[2]["state"], "active")
        self.assertEqual(periods[3]["state"], "inactive")

    @patch('screentray.services.activity_service.MAX_NO_EVENT_GAP', 600)
    @patch('screentray.services.activity_service.EventRepository')
    def test_gap_detection_creates_inactive_period(self, mock_repo_class: object) -> None:
        """Gaps > 600s insert inactive periods."""
        events = [
            self._create_event(0, "screen_on"),
            # Add intermediate event so first active period has duration > 0 (0s to 60s)
            self._create_event(60, "poll", "state=active"),
            self._create_event(760, "screen_on")  # 700s gap after poll
        ]

        # Create a new service instance that will use the mocked repo
        with patch.object(ActivityService, '__init__', lambda x: None):
            service = ActivityService()
            service.repo = mock_repo_class.return_value # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]
            service.repo.find_events_in_period.return_value = events # pyright: ignore[reportUnknownMemberType]

            # Look back 2 hours to ensure we capture our events (base_time is -1h)
            periods = service.get_detailed_activity_periods(hours=2)

        # Should have: active (0-60), gap-inactive (60-760), active (760-end)
        self.assertGreaterEqual(len(periods), 3)

        # Handle explicit None in trigger_event using safe access
        gap_periods = [p for p in periods if (p.get("trigger_event") or {}).get("type") == "gap"] # pyright: ignore[reportUnknownMemberType]
        self.assertGreater(len(gap_periods), 0)
        self.assertEqual(gap_periods[0]["state"], "inactive")

    @patch('screentray.services.activity_service.EventRepository')
    def test_detailed_periods_include_raw_events(self, mock_repo_class: object) -> None:
        """Detailed periods attach raw event list."""
        events = [
            self._create_event(0, "idle_end"),
            self._create_event(60, "poll", "state=active idle=5s"),
            self._create_event(120, "poll", "state=active idle=599s screen=on")
        ]

        with patch.object(ActivityService, '__init__', lambda x: None):
            service = ActivityService()
            service.repo = mock_repo_class.return_value # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType]
            service.repo.find_events_in_period.return_value = events # pyright: ignore[reportUnknownMemberType]

            periods = service.get_detailed_activity_periods(hours=1)

        active_period = periods[1]
        self.assertEqual(active_period["state"], "active")
        self.assertGreaterEqual(len(active_period["events"]), 2)

        self.skipTest('Test is incomplete')


if __name__ == "__main__":
    unittest.main()

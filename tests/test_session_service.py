"""Unit tests for SessionService."""
from typing import Any
import unittest
from unittest.mock import Mock
import datetime
from screentray.services.session_service import SessionService


class TestSessionService(unittest.TestCase):
    """Test session calculations."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.service = SessionService()
        self.base_time = datetime.datetime(2025, 1, 1, 12, 0, 0)

    def _mock_periods(self, periods: list[dict[str, object]]) -> None:
        """Mock ActivityService to return test periods with ISO timestamps."""
        formatted_periods: list[dict[str, Any]] = []
        for p in periods:
            formatted: dict[str, Any] = {
                "start": p["start"].isoformat() if isinstance(p["start"], datetime.datetime) else p["start"],
                "end": p["end"].isoformat() if isinstance(p["end"], datetime.datetime) else p["end"],
                "state": p["state"],
                "duration_sec": p["duration"]
            }
            formatted_periods.append(formatted)

        self.service.activity_service.get_detailed_activity_periods = Mock(
            return_value=formatted_periods
        )

    def test_no_session_when_inactive(self) -> None:
        """Inactive state = no current session."""
        self._mock_periods([
            {"start": self.base_time, "end": self.base_time + datetime.timedelta(minutes=5),
             "state": "inactive", "duration": 300.0}
        ])

        start, duration = self.service.get_current_session()

        self.assertIsNone(start)
        self.assertEqual(duration, 0.0)

    def test_current_session_returns_last_active_period(self) -> None:
        """Last period active = return its start and duration."""
        session_start = self.base_time + datetime.timedelta(minutes=5)
        self._mock_periods([
            {"start": self.base_time, "end": session_start,
             "state": "inactive", "duration": 300.0},
            {"start": session_start, "end": session_start + datetime.timedelta(minutes=10),
             "state": "active", "duration": 600.0}
        ])

        start, duration = self.service.get_current_session()

        self.assertIsNotNone(start)
        self.assertEqual(duration, 600.0)

    def test_last_break_returns_most_recent_inactive(self) -> None:
        """Find most recent inactive period."""
        break_start = self.base_time + datetime.timedelta(minutes=10)
        break_end = break_start + datetime.timedelta(minutes=5)
        self._mock_periods([
            {"start": self.base_time, "end": break_start,
             "state": "active", "duration": 600.0},
            {"start": break_start, "end": break_end,
             "state": "inactive", "duration": 300.0},
            {"start": break_end, "end": break_end + datetime.timedelta(minutes=5),
             "state": "active", "duration": 300.0}
        ])

        start, end, duration = self.service.get_last_break()

        self.assertIsNotNone(start)
        self.assertIsNotNone(end)
        self.assertEqual(duration, 300.0)

    def test_is_currently_active_checks_session(self) -> None:
        """is_currently_active = session duration > 0."""
        self._mock_periods([
            {"start": self.base_time, "end": self.base_time + datetime.timedelta(minutes=5),
             "state": "active", "duration": 300.0}
        ])

        self.assertTrue(self.service.is_currently_active())

        # Test inactive case
        self._mock_periods([
            {"start": self.base_time, "end": self.base_time + datetime.timedelta(minutes=5),
             "state": "inactive", "duration": 300.0}
        ])

        self.assertFalse(self.service.is_currently_active())


if __name__ == "__main__":
    unittest.main()

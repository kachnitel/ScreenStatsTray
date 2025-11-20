"""Unit tests for the main tracker service loop."""
import unittest
from unittest.mock import patch, MagicMock, ANY
import datetime
from screentray.tracker import main as tracker_main

class TestTrackerService(unittest.TestCase):
    """Test the main event loop and state transitions."""

    def setUp(self) -> None:
        # Use patch.object on the imported module to avoid path resolution errors
        self.mock_repo_patcher = patch.object(tracker_main, 'EventRepository')
        self.mock_plugin_patcher = patch.object(tracker_main, 'PluginManager')
        self.mock_platform_patcher = patch.object(tracker_main, 'platform')
        self.mock_ensure_db_patcher = patch.object(tracker_main, 'ensure_db_exists')

        # Patch time.sleep specifically in the main module's namespace
        self.mock_sleep_patcher = patch('screentray.tracker.main.time.sleep')

        # Patch constants
        self.mock_threshold_patcher = patch.object(tracker_main, 'IDLE_THRESHOLD_SEC', 60.0)
        self.mock_log_interval_patcher = patch.object(tracker_main, 'LOG_INTERVAL', 0.1)

        # Start patches
        self.mock_repo_cls = self.mock_repo_patcher.start()
        self.mock_plugin_cls = self.mock_plugin_patcher.start()
        self.mock_platform = self.mock_platform_patcher.start()
        self.mock_ensure_db = self.mock_ensure_db_patcher.start()
        self.mock_sleep = self.mock_sleep_patcher.start()
        self.mock_threshold_patcher.start()
        self.mock_log_interval_patcher.start()

        self.repo_instance = self.mock_repo_cls.return_value
        self.plugin_instance = self.mock_plugin_cls.return_value

        # Configure default return values for the platform mock.
        # Otherwise, they return MagicMocks which cause TypeErrors when compared to floats/bools.
        self.mock_platform.get_idle_seconds.return_value = 0.0
        self.mock_platform.is_screen_on.return_value = True
        self.mock_platform.get_active_window_info.return_value = ("TestApp", "TestWindow")

    def tearDown(self) -> None:
        self.mock_repo_patcher.stop()
        self.mock_plugin_patcher.stop()
        self.mock_platform_patcher.stop()
        self.mock_sleep_patcher.stop()
        self.mock_ensure_db_patcher.stop()
        self.mock_threshold_patcher.stop()
        self.mock_log_interval_patcher.stop()

    def test_startup_and_shutdown(self) -> None:
        """Test that the tracker initializes and shuts down gracefully."""
        # Setup: Sleep raises KeyboardInterrupt immediately to simulate user stopping app
        self.mock_sleep.side_effect = KeyboardInterrupt

        # Run
        tracker_main.main()

        # Verify Initialization
        self.mock_ensure_db.assert_called_once()
        self.mock_plugin_cls.assert_called()
        self.plugin_instance.discover_plugins.assert_called()
        self.plugin_instance.start_all.assert_called()

        # Verify Startup Event
        self.repo_instance.insert.assert_any_call("tracker_start")

        # Verify Shutdown
        self.plugin_instance.stop_all.assert_called()
        self.repo_instance.insert.assert_any_call("tracker_stop")

    @patch('screentray.tracker.main.get_idle_seconds')
    @patch('screentray.tracker.main.is_screen_on')
    def test_state_transitions(self, mock_is_screen_on: MagicMock, mock_get_idle: MagicMock) -> None:
        """
        Test the state machine:
        1. Unknown -> Active (Initial)
        2. Active -> Inactive (Idle threshold exceeded)
        3. Inactive -> Active (User returns)
        """
        # Configuration: Threshold is 60s (patched in setUp)

        # Iteration 1: 10s idle (Active) -> Initial State
        # Iteration 2: 100s idle (Inactive) -> Transition: idle_start
        # Iteration 3: 5s idle (Active) -> Transition: idle_end
        # Iteration 4: Stop
        mock_get_idle.side_effect = [10.0, 100.0, 5.0, 5.0]
        mock_is_screen_on.return_value = True

        # Sleep logic:
        # 1. Sleep after Init
        # 2. Sleep after Active->Inactive
        # 3. Sleep after Inactive->Active
        # 4. Raise KeyboardInterrupt
        self.mock_sleep.side_effect = [None, None, None, KeyboardInterrupt]

        # Run
        tracker_main.main()

        # --- Assertions ---

        # 1. Initial State Establishment
        # Should insert 'poll' with initial state
        self.repo_instance.insert.assert_any_call("poll", ANY)
        self.plugin_instance.notify_active.assert_any_call()

        # 2. Active -> Inactive (Idle)
        # Should insert 'idle_start'
        calls = self.repo_instance.insert.call_args_list
        idle_start_calls = [c for c in calls if c[0][0] == 'idle_start']
        self.assertEqual(len(idle_start_calls), 1)
        self.assertIn("idle 100s > 60.0s", idle_start_calls[0][0][1])

        self.plugin_instance.notify_inactive.assert_called()

        # 3. Inactive -> Active (Return)
        # Should insert 'idle_end'
        idle_end_calls = [c for c in calls if c[0][0] == 'idle_end']
        self.assertEqual(len(idle_end_calls), 1)
        self.assertIn("idle was 5s", idle_end_calls[0][0][1])

        # Notify active should be called twice (startup + return)
        self.assertEqual(self.plugin_instance.notify_active.call_count, 2)

    @patch('screentray.tracker.main.get_idle_seconds')
    @patch('screentray.tracker.main.is_screen_on')
    def test_screen_off_behavior(self, mock_is_screen_on: MagicMock, mock_get_idle: MagicMock) -> None:
        """Test transitions when screen turns off."""
        # Iteration 1: Active
        # Iteration 2: Screen Off (Inactive)
        # Iteration 3: Stop
        mock_get_idle.return_value = 10.0 # Low idle, but screen status dictates state
        mock_is_screen_on.side_effect = [True, False, False]

        self.mock_sleep.side_effect = [None, None, KeyboardInterrupt]

        # Run
        tracker_main.main()

        # Verify screen_off event
        self.repo_instance.insert.assert_any_call("screen_off")
        self.plugin_instance.notify_inactive.assert_called()

    @patch('screentray.tracker.main.datetime')
    @patch('screentray.tracker.main.get_idle_seconds')
    @patch('screentray.tracker.main.is_screen_on')
    def test_periodic_poll_logging(self, mock_is_screen_on: MagicMock, mock_get_idle: MagicMock, mock_dt: MagicMock) -> None:
        """Test that a 'poll' event is inserted every 60 seconds."""
        mock_get_idle.return_value = 10.0
        mock_is_screen_on.return_value = True

        # Mock time flow: Start, Loop 1 (Init), Loop 2 (No Poll), Loop 3 (+61s, Poll triggers)
        base_time = datetime.datetime(2025, 1, 1, 12, 0, 0)
        mock_dt.datetime.now.side_effect = [
            base_time, # Startup logging
            base_time, # Init loop start
            base_time, # Init log
            base_time + datetime.timedelta(seconds=10), # Loop 2 start (Diff < 60)
            base_time + datetime.timedelta(seconds=70), # Loop 3 start (Diff > 60)
            base_time + datetime.timedelta(seconds=70), # Loop 3 poll log
            base_time + datetime.timedelta(seconds=70), # Loop 3 end
            base_time + datetime.timedelta(seconds=70), # Stop log
        ]

        self.mock_sleep.side_effect = [None, None, KeyboardInterrupt]

        # Run
        tracker_main.main()

        # Verify 'poll' was called for the periodic update
        poll_calls = [c for c in self.repo_instance.insert.call_args_list if c[0][0] == 'poll']
        self.assertGreaterEqual(len(poll_calls), 2)

        self.plugin_instance.plugins.values.assert_called()


if __name__ == "__main__":
    unittest.main()

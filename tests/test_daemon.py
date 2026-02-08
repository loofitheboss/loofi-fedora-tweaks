"""
Tests for Daemon - Background service for scheduled task execution.
"""

import os
import sys
import signal
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add source path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.daemon import Daemon


class TestDaemonSignalHandler(unittest.TestCase):
    """Tests for signal handling."""

    def setUp(self):
        """Reset daemon state before each test."""
        Daemon._running = True

    def tearDown(self):
        """Restore daemon state after each test."""
        Daemon._running = True

    def test_signal_handler_sets_running_false(self):
        """signal_handler sets _running to False."""
        self.assertTrue(Daemon._running)
        Daemon.signal_handler(signal.SIGTERM, None)
        self.assertFalse(Daemon._running)

    def test_signal_handler_handles_sigint(self):
        """signal_handler handles SIGINT signal."""
        Daemon._running = True
        Daemon.signal_handler(signal.SIGINT, None)
        self.assertFalse(Daemon._running)


class TestGetPowerState(unittest.TestCase):
    """Tests for power state detection."""

    @patch('utils.daemon.subprocess.run')
    def test_get_power_state_ac_via_upower(self, mock_run):
        """get_power_state returns 'ac' when upower shows online."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="  native-path:        /sys/devices/...\n  online: yes\n"
        )
        result = Daemon.get_power_state()
        self.assertEqual(result, "ac")

    @patch('utils.daemon.subprocess.run')
    def test_get_power_state_battery_via_upower(self, mock_run):
        """get_power_state returns 'battery' when upower shows offline."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="  online:                 no\n"
        )
        # Will fall through to sys check, mock that too
        with patch.object(Path, 'exists', return_value=False):
            with patch.object(Path, 'glob', return_value=[]):
                result = Daemon.get_power_state()
                # Default is 'ac' when all checks fail
                self.assertEqual(result, "ac")

    @patch('utils.daemon.subprocess.run')
    @patch('builtins.open', new_callable=MagicMock)
    def test_get_power_state_ac_via_sys(self, mock_open, mock_run):
        """get_power_state reads from /sys as fallback."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")

        # Mock opening /sys/class/power_supply/AC0/online
        mock_file = MagicMock()
        mock_file.read.return_value = "1"
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)
        mock_open.return_value = mock_file

        with patch.object(Path, 'exists', return_value=True):
            result = Daemon.get_power_state()
            self.assertEqual(result, "ac")

    @patch('utils.daemon.subprocess.run')
    def test_get_power_state_exception_returns_ac(self, mock_run):
        """get_power_state returns 'ac' on exception."""
        mock_run.side_effect = Exception("Command failed")
        result = Daemon.get_power_state()
        self.assertEqual(result, "ac")


class TestCheckPowerTriggers(unittest.TestCase):
    """Tests for power-triggered tasks."""

    def setUp(self):
        """Reset power state before each test."""
        Daemon._last_power_state = None

    def tearDown(self):
        """Reset power state after test."""
        Daemon._last_power_state = None

    @patch('utils.daemon.Daemon.get_power_state', return_value='ac')
    @patch('utils.daemon.TaskScheduler', create=True)
    def test_check_power_triggers_initializes_state(self, mock_scheduler, mock_power):
        """check_power_triggers initializes _last_power_state on first call."""
        self.assertIsNone(Daemon._last_power_state)

        # Patch the import inside the method
        with patch.dict('sys.modules', {'utils.scheduler': MagicMock()}):
            Daemon.check_power_triggers()

        self.assertEqual(Daemon._last_power_state, 'ac')

    @patch('utils.daemon.Daemon.get_power_state')
    def test_check_power_triggers_detects_state_change(self, mock_power):
        """check_power_triggers detects power state changes."""
        Daemon._last_power_state = 'ac'
        mock_power.return_value = 'battery'

        mock_scheduler = MagicMock()
        mock_scheduler.get_power_trigger_tasks.return_value = []

        with patch.dict('sys.modules', {'utils.scheduler': MagicMock(TaskScheduler=mock_scheduler)}):
            Daemon.check_power_triggers()

        self.assertEqual(Daemon._last_power_state, 'battery')

    @patch('utils.daemon.Daemon.get_power_state', return_value='ac')
    def test_check_power_triggers_no_change(self, mock_power):
        """check_power_triggers does nothing when state unchanged."""
        Daemon._last_power_state = 'ac'

        with patch.dict('sys.modules', {'utils.scheduler': MagicMock()}):
            # Should not raise any errors
            Daemon.check_power_triggers()

        self.assertEqual(Daemon._last_power_state, 'ac')


class TestRunBootTasks(unittest.TestCase):
    """Tests for boot task execution."""

    @patch('utils.daemon.TaskScheduler', create=True)
    def test_run_boot_tasks_executes_all_boot_tasks(self, mock_scheduler_class):
        """run_boot_tasks executes all on_boot tasks."""
        mock_task1 = MagicMock(name="Task1")
        mock_task2 = MagicMock(name="Task2")

        mock_scheduler = MagicMock()
        mock_scheduler.get_boot_tasks.return_value = [mock_task1, mock_task2]

        with patch.dict('sys.modules', {'utils.scheduler': MagicMock(TaskScheduler=mock_scheduler)}):
            Daemon.run_boot_tasks()

        mock_scheduler.get_boot_tasks.assert_called_once()
        self.assertEqual(mock_scheduler.execute_task.call_count, 2)

    @patch('utils.daemon.TaskScheduler', create=True)
    def test_run_boot_tasks_empty_list(self, mock_scheduler_class):
        """run_boot_tasks handles empty task list."""
        mock_scheduler = MagicMock()
        mock_scheduler.get_boot_tasks.return_value = []

        with patch.dict('sys.modules', {'utils.scheduler': MagicMock(TaskScheduler=mock_scheduler)}):
            Daemon.run_boot_tasks()  # Should not raise

        mock_scheduler.get_boot_tasks.assert_called_once()
        mock_scheduler.execute_task.assert_not_called()


class TestRunDueTasks(unittest.TestCase):
    """Tests for due task execution."""

    @patch('utils.daemon.TaskScheduler', create=True)
    def test_run_due_tasks_executes_due_tasks(self, mock_scheduler_class):
        """run_due_tasks executes all due scheduled tasks."""
        mock_task = MagicMock(name="DueTask")

        mock_scheduler = MagicMock()
        mock_scheduler.get_due_tasks.return_value = [mock_task]
        mock_scheduler.execute_task.return_value = (True, "Success")

        with patch.dict('sys.modules', {'utils.scheduler': MagicMock(TaskScheduler=mock_scheduler)}):
            Daemon.run_due_tasks()

        mock_scheduler.get_due_tasks.assert_called_once()
        mock_scheduler.execute_task.assert_called_once_with(mock_task)

    @patch('utils.daemon.TaskScheduler', create=True)
    def test_run_due_tasks_no_due_tasks(self, mock_scheduler_class):
        """run_due_tasks does nothing when no tasks are due."""
        mock_scheduler = MagicMock()
        mock_scheduler.get_due_tasks.return_value = []

        with patch.dict('sys.modules', {'utils.scheduler': MagicMock(TaskScheduler=mock_scheduler)}):
            Daemon.run_due_tasks()

        mock_scheduler.get_due_tasks.assert_called_once()
        mock_scheduler.execute_task.assert_not_called()

    @patch('utils.daemon.TaskScheduler', create=True)
    def test_run_due_tasks_handles_task_failure(self, mock_scheduler_class):
        """run_due_tasks handles task execution failures."""
        mock_task = MagicMock(name="FailingTask")

        mock_scheduler = MagicMock()
        mock_scheduler.get_due_tasks.return_value = [mock_task]
        mock_scheduler.execute_task.return_value = (False, "Task failed")

        with patch.dict('sys.modules', {'utils.scheduler': MagicMock(TaskScheduler=mock_scheduler)}):
            Daemon.run_due_tasks()  # Should not raise

        mock_scheduler.execute_task.assert_called_once()


class TestDaemonRun(unittest.TestCase):
    """Tests for main daemon loop."""

    def setUp(self):
        """Reset daemon state before each test."""
        Daemon._running = True
        Daemon._last_power_state = None

    def tearDown(self):
        """Restore daemon state after each test."""
        Daemon._running = True
        Daemon._last_power_state = None

    @patch('utils.daemon.time.sleep')
    @patch('utils.daemon.signal.signal')
    @patch.object(Daemon, 'run_boot_tasks')
    @patch.object(Daemon, 'run_due_tasks')
    @patch.object(Daemon, 'check_power_triggers')
    def test_run_registers_signal_handlers(self, mock_power, mock_due, mock_boot, mock_signal, mock_sleep):
        """run() registers SIGTERM and SIGINT handlers."""
        # Stop after first iteration
        mock_sleep.side_effect = lambda x: setattr(Daemon, '_running', False)

        Daemon.run()

        calls = mock_signal.call_args_list
        signal_nums = [call[0][0] for call in calls]
        self.assertIn(signal.SIGTERM, signal_nums)
        self.assertIn(signal.SIGINT, signal_nums)

    @patch('utils.daemon.time.sleep')
    @patch('utils.daemon.signal.signal')
    @patch.object(Daemon, 'run_boot_tasks')
    @patch.object(Daemon, 'run_due_tasks')
    @patch.object(Daemon, 'check_power_triggers')
    def test_run_calls_boot_tasks_on_startup(self, mock_power, mock_due, mock_boot, mock_signal, mock_sleep):
        """run() calls run_boot_tasks on startup."""
        mock_sleep.side_effect = lambda x: setattr(Daemon, '_running', False)

        Daemon.run()

        mock_boot.assert_called_once()

    @patch('utils.daemon.time.time')
    @patch('utils.daemon.time.sleep')
    @patch('utils.daemon.signal.signal')
    @patch.object(Daemon, 'run_boot_tasks')
    @patch.object(Daemon, 'run_due_tasks')
    @patch.object(Daemon, 'check_power_triggers')
    def test_run_stops_on_running_false(self, mock_power, mock_due, mock_boot, mock_signal, mock_sleep, mock_time):
        """run() stops when _running is set to False."""
        mock_time.return_value = 1000
        call_count = [0]

        def stop_after_iterations(x):
            call_count[0] += 1
            if call_count[0] >= 2:
                Daemon._running = False

        mock_sleep.side_effect = stop_after_iterations

        Daemon.run()

        self.assertFalse(Daemon._running)


class TestDaemonConstants(unittest.TestCase):
    """Tests for daemon constants."""

    def test_check_interval_is_reasonable(self):
        """CHECK_INTERVAL is a reasonable value (5 minutes)."""
        self.assertEqual(Daemon.CHECK_INTERVAL, 300)

    def test_power_check_interval_is_reasonable(self):
        """POWER_CHECK_INTERVAL is a reasonable value (30 seconds)."""
        self.assertEqual(Daemon.POWER_CHECK_INTERVAL, 30)


class TestDaemonMain(unittest.TestCase):
    """Tests for daemon main entry point."""

    @patch.object(Daemon, 'run')
    def test_main_calls_daemon_run(self, mock_run):
        """main() calls Daemon.run()."""
        from utils.daemon import main
        main()
        mock_run.assert_called_once()


if __name__ == '__main__':
    unittest.main()

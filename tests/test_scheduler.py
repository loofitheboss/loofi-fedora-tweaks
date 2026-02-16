"""
Tests for utils/scheduler.py
"""
import unittest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.scheduler import ScheduledTask, TaskScheduler, TaskSchedule, TaskAction


class TestScheduledTask(unittest.TestCase):
    """Tests for ScheduledTask helpers."""

    def test_is_due_disabled_task(self):
        """Disabled tasks are never due."""
        task = ScheduledTask(id="t1", name="x", action=TaskAction.CLEANUP.value, schedule=TaskSchedule.DAILY.value, enabled=False)
        self.assertFalse(task.is_due())

    def test_is_due_without_last_run(self):
        """Enabled periodic tasks with no last_run are due."""
        task = ScheduledTask(id="t2", name="x", action=TaskAction.CLEANUP.value, schedule=TaskSchedule.HOURLY.value)
        self.assertTrue(task.is_due())

    def test_is_due_on_boot_is_special(self):
        """ON_BOOT tasks are handled separately and not returned as due."""
        task = ScheduledTask(id="t3", name="x", action=TaskAction.CLEANUP.value, schedule=TaskSchedule.ON_BOOT.value)
        self.assertFalse(task.is_due())

    @patch('utils.scheduler.datetime')
    def test_is_due_hourly_not_due_yet(self, mock_dt):
        """Hourly task is not due when less than one hour passed."""
        mock_last = MagicMock()
        mock_now = MagicMock()
        mock_now.__sub__.return_value = __import__('datetime').timedelta(minutes=30)
        mock_dt.fromisoformat.return_value = mock_last
        mock_dt.now.return_value = mock_now

        task = ScheduledTask(
            id="t4",
            name="x",
            action=TaskAction.CLEANUP.value,
            schedule=TaskSchedule.HOURLY.value,
            last_run="2026-02-13T10:00:00",
        )
        self.assertFalse(task.is_due())

    def test_is_due_invalid_last_run_fallback_true(self):
        """Invalid timestamps fall back to due=True."""
        task = ScheduledTask(
            id="t5",
            name="x",
            action=TaskAction.CLEANUP.value,
            schedule=TaskSchedule.DAILY.value,
            last_run="not-a-timestamp",
        )
        self.assertTrue(task.is_due())


class TestTaskScheduler(unittest.TestCase):
    """Tests for TaskScheduler behavior."""

    @patch('utils.scheduler.TaskScheduler.save_tasks', return_value=True)
    @patch('utils.scheduler.TaskScheduler.list_tasks')
    def test_add_task_duplicate_id_returns_false(self, mock_list_tasks, mock_save):
        """Adding a duplicate task id fails."""
        existing = ScheduledTask(id="dup", name="e", action=TaskAction.CLEANUP.value, schedule=TaskSchedule.DAILY.value)
        mock_list_tasks.return_value = [existing]

        new_task = ScheduledTask(id="dup", name="n", action=TaskAction.CLEANUP.value, schedule=TaskSchedule.DAILY.value)
        self.assertFalse(TaskScheduler.add_task(new_task))
        mock_save.assert_not_called()

    @patch('utils.scheduler.TaskScheduler.list_tasks', return_value=[])
    def test_execute_task_unknown_action(self, mock_list_tasks):
        """Unknown actions are rejected."""
        task = ScheduledTask(id="x", name="Unknown", action="invalid", schedule=TaskSchedule.DAILY.value)
        success, message = TaskScheduler.execute_task(task)
        self.assertFalse(success)
        self.assertIn("Disallowed action", message)

    @patch('utils.notifications.NotificationManager.notify_task_complete')
    @patch('utils.scheduler.TaskScheduler.update_last_run', return_value=True)
    @patch('utils.scheduler.TaskScheduler._run_cleanup', return_value=(True, 'Cleanup completed'))
    def test_execute_task_cleanup_success(self, mock_cleanup, mock_update, mock_notify):
        """Cleanup action executes, updates timestamp, and sends notification."""
        task = ScheduledTask(id="c1", name="Cleanup", action=TaskAction.CLEANUP.value, schedule=TaskSchedule.DAILY.value)

        result = TaskScheduler.execute_task(task)

        self.assertEqual(result, (True, 'Cleanup completed'))
        mock_cleanup.assert_called_once()
        mock_update.assert_called_once_with("c1")
        mock_notify.assert_called_once_with("Cleanup", True)

    @patch('utils.scheduler.TaskScheduler.execute_task')
    @patch('utils.scheduler.TaskScheduler.get_due_tasks')
    def test_run_due_tasks_collects_results(self, mock_due, mock_execute):
        """run_due_tasks returns summarized per-task results."""
        t1 = ScheduledTask(id="1", name="One", action=TaskAction.CLEANUP.value, schedule=TaskSchedule.DAILY.value)
        t2 = ScheduledTask(id="2", name="Two", action=TaskAction.UPDATE_CHECK.value, schedule=TaskSchedule.DAILY.value)
        mock_due.return_value = [t1, t2]
        mock_execute.side_effect = [(True, "ok"), (False, "err")]

        results = TaskScheduler.run_due_tasks()

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["task"], "One")
        self.assertTrue(results[0]["success"])
        self.assertEqual(results[1]["task"], "Two")
        self.assertFalse(results[1]["success"])

    @patch('utils.notifications.NotificationManager.notify_updates_available')
    @patch('utils.scheduler.subprocess.run')
    def test_run_update_check_updates_available(self, mock_run, mock_notify):
        """dnf return code 100 reports update availability."""
        mock_run.return_value = MagicMock(returncode=100, stdout="pkg1\npkg2\n", stderr="")

        success, message = TaskScheduler._run_update_check()

        self.assertTrue(success)
        self.assertIn("updates available", message)
        mock_notify.assert_called_once_with(2)

    @patch('utils.scheduler.subprocess.run')
    def test_is_service_enabled_true(self, mock_run):
        """is_service_enabled parses systemctl output."""
        mock_run.return_value = MagicMock(stdout="enabled\n", returncode=0)
        self.assertTrue(TaskScheduler.is_service_enabled())

    @patch('utils.scheduler.subprocess.run')
    def test_is_service_running_true(self, mock_run):
        """is_service_running parses systemctl output."""
        mock_run.return_value = MagicMock(stdout="active\n", returncode=0)
        self.assertTrue(TaskScheduler.is_service_running())

    @patch('utils.scheduler.subprocess.run', side_effect=OSError("boom"))
    def test_enable_service_failure(self, mock_run):
        """Service enable errors return False."""
        self.assertFalse(TaskScheduler.enable_service())


if __name__ == '__main__':
    unittest.main()

"""
Tests for utils/scheduler.py — ScheduledTask + TaskScheduler.
Covers task CRUD, due-check logic, service management, and task execution.
All system calls mocked.
"""

import json
import os
import subprocess
import sys
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, mock_open, patch

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.scheduler import (
    ScheduledTask,
    TaskAction,
    TaskSchedule,
    TaskScheduler,
)


# ---------------------------------------------------------------------------
# ScheduledTask dataclass
# ---------------------------------------------------------------------------
class TestScheduledTask(unittest.TestCase):
    """ScheduledTask to_dict / from_dict / is_due."""

    def _task(self, **overrides):
        defaults = dict(
            id="t1", name="Test", action="cleanup",
            schedule="daily", enabled=True, last_run=None,
        )
        defaults.update(overrides)
        return ScheduledTask(**defaults)

    # -- serialization -------------------------------------------------------
    def test_to_dict_roundtrip(self):
        t = self._task(preset_name="foo")
        d = t.to_dict()
        self.assertEqual(d["id"], "t1")
        self.assertEqual(d["preset_name"], "foo")
        t2 = ScheduledTask.from_dict(d)
        self.assertEqual(t2, t)

    def test_from_dict_minimal(self):
        t = ScheduledTask.from_dict({"id": "x", "name": "N", "action": "cleanup", "schedule": "hourly"})
        self.assertTrue(t.enabled)
        self.assertIsNone(t.last_run)

    # -- is_due: disabled ----------------------------------------------------
    def test_is_due_disabled(self):
        self.assertFalse(self._task(enabled=False).is_due())

    # -- is_due: boot / power triggers return False --------------------------
    def test_is_due_on_boot(self):
        self.assertFalse(self._task(schedule="on_boot").is_due())

    def test_is_due_on_battery(self):
        self.assertFalse(self._task(schedule="on_battery").is_due())

    def test_is_due_on_ac(self):
        self.assertFalse(self._task(schedule="on_ac").is_due())

    # -- is_due: never run => True -------------------------------------------
    def test_is_due_never_run(self):
        self.assertTrue(self._task(last_run=None).is_due())

    # -- is_due: hourly ------------------------------------------------------
    def test_is_due_hourly_stale(self):
        past = (datetime.now() - timedelta(hours=2)).isoformat()
        self.assertTrue(self._task(schedule="hourly", last_run=past).is_due())

    def test_is_due_hourly_recent(self):
        recent = (datetime.now() - timedelta(minutes=10)).isoformat()
        self.assertFalse(self._task(schedule="hourly", last_run=recent).is_due())

    # -- is_due: daily -------------------------------------------------------
    def test_is_due_daily_stale(self):
        past = (datetime.now() - timedelta(days=2)).isoformat()
        self.assertTrue(self._task(schedule="daily", last_run=past).is_due())

    def test_is_due_daily_recent(self):
        recent = (datetime.now() - timedelta(hours=6)).isoformat()
        self.assertFalse(self._task(schedule="daily", last_run=recent).is_due())

    # -- is_due: weekly ------------------------------------------------------
    def test_is_due_weekly_stale(self):
        past = (datetime.now() - timedelta(weeks=2)).isoformat()
        self.assertTrue(self._task(schedule="weekly", last_run=past).is_due())

    def test_is_due_weekly_recent(self):
        recent = (datetime.now() - timedelta(days=3)).isoformat()
        self.assertFalse(self._task(schedule="weekly", last_run=recent).is_due())

    # -- is_due: invalid timestamp => True -----------------------------------
    def test_is_due_invalid_timestamp(self):
        self.assertTrue(self._task(last_run="not-a-date").is_due())

    # -- is_due: unknown schedule => False (falls through) -------------------
    def test_is_due_unknown_schedule(self):
        self.assertFalse(self._task(schedule="monthly", last_run=(datetime.now() - timedelta(days=100)).isoformat()).is_due())


# ---------------------------------------------------------------------------
# TaskScheduler — CRUD
# ---------------------------------------------------------------------------
class TestTaskSchedulerCRUD(unittest.TestCase):
    """list / save / add / remove / enable / update_last_run."""

    def _sample_data(self):
        return {"tasks": [
            {"id": "a", "name": "A", "action": "cleanup", "schedule": "daily", "enabled": True, "last_run": None, "preset_name": None},
        ]}

    @patch("utils.scheduler.TaskScheduler.CONFIG_FILE")
    @patch("utils.scheduler.TaskScheduler.CONFIG_DIR")
    def test_list_tasks_empty_file(self, mock_dir, mock_file):
        mock_dir.mkdir = MagicMock()
        mock_file.exists.return_value = False
        self.assertEqual(TaskScheduler.list_tasks(), [])

    @patch("builtins.open", new_callable=mock_open, read_data='{"tasks":[]}')
    @patch("utils.scheduler.TaskScheduler.CONFIG_FILE")
    @patch("utils.scheduler.TaskScheduler.CONFIG_DIR")
    def test_list_tasks_empty_list(self, mock_dir, mock_file, _open):
        mock_dir.mkdir = MagicMock()
        mock_file.exists.return_value = True
        self.assertEqual(TaskScheduler.list_tasks(), [])

    @patch("builtins.open", new_callable=mock_open, read_data='INVALID')
    @patch("utils.scheduler.TaskScheduler.CONFIG_FILE")
    @patch("utils.scheduler.TaskScheduler.CONFIG_DIR")
    def test_list_tasks_corrupt_json(self, mock_dir, mock_file, _open):
        mock_dir.mkdir = MagicMock()
        mock_file.exists.return_value = True
        self.assertEqual(TaskScheduler.list_tasks(), [])

    @patch("builtins.open", new_callable=mock_open)
    @patch("utils.scheduler.TaskScheduler.CONFIG_FILE")
    @patch("utils.scheduler.TaskScheduler.CONFIG_DIR")
    def test_list_tasks_with_data(self, mock_dir, mock_file, mopen):
        mock_dir.mkdir = MagicMock()
        mock_file.exists.return_value = True
        mopen.return_value.read.return_value = json.dumps(self._sample_data())
        mopen.return_value.__enter__ = lambda s: s
        mopen.return_value.__exit__ = MagicMock(return_value=False)
        # Use json.load mock
        with patch("json.load", return_value=self._sample_data()):
            tasks = TaskScheduler.list_tasks()
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].id, "a")

    @patch("builtins.open", new_callable=mock_open)
    @patch("utils.scheduler.TaskScheduler.CONFIG_FILE")
    @patch("utils.scheduler.TaskScheduler.CONFIG_DIR")
    def test_save_tasks_success(self, mock_dir, mock_file, mopen):
        mock_dir.mkdir = MagicMock()
        task = ScheduledTask(id="x", name="X", action="cleanup", schedule="daily")
        result = TaskScheduler.save_tasks([task])
        self.assertTrue(result)

    @patch("builtins.open", side_effect=OSError("disk full"))
    @patch("utils.scheduler.TaskScheduler.CONFIG_FILE")
    @patch("utils.scheduler.TaskScheduler.CONFIG_DIR")
    def test_save_tasks_failure(self, mock_dir, mock_file, _open):
        mock_dir.mkdir = MagicMock()
        self.assertFalse(TaskScheduler.save_tasks([]))

    @patch.object(TaskScheduler, "save_tasks", return_value=True)
    @patch.object(TaskScheduler, "list_tasks", return_value=[])
    def test_add_task_success(self, _list, _save):
        t = ScheduledTask(id="n", name="N", action="cleanup", schedule="daily")
        self.assertTrue(TaskScheduler.add_task(t))
        _save.assert_called_once()

    @patch.object(TaskScheduler, "list_tasks")
    def test_add_task_duplicate(self, mock_list):
        existing = ScheduledTask(id="dup", name="D", action="cleanup", schedule="daily")
        mock_list.return_value = [existing]
        self.assertFalse(TaskScheduler.add_task(existing))

    @patch.object(TaskScheduler, "save_tasks", return_value=True)
    @patch.object(TaskScheduler, "list_tasks")
    def test_remove_task_found(self, mock_list, _save):
        mock_list.return_value = [
            ScheduledTask(id="a", name="A", action="cleanup", schedule="daily"),
        ]
        self.assertTrue(TaskScheduler.remove_task("a"))

    @patch.object(TaskScheduler, "list_tasks", return_value=[])
    def test_remove_task_not_found(self, _list):
        self.assertFalse(TaskScheduler.remove_task("nope"))

    @patch.object(TaskScheduler, "save_tasks", return_value=True)
    @patch.object(TaskScheduler, "list_tasks")
    def test_enable_task_found(self, mock_list, _save):
        t = ScheduledTask(id="a", name="A", action="cleanup", schedule="daily", enabled=True)
        mock_list.return_value = [t]
        self.assertTrue(TaskScheduler.enable_task("a", False))

    @patch.object(TaskScheduler, "list_tasks", return_value=[])
    def test_enable_task_not_found(self, _list):
        self.assertFalse(TaskScheduler.enable_task("nope", True))

    @patch.object(TaskScheduler, "save_tasks", return_value=True)
    @patch.object(TaskScheduler, "list_tasks")
    def test_update_last_run_found(self, mock_list, _save):
        t = ScheduledTask(id="a", name="A", action="cleanup", schedule="daily")
        mock_list.return_value = [t]
        self.assertTrue(TaskScheduler.update_last_run("a"))

    @patch.object(TaskScheduler, "list_tasks", return_value=[])
    def test_update_last_run_not_found(self, _list):
        self.assertFalse(TaskScheduler.update_last_run("nope"))


# ---------------------------------------------------------------------------
# TaskScheduler — query helpers
# ---------------------------------------------------------------------------
class TestTaskSchedulerQueries(unittest.TestCase):

    @patch.object(TaskScheduler, "list_tasks")
    def test_get_due_tasks(self, mock_list):
        stale = ScheduledTask(id="s", name="S", action="cleanup", schedule="daily", last_run=None)
        fresh = ScheduledTask(id="f", name="F", action="cleanup", schedule="daily",
                              last_run=datetime.now().isoformat())
        mock_list.return_value = [stale, fresh]
        due = TaskScheduler.get_due_tasks()
        self.assertEqual(len(due), 1)
        self.assertEqual(due[0].id, "s")

    @patch.object(TaskScheduler, "list_tasks")
    def test_get_power_trigger_tasks_battery(self, mock_list):
        t = ScheduledTask(id="b", name="B", action="cleanup", schedule="on_battery")
        mock_list.return_value = [t]
        self.assertEqual(len(TaskScheduler.get_power_trigger_tasks(True)), 1)
        self.assertEqual(len(TaskScheduler.get_power_trigger_tasks(False)), 0)

    @patch.object(TaskScheduler, "list_tasks")
    def test_get_power_trigger_tasks_ac(self, mock_list):
        t = ScheduledTask(id="a", name="A", action="cleanup", schedule="on_ac")
        mock_list.return_value = [t]
        self.assertEqual(len(TaskScheduler.get_power_trigger_tasks(False)), 1)

    @patch.object(TaskScheduler, "list_tasks")
    def test_get_boot_tasks(self, mock_list):
        boot = ScheduledTask(id="b", name="B", action="cleanup", schedule="on_boot")
        daily = ScheduledTask(id="d", name="D", action="cleanup", schedule="daily")
        mock_list.return_value = [boot, daily]
        self.assertEqual(len(TaskScheduler.get_boot_tasks()), 1)


# ---------------------------------------------------------------------------
# TaskScheduler — execute_task
# ---------------------------------------------------------------------------
class TestTaskSchedulerExecution(unittest.TestCase):

    @patch("utils.scheduler.TaskScheduler.update_last_run", return_value=True)
    @patch("utils.scheduler.TaskScheduler._run_cleanup", return_value=(True, "OK"))
    @patch("utils.notifications.NotificationManager.notify_task_complete")
    def test_execute_cleanup(self, mock_notify, mock_cleanup, _upd):
        t = ScheduledTask(id="c", name="Clean", action="cleanup", schedule="daily")
        ok, msg = TaskScheduler.execute_task(t)
        self.assertTrue(ok)
        mock_cleanup.assert_called_once()

    @patch("utils.scheduler.TaskScheduler.update_last_run", return_value=True)
    @patch("utils.scheduler.TaskScheduler._run_update_check", return_value=(True, "5 updates available"))
    @patch("utils.notifications.NotificationManager.notify_task_complete")
    def test_execute_update_check(self, mock_notify, mock_check, _upd):
        t = ScheduledTask(id="u", name="Upd", action="update_check", schedule="daily")
        ok, msg = TaskScheduler.execute_task(t)
        self.assertTrue(ok)

    @patch("utils.scheduler.TaskScheduler.update_last_run", return_value=True)
    @patch("utils.scheduler.TaskScheduler._run_sync_config", return_value=(True, "synced"))
    @patch("utils.notifications.NotificationManager.notify_task_complete")
    def test_execute_sync_config(self, _n, _sync, _upd):
        t = ScheduledTask(id="s", name="Sync", action="sync_config", schedule="daily")
        ok, _ = TaskScheduler.execute_task(t)
        self.assertTrue(ok)

    @patch("utils.scheduler.TaskScheduler.update_last_run", return_value=True)
    @patch("utils.scheduler.TaskScheduler._run_apply_preset", return_value=(True, "applied"))
    @patch("utils.notifications.NotificationManager.notify_task_complete")
    def test_execute_apply_preset(self, _n, _ap, _upd):
        t = ScheduledTask(id="p", name="Preset", action="apply_preset", schedule="daily", preset_name="mypreset")
        ok, _ = TaskScheduler.execute_task(t)
        self.assertTrue(ok)

    def test_execute_unknown_action(self):
        t = ScheduledTask(id="u", name="Unk", action="nonexistent", schedule="daily")
        ok, msg = TaskScheduler.execute_task(t)
        self.assertFalse(ok)
        self.assertIn("Disallowed action", msg)

    @patch("utils.scheduler.TaskScheduler._run_cleanup", side_effect=OSError("fail"))
    def test_execute_oserror(self, _):
        t = ScheduledTask(id="e", name="Err", action="cleanup", schedule="daily")
        ok, msg = TaskScheduler.execute_task(t)
        self.assertFalse(ok)

    @patch.object(TaskScheduler, "get_due_tasks")
    @patch.object(TaskScheduler, "execute_task", return_value=(True, "done"))
    def test_run_due_tasks(self, mock_exec, mock_due):
        t1 = ScheduledTask(id="1", name="T1", action="cleanup", schedule="daily")
        mock_due.return_value = [t1]
        results = TaskScheduler.run_due_tasks()
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["success"])


# ---------------------------------------------------------------------------
# Task implementations
# ---------------------------------------------------------------------------
class TestTaskImplementations(unittest.TestCase):

    @patch("subprocess.run")
    @patch("utils.notifications.NotificationManager.notify_cleanup_complete")
    def test_run_cleanup_success(self, _notify, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        ok, msg = TaskScheduler._run_cleanup()
        self.assertTrue(ok)
        self.assertIn("Cleanup", msg)

    @patch("subprocess.run", side_effect=OSError("nope"))
    def test_run_cleanup_failure(self, _):
        ok, msg = TaskScheduler._run_cleanup()
        self.assertFalse(ok)

    @patch("subprocess.run")
    @patch("utils.notifications.NotificationManager.notify_updates_available")
    def test_run_update_check_updates_available(self, mock_notify, mock_run):
        mock_run.return_value = MagicMock(returncode=100, stdout="pkg1\npkg2\n")
        ok, msg = TaskScheduler._run_update_check()
        self.assertTrue(ok)
        self.assertIn("2 updates", msg)

    @patch("subprocess.run")
    def test_run_update_check_up_to_date(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        ok, msg = TaskScheduler._run_update_check()
        self.assertTrue(ok)
        self.assertIn("up to date", msg)

    @patch("subprocess.run", side_effect=OSError("fail"))
    def test_run_update_check_error(self, _):
        ok, msg = TaskScheduler._run_update_check()
        self.assertFalse(ok)

    @patch("utils.cloud_sync.CloudSyncManager.sync_to_gist", return_value=(True, "synced"))
    @patch("utils.config_manager.ConfigManager.export_all", return_value={})
    @patch("utils.notifications.NotificationManager.notify_sync_complete")
    def test_run_sync_config_success(self, _n, _exp, _sync):
        ok, msg = TaskScheduler._run_sync_config()
        self.assertTrue(ok)

    @patch("utils.cloud_sync.CloudSyncManager.sync_to_gist", return_value=(False, "token missing"))
    @patch("utils.config_manager.ConfigManager.export_all", return_value={})
    def test_run_sync_config_failure(self, _exp, _sync):
        ok, msg = TaskScheduler._run_sync_config()
        self.assertFalse(ok)

    @patch("utils.cloud_sync.CloudSyncManager.sync_to_gist", side_effect=ImportError("no module"))
    @patch("utils.config_manager.ConfigManager.export_all", side_effect=ImportError("no module"))
    def test_run_sync_config_import_error(self, _a, _b):
        ok, msg = TaskScheduler._run_sync_config()
        self.assertFalse(ok)

    def test_run_apply_preset_no_name(self):
        ok, msg = TaskScheduler._run_apply_preset(None)
        self.assertFalse(ok)
        self.assertIn("No preset name", msg)

    @patch("utils.presets.PresetManager")
    @patch("utils.notifications.NotificationManager.notify_preset_applied")
    def test_run_apply_preset_found(self, _n, MockPM):
        inst = MockPM.return_value
        inst.load_preset.return_value = {"tweaks": []}
        ok, msg = TaskScheduler._run_apply_preset("mypreset")
        self.assertTrue(ok)
        self.assertIn("mypreset", msg)

    @patch("utils.presets.PresetManager")
    def test_run_apply_preset_not_found(self, MockPM):
        inst = MockPM.return_value
        inst.load_preset.return_value = None
        ok, msg = TaskScheduler._run_apply_preset("missing")
        self.assertFalse(ok)
        self.assertIn("not found", msg)

    @patch("utils.presets.PresetManager", side_effect=ImportError("no module"))
    def test_run_apply_preset_import_error(self, _):
        ok, msg = TaskScheduler._run_apply_preset("x")
        self.assertFalse(ok)


# ---------------------------------------------------------------------------
# Service management
# ---------------------------------------------------------------------------
class TestServiceManagement(unittest.TestCase):

    @patch("subprocess.run")
    def test_is_service_enabled_true(self, mock_run):
        mock_run.return_value = MagicMock(stdout="enabled\n")
        self.assertTrue(TaskScheduler.is_service_enabled())

    @patch("subprocess.run")
    def test_is_service_enabled_false(self, mock_run):
        mock_run.return_value = MagicMock(stdout="disabled\n")
        self.assertFalse(TaskScheduler.is_service_enabled())

    @patch("subprocess.run", side_effect=OSError("no systemctl"))
    def test_is_service_enabled_error(self, _):
        self.assertFalse(TaskScheduler.is_service_enabled())

    @patch("subprocess.run")
    def test_is_service_running_true(self, mock_run):
        mock_run.return_value = MagicMock(stdout="active\n")
        self.assertTrue(TaskScheduler.is_service_running())

    @patch("subprocess.run")
    def test_is_service_running_false(self, mock_run):
        mock_run.return_value = MagicMock(stdout="inactive\n")
        self.assertFalse(TaskScheduler.is_service_running())

    @patch("subprocess.run", side_effect=OSError("no systemctl"))
    def test_is_service_running_error(self, _):
        self.assertFalse(TaskScheduler.is_service_running())

    @patch("subprocess.run")
    def test_enable_service_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        self.assertTrue(TaskScheduler.enable_service())

    @patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "systemctl"))
    def test_enable_service_failure(self, _):
        self.assertFalse(TaskScheduler.enable_service())

    @patch("subprocess.run")
    def test_disable_service_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        self.assertTrue(TaskScheduler.disable_service())

    @patch("subprocess.run", side_effect=OSError("fail"))
    def test_disable_service_failure(self, _):
        self.assertFalse(TaskScheduler.disable_service())


if __name__ == "__main__":
    unittest.main()

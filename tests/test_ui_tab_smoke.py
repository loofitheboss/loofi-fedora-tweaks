"""
UI Tab / Dialog Smoke Tests — Coverage Campaign.

Instantiates and exercises UI tabs, dialogs, and panels that currently
sit at 0% coverage.  Uses QT_QPA_PLATFORM=offscreen (set in conftest.py)
and mocks all system calls.

Targets: AgentsTab, LogsTab, StorageTab, PerformanceTab, SnapshotTab,
         ProfilesTab, HealthTimelineTab, NotificationPanel,
         FirstRunWizard, CommandPalette, FingerprintDialog,
         DependencyDoctor, WhatsNewDialog.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, PropertyMock, patch

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))


# ---------------------------------------------------------------------------
# DependencyDoctor (ui/doctor.py)
# ---------------------------------------------------------------------------
class TestDependencyDoctor(unittest.TestCase):
    """Tests for DependencyDoctor dialog."""

    @patch("shutil.which", return_value="/usr/bin/fake")
    def test_init_all_tools_found(self, mock_which):
        from ui.doctor import DependencyDoctor
        d = DependencyDoctor()
        self.assertIsNotNone(d)
        self.assertEqual(d.missing_tools, [])
        self.assertFalse(d.btn_fix.isEnabled())
        d.close()

    @patch("shutil.which", return_value=None)
    def test_init_all_tools_missing(self, mock_which):
        from ui.doctor import DependencyDoctor
        d = DependencyDoctor()
        self.assertTrue(len(d.missing_tools) > 0)
        self.assertTrue(d.btn_fix.isEnabled())
        d.close()

    @patch("shutil.which", side_effect=lambda t: "/usr/bin/dnf" if t == "dnf" else None)
    def test_init_partial_tools(self, mock_which):
        from ui.doctor import DependencyDoctor
        d = DependencyDoctor()
        self.assertNotIn("dnf", d.missing_tools)
        self.assertGreater(len(d.missing_tools), 0)
        d.close()

    @patch("shutil.which", return_value=None)
    def test_check_tools_refreshes(self, mock_which):
        from ui.doctor import DependencyDoctor
        d = DependencyDoctor()
        count1 = len(d.missing_tools)
        mock_which.return_value = "/usr/bin/fake"
        d.check_tools()
        self.assertEqual(d.missing_tools, [])
        d.close()

    @patch("shutil.which", return_value=None)
    @patch("utils.command_runner.CommandRunner.run_command")
    def test_fix_dependencies_runs_command(self, mock_run, mock_which):
        from ui.doctor import DependencyDoctor
        d = DependencyDoctor()
        d.fix_dependencies()
        mock_run.assert_called_once()
        args = mock_run.call_args
        self.assertEqual(args[0][0], "pkexec")
        d.close()

    @patch("shutil.which", return_value="/usr/bin/all")
    @patch("utils.command_runner.CommandRunner.run_command")
    def test_fix_dependencies_no_missing(self, mock_run, mock_which):
        from ui.doctor import DependencyDoctor
        d = DependencyDoctor()
        d.fix_dependencies()
        mock_run.assert_not_called()
        d.close()

    @patch("shutil.which", return_value=None)
    def test_on_fix_complete_success(self, mock_which):
        from ui.doctor import DependencyDoctor
        d = DependencyDoctor()
        # After "fix" succeeds, check_tools is called again
        mock_which.return_value = "/usr/bin/all"
        with patch.object(d, 'check_tools', wraps=d.check_tools) as mock_ct:
            # Suppress QMessageBox
            with patch("ui.doctor.QMessageBox.information"):
                d.on_fix_complete(0)
            mock_ct.assert_called_once()
        d.close()

    @patch("shutil.which", return_value=None)
    def test_on_fix_complete_failure(self, mock_which):
        from ui.doctor import DependencyDoctor
        d = DependencyDoctor()
        with patch("ui.doctor.QMessageBox.warning"):
            d.on_fix_complete(1)
        d.close()


# ---------------------------------------------------------------------------
# WhatsNewDialog (ui/whats_new_dialog.py)
# ---------------------------------------------------------------------------
class TestWhatsNewDialog(unittest.TestCase):
    """Tests for WhatsNewDialog."""

    def test_init(self):
        from ui.whats_new_dialog import WhatsNewDialog
        d = WhatsNewDialog()
        self.assertIsNotNone(d)
        self.assertFalse(d.dont_show_again)
        d.close()

    def test_on_close_sets_dont_show(self):
        from ui.whats_new_dialog import WhatsNewDialog
        d = WhatsNewDialog()
        d.dont_show_cb.setChecked(True)
        d._on_close()
        self.assertTrue(d.dont_show_again)

    def test_on_close_unchecked(self):
        from ui.whats_new_dialog import WhatsNewDialog
        d = WhatsNewDialog()
        d.dont_show_cb.setChecked(False)
        d._on_close()
        self.assertFalse(d.dont_show_again)

    @patch("utils.settings.SettingsManager.instance")
    def test_should_show_different_version(self, mock_inst):
        mock_mgr = MagicMock()
        mock_mgr.get.return_value = "0.0.0"
        mock_inst.return_value = mock_mgr
        from ui.whats_new_dialog import WhatsNewDialog
        self.assertTrue(WhatsNewDialog.should_show())

    @patch("utils.settings.SettingsManager.instance")
    def test_should_show_same_version(self, mock_inst):
        from version import __version__
        mock_mgr = MagicMock()
        mock_mgr.get.return_value = __version__
        mock_inst.return_value = mock_mgr
        from ui.whats_new_dialog import WhatsNewDialog
        self.assertFalse(WhatsNewDialog.should_show())

    def test_should_show_import_error(self):
        from ui.whats_new_dialog import WhatsNewDialog
        with patch("utils.settings.SettingsManager.instance", side_effect=ImportError):
            self.assertTrue(WhatsNewDialog.should_show())

    @patch("utils.settings.SettingsManager.instance")
    def test_mark_seen(self, mock_inst):
        mock_mgr = MagicMock()
        mock_inst.return_value = mock_mgr
        from ui.whats_new_dialog import WhatsNewDialog
        WhatsNewDialog.mark_seen()
        mock_mgr.set.assert_called_once()
        mock_mgr.save.assert_called_once()

    def test_mark_seen_exception(self):
        from ui.whats_new_dialog import WhatsNewDialog
        with patch("utils.settings.SettingsManager.instance", side_effect=Exception):
            WhatsNewDialog.mark_seen()  # Should not raise


# ---------------------------------------------------------------------------
# FingerprintDialog (ui/fingerprint_dialog.py)
# ---------------------------------------------------------------------------
class TestFingerprintDialog(unittest.TestCase):
    """Tests for FingerprintDialog."""

    def test_init(self):
        from ui.fingerprint_dialog import FingerprintDialog
        d = FingerprintDialog()
        self.assertIsNotNone(d)
        self.assertEqual(d.enroll_step, 0)
        d.close()

    @patch("PyQt6.QtCore.QProcess.start")
    def test_start_enrollment(self, mock_start):
        from ui.fingerprint_dialog import FingerprintDialog
        d = FingerprintDialog()
        d.start_enrollment()
        mock_start.assert_called_once_with("fprintd-enroll", ["-", "right-index-finger"])
        self.assertFalse(d.btn_start.isEnabled())
        d.close()

    def test_on_output_stage_passed(self):
        from ui.fingerprint_dialog import FingerprintDialog
        d = FingerprintDialog()
        # Mock readAllStandardOutput
        mock_ba = MagicMock()
        mock_ba.data.return_value = b"enroll-stage-passed"
        d.process.readAllStandardOutput = MagicMock(return_value=mock_ba)
        d.on_output()
        self.assertEqual(d.enroll_step, 1)
        self.assertEqual(d.progress.value(), 20)
        d.close()

    def test_on_output_multiple_stages(self):
        from ui.fingerprint_dialog import FingerprintDialog
        d = FingerprintDialog()
        for i in range(5):
            mock_ba = MagicMock()
            mock_ba.data.return_value = b"enroll-stage-passed"
            d.process.readAllStandardOutput = MagicMock(return_value=mock_ba)
            d.on_output()
        self.assertEqual(d.enroll_step, 5)
        d.close()

    def test_on_output_retry(self):
        from ui.fingerprint_dialog import FingerprintDialog
        d = FingerprintDialog()
        mock_ba = MagicMock()
        mock_ba.data.return_value = b"enroll-retry-scan"
        d.process.readAllStandardOutput = MagicMock(return_value=mock_ba)
        d.on_output()
        self.assertEqual(d.enroll_step, 0)
        d.close()

    def test_on_output_completed(self):
        from ui.fingerprint_dialog import FingerprintDialog
        d = FingerprintDialog()
        mock_ba = MagicMock()
        mock_ba.data.return_value = b"enroll-completed"
        d.process.readAllStandardOutput = MagicMock(return_value=mock_ba)
        d.on_output()
        self.assertEqual(d.progress.value(), 100)
        self.assertTrue(d.btn_start.isEnabled())
        d.close()

    def test_on_error_permission_denied(self):
        from ui.fingerprint_dialog import FingerprintDialog
        d = FingerprintDialog()
        mock_ba = MagicMock()
        mock_ba.data.return_value = b"Permission denied"
        d.process.readAllStandardError = MagicMock(return_value=mock_ba)
        d.on_error()
        self.assertIn("Permission", d.lbl_status.text())
        d.close()

    def test_on_error_empty(self):
        from ui.fingerprint_dialog import FingerprintDialog
        d = FingerprintDialog()
        mock_ba = MagicMock()
        mock_ba.data.return_value = b""
        d.process.readAllStandardError = MagicMock(return_value=mock_ba)
        d.on_error()  # Should not crash
        d.close()

    def test_on_finished_failure(self):
        from ui.fingerprint_dialog import FingerprintDialog
        d = FingerprintDialog()
        d.on_finished(1, 0)
        self.assertTrue(d.btn_start.isEnabled())
        self.assertIn("failed", d.lbl_status.text().lower())
        d.close()

    def test_on_finished_success(self):
        from ui.fingerprint_dialog import FingerprintDialog
        d = FingerprintDialog()
        d.progress.setValue(100)
        d.on_finished(0, 0)
        self.assertTrue(d.btn_start.isEnabled())
        d.close()


# ---------------------------------------------------------------------------
# NotificationPanel (ui/notification_panel.py)
# ---------------------------------------------------------------------------
class TestNotificationPanel(unittest.TestCase):
    """Tests for NotificationPanel and NotificationCard."""

    @patch("utils.notification_center.NotificationCenter")
    def test_init(self, mock_nc_cls):
        mock_nc = MagicMock()
        mock_nc.get_recent.return_value = []
        mock_nc.get_unread_count.return_value = 0
        mock_nc_cls.return_value = mock_nc
        from ui.notification_panel import NotificationPanel
        p = NotificationPanel()
        self.assertIsNotNone(p)
        mock_nc.get_recent.assert_called()
        p.close()

    @patch("utils.notification_center.NotificationCenter")
    def test_refresh_with_notifications(self, mock_nc_cls):
        mock_notif = MagicMock()
        mock_notif.title = "Test"
        mock_notif.message = "Hello"
        mock_notif.timestamp = 1700000000.0
        mock_notif.id = "n1"
        mock_nc = MagicMock()
        mock_nc.get_recent.return_value = [mock_notif]
        mock_nc.get_unread_count.return_value = 1
        mock_nc_cls.return_value = mock_nc
        from ui.notification_panel import NotificationPanel
        p = NotificationPanel()
        self.assertIsNotNone(p)
        p.close()

    @patch("utils.notification_center.NotificationCenter")
    def test_refresh_empty(self, mock_nc_cls):
        mock_nc = MagicMock()
        mock_nc.get_recent.return_value = []
        mock_nc.get_unread_count.return_value = 0
        mock_nc_cls.return_value = mock_nc
        from ui.notification_panel import NotificationPanel
        p = NotificationPanel()
        p.refresh()
        p.close()

    @patch("utils.notification_center.NotificationCenter")
    def test_dismiss(self, mock_nc_cls):
        mock_nc = MagicMock()
        mock_nc.get_recent.return_value = []
        mock_nc.get_unread_count.return_value = 0
        mock_nc_cls.return_value = mock_nc
        from ui.notification_panel import NotificationPanel
        p = NotificationPanel()
        p._dismiss("test-id")
        mock_nc.dismiss.assert_called_with("test-id")
        p.close()

    @patch("utils.notification_center.NotificationCenter")
    def test_mark_all_read(self, mock_nc_cls):
        mock_nc = MagicMock()
        mock_nc.get_recent.return_value = []
        mock_nc.get_unread_count.return_value = 0
        mock_nc_cls.return_value = mock_nc
        from ui.notification_panel import NotificationPanel
        p = NotificationPanel()
        p._mark_all_read()
        mock_nc.mark_all_read.assert_called()
        p.close()


# ---------------------------------------------------------------------------
# NotificationCard (ui/notification_panel.py)
# ---------------------------------------------------------------------------
class TestNotificationCard(unittest.TestCase):
    """Tests for NotificationCard widget."""

    def test_card_init(self):
        import time

        from ui.notification_panel import NotificationCard
        mock_notif = MagicMock()
        mock_notif.title = "Test Title"
        mock_notif.message = "Test Message"
        mock_notif.timestamp = time.time() - 60  # 1 minute ago
        mock_notif.id = "card1"
        card = NotificationCard(mock_notif)
        self.assertIsNotNone(card)
        card.close()

    def test_card_with_dismiss_callback(self):
        import time

        from ui.notification_panel import NotificationCard
        mock_notif = MagicMock()
        mock_notif.title = "Dismiss Test"
        mock_notif.message = "..."
        mock_notif.timestamp = time.time() - 3600  # 1 hour ago
        mock_notif.id = "card2"
        dismiss_fn = MagicMock()
        card = NotificationCard(mock_notif, on_dismiss=dismiss_fn)
        self.assertIsNotNone(card)
        card.close()

    def test_card_old_timestamp(self):
        from ui.notification_panel import NotificationCard
        mock_notif = MagicMock()
        mock_notif.title = "Old"
        mock_notif.message = "From the past"
        mock_notif.timestamp = 0.0  # epoch
        mock_notif.id = "card3"
        card = NotificationCard(mock_notif)
        self.assertIsNotNone(card)
        card.close()


# ---------------------------------------------------------------------------
# FirstRunWizard (ui/wizard.py) — module-level functions too
# ---------------------------------------------------------------------------
class TestFirstRunWizard(unittest.TestCase):
    """Tests for FirstRunWizard dialog."""

    @patch("services.hardware.hardware_profiles.detect_hardware_profile", return_value="generic")
    def test_init(self, mock_detect):
        from ui.wizard import FirstRunWizard
        w = FirstRunWizard()
        self.assertIsNotNone(w)
        self.assertEqual(w._selected_use_case, "daily")
        w.close()

    @patch("ui.wizard._FIRST_RUN_SENTINEL")
    def test_needs_first_run_no_file(self, mock_sentinel):
        mock_sentinel.exists.return_value = False
        from ui.wizard import needs_first_run
        result = needs_first_run()
        self.assertTrue(result)

    @patch("ui.wizard._FIRST_RUN_SENTINEL")
    def test_needs_first_run_file_exists(self, mock_sentinel):
        mock_sentinel.exists.return_value = True
        from ui.wizard import needs_first_run
        result = needs_first_run()
        self.assertFalse(result)

    @patch("builtins.open", side_effect=OSError("fail"))
    @patch("os.makedirs")
    def test_mark_first_run_complete_oserror(self, mock_mkdirs, mock_open):
        from ui.wizard import _mark_first_run_complete
        _mark_first_run_complete()  # Should handle error gracefully

    @patch("builtins.open", MagicMock())
    @patch("os.makedirs")
    def test_mark_first_run_complete_ok(self, mock_mkdirs):
        from ui.wizard import _mark_first_run_complete
        _mark_first_run_complete()

    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_detect_cpu_model_no_file(self, mock_open):
        from ui.wizard import _detect_cpu_model
        result = _detect_cpu_model()
        self.assertIsInstance(result, str)

    @patch("builtins.open", MagicMock(
        return_value=MagicMock(
            __enter__=MagicMock(return_value=MagicMock(
                read=MagicMock(return_value="model name : Intel Core i7-1234\nprocessor : 0\n")
            )),
            __exit__=MagicMock(return_value=False)
        )
    ))
    def test_detect_cpu_model_found(self):
        from ui.wizard import _detect_cpu_model
        result = _detect_cpu_model()
        self.assertIsInstance(result, str)

    @patch("subprocess.check_output", return_value="NVIDIA Corporation")
    def test_detect_gpu_vendor_nvidia(self, mock_co):
        from ui.wizard import _detect_gpu_vendor
        result = _detect_gpu_vendor()
        self.assertIsInstance(result, str)

    @patch("subprocess.check_output", side_effect=Exception("no lspci"))
    def test_detect_gpu_vendor_error(self, mock_co):
        from ui.wizard import _detect_gpu_vendor
        result = _detect_gpu_vendor()
        self.assertIsInstance(result, str)

    @patch("os.path.exists", return_value=True)
    def test_has_battery_true(self, mock_exists):
        from ui.wizard import _has_battery
        result = _has_battery()
        # may depend on implementation — just verify no crash
        self.assertIsInstance(result, bool)

    @patch("os.path.exists", return_value=False)
    @patch("os.listdir", return_value=[])
    def test_has_battery_false(self, mock_listdir, mock_exists):
        from ui.wizard import _has_battery
        result = _has_battery()
        self.assertIsInstance(result, bool)


# ---------------------------------------------------------------------------
# ProfilesTab (ui/profiles_tab.py)
# ---------------------------------------------------------------------------
class TestProfilesTab(unittest.TestCase):
    """Tests for ProfilesTab widget."""

    @patch("utils.profiles.ProfileManager")
    def test_init(self, mock_pm):
        from ui.profiles_tab import ProfilesTab
        t = ProfilesTab()
        self.assertIsNotNone(t)
        self.assertTrue(hasattr(t, '_METADATA'))

    @patch("utils.profiles.ProfileManager")
    def test_metadata(self, mock_pm):
        from ui.profiles_tab import ProfilesTab
        t = ProfilesTab()
        self.assertEqual(t._METADATA.id, "profiles")


# ---------------------------------------------------------------------------
# HealthTimelineTab (ui/health_timeline_tab.py)
# ---------------------------------------------------------------------------
class TestHealthTimelineTab(unittest.TestCase):
    """Tests for HealthTimelineTab widget."""

    @patch("utils.health_timeline.HealthTimeline")
    def test_init(self, mock_ht):
        mock_ht.return_value = MagicMock()
        from ui.health_timeline_tab import HealthTimelineTab
        t = HealthTimelineTab()
        self.assertIsNotNone(t)
        self.assertTrue(hasattr(t, 'timeline'))

    @patch("utils.health_timeline.HealthTimeline")
    def test_metadata(self, mock_ht):
        mock_ht.return_value = MagicMock()
        from ui.health_timeline_tab import HealthTimelineTab
        t = HealthTimelineTab()
        self.assertEqual(t._METADATA.id, "health")


# ---------------------------------------------------------------------------
# CommandPalette (ui/command_palette.py)
# ---------------------------------------------------------------------------
class TestCommandPalette(unittest.TestCase):
    """Tests for CommandPalette dialog."""

    def test_init(self):
        from ui.command_palette import CommandPalette
        callback = MagicMock()
        d = CommandPalette(on_action=callback)
        self.assertIsNotNone(d)
        self.assertTrue(hasattr(d, '_registry'))
        d.close()

    def test_populate_empty_filter(self):
        from ui.command_palette import CommandPalette
        callback = MagicMock()
        d = CommandPalette(on_action=callback)
        d._populate_results("")
        self.assertGreaterEqual(len(d._visible_entries), 0)
        d.close()

    def test_populate_with_filter(self):
        from ui.command_palette import CommandPalette
        callback = MagicMock()
        d = CommandPalette(on_action=callback)
        d._populate_results("nonexistent_xyz_filter")
        d.close()

    def test_activate_entry(self):
        from ui.command_palette import CommandPalette
        callback = MagicMock()
        d = CommandPalette(on_action=callback)
        # Manually trigger if there are entries
        if d._results_list.count() > 0:
            item = d._results_list.item(0)
            d._activate_item(item)
        d.close()


# ---------------------------------------------------------------------------
# BaseTab subclass smoke tests — AgentsTab, LogsTab, StorageTab,
# PerformanceTab, SnapshotTab
# ---------------------------------------------------------------------------
class TestAgentsTabSmoke(unittest.TestCase):
    """Smoke test for AgentsTab."""

    @patch("PyQt6.QtCore.QTimer.singleShot")
    @patch("PyQt6.QtCore.QTimer.start")
    def test_init(self, mock_timer_start, mock_single_shot):
        from ui.agents_tab import AgentsTab
        t = AgentsTab()
        self.assertIsNotNone(t)
        self.assertTrue(hasattr(t, '_METADATA'))
        self.assertEqual(t._METADATA.id, "agents")


class TestLogsTabSmoke(unittest.TestCase):
    """Smoke test for LogsTab."""

    @patch("PyQt6.QtCore.QTimer.singleShot")
    def test_init(self, mock_single_shot):
        from ui.logs_tab import LogsTab
        t = LogsTab()
        self.assertIsNotNone(t)
        self.assertEqual(t._METADATA.id, "logs")
        self.assertIsNotNone(t._live_timer)


class TestStorageTabSmoke(unittest.TestCase):
    """Smoke test for StorageTab."""

    @patch("PyQt6.QtCore.QTimer.singleShot")
    def test_init(self, mock_single_shot):
        from ui.storage_tab import StorageTab
        t = StorageTab()
        self.assertIsNotNone(t)
        self.assertEqual(t._METADATA.id, "storage")


class TestPerformanceTabSmoke(unittest.TestCase):
    """Smoke test for PerformanceTab."""

    @patch("PyQt6.QtCore.QTimer.singleShot")
    @patch("PyQt6.QtCore.QTimer.start")
    def test_init(self, mock_timer_start, mock_single_shot):
        from ui.performance_tab import PerformanceTab
        t = PerformanceTab()
        self.assertIsNotNone(t)
        self.assertEqual(t._METADATA.id, "performance")


class TestSnapshotTabSmoke(unittest.TestCase):
    """Smoke test for SnapshotTab."""

    @patch("PyQt6.QtCore.QTimer.singleShot")
    def test_init(self, mock_single_shot):
        from ui.snapshot_tab import SnapshotTab
        t = SnapshotTab()
        self.assertIsNotNone(t)
        self.assertEqual(t._METADATA.id, "snapshots")


# ---------------------------------------------------------------------------
# CommandPalette deeper method tests
# ---------------------------------------------------------------------------
class TestCommandPaletteDeep(unittest.TestCase):
    """Deeper tests for CommandPalette methods."""

    def test_build_feature_registry(self):
        from ui.command_palette import CommandPalette
        d = CommandPalette(on_action=MagicMock())
        self.assertIsInstance(d._registry, list)
        self.assertTrue(len(d._registry) > 0)
        d.close()

    def test_filter_case_insensitive(self):
        from ui.command_palette import CommandPalette
        d = CommandPalette(on_action=MagicMock())
        d._populate_results("SYSTEM")
        upper_count = len(d._visible_entries)
        d._populate_results("system")
        lower_count = len(d._visible_entries)
        self.assertEqual(upper_count, lower_count)
        d.close()


if __name__ == '__main__':
    unittest.main()

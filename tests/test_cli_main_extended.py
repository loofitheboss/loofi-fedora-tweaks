"""
Extended CLI tests for cli/main.py — targeting uncovered lines.

Covers: run_operation dry-run, cmd_audit_log, cmd_self_update, cmd_preset,
cmd_health_history, cmd_security_audit, cmd_focus_mode, cmd_snapshot,
cmd_logs, cmd_tuner, cmd_profile, cmd_plugins, main() global flags,
and cmd_tweak edge cases.
"""

import json
import subprocess
import unittest
from io import StringIO
from unittest.mock import MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

import cli.main as cli_mod
from cli.main import (
    main,
    run_operation,
    cmd_audit_log,
    cmd_self_update,
    cmd_preset,
    cmd_health_history,
    cmd_security_audit,
    cmd_focus_mode,
    cmd_snapshot,
    cmd_logs,
    cmd_tuner,
    cmd_profile,
    cmd_plugins,
    cmd_tweak,
)


def _make_args(**kwargs):
    """Build a simple namespace for command args."""
    ns = MagicMock()
    for k, v in kwargs.items():
        setattr(ns, k, v)
    return ns


# =====================================================================
# 1. run_operation — dry-run mode  (lines 78-94)
# =====================================================================
class TestRunOperationDryRun(unittest.TestCase):
    """Dry-run mode shows commands without executing them."""

    def setUp(self):
        self._orig_dry = cli_mod._dry_run
        self._orig_json = cli_mod._json_output

    def tearDown(self):
        cli_mod._dry_run = self._orig_dry
        cli_mod._json_output = self._orig_json

    @patch("cli.main.subprocess.run")
    def test_dry_run_text_mode(self, mock_run):
        """Dry-run prints command and description, does NOT call subprocess."""
        cli_mod._dry_run = True
        cli_mod._json_output = False
        with patch("cli.main.AuditLogger", create=True) as mock_audit_cls:
            mock_audit = MagicMock()
            mock_audit_cls.return_value = mock_audit
            with patch("cli.main._print") as mock_print:
                result = run_operation(("pkexec", ["dnf", "clean", "all"], "Cleaning"))
        self.assertTrue(result)
        mock_run.assert_not_called()

    @patch("cli.main.subprocess.run")
    def test_dry_run_json_mode(self, mock_run):
        """Dry-run with JSON outputs dry_run JSON payload."""
        cli_mod._dry_run = True
        cli_mod._json_output = True
        with patch("builtins.print") as mock_print:
            result = run_operation(("dnf", ["install", "vim"], "Installing vim"))
        self.assertTrue(result)
        mock_run.assert_not_called()
        # Verify JSON was printed
        printed = mock_print.call_args[0][0]
        data = json.loads(printed)
        self.assertTrue(data["dry_run"])
        self.assertEqual(data["command"], ["dnf", "install", "vim"])

    @patch("cli.main.subprocess.run")
    def test_dry_run_audit_logger_exception(self, mock_run):
        """Dry-run handles AuditLogger import/call failure gracefully."""
        cli_mod._dry_run = True
        cli_mod._json_output = False
        with patch.dict(
            "sys.modules",
            {
                "utils.audit": MagicMock(
                    AuditLogger=MagicMock(side_effect=RuntimeError("no audit"))
                )
            },
        ):
            with patch("cli.main._print"):
                result = run_operation(("echo", ["hello"], "test"))
        self.assertTrue(result)
        mock_run.assert_not_called()


# =====================================================================
# 2. run_operation — timeout and empty stdout  (lines 110, 117-119)
# =====================================================================
class TestRunOperationEdgeCases(unittest.TestCase):
    """Timeout and empty-stdout paths in run_operation."""

    def setUp(self):
        self._orig_dry = cli_mod._dry_run
        self._orig_json = cli_mod._json_output
        cli_mod._dry_run = False
        cli_mod._json_output = False

    def tearDown(self):
        cli_mod._dry_run = self._orig_dry
        cli_mod._json_output = self._orig_json

    @patch("cli.main._print")
    @patch("cli.main.subprocess.run")
    def test_timeout_expired(self, mock_run, mock_print):
        """TimeoutExpired returns False."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=5)
        result = run_operation(("test", [], "timeout test"), timeout=5)
        self.assertFalse(result)

    @patch("cli.main._print")
    @patch("cli.main.subprocess.run")
    def test_success_empty_stdout(self, mock_run, mock_print):
        """Success with empty stdout does not print stdout."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = run_operation(("echo", [], "empty output"))
        self.assertTrue(result)
        # Only "Running..." and "Success" printed, not stdout
        calls = [c[0][0] for c in mock_print.call_args_list]
        self.assertTrue(any("Success" in c for c in calls))
        self.assertFalse(any(c == "" for c in calls))


# =====================================================================
# 3. cmd_audit_log — completely uncovered  (lines 2725-2757)
# =====================================================================
class TestCmdAuditLog(unittest.TestCase):
    """Cover cmd_audit_log text and JSON modes."""

    def setUp(self):
        self._orig_json = cli_mod._json_output

    def tearDown(self):
        cli_mod._json_output = self._orig_json

    @patch("cli.main._print")
    def test_audit_log_text_empty(self, mock_print):
        """Text mode with no entries prints 'No audit log entries found.'."""
        cli_mod._json_output = False
        mock_audit = MagicMock()
        mock_audit.get_recent.return_value = []
        mock_audit.log_path = "/var/log/loofi-audit.log"
        with patch("utils.audit.AuditLogger", return_value=mock_audit):
            args = _make_args(count=20)
            result = cmd_audit_log(args)
        self.assertEqual(result, 0)
        printed = [c[0][0] for c in mock_print.call_args_list]
        self.assertTrue(any("No audit log entries" in p for p in printed))

    @patch("cli.main._print")
    def test_audit_log_text_with_entries(self, mock_print):
        """Text mode with entries including dry_run and failed exit codes."""
        cli_mod._json_output = False
        entries = [
            {
                "ts": "2025-01-15T10:30:00",
                "action": "cli.dnf",
                "exit_code": 0,
                "dry_run": False,
            },
            {
                "ts": "2025-01-15T10:31:00",
                "action": "cli.trim",
                "exit_code": None,
                "dry_run": True,
            },
            {
                "ts": "2025-01-15T10:32:00",
                "action": "cli.install",
                "exit_code": 1,
                "dry_run": False,
            },
        ]
        mock_audit = MagicMock()
        mock_audit.get_recent.return_value = entries
        mock_audit.log_path = "/var/log/loofi-audit.log"
        with patch("utils.audit.AuditLogger", return_value=mock_audit):
            args = _make_args(count=20)
            result = cmd_audit_log(args)
        self.assertEqual(result, 0)
        printed = " ".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("DRY", printed)
        self.assertIn("cli.install", printed)

    @patch("builtins.print")
    def test_audit_log_json_mode(self, mock_print):
        """JSON mode outputs entries and log_path."""
        cli_mod._json_output = True
        entries = [{"ts": "2025-01-15T10:30:00", "action": "test", "exit_code": 0}]
        mock_audit = MagicMock()
        mock_audit.get_recent.return_value = entries
        mock_audit.log_path = "/tmp/audit.log"
        with patch("utils.audit.AuditLogger", return_value=mock_audit):
            args = _make_args(count=10)
            result = cmd_audit_log(args)
        self.assertEqual(result, 0)
        data = json.loads(mock_print.call_args[0][0])
        self.assertEqual(data["count"], 1)
        self.assertIn("entries", data)


# =====================================================================
# 4. cmd_self_update  (lines 628-706)
# =====================================================================
class TestCmdSelfUpdate(unittest.TestCase):
    """Cover cmd_self_update check and run actions in text and JSON."""

    def setUp(self):
        self._orig_json = cli_mod._json_output
        cli_mod._json_output = False

    def tearDown(self):
        cli_mod._json_output = self._orig_json

    def _make_update_args(self, action="check", **kw):
        defaults = {
            "action": action,
            "channel": "auto",
            "no_cache": False,
            "timeout": 30,
            "download_dir": "/tmp/updates",
            "checksum": "",
            "signature_path": None,
            "public_key_path": None,
        }
        defaults.update(kw)
        return _make_args(**defaults)

    @patch("cli.main.UpdateChecker.resolve_artifact_preference", return_value="rpm")
    @patch("cli.main.UpdateChecker.check_for_updates", return_value=None)
    @patch("cli.main._print")
    @patch("cli.main.SystemManager.get_package_manager", return_value="dnf")
    def test_check_info_none_text(self, mock_pm, mock_print, mock_check, mock_pref):
        """check action with info=None returns 1 in text mode."""
        result = cmd_self_update(self._make_update_args("check"))
        self.assertEqual(result, 1)

    @patch("cli.main.UpdateChecker.resolve_artifact_preference", return_value="rpm")
    @patch("cli.main.UpdateChecker.check_for_updates")
    @patch("cli.main._print")
    @patch("cli.main.SystemManager.get_package_manager", return_value="dnf")
    def test_check_no_update_text(self, mock_pm, mock_print, mock_check, mock_pref):
        """check action with is_newer=False prints 'No update available'."""
        info = MagicMock(
            is_newer=False,
            offline=False,
            source="network",
            current_version="1.0",
            latest_version="1.0",
            selected_asset=None,
        )
        mock_check.return_value = info
        result = cmd_self_update(self._make_update_args("check"))
        self.assertEqual(result, 0)
        printed = " ".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("No update available", printed)

    @patch("cli.main.UpdateChecker.resolve_artifact_preference", return_value="rpm")
    @patch("cli.main.UpdateChecker.check_for_updates")
    @patch("cli.main._print")
    @patch("cli.main.SystemManager.get_package_manager", return_value="dnf")
    def test_check_update_available_text(
        self, mock_pm, mock_print, mock_check, mock_pref
    ):
        """check action with is_newer=True and selected_asset prints asset name."""
        asset = MagicMock()
        asset.name = "loofi-2.0.rpm"
        info = MagicMock(
            is_newer=True,
            offline=False,
            source="network",
            current_version="1.0",
            latest_version="2.0",
            selected_asset=asset,
        )
        mock_check.return_value = info
        result = cmd_self_update(self._make_update_args("check"))
        self.assertEqual(result, 0)
        printed = " ".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("Update available", printed)
        self.assertIn("loofi-2.0.rpm", printed)

    @patch("cli.main.UpdateChecker.resolve_artifact_preference", return_value="rpm")
    @patch("cli.main.UpdateChecker.check_for_updates")
    @patch("builtins.print")
    @patch("cli.main.SystemManager.get_package_manager", return_value="dnf")
    def test_check_json_mode(self, mock_pm, mock_print, mock_check, mock_pref):
        """check action JSON mode outputs correct schema."""
        cli_mod._json_output = True
        info = MagicMock(
            is_newer=True,
            offline=False,
            source="cache",
            current_version="1.0",
            latest_version="2.0",
            selected_asset=None,
        )
        mock_check.return_value = info
        result = cmd_self_update(self._make_update_args("check"))
        self.assertEqual(result, 0)
        data = json.loads(mock_print.call_args[0][0])
        self.assertTrue(data["success"])
        self.assertTrue(data["update_available"])

    @patch("cli.main.UpdateChecker.resolve_artifact_preference", return_value="rpm")
    @patch("cli.main.UpdateChecker.check_for_updates", return_value=None)
    @patch("builtins.print")
    @patch("cli.main.SystemManager.get_package_manager", return_value="dnf")
    def test_check_json_mode_none(self, mock_pm, mock_print, mock_check, mock_pref):
        """check action JSON mode with info=None returns 1."""
        cli_mod._json_output = True
        result = cmd_self_update(self._make_update_args("check"))
        self.assertEqual(result, 1)

    @patch("cli.main.UpdateChecker.resolve_artifact_preference", return_value="rpm")
    @patch("cli.main.UpdateChecker.run_auto_update")
    @patch("cli.main._print")
    @patch("cli.main.SystemManager.get_package_manager", return_value="dnf")
    def test_run_success_text(self, mock_pm, mock_print, mock_update, mock_pref):
        """run action success text mode."""
        download = MagicMock(file_path="/tmp/loofi.rpm", ok=True)
        verify = MagicMock(ok=True)
        mock_update.return_value = MagicMock(
            success=True,
            stage="complete",
            error=None,
            offline=False,
            source="network",
            selected_asset=None,
            download=download,
            verify=verify,
        )
        result = cmd_self_update(self._make_update_args("run"))
        self.assertEqual(result, 0)

    @patch("cli.main.UpdateChecker.resolve_artifact_preference", return_value="rpm")
    @patch("cli.main.UpdateChecker.run_auto_update")
    @patch("cli.main._print")
    @patch("cli.main.SystemManager.get_package_manager", return_value="dnf")
    def test_run_failure_text(self, mock_pm, mock_print, mock_update, mock_pref):
        """run action failure text mode."""
        mock_update.return_value = MagicMock(
            success=False,
            stage="download",
            error="timeout",
            offline=False,
            source="network",
            selected_asset=None,
            download=None,
            verify=None,
        )
        result = cmd_self_update(self._make_update_args("run"))
        self.assertEqual(result, 1)

    @patch("cli.main.UpdateChecker.resolve_artifact_preference", return_value="rpm")
    @patch("cli.main.UpdateChecker.run_auto_update")
    @patch("builtins.print")
    @patch("cli.main.SystemManager.get_package_manager", return_value="dnf")
    def test_run_json_mode(self, mock_pm, mock_print, mock_update, mock_pref):
        """run action JSON mode."""
        cli_mod._json_output = True
        mock_update.return_value = MagicMock(
            success=True,
            stage="complete",
            error=None,
            offline=False,
            source="network",
            selected_asset=MagicMock(name="pkg.rpm"),
            download=MagicMock(file_path="/tmp/pkg.rpm", ok=True),
            verify=MagicMock(ok=True),
        )
        result = cmd_self_update(self._make_update_args("run"))
        self.assertEqual(result, 0)
        data = json.loads(mock_print.call_args[0][0])
        self.assertTrue(data["success"])


# =====================================================================
# 5. cmd_preset  (lines 1370-1436)
# =====================================================================
class TestCmdPreset(unittest.TestCase):
    """Cover cmd_preset list/apply/export in text and JSON."""

    def setUp(self):
        self._orig_json = cli_mod._json_output
        cli_mod._json_output = False

    def tearDown(self):
        cli_mod._json_output = self._orig_json

    @patch("cli.main._print")
    @patch("cli.main.PresetManager")
    def test_list_text_empty(self, mock_cls, mock_print):
        """list text mode with no presets."""
        mock_cls.return_value.list_presets.return_value = []
        result = cmd_preset(_make_args(action="list"))
        self.assertEqual(result, 0)
        printed = " ".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("no presets found", printed)

    @patch("cli.main._print")
    @patch("cli.main.PresetManager")
    def test_list_text_with_presets(self, mock_cls, mock_print):
        """list text mode with presets."""
        mock_cls.return_value.list_presets.return_value = ["gaming", "office"]
        result = cmd_preset(_make_args(action="list"))
        self.assertEqual(result, 0)
        printed = " ".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("gaming", printed)

    @patch("builtins.print")
    @patch("cli.main.PresetManager")
    def test_list_json(self, mock_cls, mock_print):
        """list JSON mode."""
        cli_mod._json_output = True
        mock_cls.return_value.list_presets.return_value = ["gaming"]
        result = cmd_preset(_make_args(action="list"))
        self.assertEqual(result, 0)
        data = json.loads(mock_print.call_args[0][0])
        self.assertEqual(data["presets"], ["gaming"])

    @patch("cli.main._print")
    @patch("cli.main.PresetManager")
    def test_apply_text_success(self, mock_cls, mock_print):
        """apply text mode success."""
        mock_cls.return_value.load_preset.return_value = {"swappiness": 10}
        result = cmd_preset(_make_args(action="apply", name="gaming"))
        self.assertEqual(result, 0)
        printed = " ".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("Applied preset", printed)

    @patch("cli.main._print")
    @patch("cli.main.PresetManager")
    def test_apply_text_not_found(self, mock_cls, mock_print):
        """apply text mode preset not found."""
        mock_cls.return_value.load_preset.return_value = None
        result = cmd_preset(_make_args(action="apply", name="nope"))
        self.assertEqual(result, 1)

    @patch("cli.main._print")
    @patch("cli.main.PresetManager")
    def test_apply_no_name(self, mock_cls, mock_print):
        """apply without name returns 1."""
        result = cmd_preset(_make_args(action="apply", name=None))
        self.assertEqual(result, 1)

    @patch("builtins.print")
    @patch("cli.main.PresetManager")
    def test_apply_json_success(self, mock_cls, mock_print):
        """apply JSON mode success."""
        cli_mod._json_output = True
        mock_cls.return_value.load_preset.return_value = {"swap": 10}
        result = cmd_preset(_make_args(action="apply", name="gaming"))
        self.assertEqual(result, 0)
        data = json.loads(mock_print.call_args[0][0])
        self.assertTrue(data["success"])

    @patch("builtins.print")
    @patch("cli.main.PresetManager")
    def test_apply_json_not_found(self, mock_cls, mock_print):
        """apply JSON mode not found."""
        cli_mod._json_output = True
        mock_cls.return_value.load_preset.return_value = None
        result = cmd_preset(_make_args(action="apply", name="nope"))
        self.assertEqual(result, 1)
        data = json.loads(mock_print.call_args[0][0])
        self.assertFalse(data["success"])

    @patch("cli.main._print")
    @patch("cli.main.PresetManager")
    def test_export_text_not_found(self, mock_cls, mock_print):
        """export text mode preset not found."""
        mock_cls.return_value.load_preset.return_value = None
        result = cmd_preset(
            _make_args(action="export", name="nope", path="/tmp/out.json")
        )
        self.assertEqual(result, 1)

    @patch("cli.main._print")
    @patch("cli.main.PresetManager")
    def test_export_no_name(self, mock_cls, mock_print):
        """export without name returns 1."""
        result = cmd_preset(_make_args(action="export", name=None, path=None))
        self.assertEqual(result, 1)

    @patch("builtins.open", new_callable=lambda: lambda: MagicMock())
    @patch("cli.main._print")
    @patch("cli.main.PresetManager")
    def test_export_text_success(self, mock_cls, mock_print, mock_open_fn):
        """export text mode success."""
        mock_cls.return_value.load_preset.return_value = {"key": "val"}
        with patch("builtins.open", unittest.mock.mock_open()):
            result = cmd_preset(
                _make_args(action="export", name="gaming", path="/tmp/out.json")
            )
        self.assertEqual(result, 0)

    @patch("builtins.print")
    @patch("cli.main.PresetManager")
    def test_export_json_success(self, mock_cls, mock_print):
        """export JSON mode success."""
        cli_mod._json_output = True
        mock_cls.return_value.load_preset.return_value = {"key": "val"}
        with patch("builtins.open", unittest.mock.mock_open()):
            result = cmd_preset(
                _make_args(action="export", name="gaming", path="/tmp/out.json")
            )
        self.assertEqual(result, 0)
        data = json.loads(mock_print.call_args[0][0])
        self.assertTrue(data["success"])

    def test_unknown_action(self):
        """Unknown action returns 1."""
        result = cmd_preset(_make_args(action="unknown"))
        self.assertEqual(result, 1)


# =====================================================================
# 6. cmd_health_history  (lines 1697-1781)
# =====================================================================
class TestCmdHealthHistory(unittest.TestCase):
    """Cover cmd_health_history show/record/export/prune."""

    def setUp(self):
        self._orig_json = cli_mod._json_output
        cli_mod._json_output = False

    def tearDown(self):
        cli_mod._json_output = self._orig_json

    @patch("cli.main._print")
    @patch("cli.main.HealthTimeline")
    def test_show_text_empty(self, mock_cls, mock_print):
        """show text mode with no metrics."""
        mock_cls.return_value.get_summary.return_value = {}
        result = cmd_health_history(_make_args(action="show"))
        self.assertEqual(result, 0)
        printed = " ".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("no metrics recorded", printed)

    @patch("cli.main._print")
    @patch("cli.main.HealthTimeline")
    def test_show_text_with_summary(self, mock_cls, mock_print):
        """show text mode with summary data."""
        mock_cls.return_value.get_summary.return_value = {
            "cpu_temp": {"min": 40.0, "max": 80.0, "avg": 55.5, "count": 10},
            "ram_usage": {"min": 30.0, "max": 70.0, "avg": 50.0, "count": 10},
        }
        result = cmd_health_history(_make_args(action="show"))
        self.assertEqual(result, 0)
        printed = " ".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("CPU Temp", printed)
        self.assertIn("RAM Usage", printed)

    @patch("builtins.print")
    @patch("cli.main.HealthTimeline")
    def test_show_json(self, mock_cls, mock_builtin_print):
        """show JSON mode."""
        cli_mod._json_output = True
        summary = {"cpu_temp": {"min": 40, "max": 80, "avg": 60, "count": 5}}
        mock_cls.return_value.get_summary.return_value = summary
        result = cmd_health_history(_make_args(action="show"))
        self.assertEqual(result, 0)
        data = json.loads(mock_builtin_print.call_args[0][0])
        self.assertIn("summary", data)

    @patch("cli.main._print")
    @patch("cli.main.HealthTimeline")
    def test_record_text_success(self, mock_cls, mock_print):
        """record text mode success."""
        mock_cls.return_value.record_snapshot.return_value = MagicMock(
            success=True, message="Recorded", data={}
        )
        result = cmd_health_history(_make_args(action="record"))
        self.assertEqual(result, 0)

    @patch("cli.main._print")
    @patch("cli.main.HealthTimeline")
    def test_record_text_failure(self, mock_cls, mock_print):
        """record text mode failure."""
        mock_cls.return_value.record_snapshot.return_value = MagicMock(
            success=False, message="Failed", data={}
        )
        result = cmd_health_history(_make_args(action="record"))
        self.assertEqual(result, 1)

    @patch("builtins.print")
    @patch("cli.main.HealthTimeline")
    def test_record_json(self, mock_cls, mock_print):
        """record JSON mode."""
        cli_mod._json_output = True
        mock_cls.return_value.record_snapshot.return_value = MagicMock(
            success=True, message="OK", data={"cpu": 50}
        )
        result = cmd_health_history(_make_args(action="record"))
        self.assertEqual(result, 0)

    @patch("cli.main._print")
    @patch("cli.main.HealthTimeline")
    def test_export_csv_text(self, mock_cls, mock_print):
        """export with .csv extension uses csv format."""
        mock_cls.return_value.export_metrics.return_value = MagicMock(
            success=True, message="Exported", data={}
        )
        result = cmd_health_history(_make_args(action="export", path="/tmp/data.csv"))
        self.assertEqual(result, 0)
        mock_cls.return_value.export_metrics.assert_called_once_with(
            "/tmp/data.csv", format="csv"
        )

    @patch("cli.main._print")
    @patch("cli.main.HealthTimeline")
    def test_export_json_extension(self, mock_cls, mock_print):
        """export with .json extension uses json format."""
        mock_cls.return_value.export_metrics.return_value = MagicMock(
            success=True, message="Exported", data={}
        )
        result = cmd_health_history(_make_args(action="export", path="/tmp/data.json"))
        self.assertEqual(result, 0)
        mock_cls.return_value.export_metrics.assert_called_once_with(
            "/tmp/data.json", format="json"
        )

    @patch("cli.main._print")
    @patch("cli.main.HealthTimeline")
    def test_export_no_path(self, mock_cls, mock_print):
        """export without path returns 1."""
        result = cmd_health_history(_make_args(action="export", path=None))
        self.assertEqual(result, 1)

    @patch("builtins.print")
    @patch("cli.main.HealthTimeline")
    def test_export_json_mode(self, mock_cls, mock_print):
        """export JSON mode."""
        cli_mod._json_output = True
        mock_cls.return_value.export_metrics.return_value = MagicMock(
            success=True, message="Done", data={"rows": 100}
        )
        result = cmd_health_history(_make_args(action="export", path="/tmp/out.json"))
        self.assertEqual(result, 0)

    @patch("cli.main._print")
    @patch("cli.main.HealthTimeline")
    def test_prune_text_success(self, mock_cls, mock_print):
        """prune text mode success."""
        mock_cls.return_value.prune_old_data.return_value = MagicMock(
            success=True, message="Pruned 50 rows", data={}
        )
        result = cmd_health_history(_make_args(action="prune"))
        self.assertEqual(result, 0)

    @patch("builtins.print")
    @patch("cli.main.HealthTimeline")
    def test_prune_json(self, mock_cls, mock_print):
        """prune JSON mode."""
        cli_mod._json_output = True
        mock_cls.return_value.prune_old_data.return_value = MagicMock(
            success=True, message="OK", data={}
        )
        result = cmd_health_history(_make_args(action="prune"))
        self.assertEqual(result, 0)

    def test_unknown_action(self):
        """Unknown action returns 1."""
        with patch("cli.main.HealthTimeline"):
            result = cmd_health_history(_make_args(action="unknown"))
        self.assertEqual(result, 1)


# =====================================================================
# 7. cmd_security_audit  (lines 1495-1531)
# =====================================================================
class TestCmdSecurityAudit(unittest.TestCase):
    """Cover cmd_security_audit score thresholds and JSON mode."""

    def setUp(self):
        self._orig_json = cli_mod._json_output
        cli_mod._json_output = False

    def tearDown(self):
        cli_mod._json_output = self._orig_json

    def _score_data(self, score, rating="Good", recs=None):
        return {
            "score": score,
            "rating": rating,
            "open_ports": 3,
            "risky_ports": 1,
            "recommendations": recs or [],
        }

    @patch("cli.main.PortAuditor.is_firewalld_running", return_value=True)
    @patch("cli.main.PortAuditor.get_security_score")
    @patch("builtins.print")
    def test_json_mode(self, mock_print, mock_score, mock_fw):
        """JSON mode outputs score_data directly."""
        cli_mod._json_output = True
        mock_score.return_value = self._score_data(95)
        result = cmd_security_audit(_make_args())
        self.assertEqual(result, 0)
        data = json.loads(mock_print.call_args[0][0])
        self.assertEqual(data["score"], 95)

    @patch("cli.main.PortAuditor.is_firewalld_running", return_value=True)
    @patch("cli.main.PortAuditor.get_security_score")
    @patch("cli.main._print")
    def test_score_green(self, mock_print, mock_score, mock_fw):
        """Score >= 90 uses green icon."""
        mock_score.return_value = self._score_data(95, "Excellent")
        result = cmd_security_audit(_make_args())
        self.assertEqual(result, 0)

    @patch("cli.main.PortAuditor.is_firewalld_running", return_value=True)
    @patch("cli.main.PortAuditor.get_security_score")
    @patch("cli.main._print")
    def test_score_yellow(self, mock_print, mock_score, mock_fw):
        """Score 70-89 uses yellow icon."""
        mock_score.return_value = self._score_data(75, "Good")
        result = cmd_security_audit(_make_args())
        self.assertEqual(result, 0)

    @patch("cli.main.PortAuditor.is_firewalld_running", return_value=True)
    @patch("cli.main.PortAuditor.get_security_score")
    @patch("cli.main._print")
    def test_score_orange(self, mock_print, mock_score, mock_fw):
        """Score 50-69 uses orange icon."""
        mock_score.return_value = self._score_data(55, "Fair")
        result = cmd_security_audit(_make_args())
        self.assertEqual(result, 0)

    @patch("cli.main.PortAuditor.is_firewalld_running", return_value=True)
    @patch("cli.main.PortAuditor.get_security_score")
    @patch("cli.main._print")
    def test_score_red(self, mock_print, mock_score, mock_fw):
        """Score < 50 uses red icon."""
        mock_score.return_value = self._score_data(30, "Poor")
        result = cmd_security_audit(_make_args())
        self.assertEqual(result, 0)

    @patch("cli.main.PortAuditor.is_firewalld_running", return_value=False)
    @patch("cli.main.PortAuditor.get_security_score")
    @patch("cli.main._print")
    def test_firewall_not_running(self, mock_print, mock_score, mock_fw):
        """Firewall not running shows red icon."""
        mock_score.return_value = self._score_data(80, "Good")
        result = cmd_security_audit(_make_args())
        self.assertEqual(result, 0)

    @patch("cli.main.PortAuditor.is_firewalld_running", return_value=True)
    @patch("cli.main.PortAuditor.get_security_score")
    @patch("cli.main._print")
    def test_with_recommendations(self, mock_print, mock_score, mock_fw):
        """Recommendations section printed when present."""
        mock_score.return_value = self._score_data(
            60, "Fair", ["Close port 22", "Enable firewall"]
        )
        result = cmd_security_audit(_make_args())
        self.assertEqual(result, 0)
        printed = " ".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("Close port 22", printed)

    @patch("cli.main.PortAuditor.is_firewalld_running", return_value=True)
    @patch("cli.main.PortAuditor.get_security_score")
    @patch("cli.main._print")
    def test_empty_recommendations(self, mock_print, mock_score, mock_fw):
        """No recommendations section when list is empty."""
        mock_score.return_value = self._score_data(95, "Excellent", [])
        result = cmd_security_audit(_make_args())
        self.assertEqual(result, 0)
        printed = " ".join(c[0][0] for c in mock_print.call_args_list)
        self.assertNotIn("Recommendations", printed)


# =====================================================================
# 8. cmd_focus_mode  (lines 1439-1492)
# =====================================================================
class TestCmdFocusMode(unittest.TestCase):
    """Cover cmd_focus_mode on/off/status in text and JSON."""

    def setUp(self):
        self._orig_json = cli_mod._json_output
        cli_mod._json_output = False

    def tearDown(self):
        cli_mod._json_output = self._orig_json

    @patch("cli.main.FocusMode.disable")
    @patch("builtins.print")
    def test_off_json(self, mock_print, mock_disable):
        """off action JSON mode."""
        cli_mod._json_output = True
        mock_disable.return_value = {"success": True, "message": "Disabled"}
        result = cmd_focus_mode(_make_args(action="off"))
        self.assertEqual(result, 0)
        data = json.loads(mock_print.call_args[0][0])
        self.assertTrue(data["success"])

    @patch("cli.main.FocusMode.disable")
    @patch("cli.main._print")
    def test_off_text_failure(self, mock_print, mock_disable):
        """off action text mode failure."""
        mock_disable.return_value = {"success": False, "message": "Failed"}
        result = cmd_focus_mode(_make_args(action="off"))
        self.assertEqual(result, 1)

    @patch("cli.main.FocusMode.list_profiles", return_value=["default", "work"])
    @patch("cli.main.FocusMode.get_active_profile", return_value="work")
    @patch("cli.main.FocusMode.is_active", return_value=True)
    @patch("builtins.print")
    def test_status_json(self, mock_print, mock_active, mock_profile, mock_profiles):
        """status action JSON mode."""
        cli_mod._json_output = True
        result = cmd_focus_mode(_make_args(action="status"))
        self.assertEqual(result, 0)
        data = json.loads(mock_print.call_args[0][0])
        self.assertTrue(data["active"])
        self.assertEqual(data["active_profile"], "work")

    @patch("cli.main.FocusMode.list_profiles", return_value=["default"])
    @patch("cli.main.FocusMode.get_active_profile", return_value=None)
    @patch("cli.main.FocusMode.is_active", return_value=False)
    @patch("cli.main._print")
    def test_status_text_inactive(
        self, mock_print, mock_active, mock_profile, mock_profiles
    ):
        """status text mode when inactive."""
        result = cmd_focus_mode(_make_args(action="status"))
        self.assertEqual(result, 0)
        printed = " ".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("Inactive", printed)

    @patch("cli.main.FocusMode.enable")
    @patch("cli.main._print")
    def test_on_text_with_extras(self, mock_print, mock_enable):
        """on action text mode with hosts_modified, dnd, processes_killed."""
        mock_enable.return_value = {
            "success": True,
            "message": "Focus enabled",
            "hosts_modified": True,
            "dnd_enabled": True,
            "processes_killed": ["firefox", "slack"],
        }
        result = cmd_focus_mode(_make_args(action="on", profile="default"))
        self.assertEqual(result, 0)
        printed = " ".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("Domains blocked", printed)
        self.assertIn("Do Not Disturb", printed)
        self.assertIn("firefox", printed)

    def test_unknown_action(self):
        """Unknown action returns 1."""
        result = cmd_focus_mode(_make_args(action="unknown"))
        self.assertEqual(result, 1)


# =====================================================================
# 9. cmd_snapshot — backends  (lines 1854-1908)
# =====================================================================
class TestCmdSnapshot(unittest.TestCase):
    """Cover cmd_snapshot backends and list with snapshots."""

    def setUp(self):
        self._orig_json = cli_mod._json_output
        cli_mod._json_output = False

    def tearDown(self):
        cli_mod._json_output = self._orig_json

    @patch("cli.main._print")
    def test_backends_text(self, mock_print):
        """backends text mode shows available/unavailable backends."""
        backend1 = MagicMock(name="timeshift", available=True, version="24.01")
        backend1.name = "timeshift"
        backend2 = MagicMock(name="snapper", available=False, version="")
        backend2.name = "snapper"
        with patch(
            "utils.snapshot_manager.SnapshotManager.detect_backends",
            return_value=[backend1, backend2],
        ):
            result = cmd_snapshot(_make_args(action="backends"))
        self.assertEqual(result, 0)

    @patch("builtins.print")
    def test_backends_json(self, mock_print):
        """backends JSON mode."""
        cli_mod._json_output = True
        backend = MagicMock(available=True)
        backend.name = "timeshift"
        with patch(
            "utils.snapshot_manager.SnapshotManager.detect_backends",
            return_value=[backend],
        ):
            result = cmd_snapshot(_make_args(action="backends"))
        self.assertEqual(result, 0)

    @patch("cli.main._print")
    def test_list_text_with_snapshots(self, mock_print):
        """list text mode with snapshots."""
        import time as time_mod

        snap = MagicMock(
            backend="btrfs", id="123", label="test-snap", timestamp=time_mod.time()
        )
        with patch(
            "utils.snapshot_manager.SnapshotManager.list_snapshots", return_value=[snap]
        ):
            result = cmd_snapshot(_make_args(action="list"))
        self.assertEqual(result, 0)

    @patch("cli.main._print")
    def test_list_text_no_timestamp(self, mock_print):
        """list text mode snapshot with timestamp=None."""
        snap = MagicMock(backend="btrfs", id="456", label=None, timestamp=None)
        with patch(
            "utils.snapshot_manager.SnapshotManager.list_snapshots", return_value=[snap]
        ):
            result = cmd_snapshot(_make_args(action="list"))
        self.assertEqual(result, 0)

    @patch("builtins.print")
    def test_list_json(self, mock_print):
        """list JSON mode."""
        cli_mod._json_output = True
        snap = MagicMock(backend="btrfs", id="1")
        with patch(
            "utils.snapshot_manager.SnapshotManager.list_snapshots", return_value=[snap]
        ):
            result = cmd_snapshot(_make_args(action="list"))
        self.assertEqual(result, 0)

    @patch("cli.main._print")
    @patch("cli.main.run_operation", return_value=True)
    def test_delete_with_id(self, mock_run, mock_print):
        """delete action with snapshot_id."""
        with patch(
            "utils.snapshot_manager.SnapshotManager.delete_snapshot",
            return_value=("cmd", [], "deleting"),
        ):
            result = cmd_snapshot(_make_args(action="delete", snapshot_id="42"))
        self.assertEqual(result, 0)

    @patch("cli.main._print")
    def test_delete_no_id(self, mock_print):
        """delete without snapshot_id returns 1."""
        result = cmd_snapshot(_make_args(action="delete", snapshot_id=None))
        self.assertEqual(result, 1)

    def test_unknown_action(self):
        """Unknown action returns 1."""
        with patch("utils.snapshot_manager.SnapshotManager"):
            result = cmd_snapshot(_make_args(action="unknown"))
        self.assertEqual(result, 1)


# =====================================================================
# 10. cmd_logs  (lines 1911-1967)
# =====================================================================
class TestCmdLogs(unittest.TestCase):
    """Cover cmd_logs show/errors/export."""

    def setUp(self):
        self._orig_json = cli_mod._json_output
        cli_mod._json_output = False

    def tearDown(self):
        cli_mod._json_output = self._orig_json

    @patch("cli.main._print")
    def test_show_text_with_pattern_match(self, mock_print):
        """show text mode with entries that have pattern_match."""
        entry = MagicMock(
            timestamp="2025-01-15 10:00:00",
            priority_label="err",
            unit="sshd.service",
            message="Connection refused" * 5,
            pattern_match="SSH brute force detected",
        )
        with patch("utils.smart_logs.SmartLogViewer.get_logs", return_value=[entry]):
            result = cmd_logs(
                _make_args(
                    action="show", unit=None, priority=None, since=None, lines=50
                )
            )
        self.assertEqual(result, 0)
        printed = " ".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("SSH brute force", printed)

    @patch("cli.main._print")
    def test_show_text_no_pattern(self, mock_print):
        """show text mode with entries without pattern_match."""
        entry = MagicMock(
            timestamp="2025-01-15 10:00:00",
            priority_label="info",
            unit="systemd",
            message="Started service",
            pattern_match=None,
        )
        with patch("utils.smart_logs.SmartLogViewer.get_logs", return_value=[entry]):
            result = cmd_logs(
                _make_args(
                    action="show", unit=None, priority=None, since=None, lines=50
                )
            )
        self.assertEqual(result, 0)

    @patch("builtins.print")
    def test_show_json(self, mock_print):
        """show JSON mode."""
        cli_mod._json_output = True
        entry = MagicMock(
            timestamp="2025-01-15",
            priority_label="err",
            unit="test",
            message="msg",
            pattern_match=None,
        )
        with patch("utils.smart_logs.SmartLogViewer.get_logs", return_value=[entry]):
            result = cmd_logs(
                _make_args(
                    action="show", unit=None, priority=None, since=None, lines=10
                )
            )
        self.assertEqual(result, 0)

    @patch("cli.main._print")
    def test_errors_text_with_top_units_and_patterns(self, mock_print):
        """errors text mode with top_units and detected_patterns."""
        summary = MagicMock(
            total_entries=100,
            critical_count=2,
            error_count=10,
            warning_count=30,
            top_units=[("sshd.service", 15), ("NetworkManager", 8)],
            detected_patterns=[("OOM killer", 3), ("disk full", 1)],
        )
        with patch(
            "utils.smart_logs.SmartLogViewer.get_error_summary", return_value=summary
        ):
            result = cmd_logs(_make_args(action="errors", since=None))
        self.assertEqual(result, 0)
        printed = " ".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("sshd.service", printed)
        self.assertIn("OOM killer", printed)

    @patch("cli.main._print")
    def test_errors_text_empty_patterns(self, mock_print):
        """errors text mode with empty top_units and patterns."""
        summary = MagicMock(
            total_entries=5,
            critical_count=0,
            error_count=0,
            warning_count=5,
            top_units=[],
            detected_patterns=[],
        )
        with patch(
            "utils.smart_logs.SmartLogViewer.get_error_summary", return_value=summary
        ):
            result = cmd_logs(_make_args(action="errors", since="1h ago"))
        self.assertEqual(result, 0)

    @patch("builtins.print")
    def test_errors_json(self, mock_print):
        """errors JSON mode."""
        cli_mod._json_output = True
        summary = MagicMock(
            total_entries=10,
            critical_count=0,
            error_count=2,
            warning_count=8,
            top_units=[],
            detected_patterns=[],
        )
        with patch(
            "utils.smart_logs.SmartLogViewer.get_error_summary", return_value=summary
        ):
            result = cmd_logs(_make_args(action="errors", since=None))
        self.assertEqual(result, 0)

    @patch("cli.main._print")
    def test_export_success(self, mock_print):
        """export success path."""
        with patch("utils.smart_logs.SmartLogViewer.get_logs", return_value=[]):
            with patch(
                "utils.smart_logs.SmartLogViewer.export_logs", return_value=True
            ):
                result = cmd_logs(
                    _make_args(
                        action="export", path="/tmp/logs.txt", since=None, lines=None
                    )
                )
        self.assertEqual(result, 0)

    @patch("cli.main._print")
    def test_export_failure(self, mock_print):
        """export failure path."""
        with patch("utils.smart_logs.SmartLogViewer.get_logs", return_value=[]):
            with patch(
                "utils.smart_logs.SmartLogViewer.export_logs", return_value=False
            ):
                result = cmd_logs(
                    _make_args(
                        action="export", path="/tmp/logs.txt", since=None, lines=None
                    )
                )
        self.assertEqual(result, 1)

    @patch("cli.main._print")
    def test_export_no_path(self, mock_print):
        """export without path returns 1."""
        result = cmd_logs(
            _make_args(action="export", path=None, since=None, lines=None)
        )
        self.assertEqual(result, 1)

    @patch("cli.main._print")
    def test_export_json_extension(self, mock_print):
        """export with .json extension uses json format."""
        with patch("utils.smart_logs.SmartLogViewer.get_logs", return_value=[]):
            with patch(
                "utils.smart_logs.SmartLogViewer.export_logs", return_value=True
            ) as mock_export:
                result = cmd_logs(
                    _make_args(
                        action="export", path="/tmp/out.json", since=None, lines=None
                    )
                )
        self.assertEqual(result, 0)
        # Second arg is path, third is format
        mock_export.assert_called_once()
        call_kwargs = mock_export.call_args
        self.assertEqual(
            call_kwargs[1].get(
                "format", call_kwargs[0][2] if len(call_kwargs[0]) > 2 else None
            ),
            "json",
        )

    def test_unknown_action(self):
        """Unknown action returns 1."""
        with patch("utils.smart_logs.SmartLogViewer"):
            result = cmd_logs(_make_args(action="unknown"))
        self.assertEqual(result, 1)


# =====================================================================
# 11. cmd_tuner  (lines 1787-1851)
# =====================================================================
class TestCmdTuner(unittest.TestCase):
    """Cover cmd_tuner analyze/apply/history."""

    def setUp(self):
        self._orig_json = cli_mod._json_output
        cli_mod._json_output = False

    def tearDown(self):
        cli_mod._json_output = self._orig_json

    @patch("cli.main._print")
    def test_analyze_text(self, mock_print):
        """analyze text mode."""
        workload = MagicMock(
            name="general",
            cpu_percent=25.0,
            memory_percent=60.0,
            description="General workload",
        )
        rec = MagicMock(
            governor="schedutil",
            swappiness=60,
            io_scheduler="mq-deadline",
            thp="always",
            reason="balanced",
        )
        current = {"governor": "performance", "swappiness": 60}
        with patch("utils.auto_tuner.AutoTuner.detect_workload", return_value=workload):
            with patch("utils.auto_tuner.AutoTuner.recommend", return_value=rec):
                with patch(
                    "utils.auto_tuner.AutoTuner.get_current_settings",
                    return_value=current,
                ):
                    result = cmd_tuner(_make_args(action="analyze"))
        self.assertEqual(result, 0)

    @patch("builtins.print")
    def test_analyze_json(self, mock_print):
        """analyze JSON mode."""
        cli_mod._json_output = True
        workload = MagicMock(name="general")
        rec = MagicMock(governor="schedutil")
        current = {"governor": "performance"}
        with patch("utils.auto_tuner.AutoTuner.detect_workload", return_value=workload):
            with patch("utils.auto_tuner.AutoTuner.recommend", return_value=rec):
                with patch(
                    "utils.auto_tuner.AutoTuner.get_current_settings",
                    return_value=current,
                ):
                    result = cmd_tuner(_make_args(action="analyze"))
        self.assertEqual(result, 0)

    @patch("cli.main.run_operation", return_value=True)
    @patch("cli.main._print")
    def test_apply_success(self, mock_print, mock_run):
        """apply action success — both operations called."""
        rec = MagicMock(governor="schedutil", swappiness=60)
        with patch("utils.auto_tuner.AutoTuner.recommend", return_value=rec):
            with patch(
                "utils.auto_tuner.AutoTuner.apply_recommendation",
                return_value=("cmd", [], "applying"),
            ):
                with patch(
                    "utils.auto_tuner.AutoTuner.apply_swappiness",
                    return_value=("sysctl", [], "swappiness"),
                ):
                    result = cmd_tuner(_make_args(action="apply"))
        self.assertEqual(result, 0)
        self.assertEqual(mock_run.call_count, 2)

    @patch("cli.main.run_operation", return_value=False)
    @patch("cli.main._print")
    def test_apply_first_fails(self, mock_print, mock_run):
        """apply action first op fails — swappiness not called."""
        rec = MagicMock(governor="schedutil", swappiness=60)
        with patch("utils.auto_tuner.AutoTuner.recommend", return_value=rec):
            with patch(
                "utils.auto_tuner.AutoTuner.apply_recommendation",
                return_value=("cmd", [], "applying"),
            ):
                result = cmd_tuner(_make_args(action="apply"))
        self.assertEqual(result, 1)
        self.assertEqual(mock_run.call_count, 1)

    @patch("cli.main._print")
    def test_history_text_with_entries(self, mock_print):
        """history text mode with entries."""
        import time as time_mod

        entry = MagicMock(timestamp=time_mod.time(), workload="gaming", applied=True)
        with patch(
            "utils.auto_tuner.AutoTuner.get_tuning_history", return_value=[entry]
        ):
            result = cmd_tuner(_make_args(action="history"))
        self.assertEqual(result, 0)

    @patch("cli.main._print")
    def test_history_text_empty(self, mock_print):
        """history text mode empty."""
        with patch("utils.auto_tuner.AutoTuner.get_tuning_history", return_value=[]):
            result = cmd_tuner(_make_args(action="history"))
        self.assertEqual(result, 0)
        printed = " ".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("no tuning history", printed)

    @patch("builtins.print")
    def test_history_json(self, mock_print):
        """history JSON mode."""
        cli_mod._json_output = True
        entry = MagicMock(timestamp=1700000000, workload="general", applied=False)
        with patch(
            "utils.auto_tuner.AutoTuner.get_tuning_history", return_value=[entry]
        ):
            result = cmd_tuner(_make_args(action="history"))
        self.assertEqual(result, 0)

    def test_unknown_action(self):
        """Unknown action returns 1."""
        with patch("utils.auto_tuner.AutoTuner"):
            result = cmd_tuner(_make_args(action="unknown"))
        self.assertEqual(result, 1)


# =====================================================================
# 12. cmd_profile  (lines 1534-1694)
# =====================================================================
class TestCmdProfile(unittest.TestCase):
    """Cover cmd_profile list with profiles, create, delete text/json."""

    def setUp(self):
        self._orig_json = cli_mod._json_output
        cli_mod._json_output = False

    def tearDown(self):
        cli_mod._json_output = self._orig_json

    @patch("cli.main.ProfileManager.get_active_profile", return_value="gaming")
    @patch("cli.main.ProfileManager.list_profiles")
    @patch("cli.main._print")
    def test_list_text_with_profiles(self, mock_print, mock_list, mock_active):
        """list text mode with profiles and active badge."""
        mock_list.return_value = [
            {
                "key": "gaming",
                "name": "Gaming",
                "builtin": True,
                "icon": "🎮",
                "description": "Optimized for games",
            },
            {
                "key": "office",
                "name": "Office",
                "builtin": False,
                "icon": "📋",
                "description": "Office work",
            },
        ]
        result = cmd_profile(_make_args(action="list"))
        self.assertEqual(result, 0)
        printed = " ".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("[ACTIVE]", printed)
        self.assertIn("custom", printed)

    @patch("cli.main.ProfileManager.capture_current_as_profile")
    @patch("cli.main._print")
    def test_create_text_success(self, mock_print, mock_capture):
        """create text mode success."""
        mock_capture.return_value = MagicMock(
            success=True, message="Created profile 'test'", data={}
        )
        result = cmd_profile(_make_args(action="create", name="test"))
        self.assertEqual(result, 0)

    @patch("cli.main.ProfileManager.capture_current_as_profile")
    @patch("builtins.print")
    def test_create_json(self, mock_print, mock_capture):
        """create JSON mode."""
        cli_mod._json_output = True
        mock_capture.return_value = MagicMock(success=True, message="OK", data={})
        result = cmd_profile(_make_args(action="create", name="test"))
        self.assertEqual(result, 0)

    @patch("cli.main._print")
    def test_create_no_name(self, mock_print):
        """create without name returns 1."""
        result = cmd_profile(_make_args(action="create", name=None))
        self.assertEqual(result, 1)

    @patch("cli.main.ProfileManager.delete_custom_profile")
    @patch("cli.main._print")
    def test_delete_text_success(self, mock_print, mock_delete):
        """delete text mode success."""
        mock_delete.return_value = MagicMock(success=True, message="Deleted")
        result = cmd_profile(_make_args(action="delete", name="old"))
        self.assertEqual(result, 0)

    @patch("cli.main.ProfileManager.delete_custom_profile")
    @patch("builtins.print")
    def test_delete_json(self, mock_print, mock_delete):
        """delete JSON mode."""
        cli_mod._json_output = True
        mock_delete.return_value = MagicMock(success=True, message="Deleted")
        result = cmd_profile(_make_args(action="delete", name="old"))
        self.assertEqual(result, 0)

    @patch("cli.main._print")
    def test_delete_no_name(self, mock_print):
        """delete without name returns 1."""
        result = cmd_profile(_make_args(action="delete", name=None))
        self.assertEqual(result, 1)


# =====================================================================
# 13. cmd_plugins  (lines 709-750)
# =====================================================================
class TestCmdPlugins(unittest.TestCase):
    """Cover cmd_plugins edge cases."""

    def setUp(self):
        self._orig_json = cli_mod._json_output
        cli_mod._json_output = False

    def tearDown(self):
        cli_mod._json_output = self._orig_json

    @patch("cli.main.PluginLoader")
    @patch("cli.main._print")
    def test_list_text_empty(self, mock_print, mock_loader_cls):
        """list text mode with no plugins."""
        mock_loader_cls.return_value.list_plugins.return_value = []
        result = cmd_plugins(_make_args(action="list"))
        self.assertEqual(result, 0)
        printed = " ".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("no plugins found", printed)

    @patch("cli.main.PluginLoader")
    @patch("cli.main._print")
    def test_list_text_with_manifest_none(self, mock_print, mock_loader_cls):
        """list text mode with plugin whose manifest is None."""
        mock_loader_cls.return_value.list_plugins.return_value = [
            {"name": "test-plugin", "enabled": True, "manifest": None}
        ]
        result = cmd_plugins(_make_args(action="list"))
        self.assertEqual(result, 0)
        printed = " ".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("test-plugin", printed)
        self.assertIn("unknown", printed)

    @patch("cli.main.PluginLoader")
    @patch("cli.main._print")
    def test_enable_text_success(self, mock_print, mock_loader_cls):
        """enable text mode."""
        result = cmd_plugins(_make_args(action="enable", name="my-plugin"))
        self.assertEqual(result, 0)
        printed = " ".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("enabled", printed)

    @patch("cli.main.PluginLoader")
    @patch("cli.main._print")
    def test_disable_text_success(self, mock_print, mock_loader_cls):
        """disable text mode."""
        result = cmd_plugins(_make_args(action="disable", name="my-plugin"))
        self.assertEqual(result, 0)

    @patch("cli.main.PluginLoader")
    @patch("builtins.print")
    def test_enable_json(self, mock_print, mock_loader_cls):
        """enable JSON mode."""
        cli_mod._json_output = True
        result = cmd_plugins(_make_args(action="enable", name="my-plugin"))
        self.assertEqual(result, 0)
        data = json.loads(mock_print.call_args[0][0])
        self.assertTrue(data["enabled"])

    @patch("cli.main.PluginLoader")
    @patch("cli.main._print")
    def test_enable_no_name(self, mock_print, mock_loader_cls):
        """enable without name returns 1."""
        result = cmd_plugins(_make_args(action="enable", name=None))
        self.assertEqual(result, 1)

    def test_unknown_action(self):
        """Unknown action returns 1."""
        with patch("cli.main.PluginLoader"):
            result = cmd_plugins(_make_args(action="unknown"))
        self.assertEqual(result, 1)


# =====================================================================
# 14. cmd_tweak edge cases  (lines 148-175)
# =====================================================================
class TestCmdTweakEdges(unittest.TestCase):
    """Cover cmd_tweak power return path and unknown action."""

    def setUp(self):
        self._orig_json = cli_mod._json_output
        cli_mod._json_output = False

    def tearDown(self):
        cli_mod._json_output = self._orig_json

    @patch("cli.main.run_operation", return_value=True)
    @patch("cli.main.TweakOps.set_power_profile", return_value=("cmd", [], "set power"))
    def test_power_success(self, mock_tweak, mock_run):
        """power action returns 0 on success."""
        result = cmd_tweak(_make_args(action="power", profile="balanced"))
        self.assertEqual(result, 0)

    @patch("cli.main.run_operation", return_value=False)
    @patch("cli.main.TweakOps.set_power_profile", return_value=("cmd", [], "set power"))
    def test_power_failure(self, mock_tweak, mock_run):
        """power action returns 1 on failure."""
        result = cmd_tweak(_make_args(action="power", profile="balanced"))
        self.assertEqual(result, 1)

    def test_unknown_action(self):
        """Unknown action returns 1."""
        result = cmd_tweak(_make_args(action="unknown"))
        self.assertEqual(result, 1)


# =====================================================================
# 15. main() global flags  (lines 3664-3735)
# =====================================================================
class TestMainFlags(unittest.TestCase):
    """Cover --json, --timeout, --dry-run flags and no-command path."""

    @patch("cli.main.cmd_info", return_value=0)
    def test_json_flag(self, mock_cmd):
        """--json flag dispatches correctly."""
        result = main(["--json", "info"])
        self.assertEqual(result, 0)

    @patch("cli.main.cmd_cleanup", return_value=0)
    def test_timeout_flag(self, mock_cmd):
        """--timeout flag dispatches correctly."""
        result = main(["--timeout", "60", "cleanup"])
        self.assertEqual(result, 0)

    @patch("cli.main.cmd_cleanup", return_value=0)
    def test_dry_run_flag(self, mock_cmd):
        """--dry-run flag dispatches correctly."""
        result = main(["--dry-run", "cleanup"])
        self.assertEqual(result, 0)

    def test_no_command_returns_0(self):
        """No command given prints help and returns 0."""
        with patch("sys.stdout", new_callable=StringIO):
            result = main([])
        self.assertEqual(result, 0)

    @patch("cli.main.cmd_audit_log", return_value=0)
    def test_audit_log_command_dispatch(self, mock_cmd):
        """audit-log command dispatches correctly."""
        result = main(["audit-log"])
        self.assertEqual(result, 0)

    @patch("cli.main.cmd_self_update", return_value=0)
    def test_self_update_command_dispatch(self, mock_cmd):
        """self-update command dispatches correctly."""
        result = main(["self-update"])
        self.assertEqual(result, 0)

    @patch("cli.main.cmd_preset", return_value=0)
    def test_preset_command_dispatch(self, mock_cmd):
        """preset command dispatches correctly."""
        result = main(["preset", "list"])
        self.assertEqual(result, 0)

    @patch("cli.main.cmd_focus_mode", return_value=0)
    def test_focus_mode_dispatch(self, mock_cmd):
        """focus-mode command dispatches correctly."""
        result = main(["focus-mode", "status"])
        self.assertEqual(result, 0)

    @patch("cli.main.cmd_health_history", return_value=0)
    def test_health_history_dispatch(self, mock_cmd):
        """health-history command dispatches correctly."""
        result = main(["health-history", "show"])
        self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()

"""Extended tests for utils/safety.py SafetyManager.

Covers check_dnf_lock, check_snapshot_tool, create_snapshot, and
confirm_action with both success and failure paths, edge cases,
and UI interaction scenarios.
"""

import os
import subprocess
import sys
import unittest
from unittest.mock import MagicMock, call, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from utils.safety import SafetyManager


# ---------------------------------------------------------------------------
# check_dnf_lock
# ---------------------------------------------------------------------------


class TestCheckDnfLock(unittest.TestCase):
    """Tests for SafetyManager.check_dnf_lock.

    Note: ``os`` is lazily imported inside the method, so we patch
    ``os.path.exists`` at the global ``os`` module level rather than
    ``utils.safety.os.path.exists``.
    """

    @patch("utils.safety.subprocess.check_call")
    @patch("os.path.exists", return_value=True)
    def test_locked_when_pid_file_exists(self, mock_exists, mock_check_call):
        """Returns True immediately when /var/run/dnf.pid exists."""
        result = SafetyManager.check_dnf_lock()
        self.assertTrue(result)
        mock_exists.assert_called_once_with("/var/run/dnf.pid")
        mock_check_call.assert_not_called()

    @patch("utils.safety.subprocess.check_call", return_value=0)
    @patch("os.path.exists", return_value=False)
    def test_locked_when_pgrep_finds_process(self, mock_exists, mock_check_call):
        """Returns True when pid file absent but pgrep finds dnf/yum/rpm."""
        result = SafetyManager.check_dnf_lock()
        self.assertTrue(result)
        mock_check_call.assert_called_once_with(
            ["pgrep", "-f", "dnf|yum|rpm"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )

    @patch(
        "utils.safety.subprocess.check_call",
        side_effect=subprocess.CalledProcessError(1, "pgrep"),
    )
    @patch("os.path.exists", return_value=False)
    def test_not_locked_when_nothing_running(self, mock_exists, mock_check_call):
        """Returns False when pid file absent and no matching processes."""
        result = SafetyManager.check_dnf_lock()
        self.assertFalse(result)

    @patch(
        "utils.safety.subprocess.check_call",
        side_effect=subprocess.CalledProcessError(2, "pgrep"),
    )
    @patch("os.path.exists", return_value=False)
    def test_not_locked_pgrep_syntax_error(self, mock_exists, mock_check_call):
        """Returns False on pgrep syntax/other error (exit code 2)."""
        result = SafetyManager.check_dnf_lock()
        self.assertFalse(result)

    @patch("utils.safety.subprocess.check_call")
    @patch("os.path.exists", return_value=True)
    def test_pid_file_short_circuits_pgrep(self, mock_exists, mock_check_call):
        """Pgrep is never called when pid file already signals a lock."""
        SafetyManager.check_dnf_lock()
        mock_check_call.assert_not_called()

    @patch("utils.safety.subprocess.check_call")
    @patch("os.path.exists", return_value=False)
    def test_pgrep_called_with_correct_timeout(self, mock_exists, mock_check_call):
        """Pgrep call uses timeout=10."""
        SafetyManager.check_dnf_lock()
        _, kwargs = mock_check_call.call_args
        self.assertEqual(kwargs["timeout"], 10)

    @patch("utils.safety.subprocess.check_call")
    @patch("os.path.exists", return_value=False)
    def test_pgrep_stdout_stderr_devnull(self, mock_exists, mock_check_call):
        """Pgrep suppresses stdout and stderr."""
        SafetyManager.check_dnf_lock()
        _, kwargs = mock_check_call.call_args
        self.assertEqual(kwargs["stdout"], subprocess.DEVNULL)
        self.assertEqual(kwargs["stderr"], subprocess.DEVNULL)

    @patch("utils.safety.subprocess.check_call")
    @patch("os.path.exists", return_value=False)
    def test_pgrep_pattern_matches_dnf_yum_rpm(self, mock_exists, mock_check_call):
        """Pgrep uses the pattern 'dnf|yum|rpm' to find processes."""
        SafetyManager.check_dnf_lock()
        cmd = mock_check_call.call_args[0][0]
        self.assertEqual(cmd, ["pgrep", "-f", "dnf|yum|rpm"])

    @patch("utils.safety.subprocess.check_call", return_value=0)
    @patch("os.path.exists", return_value=False)
    def test_return_type_is_bool(self, mock_exists, mock_check_call):
        """Return value is always a boolean."""
        result = SafetyManager.check_dnf_lock()
        self.assertIsInstance(result, bool)


# ---------------------------------------------------------------------------
# check_snapshot_tool
# ---------------------------------------------------------------------------


class TestCheckSnapshotTool(unittest.TestCase):
    """Tests for SafetyManager.check_snapshot_tool."""

    @patch("utils.safety.shutil.which")
    def test_timeshift_preferred_over_snapper(self, mock_which):
        """Returns 'timeshift' when both tools are available."""
        mock_which.side_effect = lambda x: f"/usr/bin/{x}"
        result = SafetyManager.check_snapshot_tool()
        self.assertEqual(result, "timeshift")

    @patch("utils.safety.shutil.which")
    def test_returns_timeshift_when_only_timeshift(self, mock_which):
        """Returns 'timeshift' when only timeshift is installed."""
        mock_which.side_effect = lambda x: (
            "/usr/bin/timeshift" if x == "timeshift" else None
        )
        result = SafetyManager.check_snapshot_tool()
        self.assertEqual(result, "timeshift")

    @patch("utils.safety.shutil.which")
    def test_returns_snapper_when_only_snapper(self, mock_which):
        """Returns 'snapper' when only snapper is installed."""
        mock_which.side_effect = lambda x: (
            "/usr/bin/snapper" if x == "snapper" else None
        )
        result = SafetyManager.check_snapshot_tool()
        self.assertEqual(result, "snapper")

    @patch("utils.safety.shutil.which", return_value=None)
    def test_returns_none_when_no_tool(self, mock_which):
        """Returns None when neither tool is installed."""
        result = SafetyManager.check_snapshot_tool()
        self.assertIsNone(result)

    @patch("utils.safety.shutil.which")
    def test_checks_timeshift_before_snapper(self, mock_which):
        """Checks timeshift first; does not check snapper if timeshift found."""
        mock_which.return_value = "/usr/bin/timeshift"
        SafetyManager.check_snapshot_tool()
        self.assertEqual(mock_which.call_args_list[0], call("timeshift"))

    @patch("utils.safety.shutil.which")
    def test_return_type_is_string_or_none(self, mock_which):
        """Return value is always a string or None, never another type."""
        mock_which.return_value = None
        result = SafetyManager.check_snapshot_tool()
        self.assertIsNone(result)

        mock_which.return_value = "/usr/bin/timeshift"
        result = SafetyManager.check_snapshot_tool()
        self.assertIsInstance(result, str)


# ---------------------------------------------------------------------------
# create_snapshot
# ---------------------------------------------------------------------------


class TestCreateSnapshot(unittest.TestCase):
    """Tests for SafetyManager.create_snapshot."""

    @patch("utils.safety.subprocess.run")
    def test_timeshift_snapshot_success(self, mock_run):
        """Returns True on successful timeshift snapshot."""
        mock_run.return_value = MagicMock(returncode=0)
        result = SafetyManager.create_snapshot("timeshift", "Test snapshot")
        self.assertTrue(result)
        mock_run.assert_called_once_with(
            [
                "pkexec",
                "timeshift",
                "--create",
                "--comments",
                "Test snapshot",
                "--tags",
                "D",
            ],
            check=True,
            timeout=600,
        )

    @patch("utils.safety.subprocess.run")
    def test_snapper_snapshot_success(self, mock_run):
        """Returns True on successful snapper snapshot."""
        mock_run.return_value = MagicMock(returncode=0)
        result = SafetyManager.create_snapshot("snapper", "Test snapshot")
        self.assertTrue(result)
        mock_run.assert_called_once_with(
            ["pkexec", "snapper", "create", "--description", "Test snapshot"],
            check=True,
            timeout=600,
        )

    @patch("utils.safety.subprocess.run")
    def test_timeshift_default_comment(self, mock_run):
        """Uses default comment when none provided."""
        mock_run.return_value = MagicMock(returncode=0)
        SafetyManager.create_snapshot("timeshift")
        args, kwargs = mock_run.call_args
        self.assertIn("Loofi Auto-Snapshot", args[0])

    @patch("utils.safety.subprocess.run")
    def test_snapper_default_comment(self, mock_run):
        """Uses default comment for snapper when none provided."""
        mock_run.return_value = MagicMock(returncode=0)
        SafetyManager.create_snapshot("snapper")
        cmd = mock_run.call_args[0][0]
        self.assertIn("Loofi Auto-Snapshot", cmd)

    @patch(
        "utils.safety.subprocess.run",
        side_effect=subprocess.CalledProcessError(1, "pkexec"),
    )
    def test_timeshift_snapshot_failure(self, mock_run):
        """Returns False when timeshift command fails."""
        result = SafetyManager.create_snapshot("timeshift", "fail")
        self.assertFalse(result)

    @patch(
        "utils.safety.subprocess.run",
        side_effect=subprocess.CalledProcessError(1, "pkexec"),
    )
    def test_snapper_snapshot_failure(self, mock_run):
        """Returns False when snapper command fails."""
        result = SafetyManager.create_snapshot("snapper", "fail")
        self.assertFalse(result)

    @patch("utils.safety.subprocess.run")
    def test_unknown_tool_returns_false(self, mock_run):
        """Returns False for an unrecognised tool name."""
        result = SafetyManager.create_snapshot("btrfs-snap", "test")
        self.assertFalse(result)
        mock_run.assert_not_called()

    @patch("utils.safety.subprocess.run")
    def test_empty_tool_returns_false(self, mock_run):
        """Returns False when tool is an empty string."""
        result = SafetyManager.create_snapshot("", "test")
        self.assertFalse(result)
        mock_run.assert_not_called()

    @patch("utils.safety.subprocess.run")
    def test_none_tool_returns_false(self, mock_run):
        """Returns False when tool is None."""
        result = SafetyManager.create_snapshot(None, "test")
        self.assertFalse(result)
        mock_run.assert_not_called()

    @patch("utils.safety.subprocess.run")
    def test_timeout_is_600_seconds(self, mock_run):
        """Snapshot commands use a 600-second timeout."""
        mock_run.return_value = MagicMock(returncode=0)
        SafetyManager.create_snapshot("timeshift")
        _, kwargs = mock_run.call_args
        self.assertEqual(kwargs["timeout"], 600)

    @patch("utils.safety.subprocess.run")
    def test_check_true_passed(self, mock_run):
        """Snapshot commands use check=True for CalledProcessError on failure."""
        mock_run.return_value = MagicMock(returncode=0)
        SafetyManager.create_snapshot("snapper")
        _, kwargs = mock_run.call_args
        self.assertTrue(kwargs["check"])

    @patch("utils.safety.subprocess.run")
    def test_timeshift_uses_pkexec(self, mock_run):
        """Timeshift command starts with pkexec for privilege escalation."""
        mock_run.return_value = MagicMock(returncode=0)
        SafetyManager.create_snapshot("timeshift", "priv check")
        cmd = mock_run.call_args[0][0]
        self.assertEqual(cmd[0], "pkexec")

    @patch("utils.safety.subprocess.run")
    def test_snapper_uses_pkexec(self, mock_run):
        """Snapper command starts with pkexec for privilege escalation."""
        mock_run.return_value = MagicMock(returncode=0)
        SafetyManager.create_snapshot("snapper", "priv check")
        cmd = mock_run.call_args[0][0]
        self.assertEqual(cmd[0], "pkexec")

    @patch("utils.safety.subprocess.run")
    def test_comment_with_special_characters(self, mock_run):
        """Comment containing special characters is passed through unchanged."""
        mock_run.return_value = MagicMock(returncode=0)
        comment = "Pre-install: foo & bar 'baz'"
        SafetyManager.create_snapshot("timeshift", comment)
        cmd = mock_run.call_args[0][0]
        self.assertIn(comment, cmd)

    @patch("utils.safety.subprocess.run")
    def test_timeshift_tag_is_daily(self, mock_run):
        """Timeshift snapshots are tagged with 'D' (daily)."""
        mock_run.return_value = MagicMock(returncode=0)
        SafetyManager.create_snapshot("timeshift", "tag check")
        cmd = mock_run.call_args[0][0]
        tag_idx = cmd.index("--tags")
        self.assertEqual(cmd[tag_idx + 1], "D")

    @patch("utils.safety.subprocess.run")
    def test_snapper_no_shell_true(self, mock_run):
        """Snapper command does not use shell=True."""
        mock_run.return_value = MagicMock(returncode=0)
        SafetyManager.create_snapshot("snapper", "security")
        _, kwargs = mock_run.call_args
        self.assertNotIn("shell", kwargs)


# ---------------------------------------------------------------------------
# confirm_action
# ---------------------------------------------------------------------------


class TestConfirmAction(unittest.TestCase):
    """Tests for SafetyManager.confirm_action (PyQt6 dialog).

    ``QMessageBox`` is lazily imported inside ``confirm_action`` via
    ``from PyQt6.QtWidgets import QMessageBox``.  We patch it at the
    PyQt6 module level so the lazy import picks up the mock.
    """

    def _make_parent(self):
        """Create a mock parent widget."""
        parent = MagicMock()
        parent.setDisabled = MagicMock()
        return parent

    @patch("utils.safety.SafetyManager.check_snapshot_tool", return_value=None)
    @patch("PyQt6.QtWidgets.QMessageBox")
    def test_cancel_returns_false(self, MockQMessageBox, mock_tool):
        """Returns False when the user clicks Cancel."""
        parent = self._make_parent()
        mock_msg = MagicMock()
        MockQMessageBox.return_value = mock_msg

        btn_cancel = MagicMock(name="btn_cancel")
        mock_msg.addButton.return_value = btn_cancel
        mock_msg.clickedButton.return_value = btn_cancel

        result = SafetyManager.confirm_action(parent, "install packages")
        self.assertFalse(result)

    @patch("utils.safety.SafetyManager.check_snapshot_tool", return_value=None)
    @patch("PyQt6.QtWidgets.QMessageBox")
    def test_continue_without_snapshot_returns_true(self, MockQMessageBox, mock_tool):
        """Returns True when user clicks 'Continue Without Snapshot'."""
        parent = self._make_parent()
        mock_msg = MagicMock()
        MockQMessageBox.return_value = mock_msg

        btn_continue = MagicMock(name="btn_continue")
        btn_cancel = MagicMock(name="btn_cancel")
        mock_msg.addButton.side_effect = [btn_continue, btn_cancel]
        mock_msg.clickedButton.return_value = btn_continue

        result = SafetyManager.confirm_action(parent, "remove package")
        self.assertTrue(result)

    @patch("utils.safety.SafetyManager.create_snapshot", return_value=True)
    @patch("utils.safety.SafetyManager.check_snapshot_tool", return_value="timeshift")
    @patch("PyQt6.QtWidgets.QMessageBox")
    def test_snapshot_and_continue_success(self, MockQMessageBox, mock_tool, mock_snap):
        """Returns True and creates snapshot when user clicks snapshot button."""
        parent = self._make_parent()
        mock_msg = MagicMock()
        MockQMessageBox.return_value = mock_msg

        btn_continue = MagicMock(name="btn_continue")
        btn_cancel = MagicMock(name="btn_cancel")
        btn_snapshot = MagicMock(name="btn_snapshot")
        mock_msg.addButton.side_effect = [btn_continue, btn_cancel, btn_snapshot]
        mock_msg.clickedButton.return_value = btn_snapshot

        result = SafetyManager.confirm_action(parent, "install foo")
        self.assertTrue(result)
        mock_snap.assert_called_once()
        MockQMessageBox.information.assert_called_once()

    @patch("utils.safety.SafetyManager.create_snapshot", return_value=False)
    @patch("utils.safety.SafetyManager.check_snapshot_tool", return_value="snapper")
    @patch("PyQt6.QtWidgets.QMessageBox")
    def test_snapshot_failure_shows_warning(
        self, MockQMessageBox, mock_tool, mock_snap
    ):
        """Shows warning dialog when snapshot creation fails."""
        parent = self._make_parent()
        mock_msg = MagicMock()
        MockQMessageBox.return_value = mock_msg

        btn_continue = MagicMock(name="btn_continue")
        btn_cancel = MagicMock(name="btn_cancel")
        btn_snapshot = MagicMock(name="btn_snapshot")
        mock_msg.addButton.side_effect = [btn_continue, btn_cancel, btn_snapshot]
        mock_msg.clickedButton.return_value = btn_snapshot

        result = SafetyManager.confirm_action(parent, "remove bar")
        self.assertTrue(result)
        MockQMessageBox.warning.assert_called_once()
        MockQMessageBox.information.assert_not_called()

    @patch("utils.safety.SafetyManager.create_snapshot", return_value=True)
    @patch("utils.safety.SafetyManager.check_snapshot_tool", return_value="timeshift")
    @patch("PyQt6.QtWidgets.QMessageBox")
    def test_parent_disabled_during_snapshot(
        self, MockQMessageBox, mock_tool, mock_snap
    ):
        """Parent widget is disabled then re-enabled during snapshot."""
        parent = self._make_parent()
        mock_msg = MagicMock()
        MockQMessageBox.return_value = mock_msg

        btn_continue = MagicMock(name="btn_continue")
        btn_cancel = MagicMock(name="btn_cancel")
        btn_snapshot = MagicMock(name="btn_snapshot")
        mock_msg.addButton.side_effect = [btn_continue, btn_cancel, btn_snapshot]
        mock_msg.clickedButton.return_value = btn_snapshot

        SafetyManager.confirm_action(parent, "do stuff")
        calls = parent.setDisabled.call_args_list
        self.assertEqual(calls[0], call(True))
        self.assertEqual(calls[1], call(False))

    @patch("utils.safety.SafetyManager.check_snapshot_tool", return_value=None)
    @patch("PyQt6.QtWidgets.QMessageBox")
    def test_no_snapshot_button_when_no_tool(self, MockQMessageBox, mock_tool):
        """Snapshot button is not added when no snapshot tool is detected."""
        parent = self._make_parent()
        mock_msg = MagicMock()
        MockQMessageBox.return_value = mock_msg

        btn_continue = MagicMock(name="btn_continue")
        btn_cancel = MagicMock(name="btn_cancel")
        mock_msg.addButton.side_effect = [btn_continue, btn_cancel]
        mock_msg.clickedButton.return_value = btn_continue

        SafetyManager.confirm_action(parent, "test action")
        self.assertEqual(mock_msg.addButton.call_count, 2)

    @patch("utils.safety.SafetyManager.check_snapshot_tool", return_value="timeshift")
    @patch("PyQt6.QtWidgets.QMessageBox")
    def test_snapshot_button_added_when_tool_available(
        self, MockQMessageBox, mock_tool
    ):
        """Snapshot button is added when a snapshot tool is detected."""
        parent = self._make_parent()
        mock_msg = MagicMock()
        MockQMessageBox.return_value = mock_msg

        btn_continue = MagicMock(name="btn_continue")
        btn_cancel = MagicMock(name="btn_cancel")
        btn_snapshot = MagicMock(name="btn_snapshot")
        mock_msg.addButton.side_effect = [btn_continue, btn_cancel, btn_snapshot]
        mock_msg.clickedButton.return_value = btn_cancel

        SafetyManager.confirm_action(parent, "test action")
        self.assertEqual(mock_msg.addButton.call_count, 3)

    @patch("utils.safety.SafetyManager.check_snapshot_tool", return_value=None)
    @patch("PyQt6.QtWidgets.QMessageBox")
    def test_default_button_cancel_when_no_tool(self, MockQMessageBox, mock_tool):
        """Default button is Cancel when no snapshot tool is available."""
        parent = self._make_parent()
        mock_msg = MagicMock()
        MockQMessageBox.return_value = mock_msg

        btn_continue = MagicMock(name="btn_continue")
        btn_cancel = MagicMock(name="btn_cancel")
        mock_msg.addButton.side_effect = [btn_continue, btn_cancel]
        mock_msg.clickedButton.return_value = btn_cancel

        SafetyManager.confirm_action(parent, "action")
        mock_msg.setDefaultButton.assert_called_once_with(btn_cancel)

    @patch("utils.safety.SafetyManager.check_snapshot_tool", return_value="timeshift")
    @patch("PyQt6.QtWidgets.QMessageBox")
    def test_default_button_snapshot_when_tool_available(
        self, MockQMessageBox, mock_tool
    ):
        """Default button is the snapshot button when a tool is available."""
        parent = self._make_parent()
        mock_msg = MagicMock()
        MockQMessageBox.return_value = mock_msg

        btn_continue = MagicMock(name="btn_continue")
        btn_cancel = MagicMock(name="btn_cancel")
        btn_snapshot = MagicMock(name="btn_snapshot")
        mock_msg.addButton.side_effect = [btn_continue, btn_cancel, btn_snapshot]
        mock_msg.clickedButton.return_value = btn_cancel

        SafetyManager.confirm_action(parent, "action")
        mock_msg.setDefaultButton.assert_called_once_with(btn_snapshot)

    @patch("utils.safety.SafetyManager.check_snapshot_tool", return_value=None)
    @patch("PyQt6.QtWidgets.QMessageBox")
    def test_dialog_title_is_safety_check(self, MockQMessageBox, mock_tool):
        """Dialog window title is 'Safety Check'."""
        parent = self._make_parent()
        mock_msg = MagicMock()
        MockQMessageBox.return_value = mock_msg

        btn_continue = MagicMock(name="btn_continue")
        btn_cancel = MagicMock(name="btn_cancel")
        mock_msg.addButton.side_effect = [btn_continue, btn_cancel]
        mock_msg.clickedButton.return_value = btn_cancel

        SafetyManager.confirm_action(parent, "test")
        mock_msg.setWindowTitle.assert_called_once_with("Safety Check")

    @patch("utils.safety.SafetyManager.check_snapshot_tool", return_value=None)
    @patch("PyQt6.QtWidgets.QMessageBox")
    def test_dialog_text_contains_description(self, MockQMessageBox, mock_tool):
        """Dialog text includes the action description."""
        parent = self._make_parent()
        mock_msg = MagicMock()
        MockQMessageBox.return_value = mock_msg

        btn_continue = MagicMock(name="btn_continue")
        btn_cancel = MagicMock(name="btn_cancel")
        mock_msg.addButton.side_effect = [btn_continue, btn_cancel]
        mock_msg.clickedButton.return_value = btn_cancel

        SafetyManager.confirm_action(parent, "remove all packages")
        text_arg = mock_msg.setText.call_args[0][0]
        self.assertIn("remove all packages", text_arg)

    @patch("utils.safety.SafetyManager.check_snapshot_tool", return_value=None)
    @patch("PyQt6.QtWidgets.QMessageBox")
    def test_dialog_icon_is_warning(self, MockQMessageBox, mock_tool):
        """Dialog icon is set to Warning."""
        parent = self._make_parent()
        mock_msg = MagicMock()
        MockQMessageBox.return_value = mock_msg

        btn_continue = MagicMock(name="btn_continue")
        btn_cancel = MagicMock(name="btn_cancel")
        mock_msg.addButton.side_effect = [btn_continue, btn_cancel]
        mock_msg.clickedButton.return_value = btn_cancel

        SafetyManager.confirm_action(parent, "test")
        mock_msg.setIcon.assert_called_once_with(MockQMessageBox.Icon.Warning)

    @patch("utils.safety.SafetyManager.check_snapshot_tool", return_value=None)
    @patch("PyQt6.QtWidgets.QMessageBox")
    def test_exec_called_on_dialog(self, MockQMessageBox, mock_tool):
        """Dialog.exec() is called to show the dialog."""
        parent = self._make_parent()
        mock_msg = MagicMock()
        MockQMessageBox.return_value = mock_msg

        btn_continue = MagicMock(name="btn_continue")
        btn_cancel = MagicMock(name="btn_cancel")
        mock_msg.addButton.side_effect = [btn_continue, btn_cancel]
        mock_msg.clickedButton.return_value = btn_cancel

        SafetyManager.confirm_action(parent, "test")
        mock_msg.exec.assert_called_once()

    @patch("utils.safety.SafetyManager.create_snapshot", return_value=True)
    @patch("utils.safety.SafetyManager.check_snapshot_tool", return_value="timeshift")
    @patch("PyQt6.QtWidgets.QMessageBox")
    def test_snapshot_comment_derives_from_description(
        self, MockQMessageBox, mock_tool, mock_snap
    ):
        """Snapshot comment is derived from the first word of description."""
        parent = self._make_parent()
        mock_msg = MagicMock()
        MockQMessageBox.return_value = mock_msg

        btn_continue = MagicMock(name="btn_continue")
        btn_cancel = MagicMock(name="btn_cancel")
        btn_snapshot = MagicMock(name="btn_snapshot")
        mock_msg.addButton.side_effect = [btn_continue, btn_cancel, btn_snapshot]
        mock_msg.clickedButton.return_value = btn_snapshot

        SafetyManager.confirm_action(parent, "install heavy packages")
        comment = mock_snap.call_args[0][1]
        self.assertEqual(comment, "Pre-install")

    @patch("utils.safety.SafetyManager.create_snapshot", return_value=False)
    @patch("utils.safety.SafetyManager.check_snapshot_tool", return_value="snapper")
    @patch("PyQt6.QtWidgets.QMessageBox")
    def test_snapshot_failure_still_returns_true(
        self, MockQMessageBox, mock_tool, mock_snap
    ):
        """Action proceeds (returns True) even when snapshot fails."""
        parent = self._make_parent()
        mock_msg = MagicMock()
        MockQMessageBox.return_value = mock_msg

        btn_continue = MagicMock(name="btn_continue")
        btn_cancel = MagicMock(name="btn_cancel")
        btn_snapshot = MagicMock(name="btn_snapshot")
        mock_msg.addButton.side_effect = [btn_continue, btn_cancel, btn_snapshot]
        mock_msg.clickedButton.return_value = btn_snapshot

        result = SafetyManager.confirm_action(parent, "update system")
        self.assertTrue(result)

    @patch("utils.safety.SafetyManager.check_snapshot_tool", return_value=None)
    @patch("PyQt6.QtWidgets.QMessageBox")
    def test_informative_text_mentions_snapshot(self, MockQMessageBox, mock_tool):
        """Informative text recommends creating a snapshot."""
        parent = self._make_parent()
        mock_msg = MagicMock()
        MockQMessageBox.return_value = mock_msg

        btn_continue = MagicMock(name="btn_continue")
        btn_cancel = MagicMock(name="btn_cancel")
        mock_msg.addButton.side_effect = [btn_continue, btn_cancel]
        mock_msg.clickedButton.return_value = btn_cancel

        SafetyManager.confirm_action(parent, "test")
        info_arg = mock_msg.setInformativeText.call_args[0][0]
        self.assertIn("snapshot", info_arg.lower())

    @patch("utils.safety.SafetyManager.create_snapshot", return_value=True)
    @patch("utils.safety.SafetyManager.check_snapshot_tool", return_value="snapper")
    @patch("PyQt6.QtWidgets.QMessageBox")
    def test_snapshot_button_label_contains_tool_name(
        self, MockQMessageBox, mock_tool, mock_snap
    ):
        """Snapshot button label includes the capitalised tool name."""
        parent = self._make_parent()
        mock_msg = MagicMock()
        MockQMessageBox.return_value = mock_msg

        btn_continue = MagicMock(name="btn_continue")
        btn_cancel = MagicMock(name="btn_cancel")
        btn_snapshot = MagicMock(name="btn_snapshot")
        mock_msg.addButton.side_effect = [btn_continue, btn_cancel, btn_snapshot]
        mock_msg.clickedButton.return_value = btn_cancel

        SafetyManager.confirm_action(parent, "test")
        # Third addButton call is the snapshot button
        third_call_args = mock_msg.addButton.call_args_list[2][0]
        label = third_call_args[0]
        self.assertIn("Snapper", label)

    @patch("utils.safety.SafetyManager.create_snapshot", return_value=True)
    @patch("utils.safety.SafetyManager.check_snapshot_tool", return_value="timeshift")
    @patch("PyQt6.QtWidgets.QMessageBox")
    def test_snapshot_success_shows_information_dialog(
        self, MockQMessageBox, mock_tool, mock_snap
    ):
        """Successful snapshot shows information dialog, not warning."""
        parent = self._make_parent()
        mock_msg = MagicMock()
        MockQMessageBox.return_value = mock_msg

        btn_continue = MagicMock(name="btn_continue")
        btn_cancel = MagicMock(name="btn_cancel")
        btn_snapshot = MagicMock(name="btn_snapshot")
        mock_msg.addButton.side_effect = [btn_continue, btn_cancel, btn_snapshot]
        mock_msg.clickedButton.return_value = btn_snapshot

        SafetyManager.confirm_action(parent, "install stuff")
        MockQMessageBox.information.assert_called_once()
        MockQMessageBox.warning.assert_not_called()

    @patch("utils.safety.SafetyManager.create_snapshot", return_value=True)
    @patch("utils.safety.SafetyManager.check_snapshot_tool", return_value="timeshift")
    @patch("PyQt6.QtWidgets.QMessageBox")
    def test_create_snapshot_receives_correct_tool(
        self, MockQMessageBox, mock_tool, mock_snap
    ):
        """create_snapshot is called with the detected tool name."""
        parent = self._make_parent()
        mock_msg = MagicMock()
        MockQMessageBox.return_value = mock_msg

        btn_continue = MagicMock(name="btn_continue")
        btn_cancel = MagicMock(name="btn_cancel")
        btn_snapshot = MagicMock(name="btn_snapshot")
        mock_msg.addButton.side_effect = [btn_continue, btn_cancel, btn_snapshot]
        mock_msg.clickedButton.return_value = btn_snapshot

        SafetyManager.confirm_action(parent, "upgrade kernel")
        tool_arg = mock_snap.call_args[0][0]
        self.assertEqual(tool_arg, "timeshift")

    @patch("utils.safety.SafetyManager.create_snapshot", return_value=False)
    @patch("utils.safety.SafetyManager.check_snapshot_tool", return_value="timeshift")
    @patch("PyQt6.QtWidgets.QMessageBox")
    def test_parent_reenabled_after_failed_snapshot(
        self, MockQMessageBox, mock_tool, mock_snap
    ):
        """Parent is re-enabled even when snapshot creation fails."""
        parent = self._make_parent()
        mock_msg = MagicMock()
        MockQMessageBox.return_value = mock_msg

        btn_continue = MagicMock(name="btn_continue")
        btn_cancel = MagicMock(name="btn_cancel")
        btn_snapshot = MagicMock(name="btn_snapshot")
        mock_msg.addButton.side_effect = [btn_continue, btn_cancel, btn_snapshot]
        mock_msg.clickedButton.return_value = btn_snapshot

        SafetyManager.confirm_action(parent, "risky op")
        # Last setDisabled call should be False (re-enable)
        last_call = parent.setDisabled.call_args_list[-1]
        self.assertEqual(last_call, call(False))


if __name__ == "__main__":
    unittest.main()

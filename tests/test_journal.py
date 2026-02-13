"""
Tests for utils/journal.py — JournalManager.
Coverage-oriented: boot errors, recent errors, service logs, kernel messages,
system info, panic log export, support bundle, quick diagnostic.
"""

import os
import subprocess
import sys
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from utils.journal import JournalManager, Result


class TestGetBootErrors(unittest.TestCase):
    """Tests for JournalManager.get_boot_errors."""

    @patch("utils.journal.subprocess.run")
    def test_returns_stdout_on_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="error line 1\nerror line 2")
        result = JournalManager.get_boot_errors()
        self.assertEqual(result, "error line 1\nerror line 2")
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        self.assertIn("-p", args)
        self.assertIn("3", args)

    @patch("utils.journal.subprocess.run")
    def test_returns_empty_on_nonzero_rc(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        self.assertEqual(JournalManager.get_boot_errors(), "")

    @patch("utils.journal.subprocess.run")
    def test_custom_priority(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="warn msg")
        JournalManager.get_boot_errors(priority=4)
        args = mock_run.call_args[0][0]
        self.assertIn("4", args)

    @patch("utils.journal.subprocess.run", side_effect=OSError("fail"))
    def test_returns_empty_on_oserror(self, mock_run):
        self.assertEqual(JournalManager.get_boot_errors(), "")

    @patch("utils.journal.subprocess.run", side_effect=subprocess.TimeoutExpired("j", 30))
    def test_returns_empty_on_timeout(self, mock_run):
        import subprocess
        self.assertEqual(JournalManager.get_boot_errors(), "")


class TestGetRecentErrors(unittest.TestCase):
    """Tests for JournalManager.get_recent_errors."""

    @patch("utils.journal.subprocess.run")
    def test_returns_stdout_on_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="recent err")
        result = JournalManager.get_recent_errors()
        self.assertEqual(result, "recent err")

    @patch("utils.journal.subprocess.run")
    def test_custom_since(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="x")
        JournalManager.get_recent_errors(since="today")
        args = mock_run.call_args[0][0]
        self.assertIn("today", args)

    @patch("utils.journal.subprocess.run")
    def test_returns_empty_on_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=2, stdout="")
        self.assertEqual(JournalManager.get_recent_errors(), "")

    @patch("utils.journal.subprocess.run", side_effect=OSError("nope"))
    def test_returns_empty_on_exception(self, mock_run):
        self.assertEqual(JournalManager.get_recent_errors(), "")


class TestGetServiceLogs(unittest.TestCase):
    """Tests for JournalManager.get_service_logs."""

    @patch("utils.journal.subprocess.run")
    def test_returns_service_stdout(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="svc log")
        result = JournalManager.get_service_logs("NetworkManager")
        self.assertEqual(result, "svc log")
        args = mock_run.call_args[0][0]
        self.assertIn("NetworkManager.service", " ".join(args))

    @patch("utils.journal.subprocess.run")
    def test_custom_lines(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="log")
        JournalManager.get_service_logs("sshd", lines=100)
        args = mock_run.call_args[0][0]
        self.assertIn("100", args)

    @patch("utils.journal.subprocess.run", side_effect=OSError("no"))
    def test_returns_empty_on_exception(self, mock_run):
        self.assertEqual(JournalManager.get_service_logs("foo"), "")


class TestGetKernelMessages(unittest.TestCase):
    """Tests for JournalManager.get_kernel_messages."""

    @patch("utils.journal.subprocess.run")
    def test_returns_kernel_stdout(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="kern msg")
        result = JournalManager.get_kernel_messages()
        self.assertEqual(result, "kern msg")

    @patch("utils.journal.subprocess.run")
    def test_custom_lines(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="k")
        JournalManager.get_kernel_messages(lines=50)
        args = mock_run.call_args[0][0]
        self.assertIn("50", args)

    @patch("utils.journal.subprocess.run", side_effect=OSError("fail"))
    def test_returns_empty_on_exception(self, mock_run):
        self.assertEqual(JournalManager.get_kernel_messages(), "")


class TestGetSystemInfo(unittest.TestCase):
    """Tests for JournalManager._get_system_info."""

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "GNOME"})
    @patch("utils.journal.subprocess.run")
    @patch("builtins.open", mock_open(read_data='NAME="Fedora"\nVERSION_ID=43\nVARIANT=Workstation\nOTHER=x\n'))
    def test_includes_os_and_desktop(self, mock_run):
        # uname + lspci calls
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="6.12.0-300.fc43.x86_64"),
            MagicMock(returncode=0, stdout="00:02.0 VGA compatible: Intel HD 630\n"),
        ]
        info = JournalManager._get_system_info()
        self.assertIn("Fedora", info)
        self.assertIn("KERNEL=", info)
        self.assertIn("DESKTOP=GNOME", info)
        self.assertIn("GPU=", info)

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "KDE"})
    @patch("utils.journal.subprocess.run", side_effect=OSError("no"))
    @patch("builtins.open", side_effect=OSError("no"))
    def test_graceful_on_all_failures(self, mock_open_fn, mock_run):
        info = JournalManager._get_system_info()
        self.assertIn("DESKTOP=KDE", info)

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": ""})
    @patch("utils.journal.subprocess.run")
    @patch("builtins.open", mock_open(read_data='NAME="Fedora"\n'))
    def test_no_gpu_line_if_no_vga(self, mock_run):
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="6.12.0"),
            MagicMock(returncode=0, stdout="00:1f.0 ISA bridge: Intel\n"),
        ]
        info = JournalManager._get_system_info()
        self.assertNotIn("GPU=", info)


class TestExportPanicLog(unittest.TestCase):
    """Tests for JournalManager.export_panic_log."""

    @patch("utils.journal.subprocess.run")
    @patch.object(JournalManager, "get_boot_errors", return_value="boot error 1")
    @patch.object(JournalManager, "get_kernel_messages", return_value="kern msg")
    @patch.object(JournalManager, "_get_system_info", return_value="NAME=Fedora")
    def test_creates_file_with_sections(self, mock_sysinfo, mock_kern, mock_boot, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="0 loaded units listed")
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "panic.txt"
            result = JournalManager.export_panic_log(out)
            self.assertTrue(result.success)
            self.assertTrue(out.exists())
            content = out.read_text()
            self.assertIn("PANIC LOG", content)
            self.assertIn("boot error 1", content)
            self.assertIn("kern msg", content)
            self.assertIn("NAME=Fedora", content)
            self.assertIn("path", result.data)

    @patch("utils.journal.subprocess.run")
    @patch.object(JournalManager, "get_boot_errors", return_value="")
    @patch.object(JournalManager, "get_kernel_messages", return_value="")
    @patch.object(JournalManager, "_get_system_info", return_value="")
    def test_handles_empty_data(self, mock_sys, mock_kern, mock_boot, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "p.txt"
            result = JournalManager.export_panic_log(out)
            self.assertTrue(result.success)
            content = out.read_text()
            self.assertIn("No errors found", content)

    @patch.object(JournalManager, "_get_system_info", side_effect=OSError("disk full"))
    def test_failure_returns_result(self, mock_sys):
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "bad" / "deep" / "fail.txt"
            result = JournalManager.export_panic_log(out)
            self.assertFalse(result.success)

    @patch("utils.journal.subprocess.run")
    @patch.object(JournalManager, "get_boot_errors", return_value="err")
    @patch.object(JournalManager, "get_kernel_messages", return_value="k")
    @patch.object(JournalManager, "_get_system_info", return_value="info")
    def test_default_path_used(self, mock_sys, mock_kern, mock_boot, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, "home", return_value=Path(tmpdir)):
                result = JournalManager.export_panic_log()
                self.assertTrue(result.success)
                self.assertIn("loofi-panic-log", result.data["path"])


class TestExportSupportBundle(unittest.TestCase):
    """Tests for JournalManager.export_support_bundle."""

    @patch("utils.journal.subprocess.run")
    @patch.object(JournalManager, "get_recent_errors", return_value="err data")
    @patch.object(JournalManager, "_get_system_info", return_value="sys data")
    @patch.object(JournalManager, "export_panic_log")
    def test_creates_zip_bundle(self, mock_panic, mock_sys, mock_recent, mock_run):
        mock_panic.return_value = Result(True, "ok")
        mock_run.return_value = MagicMock(returncode=0, stdout="no failed")
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "bundle.zip"
            result = JournalManager.export_support_bundle(out)
            self.assertTrue(result.success)
            self.assertTrue(out.exists())
            self.assertIn("path", result.data)
            self.assertTrue(result.data["panic_log_ok"])

    @patch("utils.journal.subprocess.run", side_effect=OSError("no systemctl"))
    @patch.object(JournalManager, "get_recent_errors", return_value="")
    @patch.object(JournalManager, "_get_system_info", return_value="")
    @patch.object(JournalManager, "export_panic_log")
    def test_handles_systemctl_failure(self, mock_panic, mock_sys, mock_recent, mock_run):
        mock_panic.return_value = Result(True, "ok")
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "b.zip"
            result = JournalManager.export_support_bundle(out)
            self.assertTrue(result.success)

    def test_failure_on_bad_path(self):
        result = JournalManager.export_support_bundle(Path("/nonexistent/path/bundle.zip"))
        self.assertFalse(result.success)


class TestGetQuickDiagnostic(unittest.TestCase):
    """Tests for JournalManager.get_quick_diagnostic."""

    @patch("utils.journal.subprocess.run")
    @patch.object(JournalManager, "get_boot_errors", return_value="line1\nline2\nline3\n")
    def test_counts_errors_and_parses_services(self, mock_boot, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="  foo.service  loaded failed\n  bar.service  loaded failed\n"
        )
        diag = JournalManager.get_quick_diagnostic()
        self.assertEqual(diag["error_count"], 3)
        self.assertIn("foo.service", diag["failed_services"])
        self.assertIn("bar.service", diag["failed_services"])
        self.assertIsInstance(diag["recent_errors"], list)

    @patch("utils.journal.subprocess.run", side_effect=OSError("no"))
    @patch.object(JournalManager, "get_boot_errors", return_value="")
    def test_empty_when_no_errors(self, mock_boot, mock_run):
        diag = JournalManager.get_quick_diagnostic()
        self.assertEqual(diag["error_count"], 0)
        self.assertEqual(diag["failed_services"], [])

    @patch("utils.journal.subprocess.run")
    @patch.object(JournalManager, "get_boot_errors", return_value="a\nb\nc\nd\ne\nf\ng\n")
    def test_recent_errors_capped(self, mock_boot, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        diag = JournalManager.get_quick_diagnostic()
        self.assertLessEqual(len(diag["recent_errors"]), 5)


if __name__ == "__main__":
    unittest.main()

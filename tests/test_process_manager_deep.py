"""
Tests for services/system/processes.py — ProcessManager.

Covers:
- _get_clock_ticks, _get_total_memory
- _get_uid_user_map
- _read_proc_stat, _read_proc_status_uid, _read_proc_cmdline
- get_all_processes (with snapshot logic)
- get_top_by_cpu, get_top_by_memory
- kill_process (success, PermissionError pkexec fallback, ProcessLookupError)
- renice_process (success, elevated, failure)
- get_process_count
- bytes_to_human
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, mock_open, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from services.system.processes import ProcessInfo, ProcessManager


class TestBytesToHuman(unittest.TestCase):

    def test_bytes(self):
        self.assertEqual(ProcessManager.bytes_to_human(500), "500.0 B")

    def test_kb(self):
        self.assertEqual(ProcessManager.bytes_to_human(1024), "1.0 KB")

    def test_mb(self):
        self.assertEqual(ProcessManager.bytes_to_human(1024 * 1024), "1.0 MB")

    def test_gb(self):
        self.assertEqual(ProcessManager.bytes_to_human(1024 ** 3), "1.0 GB")

    def test_tb(self):
        self.assertEqual(ProcessManager.bytes_to_human(1024 ** 4), "1.0 TB")

    def test_pb(self):
        self.assertEqual(ProcessManager.bytes_to_human(1024 ** 5), "1.0 PB")

    def test_zero(self):
        self.assertEqual(ProcessManager.bytes_to_human(0), "0.0 B")


class TestGetClockTicks(unittest.TestCase):

    @patch("os.sysconf", return_value=100)
    def test_returns_value(self, mock_sysconf):
        self.assertEqual(ProcessManager._get_clock_ticks(), 100)

    @patch("os.sysconf", side_effect=ValueError)
    def test_fallback(self, mock_sysconf):
        self.assertEqual(ProcessManager._get_clock_ticks(), 100)


class TestGetTotalMemory(unittest.TestCase):

    @patch("builtins.open", mock_open(read_data="MemTotal:       16384000 kB\nMemFree:       8000000 kB\n"))
    def test_reads_meminfo(self):
        result = ProcessManager._get_total_memory()
        self.assertEqual(result, 16384000 * 1024)

    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_fallback(self, mock_open_fn):
        result = ProcessManager._get_total_memory()
        self.assertEqual(result, 1)


class TestGetUidUserMap(unittest.TestCase):

    @patch("builtins.open", mock_open(read_data="root:x:0:0:root:/root:/bin/bash\nnobody:x:65534:65534:Nobody:/:/sbin/nologin\n"))
    def test_reads_passwd(self):
        m = ProcessManager._get_uid_user_map()
        self.assertEqual(m[0], "root")
        self.assertEqual(m[65534], "nobody")

    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_fallback(self, mock_open_fn):
        m = ProcessManager._get_uid_user_map()
        self.assertEqual(m, {})


class TestReadProcStat(unittest.TestCase):

    def _stat_content(self, pid=1, name="bash", state="S", utime=100, stime=50, nice=0, threads=1, rss=1000):
        # Format: pid (name) state ppid pgrp session tty tpgid flags minflt cminflt majflt cmajflt utime stime ...
        # Fields after ')': state(0) ppid(1) pgrp(2) session(3) tty(4) tpgid(5) flags(6) minflt(7) cminflt(8) majflt(9) cmajflt(10) utime(11) stime(12) cutime(13) cstime(14) priority(15) nice(16) threads(17) itrealvalue(18) starttime(19) vsize(20) rss(21)
        fields_after = f"S 1 1 1 0 0 0 100 0 0 0 {utime} {stime} 0 0 20 {nice} {threads} 0 1000 50000 {rss}"
        return f"{pid} ({name}) {fields_after}"

    @patch("builtins.open", mock_open(read_data="1 (bash) S 1 1 1 0 0 0 100 0 0 0 100 50 0 0 20 0 1 0 1000 50000 1000"))
    def test_reads_stat(self):
        result = ProcessManager._read_proc_stat(1)
        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "bash")
        self.assertEqual(result["state"], "S")
        self.assertEqual(result["utime"], 100)
        self.assertEqual(result["stime"], 50)

    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_file_not_found(self, mock_file):
        self.assertIsNone(ProcessManager._read_proc_stat(99999))

    @patch("builtins.open", side_effect=PermissionError)
    def test_permission_error(self, mock_file):
        self.assertIsNone(ProcessManager._read_proc_stat(1))

    @patch("builtins.open", mock_open(read_data="invalid content without parens"))
    def test_malformed(self):
        # No parentheses → ValueError in content.index("(")
        self.assertIsNone(ProcessManager._read_proc_stat(1))

    @patch("builtins.open", mock_open(read_data="1 (name) S"))
    def test_too_few_fields(self):
        result = ProcessManager._read_proc_stat(1)
        self.assertIsNone(result)

    @patch("builtins.open", mock_open(read_data="1 (name with spaces) S 1 1 1 0 0 0 100 0 0 0 100 50 0 0 20 0 1 0 1000 50000 1000"))
    def test_name_with_spaces(self):
        result = ProcessManager._read_proc_stat(1)
        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "name with spaces")


class TestReadProcStatusUid(unittest.TestCase):

    @patch("builtins.open", mock_open(read_data="Name:\tbash\nUid:\t1000\t1000\t1000\t1000\n"))
    def test_reads_uid(self):
        uid = ProcessManager._read_proc_status_uid(1)
        self.assertEqual(uid, 1000)

    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_not_found(self, mock_file):
        self.assertIsNone(ProcessManager._read_proc_status_uid(99999))

    @patch("builtins.open", mock_open(read_data="Name:\tbash\n"))
    def test_no_uid_line(self):
        uid = ProcessManager._read_proc_status_uid(1)
        self.assertIsNone(uid)


class TestReadProcCmdline(unittest.TestCase):

    @patch("builtins.open", mock_open(read_data=b"/usr/bin/bash\x00--login\x00"))
    def test_reads_cmdline(self):
        cmd = ProcessManager._read_proc_cmdline(1)
        self.assertIn("/usr/bin/bash", cmd)
        self.assertIn("--login", cmd)

    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_not_found(self, mock_file):
        cmd = ProcessManager._read_proc_cmdline(99999)
        self.assertEqual(cmd, "")

    @patch("builtins.open", mock_open(read_data=b""))
    def test_empty(self):
        cmd = ProcessManager._read_proc_cmdline(1)
        self.assertEqual(cmd, "")


class TestKillProcess(unittest.TestCase):

    @patch("os.kill")
    def test_success(self, mock_kill):
        ok, msg = ProcessManager.kill_process(1234, 15)
        self.assertTrue(ok)
        mock_kill.assert_called_with(1234, 15)

    @patch("subprocess.run")
    @patch("os.kill", side_effect=PermissionError)
    def test_pkexec_fallback(self, mock_kill, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        ok, msg = ProcessManager.kill_process(1234, 9)
        self.assertTrue(ok)
        self.assertIn("elevated", msg)

    @patch("subprocess.run")
    @patch("os.kill", side_effect=PermissionError)
    def test_pkexec_failure(self, mock_kill, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="denied")
        ok, msg = ProcessManager.kill_process(1234, 9)
        self.assertFalse(ok)

    @patch("os.kill", side_effect=PermissionError)
    @patch("subprocess.run", side_effect=FileNotFoundError)
    def test_no_pkexec(self, mock_run, mock_kill):
        ok, msg = ProcessManager.kill_process(1234)
        self.assertFalse(ok)
        self.assertIn("pkexec not found", msg)

    @patch("os.kill", side_effect=PermissionError)
    @patch("subprocess.run", side_effect=__import__("subprocess").TimeoutExpired("kill", 30))
    def test_pkexec_timeout(self, mock_run, mock_kill):
        ok, msg = ProcessManager.kill_process(1234)
        self.assertFalse(ok)
        self.assertIn("Timed out", msg)

    @patch("os.kill", side_effect=ProcessLookupError)
    def test_process_not_found(self, mock_kill):
        ok, msg = ProcessManager.kill_process(99999)
        self.assertFalse(ok)
        self.assertIn("not found", msg)

    def test_invalid_signal(self):
        ok, msg = ProcessManager.kill_process(1234, 999)
        self.assertFalse(ok)
        self.assertIn("Invalid signal", msg)

    def test_invalid_pid(self):
        ok, msg = ProcessManager.kill_process(-1)
        self.assertFalse(ok)
        self.assertIn("Invalid PID", msg)

    @patch("os.kill", side_effect=PermissionError)
    @patch("subprocess.run", side_effect=Exception("general"))
    def test_general_exception(self, mock_run, mock_kill):
        ok, msg = ProcessManager.kill_process(1234)
        self.assertFalse(ok)

    @patch("os.kill", side_effect=OSError("unexpected"))
    def test_os_error(self, mock_kill):
        ok, msg = ProcessManager.kill_process(1234)
        self.assertFalse(ok)


class TestReniceProcess(unittest.TestCase):

    @patch("subprocess.run")
    def test_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        ok, msg = ProcessManager.renice_process(1234, 10)
        self.assertTrue(ok)

    @patch("subprocess.run")
    def test_elevated(self, mock_run):
        mock_run.side_effect = [
            MagicMock(returncode=1),  # first renice fails
            MagicMock(returncode=0),  # pkexec succeeds
        ]
        ok, msg = ProcessManager.renice_process(1234, -5)
        self.assertTrue(ok)
        self.assertIn("elevated", msg)

    @patch("subprocess.run")
    def test_both_fail(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="denied")
        ok, msg = ProcessManager.renice_process(1234, -20)
        self.assertFalse(ok)

    @patch("subprocess.run", side_effect=__import__("subprocess").TimeoutExpired("renice", 10))
    def test_timeout(self, mock_run):
        ok, msg = ProcessManager.renice_process(1234, 0)
        self.assertFalse(ok)

    @patch("subprocess.run", side_effect=FileNotFoundError)
    def test_no_renice(self, mock_run):
        ok, msg = ProcessManager.renice_process(1234, 0)
        self.assertFalse(ok)
        self.assertIn("not found", msg)

    @patch("subprocess.run", side_effect=Exception("fail"))
    def test_exception(self, mock_run):
        ok, msg = ProcessManager.renice_process(1234, 0)
        self.assertFalse(ok)

    @patch("subprocess.run")
    def test_nice_clamping(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        # -30 should be clamped to -20
        ok, msg = ProcessManager.renice_process(1234, -30)
        self.assertTrue(ok)
        cmd = mock_run.call_args[0][0]
        self.assertIn("-20", cmd)


class TestGetProcessCount(unittest.TestCase):

    @patch("builtins.open")
    @patch("os.listdir", return_value=["1", "2", "3", "notpid"])
    def test_counts_states(self, mock_listdir, mock_open_fn):
        # Simulate /proc/PID/stat for 3 processes
        mock_open_fn.side_effect = [
            MagicMock(__enter__=lambda s: MagicMock(read=lambda: "1 (init) R rest..."), __exit__=MagicMock(return_value=False)),
            MagicMock(__enter__=lambda s: MagicMock(read=lambda: "2 (bash) S rest..."), __exit__=MagicMock(return_value=False)),
            MagicMock(__enter__=lambda s: MagicMock(read=lambda: "3 (zombie) Z rest..."), __exit__=MagicMock(return_value=False)),
        ]
        counts = ProcessManager.get_process_count()
        self.assertEqual(counts["total"], 3)
        self.assertEqual(counts["running"], 1)
        self.assertEqual(counts["sleeping"], 1)
        self.assertEqual(counts["zombie"], 1)

    @patch("os.listdir", side_effect=OSError)
    def test_os_error(self, mock_listdir):
        counts = ProcessManager.get_process_count()
        self.assertEqual(counts["total"], 0)

    @patch("builtins.open", side_effect=FileNotFoundError)
    @patch("os.listdir", return_value=["1"])
    def test_file_not_found(self, mock_listdir, mock_open_fn):
        counts = ProcessManager.get_process_count()
        self.assertEqual(counts["total"], 0)


class TestGetTopByMetric(unittest.TestCase):

    @patch.object(ProcessManager, "get_all_processes")
    def test_top_by_cpu(self, mock_get):
        mock_get.return_value = [
            ProcessInfo(pid=1, name="a", user="root", cpu_percent=10.0, memory_percent=1.0, memory_bytes=1024, state="R", command="a", nice=0),
            ProcessInfo(pid=2, name="b", user="root", cpu_percent=50.0, memory_percent=2.0, memory_bytes=2048, state="S", command="b", nice=0),
            ProcessInfo(pid=3, name="c", user="root", cpu_percent=30.0, memory_percent=3.0, memory_bytes=3072, state="S", command="c", nice=0),
        ]
        top = ProcessManager.get_top_by_cpu(2)
        self.assertEqual(len(top), 2)
        self.assertEqual(top[0].pid, 2)
        self.assertEqual(top[1].pid, 3)

    @patch.object(ProcessManager, "get_all_processes")
    def test_top_by_memory(self, mock_get):
        mock_get.return_value = [
            ProcessInfo(pid=1, name="a", user="root", cpu_percent=1.0, memory_percent=1.0, memory_bytes=1024, state="R", command="a", nice=0),
            ProcessInfo(pid=2, name="b", user="root", cpu_percent=2.0, memory_percent=2.0, memory_bytes=9999, state="S", command="b", nice=0),
        ]
        top = ProcessManager.get_top_by_memory(1)
        self.assertEqual(len(top), 1)
        self.assertEqual(top[0].pid, 2)


if __name__ == '__main__':
    unittest.main()

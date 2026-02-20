"""Tests for utils/monitor.py — system resource monitoring."""

import os
import subprocess
import sys
import unittest
from unittest.mock import patch, MagicMock, mock_open

sys.path.insert(0, os.path.join(os.path.dirname(
    __file__), '..', 'loofi-fedora-tweaks'))

from utils.monitor import SystemMonitor, MemoryInfo, CpuInfo, SystemHealth


class TestBytesToHuman(unittest.TestCase):
    """Tests for SystemMonitor.bytes_to_human()."""

    def test_bytes(self):
        self.assertEqual(SystemMonitor.bytes_to_human(512), "512.0 B")

    def test_kilobytes(self):
        self.assertEqual(SystemMonitor.bytes_to_human(1024), "1.0 KB")

    def test_megabytes(self):
        result = SystemMonitor.bytes_to_human(1024 * 1024)
        self.assertEqual(result, "1.0 MB")

    def test_gigabytes(self):
        result = SystemMonitor.bytes_to_human(1024 ** 3)
        self.assertEqual(result, "1.0 GB")

    def test_terabytes(self):
        result = SystemMonitor.bytes_to_human(1024 ** 4)
        self.assertEqual(result, "1.0 TB")

    def test_zero(self):
        self.assertEqual(SystemMonitor.bytes_to_human(0), "0.0 B")

    def test_fractional(self):
        result = SystemMonitor.bytes_to_human(1536)
        self.assertEqual(result, "1.5 KB")


class TestGetMemoryInfo(unittest.TestCase):
    """Tests for SystemMonitor.get_memory_info()."""

    MOCK_MEMINFO = (
        "MemTotal:       16384000 kB\n"
        "MemFree:         2048000 kB\n"
        "MemAvailable:    8192000 kB\n"
        "Buffers:          512000 kB\n"
        "Cached:          4096000 kB\n"
    )

    @patch("builtins.open", mock_open(read_data=MOCK_MEMINFO))
    def test_success(self):
        result = SystemMonitor.get_memory_info()
        self.assertIsNotNone(result)
        self.assertIsInstance(result, MemoryInfo)
        self.assertEqual(result.total_bytes, 16384000 * 1024)
        self.assertEqual(result.available_bytes, 8192000 * 1024)
        self.assertGreater(result.percent_used, 0)

    @patch("builtins.open", side_effect=OSError("no such file"))
    def test_file_read_failure(self, _mock_file):
        result = SystemMonitor.get_memory_info()
        self.assertIsNone(result)

    @patch("builtins.open", mock_open(read_data="garbage data\n"))
    def test_malformed_meminfo_returns_none(self):
        result = SystemMonitor.get_memory_info()
        self.assertIsNone(result)


class TestMemoryInfoDataclass(unittest.TestCase):
    """Tests for MemoryInfo properties."""

    def test_human_readable_properties(self):
        mem = MemoryInfo(
            total_bytes=1024 ** 3,
            available_bytes=512 * 1024 * 1024,
            used_bytes=512 * 1024 * 1024,
            percent_used=50.0,
        )
        self.assertIn("GB", mem.total_human)
        self.assertIn("MB", mem.available_human)
        self.assertIn("MB", mem.used_human)


class TestGetCpuInfo(unittest.TestCase):
    """Tests for SystemMonitor.get_cpu_info()."""

    @patch("utils.monitor.os.cpu_count", return_value=8)
    @patch("utils.monitor.os.getloadavg", create=True, return_value=(2.5, 1.8, 1.2))
    def test_success(self, _mock_load, _mock_cores):
        result = SystemMonitor.get_cpu_info()
        self.assertIsNotNone(result)
        self.assertIsInstance(result, CpuInfo)
        self.assertEqual(result.load_1min, 2.5)
        self.assertEqual(result.load_5min, 1.8)
        self.assertEqual(result.load_15min, 1.2)
        self.assertEqual(result.core_count, 8)

    @patch("utils.monitor.os.getloadavg", create=True, side_effect=OSError("unavailable"))
    def test_failure(self, _mock_load):
        result = SystemMonitor.get_cpu_info()
        self.assertIsNone(result)


class TestCpuInfoDataclass(unittest.TestCase):
    """Tests for CpuInfo properties."""

    def test_load_percent_normal(self):
        cpu = CpuInfo(load_1min=4.0, load_5min=3.0,
                      load_15min=2.0, core_count=8)
        self.assertEqual(cpu.load_percent, 50.0)

    def test_load_percent_zero_cores(self):
        cpu = CpuInfo(load_1min=1.0, load_5min=1.0,
                      load_15min=1.0, core_count=0)
        self.assertEqual(cpu.load_percent, 0.0)


class TestGetUptime(unittest.TestCase):
    """Tests for SystemMonitor.get_uptime()."""

    @patch("builtins.open", mock_open(read_data="7380.45 29520.00\n"))
    def test_hours_and_minutes(self):
        result = SystemMonitor.get_uptime()
        self.assertIn("hour", result)
        self.assertIn("minute", result)

    @patch("builtins.open", mock_open(read_data="90000.00 360000.00\n"))
    def test_days(self):
        result = SystemMonitor.get_uptime()
        self.assertIn("day", result)

    @patch("builtins.open", mock_open(read_data="30.00 120.00\n"))
    def test_minutes_only(self):
        result = SystemMonitor.get_uptime()
        self.assertNotIn("hour", result)
        self.assertIn("minute", result)

    @patch("builtins.open", side_effect=OSError("no such file"))
    def test_failure(self, _mock_file):
        result = SystemMonitor.get_uptime()
        self.assertEqual(result, "unknown")


class TestGetHostname(unittest.TestCase):
    """Tests for SystemMonitor.get_hostname()."""

    @patch("builtins.open", mock_open(read_data="my-fedora-host\n"))
    def test_from_file(self):
        result = SystemMonitor.get_hostname()
        self.assertEqual(result, "my-fedora-host")

    @patch("utils.monitor.subprocess.run")
    @patch("builtins.open", side_effect=OSError("no file"))
    def test_fallback_to_command(self, _mock_file, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="cmd-hostname\n")
        result = SystemMonitor.get_hostname()
        self.assertEqual(result, "cmd-hostname")

    @patch("utils.monitor.subprocess.run",
           side_effect=subprocess.SubprocessError("fail"))
    @patch("builtins.open", side_effect=OSError("no file"))
    def test_all_methods_fail(self, _mock_file, _mock_run):
        result = SystemMonitor.get_hostname()
        self.assertEqual(result, "unknown")


class TestSystemHealth(unittest.TestCase):
    """Tests for SystemHealth dataclass properties."""

    def test_memory_status_ok(self):
        mem = MemoryInfo(total_bytes=100, available_bytes=50,
                         used_bytes=50, percent_used=50.0)
        health = SystemHealth(memory=mem, cpu=None,
                              uptime="1 hour", hostname="test")
        self.assertEqual(health.memory_status, "ok")

    def test_memory_status_warning(self):
        mem = MemoryInfo(total_bytes=100, available_bytes=20,
                         used_bytes=80, percent_used=80.0)
        health = SystemHealth(memory=mem, cpu=None,
                              uptime="1 hour", hostname="test")
        self.assertEqual(health.memory_status, "warning")

    def test_memory_status_critical(self):
        mem = MemoryInfo(total_bytes=100, available_bytes=5,
                         used_bytes=95, percent_used=95.0)
        health = SystemHealth(memory=mem, cpu=None,
                              uptime="1 hour", hostname="test")
        self.assertEqual(health.memory_status, "critical")

    def test_memory_status_unknown(self):
        health = SystemHealth(memory=None, cpu=None,
                              uptime="1 hour", hostname="test")
        self.assertEqual(health.memory_status, "unknown")

    def test_cpu_status_ok(self):
        cpu = CpuInfo(load_1min=1.0, load_5min=0.5,
                      load_15min=0.3, core_count=8)
        health = SystemHealth(memory=None, cpu=cpu,
                              uptime="1 hour", hostname="test")
        self.assertEqual(health.cpu_status, "ok")

    def test_cpu_status_warning(self):
        cpu = CpuInfo(load_1min=6.0, load_5min=5.0,
                      load_15min=4.0, core_count=8)
        health = SystemHealth(memory=None, cpu=cpu,
                              uptime="1 hour", hostname="test")
        self.assertEqual(health.cpu_status, "warning")

    def test_cpu_status_critical(self):
        cpu = CpuInfo(load_1min=8.0, load_5min=7.0,
                      load_15min=6.0, core_count=8)
        health = SystemHealth(memory=None, cpu=cpu,
                              uptime="1 hour", hostname="test")
        self.assertEqual(health.cpu_status, "critical")

    def test_cpu_status_unknown(self):
        health = SystemHealth(memory=None, cpu=None,
                              uptime="1 hour", hostname="test")
        self.assertEqual(health.cpu_status, "unknown")


class TestGetSystemHealth(unittest.TestCase):
    """Tests for SystemMonitor.get_system_health()."""

    @patch.object(SystemMonitor, "get_hostname", return_value="testhost")
    @patch.object(SystemMonitor, "get_uptime", return_value="2 hours")
    @patch.object(SystemMonitor, "get_cpu_info", return_value=None)
    @patch.object(SystemMonitor, "get_memory_info", return_value=None)
    def test_aggregates_all(self, mock_mem, mock_cpu,
                            mock_up, mock_host):
        result = SystemMonitor.get_system_health()
        self.assertIsInstance(result, SystemHealth)
        self.assertEqual(result.hostname, "testhost")
        self.assertEqual(result.uptime, "2 hours")
        self.assertIsNone(result.memory)
        self.assertIsNone(result.cpu)
        mock_mem.assert_called_once()
        mock_cpu.assert_called_once()
        mock_up.assert_called_once()
        mock_host.assert_called_once()


if __name__ == "__main__":
    unittest.main()

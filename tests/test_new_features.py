import unittest
from unittest.mock import patch, MagicMock, mock_open
import sys
import os

# Add source path to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.disk import DiskManager, DiskUsage, LargeDirectory
from utils.monitor import SystemMonitor, MemoryInfo, CpuInfo, SystemHealth


class TestDiskManager(unittest.TestCase):
    """Tests for disk space monitoring."""

    def test_bytes_to_human_bytes(self):
        self.assertEqual(DiskManager.bytes_to_human(500), "500.0 B")

    def test_bytes_to_human_kb(self):
        self.assertEqual(DiskManager.bytes_to_human(1024), "1.0 KB")

    def test_bytes_to_human_gb(self):
        self.assertEqual(DiskManager.bytes_to_human(1073741824), "1.0 GB")

    def test_bytes_to_human_tb(self):
        self.assertEqual(DiskManager.bytes_to_human(1099511627776), "1.0 TB")

    @patch('shutil.disk_usage')
    def test_get_disk_usage_success(self, mock_usage):
        mock_usage.return_value = MagicMock(
            total=100 * 1024**3,  # 100 GB
            used=60 * 1024**3,    # 60 GB
            free=40 * 1024**3,    # 40 GB
        )
        result = DiskManager.get_disk_usage("/")
        self.assertIsNotNone(result)
        self.assertEqual(result.mount_point, "/")
        self.assertEqual(result.percent_used, 60.0)
        self.assertEqual(result.total_bytes, 100 * 1024**3)
        self.assertEqual(result.used_bytes, 60 * 1024**3)
        self.assertEqual(result.free_bytes, 40 * 1024**3)

    @patch('shutil.disk_usage')
    def test_get_disk_usage_error(self, mock_usage):
        mock_usage.side_effect = OSError("Permission denied")
        result = DiskManager.get_disk_usage("/nonexistent")
        self.assertIsNone(result)

    @patch('shutil.disk_usage')
    def test_check_disk_health_ok(self, mock_usage):
        mock_usage.return_value = MagicMock(
            total=100 * 1024**3,
            used=50 * 1024**3,
            free=50 * 1024**3,
        )
        level, msg = DiskManager.check_disk_health("/")
        self.assertEqual(level, "ok")
        self.assertIn("healthy", msg.lower())

    @patch('shutil.disk_usage')
    def test_check_disk_health_warning(self, mock_usage):
        mock_usage.return_value = MagicMock(
            total=100 * 1024**3,
            used=85 * 1024**3,
            free=15 * 1024**3,
        )
        level, msg = DiskManager.check_disk_health("/")
        self.assertEqual(level, "warning")
        self.assertIn("low", msg.lower())

    @patch('shutil.disk_usage')
    def test_check_disk_health_critical(self, mock_usage):
        mock_usage.return_value = MagicMock(
            total=100 * 1024**3,
            used=95 * 1024**3,
            free=5 * 1024**3,
        )
        level, msg = DiskManager.check_disk_health("/")
        self.assertEqual(level, "critical")
        self.assertIn("critical", msg.lower())

    def test_disk_usage_properties(self):
        usage = DiskUsage(
            mount_point="/",
            total_bytes=1073741824,
            used_bytes=536870912,
            free_bytes=536870912,
            percent_used=50.0,
        )
        self.assertEqual(usage.total_human, "1.0 GB")
        self.assertEqual(usage.used_human, "512.0 MB")
        self.assertEqual(usage.free_human, "512.0 MB")

    def test_large_directory_properties(self):
        d = LargeDirectory(path="/home/user/Downloads", size_bytes=2147483648)
        self.assertEqual(d.size_human, "2.0 GB")


class TestSystemMonitor(unittest.TestCase):
    """Tests for system resource monitoring."""

    def test_bytes_to_human(self):
        self.assertEqual(SystemMonitor.bytes_to_human(1024 * 1024), "1.0 MB")

    @patch('builtins.open', new_callable=mock_open, read_data=(
        "MemTotal:       16384000 kB\n"
        "MemFree:         2048000 kB\n"
        "MemAvailable:    8192000 kB\n"
        "Buffers:          512000 kB\n"
        "Cached:          4096000 kB\n"
    ))
    def test_get_memory_info(self, mock_file):
        result = SystemMonitor.get_memory_info()
        self.assertIsNotNone(result)
        self.assertEqual(result.total_bytes, 16384000 * 1024)
        self.assertEqual(result.available_bytes, 8192000 * 1024)
        self.assertEqual(result.used_bytes, (16384000 - 8192000) * 1024)
        self.assertEqual(result.percent_used, 50.0)

    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_get_memory_info_error(self, mock_file):
        result = SystemMonitor.get_memory_info()
        self.assertIsNone(result)

    @patch('os.getloadavg', return_value=(1.5, 1.2, 0.9))
    @patch('os.cpu_count', return_value=4)
    def test_get_cpu_info(self, mock_count, mock_load):
        result = SystemMonitor.get_cpu_info()
        self.assertIsNotNone(result)
        self.assertEqual(result.load_1min, 1.5)
        self.assertEqual(result.load_5min, 1.2)
        self.assertEqual(result.load_15min, 0.9)
        self.assertEqual(result.core_count, 4)
        self.assertEqual(result.load_percent, 37.5)

    @patch('builtins.open', new_callable=mock_open, read_data="3600.50 7200.00\n")
    def test_get_uptime(self, mock_file):
        result = SystemMonitor.get_uptime()
        self.assertIn("1 hour", result)

    @patch('builtins.open', side_effect=FileNotFoundError)
    @patch('subprocess.getoutput', return_value="testhost")
    def test_get_hostname_fallback(self, mock_output, mock_file):
        result = SystemMonitor.get_hostname()
        self.assertEqual(result, "testhost")

    def test_memory_info_properties(self):
        mem = MemoryInfo(
            total_bytes=16 * 1024**3,
            available_bytes=8 * 1024**3,
            used_bytes=8 * 1024**3,
            percent_used=50.0,
        )
        self.assertEqual(mem.total_human, "16.0 GB")
        self.assertEqual(mem.available_human, "8.0 GB")
        self.assertEqual(mem.used_human, "8.0 GB")

    def test_cpu_info_load_percent(self):
        cpu = CpuInfo(load_1min=2.0, load_5min=1.5, load_15min=1.0, core_count=4)
        self.assertEqual(cpu.load_percent, 50.0)

    def test_cpu_info_load_percent_zero_cores(self):
        cpu = CpuInfo(load_1min=2.0, load_5min=1.5, load_15min=1.0, core_count=0)
        self.assertEqual(cpu.load_percent, 0.0)

    def test_system_health_memory_status(self):
        mem = MemoryInfo(total_bytes=16 * 1024**3, available_bytes=8 * 1024**3,
                         used_bytes=8 * 1024**3, percent_used=50.0)
        health = SystemHealth(memory=mem, cpu=None, uptime="1 hour", hostname="test")
        self.assertEqual(health.memory_status, "ok")

    def test_system_health_memory_warning(self):
        mem = MemoryInfo(total_bytes=16 * 1024**3, available_bytes=3 * 1024**3,
                         used_bytes=13 * 1024**3, percent_used=81.0)
        health = SystemHealth(memory=mem, cpu=None, uptime="1 hour", hostname="test")
        self.assertEqual(health.memory_status, "warning")

    def test_system_health_memory_critical(self):
        mem = MemoryInfo(total_bytes=16 * 1024**3, available_bytes=1 * 1024**3,
                         used_bytes=15 * 1024**3, percent_used=93.75)
        health = SystemHealth(memory=mem, cpu=None, uptime="1 hour", hostname="test")
        self.assertEqual(health.memory_status, "critical")

    def test_system_health_cpu_status(self):
        cpu = CpuInfo(load_1min=1.0, load_5min=0.8, load_15min=0.5, core_count=4)
        health = SystemHealth(memory=None, cpu=cpu, uptime="1 hour", hostname="test")
        self.assertEqual(health.cpu_status, "ok")

    def test_system_health_none_status(self):
        health = SystemHealth(memory=None, cpu=None, uptime="1 hour", hostname="test")
        self.assertEqual(health.memory_status, "unknown")
        self.assertEqual(health.cpu_status, "unknown")


class TestCLICommands(unittest.TestCase):
    """Tests for new CLI commands."""

    def test_cli_health_command_exists(self):
        from cli.main import main as cli_main
        # Running with --help should show 'health' command
        with self.assertRaises(SystemExit) as ctx:
            cli_main(["--help"])
        self.assertEqual(ctx.exception.code, 0)

    def test_cli_disk_command_exists(self):
        from cli.main import main as cli_main
        # Running disk command should succeed
        result = cli_main(["disk"])
        self.assertEqual(result, 0)

    def test_cli_health_command_runs(self):
        from cli.main import main as cli_main
        result = cli_main(["health"])
        self.assertEqual(result, 0)

    def test_cli_version_is_9(self):
        from cli.main import main as cli_main
        with self.assertRaises(SystemExit):
            cli_main(["--version"])


if __name__ == '__main__':
    unittest.main()

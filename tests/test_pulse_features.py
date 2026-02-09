"""
Tests for v9.2 Pulse Update features.
Tests performance monitoring, process management, temperature, and network monitoring.
"""
import unittest
from unittest.mock import patch, mock_open, MagicMock
import os
import sys
from io import StringIO

# Add source to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from utils.performance import (
    PerformanceCollector, CpuSample, MemorySample, DiskIOSample, NetworkSample,
)
from utils.processes import ProcessManager, ProcessInfo
from utils.temperature import TemperatureManager, TemperatureSensor
from utils.network_monitor import NetworkMonitor, InterfaceStats, ConnectionInfo


# ---------------------------------------------------------------------------
# TestPerformanceCollector
# ---------------------------------------------------------------------------

class TestPerformanceCollector(unittest.TestCase):
    """Tests for the PerformanceCollector real-time metrics module."""

    def setUp(self):
        """Create a fresh collector instance for each test."""
        self.collector = PerformanceCollector()

    @patch('utils.performance.time.monotonic')
    @patch.object(PerformanceCollector, '_read_proc_stat')
    def test_get_cpu_usage_reads_proc_stat(self, mock_stat, mock_time):
        """Mock /proc/stat, call collect_cpu(), verify it returns CpuSample dataclass."""
        # First call establishes baseline -- returns 0 percent
        mock_time.return_value = 1000.0
        mock_stat.return_value = [
            [100, 20, 50, 800, 30, 0, 0, 0],   # cpu  (aggregate)
            [50,  10, 25, 400, 15, 0, 0, 0],    # cpu0
            [50,  10, 25, 400, 15, 0, 0, 0],    # cpu1
        ]
        sample = self.collector.collect_cpu()
        self.assertIsNotNone(sample)
        self.assertIsInstance(sample, CpuSample)
        self.assertEqual(sample.percent, 0.0)
        self.assertEqual(len(sample.per_core), 2)
        self.assertEqual(sample.timestamp, 1000.0)

        # Second call computes real deltas
        mock_time.return_value = 1001.0
        mock_stat.return_value = [
            [200, 30, 60, 850, 40, 0, 0, 0],    # cpu  (aggregate)
            [100, 15, 30, 425, 20, 0, 0, 0],    # cpu0
            [100, 15, 30, 425, 20, 0, 0, 0],    # cpu1
        ]
        sample2 = self.collector.collect_cpu()
        self.assertIsNotNone(sample2)
        self.assertIsInstance(sample2, CpuSample)
        # Expected: total_delta=180, idle_delta=60 => (1 - 60/180)*100 = 66.7
        self.assertEqual(sample2.percent, 66.7)
        self.assertEqual(sample2.per_core, [66.7, 66.7])

    @patch('utils.performance.time.monotonic', return_value=1000.0)
    @patch.object(PerformanceCollector, '_read_proc_meminfo')
    def test_get_memory_usage(self, mock_meminfo, mock_time):
        """Mock /proc/meminfo, verify MemorySample fields."""
        mock_meminfo.return_value = {
            "MemTotal":     16 * 1024**3,   # 16 GB (already in bytes)
            "MemAvailable":  8 * 1024**3,   #  8 GB
        }
        sample = self.collector.collect_memory()
        self.assertIsNotNone(sample)
        self.assertIsInstance(sample, MemorySample)
        self.assertEqual(sample.total_bytes, 16 * 1024**3)
        self.assertEqual(sample.used_bytes, 8 * 1024**3)
        self.assertEqual(sample.percent, 50.0)
        self.assertEqual(sample.timestamp, 1000.0)

    @patch('utils.performance.time.monotonic', return_value=1000.0)
    @patch.object(PerformanceCollector, '_read_proc_diskstats')
    def test_get_disk_io(self, mock_diskstats, mock_time):
        """Mock /proc/diskstats, verify DiskIOSample fields."""
        mock_diskstats.return_value = (2048000, 1024000)  # (read, write)
        sample = self.collector.collect_disk_io()
        self.assertIsNotNone(sample)
        self.assertIsInstance(sample, DiskIOSample)
        self.assertEqual(sample.read_bytes, 2048000)
        self.assertEqual(sample.write_bytes, 1024000)
        # First call is a baseline -- rates are zero
        self.assertEqual(sample.read_rate, 0.0)
        self.assertEqual(sample.write_rate, 0.0)

    @patch('utils.performance.time.monotonic', return_value=1000.0)
    @patch.object(PerformanceCollector, '_read_proc_net_dev')
    def test_get_network_io(self, mock_net_dev, mock_time):
        """Mock /proc/net/dev, verify NetworkSample fields."""
        mock_net_dev.return_value = (5000000, 2000000)  # (recv, sent)
        sample = self.collector.collect_network()
        self.assertIsNotNone(sample)
        self.assertIsInstance(sample, NetworkSample)
        self.assertEqual(sample.bytes_recv, 5000000)
        self.assertEqual(sample.bytes_sent, 2000000)
        self.assertEqual(sample.send_rate, 0.0)
        self.assertEqual(sample.recv_rate, 0.0)

    @patch.object(PerformanceCollector, '_read_proc_stat', return_value=[])
    def test_cpu_usage_handles_missing_file(self, mock_stat):
        """Mock FileNotFoundError (empty stat return), verify returns None."""
        sample = self.collector.collect_cpu()
        self.assertIsNone(sample)

    def test_bytes_to_human(self):
        """Test the bytes_to_human static method with various values."""
        self.assertEqual(PerformanceCollector.bytes_to_human(0), "0.0 B")
        self.assertEqual(PerformanceCollector.bytes_to_human(500), "500.0 B")
        self.assertEqual(PerformanceCollector.bytes_to_human(1024), "1.0 KB")
        self.assertEqual(PerformanceCollector.bytes_to_human(1048576), "1.0 MB")
        self.assertEqual(PerformanceCollector.bytes_to_human(1073741824), "1.0 GB")
        self.assertEqual(PerformanceCollector.bytes_to_human(1099511627776), "1.0 TB")


# ---------------------------------------------------------------------------
# TestProcessManager
# ---------------------------------------------------------------------------

class TestProcessManager(unittest.TestCase):
    """Tests for the ProcessManager process monitoring module."""

    def setUp(self):
        """Reset class-level snapshot state between tests."""
        ProcessManager._prev_snapshot = {}
        ProcessManager._prev_snapshot_time = 0.0

    @patch('utils.processes.time.monotonic', return_value=1000.0)
    @patch('os.listdir', return_value=["1", "42", "self", "cpuinfo"])
    @patch('os.sysconf', return_value=4096)
    @patch('os.cpu_count', return_value=4)
    @patch.object(ProcessManager, '_get_uid_user_map',
                  return_value={0: "root", 1000: "testuser"})
    @patch.object(ProcessManager, '_get_total_memory',
                  return_value=16 * 1024**3)
    @patch.object(ProcessManager, '_get_clock_ticks', return_value=100)
    @patch.object(ProcessManager, '_read_proc_cmdline')
    @patch.object(ProcessManager, '_read_proc_status_uid')
    @patch.object(ProcessManager, '_read_proc_stat')
    def test_get_all_processes(self, mock_stat, mock_uid, mock_cmdline,
                               mock_clk, mock_mem, mock_uidmap,
                               mock_cpucount, mock_sysconf,
                               mock_listdir, mock_time):
        """Mock /proc listdir + per-pid stat/status/cmdline, verify ProcessInfo list."""
        def stat_side_effect(pid):
            data = {
                1:  {"name": "systemd", "state": "S", "utime": 500,
                     "stime": 200, "nice": 0, "num_threads": 1, "rss": 2048},
                42: {"name": "bash", "state": "R", "utime": 100,
                     "stime": 50, "nice": 0, "num_threads": 1, "rss": 1024},
            }
            return data.get(pid)

        mock_stat.side_effect = stat_side_effect
        mock_uid.side_effect = lambda pid: 0 if pid == 1 else 1000
        mock_cmdline.side_effect = (
            lambda pid: "/usr/lib/systemd/systemd" if pid == 1
            else "/usr/bin/bash"
        )

        processes = ProcessManager.get_all_processes()
        self.assertEqual(len(processes), 2)

        p1 = next(p for p in processes if p.pid == 1)
        self.assertIsInstance(p1, ProcessInfo)
        self.assertEqual(p1.name, "systemd")
        self.assertEqual(p1.user, "root")
        self.assertEqual(p1.state, "S")
        self.assertEqual(p1.memory_bytes, 2048 * 4096)
        self.assertEqual(p1.command, "/usr/lib/systemd/systemd")

        p42 = next(p for p in processes if p.pid == 42)
        self.assertEqual(p42.name, "bash")
        self.assertEqual(p42.user, "testuser")
        self.assertEqual(p42.command, "/usr/bin/bash")

    @patch('os.kill')
    def test_kill_process_success(self, mock_kill):
        """Mock os.kill, verify success return."""
        success, msg = ProcessManager.kill_process(1234, 15)
        mock_kill.assert_called_once_with(1234, 15)
        self.assertTrue(success)
        self.assertIn("Signal 15", msg)
        self.assertIn("1234", msg)

    @patch('utils.processes.subprocess.run')
    @patch('os.kill', side_effect=PermissionError("Operation not permitted"))
    def test_kill_process_permission_error(self, mock_kill, mock_run):
        """Mock os.kill raising PermissionError, verify pkexec fallback."""
        mock_run.return_value = MagicMock(returncode=0)
        success, msg = ProcessManager.kill_process(1234, 9)
        self.assertTrue(success)
        self.assertIn("elevated", msg)
        mock_run.assert_called_once_with(
            ["pkexec", "kill", "-9", "1234"],
            capture_output=True, text=True, timeout=30,
        )

    @patch('utils.processes.subprocess.run')
    def test_renice_process(self, mock_run):
        """Mock subprocess.run for renice command."""
        mock_run.return_value = MagicMock(returncode=0)
        success, msg = ProcessManager.renice_process(5678, 10)
        self.assertTrue(success)
        self.assertIn("5678", msg)
        self.assertIn("10", msg)
        mock_run.assert_called_once_with(
            ["renice", "-n", "10", "-p", "5678"],
            capture_output=True, text=True, timeout=10,
        )

    @patch('builtins.open')
    @patch('os.listdir')
    def test_get_process_count(self, mock_listdir, mock_open_fn):
        """Mock /proc directory listing with various process states."""
        mock_listdir.return_value = [
            "1", "2", "3", "4", "5", "self", "cpuinfo",
        ]
        stat_data = {
            "/proc/1/stat": "1 (systemd) S 0 1 1 0 -1 0",
            "/proc/2/stat": "2 (kworker) R 0 0 0 0 -1 0",
            "/proc/3/stat": "3 (defunct) Z 1 3 3 0 -1 0",
            "/proc/4/stat": "4 (worker) S 0 0 0 0 -1 0",
            "/proc/5/stat": "5 (idle) I 0 0 0 0 -1 0",
        }

        def open_side_effect(path, *args, **kwargs):
            if path in stat_data:
                return StringIO(stat_data[path])
            raise FileNotFoundError(path)

        mock_open_fn.side_effect = open_side_effect

        counts = ProcessManager.get_process_count()
        self.assertEqual(counts["total"], 5)
        self.assertEqual(counts["running"], 1)   # R
        self.assertEqual(counts["sleeping"], 3)   # S, S, I
        self.assertEqual(counts["zombie"], 1)     # Z

    @patch.object(ProcessManager, 'get_all_processes')
    def test_get_top_by_cpu(self, mock_get_all):
        """Verify sorting by CPU usage works."""
        mock_get_all.return_value = [
            ProcessInfo(pid=1, name="low", user="root", cpu_percent=5.0,
                        memory_percent=1.0, memory_bytes=1024,
                        state="S", command="low", nice=0),
            ProcessInfo(pid=2, name="high", user="root", cpu_percent=80.0,
                        memory_percent=10.0, memory_bytes=10240,
                        state="R", command="high", nice=0),
            ProcessInfo(pid=3, name="mid", user="root", cpu_percent=30.0,
                        memory_percent=5.0, memory_bytes=5120,
                        state="S", command="mid", nice=0),
        ]
        result = ProcessManager.get_top_by_cpu(2)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].name, "high")
        self.assertEqual(result[0].cpu_percent, 80.0)
        self.assertEqual(result[1].name, "mid")
        self.assertEqual(result[1].cpu_percent, 30.0)

    def test_bytes_to_human(self):
        """Test conversion utility."""
        self.assertEqual(ProcessManager.bytes_to_human(0), "0.0 B")
        self.assertEqual(ProcessManager.bytes_to_human(512), "512.0 B")
        self.assertEqual(ProcessManager.bytes_to_human(1024), "1.0 KB")
        self.assertEqual(ProcessManager.bytes_to_human(1048576), "1.0 MB")
        self.assertEqual(ProcessManager.bytes_to_human(1073741824), "1.0 GB")


# ---------------------------------------------------------------------------
# TestTemperatureMonitor
# ---------------------------------------------------------------------------

class TestTemperatureMonitor(unittest.TestCase):
    """Tests for the TemperatureManager hardware temperature module."""

    @patch('services.hardware.temperature._read_millidegree')
    @patch('services.hardware.temperature._read_sysfs_value')
    @patch('services.hardware.temperature.glob.glob')
    def test_get_all_temperatures(self, mock_glob, mock_sysfs, mock_millideg):
        """Mock /sys/class/hwmon directory structure with temp files."""
        # glob is called twice: once for hwmon dirs, once for temp*_input
        mock_glob.side_effect = [
            ["/sys/class/hwmon/hwmon0"],
            ["/sys/class/hwmon/hwmon0/temp1_input",
             "/sys/class/hwmon/hwmon0/temp2_input"],
        ]
        # _read_sysfs_value calls: name, label_for_temp1, label_for_temp2
        mock_sysfs.side_effect = ["coretemp", "Core 0", "Core 1"]
        # _read_millidegree calls: current1, high1, crit1, current2, high2, crit2
        mock_millideg.side_effect = [55.0, 80.0, 100.0, 60.0, 80.0, 100.0]

        sensors = TemperatureManager.get_all_sensors()
        self.assertEqual(len(sensors), 2)

        self.assertEqual(sensors[0].name, "coretemp")
        self.assertEqual(sensors[0].label, "Core 0")
        self.assertEqual(sensors[0].current, 55.0)
        self.assertEqual(sensors[0].high, 80.0)
        self.assertEqual(sensors[0].critical, 100.0)
        self.assertEqual(sensors[0].sensor_type, "cpu")

        self.assertEqual(sensors[1].label, "Core 1")
        self.assertEqual(sensors[1].current, 60.0)

    @patch('services.hardware.temperature.glob.glob', return_value=[])
    def test_no_sensors_found(self, mock_glob):
        """Mock empty hwmon directory -- should return empty list."""
        sensors = TemperatureManager.get_all_sensors()
        self.assertEqual(sensors, [])

    @patch.object(TemperatureManager, 'get_all_sensors')
    def test_get_temperature_summary(self, mock_sensors):
        """Mock sensors and verify summary (hottest sensor)."""
        mock_sensors.return_value = [
            TemperatureSensor(name="coretemp", label="Core 0", current=55.0,
                              high=80.0, critical=100.0, sensor_type="cpu"),
            TemperatureSensor(name="amdgpu", label="GPU Edge", current=72.0,
                              high=90.0, critical=105.0, sensor_type="gpu"),
            TemperatureSensor(name="nvme", label="Composite", current=38.0,
                              high=70.0, critical=80.0, sensor_type="disk"),
        ]
        hottest = TemperatureManager.get_hottest()
        self.assertIsNotNone(hottest)
        self.assertEqual(hottest.label, "GPU Edge")
        self.assertEqual(hottest.current, 72.0)
        self.assertEqual(hottest.sensor_type, "gpu")

    @patch.object(TemperatureManager, 'get_all_sensors')
    def test_get_thermal_status_ok(self, mock_sensors):
        """Status 'ok' when all sensors are below thresholds."""
        mock_sensors.return_value = [
            TemperatureSensor(name="coretemp", label="Core 0", current=55.0,
                              high=80.0, critical=100.0, sensor_type="cpu"),
        ]
        level, msg = TemperatureManager.get_health_status()
        self.assertEqual(level, "ok")
        self.assertIn("normal", msg.lower())

    @patch.object(TemperatureManager, 'get_all_sensors')
    def test_get_thermal_status_warning(self, mock_sensors):
        """Status 'warning' when a sensor reaches its high threshold."""
        mock_sensors.return_value = [
            TemperatureSensor(name="coretemp", label="Core 0", current=85.0,
                              high=80.0, critical=100.0, sensor_type="cpu"),
        ]
        level, msg = TemperatureManager.get_health_status()
        self.assertEqual(level, "warning")
        self.assertIn("high", msg.lower())

    @patch.object(TemperatureManager, 'get_all_sensors')
    def test_get_thermal_status_critical(self, mock_sensors):
        """Status 'critical' when a sensor reaches its critical threshold."""
        mock_sensors.return_value = [
            TemperatureSensor(name="coretemp", label="Core 0", current=100.0,
                              high=80.0, critical=100.0, sensor_type="cpu"),
        ]
        level, msg = TemperatureManager.get_health_status()
        self.assertEqual(level, "critical")
        self.assertIn("critical", msg.lower())

    @patch('utils.temperature.glob.glob',
           side_effect=PermissionError("Permission denied"))
    def test_handles_permission_error(self, mock_glob):
        """Verify graceful handling when hwmon cannot be read."""
        sensors = TemperatureManager.get_all_sensors()
        self.assertEqual(sensors, [])


# ---------------------------------------------------------------------------
# TestNetworkMonitor
# ---------------------------------------------------------------------------

class TestNetworkMonitor(unittest.TestCase):
    """Tests for the NetworkMonitor network traffic module."""

    def setUp(self):
        """Reset class-level rate-tracking state between tests."""
        NetworkMonitor._previous_readings = {}

    @patch.object(NetworkMonitor, 'get_interface_ip',
                  return_value="192.168.1.100")
    @patch.object(NetworkMonitor, '_is_interface_up', return_value=True)
    @patch.object(NetworkMonitor, '_classify_interface',
                  return_value="ethernet")
    @patch.object(NetworkMonitor, '_read_proc_net_dev')
    def test_get_all_interfaces(self, mock_dev, mock_classify,
                                mock_up, mock_ip):
        """Mock /proc/net/dev and /sys/class/net entries."""
        mock_dev.return_value = {
            "enp3s0": {
                "bytes_recv": 1000000, "packets_recv": 1000,
                "bytes_sent": 500000,  "packets_sent": 500,
            },
            "lo": {
                "bytes_recv": 50000, "packets_recv": 100,
                "bytes_sent": 50000, "packets_sent": 100,
            },
        }

        interfaces = NetworkMonitor.get_all_interfaces()
        self.assertEqual(len(interfaces), 2)

        eth = next(i for i in interfaces if i.name == "enp3s0")
        self.assertIsInstance(eth, InterfaceStats)
        self.assertEqual(eth.bytes_recv, 1000000)
        self.assertEqual(eth.bytes_sent, 500000)
        self.assertEqual(eth.packets_recv, 1000)
        self.assertTrue(eth.is_up)
        self.assertEqual(eth.ip_address, "192.168.1.100")
        # First call is baseline -- rates are zero
        self.assertEqual(eth.send_rate, 0.0)
        self.assertEqual(eth.recv_rate, 0.0)

    def test_interface_type_detection(self):
        """Verify wifi/ethernet/loopback/vpn classification from names."""
        self.assertEqual(NetworkMonitor._classify_interface("lo"), "loopback")
        self.assertEqual(NetworkMonitor._classify_interface("wlp2s0"), "wifi")
        self.assertEqual(NetworkMonitor._classify_interface("wlan0"), "wifi")
        self.assertEqual(NetworkMonitor._classify_interface("enp3s0"), "ethernet")
        self.assertEqual(NetworkMonitor._classify_interface("eth0"), "ethernet")
        self.assertEqual(NetworkMonitor._classify_interface("tun0"), "vpn")
        self.assertEqual(NetworkMonitor._classify_interface("tap0"), "vpn")
        self.assertEqual(NetworkMonitor._classify_interface("wg0"), "vpn")

    @patch.object(NetworkMonitor, 'get_all_interfaces')
    def test_get_bandwidth_summary(self, mock_interfaces):
        """Verify aggregation across interfaces (loopback excluded)."""
        mock_interfaces.return_value = [
            InterfaceStats(
                name="lo", type="loopback", is_up=True,
                ip_address="127.0.0.1",
                bytes_sent=99999, bytes_recv=99999,
                packets_sent=999, packets_recv=999,
                send_rate=100.0, recv_rate=100.0,
            ),
            InterfaceStats(
                name="enp3s0", type="ethernet", is_up=True,
                ip_address="192.168.1.100",
                bytes_sent=5000, bytes_recv=10000,
                packets_sent=50, packets_recv=100,
                send_rate=500.0, recv_rate=1000.0,
            ),
            InterfaceStats(
                name="wlp2s0", type="wifi", is_up=True,
                ip_address="192.168.1.101",
                bytes_sent=3000, bytes_recv=7000,
                packets_sent=30, packets_recv=70,
                send_rate=300.0, recv_rate=700.0,
            ),
        ]
        summary = NetworkMonitor.get_bandwidth_summary()
        # Loopback is excluded; only enp3s0 + wlp2s0 counted
        self.assertEqual(summary["total_sent"], 8000)
        self.assertEqual(summary["total_recv"], 17000)
        self.assertEqual(summary["total_send_rate"], 800.0)
        self.assertEqual(summary["total_recv_rate"], 1700.0)

    def test_bytes_to_human(self):
        """Test the utility function with various values."""
        self.assertEqual(NetworkMonitor.bytes_to_human(0), "0.0 B")
        self.assertEqual(NetworkMonitor.bytes_to_human(512), "512.0 B")
        self.assertEqual(NetworkMonitor.bytes_to_human(1024), "1.0 KB")
        self.assertEqual(NetworkMonitor.bytes_to_human(1048576), "1.0 MB")
        self.assertEqual(NetworkMonitor.bytes_to_human(1073741824), "1.0 GB")

    @patch.object(NetworkMonitor, '_read_proc_net_dev', return_value={})
    def test_handles_missing_proc_net_dev(self, mock_dev):
        """Verify empty list returned when /proc/net/dev is unreadable."""
        interfaces = NetworkMonitor.get_all_interfaces()
        self.assertEqual(interfaces, [])


if __name__ == '__main__':
    unittest.main()

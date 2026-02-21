"""Tests for utils/performance.py — PerformanceCollector and helpers.

Covers /proc readers, collection methods, history accessors,
bytes_to_human, _is_partition, delta calculations, and error paths.
"""

import os
import sys
import unittest
from unittest.mock import mock_open, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.performance import (
    CpuSample,
    DiskIOSample,
    MemorySample,
    NetworkSample,
    PerformanceCollector,
    _is_partition,
)

# ── Static helpers ─────────────────────────────────────────────────


class TestBytesToHuman(unittest.TestCase):

    def test_bytes(self):
        self.assertEqual(PerformanceCollector.bytes_to_human(500), "500.0 B")

    def test_kilobytes(self):
        self.assertEqual(PerformanceCollector.bytes_to_human(2048), "2.0 KB")

    def test_megabytes(self):
        self.assertEqual(PerformanceCollector.bytes_to_human(5 * 1024 * 1024), "5.0 MB")

    def test_gigabytes(self):
        self.assertEqual(PerformanceCollector.bytes_to_human(3 * 1024**3), "3.0 GB")

    def test_terabytes(self):
        self.assertEqual(PerformanceCollector.bytes_to_human(2 * 1024**4), "2.0 TB")

    def test_petabytes(self):
        self.assertEqual(PerformanceCollector.bytes_to_human(1.5 * 1024**5), "1.5 PB")

    def test_zero(self):
        self.assertEqual(PerformanceCollector.bytes_to_human(0), "0.0 B")


class TestIsPartition(unittest.TestCase):

    def test_sda_whole_disk(self):
        self.assertFalse(_is_partition("sda"))

    def test_sda1_partition(self):
        self.assertTrue(_is_partition("sda1"))

    def test_nvme_whole_disk_treated_as_partition(self):
        # Note: _is_partition treats nvme0n1 as partition (ends in digit)
        # This is a known limitation of the function
        self.assertTrue(_is_partition("nvme0n1"))

    def test_nvme_partition(self):
        self.assertTrue(_is_partition("nvme0n1p1"))

    def test_vda_whole_disk(self):
        self.assertFalse(_is_partition("vda"))

    def test_vda1_partition(self):
        self.assertTrue(_is_partition("vda1"))

    def test_empty_string(self):
        self.assertFalse(_is_partition(""))


# ── /proc readers ──────────────────────────────────────────────────

PROC_STAT = """\
cpu  100 20 30 500 10 5 3 0
cpu0 50 10 15 250 5 3 1 0
cpu1 50 10 15 250 5 2 2 0
intr 12345
"""

PROC_MEMINFO = """\
MemTotal:       16384000 kB
MemFree:         2000000 kB
MemAvailable:    8000000 kB
Buffers:          500000 kB
Cached:          6000000 kB
"""

PROC_NET_DEV = """\
Inter-|   Receive                                                |  Transmit
 face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
    lo: 1000 10 0 0 0 0 0 0 2000 20 0 0 0 0 0 0
  eth0: 50000 100 0 0 0 0 0 0 30000 80 0 0 0 0 0 0
  wlan0: 20000 50 0 0 0 0 0 0 10000 30 0 0 0 0 0 0
"""

PROC_DISKSTATS = """\
   8       0 sda 100 0 2000 0 50 0 1000 0 0 0 0 0 0 500
   8       1 sda1 80 0 1500 0 40 0 800 0 0 0 0 0 0 400
   7       0 loop0 10 0 100 0 0 0 0 0 0 0 0 0 0 0
 259       0 nvme0n1 200 0 4000 0 100 0 2000 0 0 0 0 0 0 1000
 259       1 nvme0n1p1 150 0 3000 0 80 0 1500 0 0 0 0 0 0 800
 253       0 dm-0 50 0 500 0 20 0 200 0 0 0 0 0 0 100
"""


class TestReadProcStat(unittest.TestCase):

    @patch('builtins.open', mock_open(read_data=PROC_STAT))
    def test_reads_cpu_lines(self):
        result = PerformanceCollector._read_proc_stat()
        # Should have aggregate + 2 cores = 3 entries
        self.assertEqual(len(result), 3)
        # Aggregate line
        self.assertEqual(result[0], [100, 20, 30, 500, 10, 5, 3, 0])

    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_handles_missing_file(self, _):
        result = PerformanceCollector._read_proc_stat()
        self.assertEqual(result, [])


class TestCalcCpuPercent(unittest.TestCase):

    def test_normal_usage(self):
        prev = [100, 20, 30, 500, 10, 5, 3, 0]
        curr = [200, 40, 60, 600, 20, 10, 6, 0]
        pct = PerformanceCollector._calc_cpu_percent(prev, curr)
        # total_delta = (200+40+60+600+20+10+6+0) - (100+20+30+500+10+5+3+0) = 936 - 668 = 268
        # idle_delta = (600+20) - (500+10) = 110
        # usage = (1 - 110/268) * 100 = 58.96%
        self.assertAlmostEqual(pct, 58.9, places=0)
        self.assertTrue(0 <= pct <= 100)

    def test_no_delta(self):
        prev = [100, 20, 30, 500, 10, 5, 3, 0]
        pct = PerformanceCollector._calc_cpu_percent(prev, prev)
        self.assertEqual(pct, 0.0)

    def test_short_lists(self):
        pct = PerformanceCollector._calc_cpu_percent([1, 2], [3, 4])
        self.assertEqual(pct, 0.0)

    def test_minimal_four_fields(self):
        prev = [100, 20, 30, 500]
        curr = [200, 40, 60, 600]
        pct = PerformanceCollector._calc_cpu_percent(prev, curr)
        # idle_delta = 600 - 500 = 100 (no iowait)
        # total_delta = 900 - 650 = 250
        # usage = (1 - 100/250) * 100 = 60%
        self.assertAlmostEqual(pct, 60.0, places=1)


class TestReadProcMeminfo(unittest.TestCase):

    @patch('builtins.open', mock_open(read_data=PROC_MEMINFO))
    def test_reads_fields(self):
        result = PerformanceCollector._read_proc_meminfo()
        self.assertEqual(result["MemTotal"], 16384000 * 1024)
        self.assertEqual(result["MemAvailable"], 8000000 * 1024)
        self.assertIn("Buffers", result)

    @patch('builtins.open', side_effect=PermissionError)
    def test_handles_error(self, _):
        result = PerformanceCollector._read_proc_meminfo()
        self.assertEqual(result, {})


class TestReadProcNetDev(unittest.TestCase):

    @patch('builtins.open', mock_open(read_data=PROC_NET_DEV))
    def test_sums_non_loopback(self):
        recv, sent = PerformanceCollector._read_proc_net_dev()
        # eth0: recv=50000 sent=30000; wlan0: recv=20000 sent=10000
        self.assertEqual(recv, 70000)
        self.assertEqual(sent, 40000)

    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_handles_missing(self, _):
        recv, sent = PerformanceCollector._read_proc_net_dev()
        self.assertEqual(recv, 0)
        self.assertEqual(sent, 0)


class TestReadProcDiskstats(unittest.TestCase):

    @patch('builtins.open', mock_open(read_data=PROC_DISKSTATS))
    def test_sums_whole_disks_only(self):
        read_b, write_b = PerformanceCollector._read_proc_diskstats()
        # Only sda is counted (doesn't end in digit, not loop/ram/dm-)
        # nvme0n1 ends in digit → treated as partition by _is_partition
        # Skips: sda1, loop0, dm-0, nvme0n1, nvme0n1p1
        expected_read = 2000 * 512
        expected_write = 1000 * 512
        self.assertEqual(read_b, expected_read)
        self.assertEqual(write_b, expected_write)

    @patch('builtins.open', side_effect=OSError)
    def test_handles_error(self, _):
        read_b, write_b = PerformanceCollector._read_proc_diskstats()
        self.assertEqual(read_b, 0)
        self.assertEqual(write_b, 0)


# ── Collection methods ─────────────────────────────────────────────

class TestCollectCpu(unittest.TestCase):

    @patch.object(PerformanceCollector, '_read_proc_stat')
    def test_first_call_baseline(self, mock_read):
        mock_read.return_value = [
            [100, 20, 30, 500, 10, 5, 3, 0],
            [50, 10, 15, 250, 5, 3, 1, 0],
        ]
        pc = PerformanceCollector()
        sample = pc.collect_cpu()
        self.assertIsInstance(sample, CpuSample)
        self.assertEqual(sample.percent, 0.0)
        self.assertEqual(len(sample.per_core), 1)  # 2 entries - 1 aggregate = 1 core

    @patch.object(PerformanceCollector, '_read_proc_stat')
    def test_second_call_with_delta(self, mock_read):
        pc = PerformanceCollector()
        # First call: baseline
        mock_read.return_value = [
            [100, 20, 30, 500, 10, 5, 3, 0],
            [50, 10, 15, 250, 5, 3, 1, 0],
        ]
        pc.collect_cpu()

        # Second call: changed values
        mock_read.return_value = [
            [200, 40, 60, 600, 20, 10, 6, 0],
            [100, 20, 30, 300, 10, 5, 3, 0],
        ]
        sample = pc.collect_cpu()
        self.assertIsInstance(sample, CpuSample)
        self.assertTrue(0 < sample.percent <= 100)
        self.assertEqual(len(pc.get_cpu_history()), 2)

    @patch.object(PerformanceCollector, '_read_proc_stat', return_value=[])
    def test_empty_proc_stat(self, mock_read):
        pc = PerformanceCollector()
        self.assertIsNone(pc.collect_cpu())

    @patch.object(PerformanceCollector, '_read_proc_stat', side_effect=OSError("fail"))
    def test_exception_returns_none(self, mock_read):
        pc = PerformanceCollector()
        self.assertIsNone(pc.collect_cpu())


class TestCollectMemory(unittest.TestCase):

    @patch.object(PerformanceCollector, '_read_proc_meminfo')
    def test_normal_collection(self, mock_read):
        mock_read.return_value = {
            "MemTotal": 16 * 1024**3,
            "MemAvailable": 8 * 1024**3,
        }
        pc = PerformanceCollector()
        sample = pc.collect_memory()
        self.assertIsInstance(sample, MemorySample)
        self.assertAlmostEqual(sample.percent, 50.0, places=1)
        self.assertEqual(sample.total_bytes, 16 * 1024**3)
        self.assertEqual(sample.used_bytes, 8 * 1024**3)

    @patch.object(PerformanceCollector, '_read_proc_meminfo', return_value={})
    def test_missing_total_returns_none(self, mock_read):
        pc = PerformanceCollector()
        self.assertIsNone(pc.collect_memory())

    @patch.object(PerformanceCollector, '_read_proc_meminfo', return_value={"MemTotal": 0})
    def test_zero_total_returns_none(self, mock_read):
        pc = PerformanceCollector()
        self.assertIsNone(pc.collect_memory())

    @patch.object(PerformanceCollector, '_read_proc_meminfo')
    def test_history_appended(self, mock_read):
        mock_read.return_value = {
            "MemTotal": 8 * 1024**3,
            "MemAvailable": 4 * 1024**3,
        }
        pc = PerformanceCollector()
        pc.collect_memory()
        pc.collect_memory()
        self.assertEqual(len(pc.get_memory_history()), 2)


class TestCollectNetwork(unittest.TestCase):

    @patch.object(PerformanceCollector, '_read_proc_net_dev')
    def test_first_call_baseline(self, mock_read):
        mock_read.return_value = (50000, 30000)
        pc = PerformanceCollector()
        sample = pc.collect_network()
        self.assertIsInstance(sample, NetworkSample)
        self.assertEqual(sample.send_rate, 0.0)
        self.assertEqual(sample.recv_rate, 0.0)
        self.assertEqual(sample.bytes_recv, 50000)
        self.assertEqual(sample.bytes_sent, 30000)

    @patch('time.monotonic')
    @patch.object(PerformanceCollector, '_read_proc_net_dev')
    def test_second_call_with_rates(self, mock_read, mock_time):
        pc = PerformanceCollector()

        # First call
        mock_time.return_value = 100.0
        mock_read.return_value = (50000, 30000)
        pc.collect_network()

        # Second call, 1 second later with +1000 bytes each
        mock_time.return_value = 101.0
        mock_read.return_value = (51000, 31000)
        sample = pc.collect_network()

        self.assertIsInstance(sample, NetworkSample)
        self.assertAlmostEqual(sample.recv_rate, 1000.0, delta=50)
        self.assertAlmostEqual(sample.send_rate, 1000.0, delta=50)
        self.assertEqual(len(pc.get_network_history()), 2)

    @patch.object(PerformanceCollector, '_read_proc_net_dev', side_effect=ValueError)
    def test_exception_returns_none(self, mock_read):
        pc = PerformanceCollector()
        self.assertIsNone(pc.collect_network())


class TestCollectDiskIO(unittest.TestCase):

    @patch.object(PerformanceCollector, '_read_proc_diskstats')
    def test_first_call_baseline(self, mock_read):
        mock_read.return_value = (1024000, 512000)
        pc = PerformanceCollector()
        sample = pc.collect_disk_io()
        self.assertIsInstance(sample, DiskIOSample)
        self.assertEqual(sample.read_rate, 0.0)
        self.assertEqual(sample.write_rate, 0.0)

    @patch('time.monotonic')
    @patch.object(PerformanceCollector, '_read_proc_diskstats')
    def test_second_call_with_rates(self, mock_read, mock_time):
        pc = PerformanceCollector()

        mock_time.return_value = 200.0
        mock_read.return_value = (1000000, 500000)
        pc.collect_disk_io()

        mock_time.return_value = 202.0  # 2 seconds later
        mock_read.return_value = (1200000, 600000)
        sample = pc.collect_disk_io()

        self.assertIsInstance(sample, DiskIOSample)
        # read_rate = (1200000 - 1000000) / 2 = 100000 bytes/sec
        self.assertAlmostEqual(sample.read_rate, 100000.0, delta=100)
        self.assertAlmostEqual(sample.write_rate, 50000.0, delta=100)

    @patch.object(PerformanceCollector, '_read_proc_diskstats', side_effect=ValueError)
    def test_exception_returns_none(self, mock_read):
        pc = PerformanceCollector()
        self.assertIsNone(pc.collect_disk_io())


class TestCollectAll(unittest.TestCase):

    @patch.object(PerformanceCollector, 'collect_disk_io', return_value=None)
    @patch.object(PerformanceCollector, 'collect_network', return_value=None)
    @patch.object(PerformanceCollector, 'collect_memory', return_value=None)
    @patch.object(PerformanceCollector, 'collect_cpu', return_value=None)
    def test_collect_all_returns_dict(self, *mocks):
        pc = PerformanceCollector()
        result = pc.collect_all()
        self.assertIn("cpu", result)
        self.assertIn("memory", result)
        self.assertIn("network", result)
        self.assertIn("disk_io", result)


# ── History accessors ──────────────────────────────────────────────

class TestHistoryAccessors(unittest.TestCase):

    def test_empty_histories(self):
        pc = PerformanceCollector()
        self.assertEqual(pc.get_cpu_history(), [])
        self.assertEqual(pc.get_memory_history(), [])
        self.assertEqual(pc.get_network_history(), [])
        self.assertEqual(pc.get_disk_io_history(), [])

    def test_ring_buffer_max_samples(self):
        pc = PerformanceCollector()
        for i in range(70):
            pc._cpu_history.append(CpuSample(timestamp=float(i), percent=float(i), per_core=[]))
        self.assertEqual(len(pc.get_cpu_history()), PerformanceCollector.MAX_SAMPLES)


if __name__ == '__main__':
    unittest.main()

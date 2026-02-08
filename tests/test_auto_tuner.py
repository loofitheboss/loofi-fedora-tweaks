"""Tests for performance auto-tuner."""
import unittest
import sys
import os
import json
from unittest.mock import patch, MagicMock, mock_open, call

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from utils.auto_tuner import AutoTuner, WorkloadProfile, TuningRecommendation, TuningHistoryEntry


class TestWorkloadProfile(unittest.TestCase):
    """Tests for WorkloadProfile dataclass."""

    def test_create_workload_profile(self):
        """Test creating a WorkloadProfile with all fields."""
        wp = WorkloadProfile(
            name="idle",
            cpu_percent=5.0,
            memory_percent=30.0,
            io_wait=0.5,
            description="System is idle.",
        )
        self.assertEqual(wp.name, "idle")
        self.assertEqual(wp.cpu_percent, 5.0)
        self.assertEqual(wp.memory_percent, 30.0)
        self.assertEqual(wp.io_wait, 0.5)

    def test_default_description(self):
        """Test description field holds provided value."""
        wp = WorkloadProfile(
            name="gaming",
            cpu_percent=75.0,
            memory_percent=50.0,
            io_wait=2.0,
            description="Gaming workload detected.",
        )
        self.assertEqual(wp.description, "Gaming workload detected.")

    def test_workload_profile_fields(self):
        """Test all fields are accessible and correctly typed."""
        wp = WorkloadProfile(
            name="compilation",
            cpu_percent=90.0,
            memory_percent=80.0,
            io_wait=5.0,
            description="Compiling.",
        )
        self.assertIsInstance(wp.name, str)
        self.assertIsInstance(wp.cpu_percent, float)
        self.assertIsInstance(wp.memory_percent, float)
        self.assertIsInstance(wp.io_wait, float)
        self.assertIsInstance(wp.description, str)


class TestTuningRecommendation(unittest.TestCase):
    """Tests for TuningRecommendation dataclass."""

    def test_create_recommendation(self):
        """Test creating a TuningRecommendation."""
        rec = TuningRecommendation(
            governor="performance",
            swappiness=10,
            io_scheduler="none",
            thp="never",
            reason="Gaming.",
            workload="gaming",
        )
        self.assertEqual(rec.governor, "performance")
        self.assertEqual(rec.swappiness, 10)
        self.assertEqual(rec.io_scheduler, "none")
        self.assertEqual(rec.thp, "never")

    def test_recommendation_fields(self):
        """Test all fields are present and typed correctly."""
        rec = TuningRecommendation(
            governor="powersave",
            swappiness=60,
            io_scheduler="mq-deadline",
            thp="always",
            reason="Idle.",
            workload="idle",
        )
        self.assertIsInstance(rec.governor, str)
        self.assertIsInstance(rec.swappiness, int)
        self.assertIsInstance(rec.io_scheduler, str)
        self.assertIsInstance(rec.thp, str)
        self.assertIsInstance(rec.reason, str)
        self.assertIsInstance(rec.workload, str)

    def test_recommendation_with_defaults(self):
        """Test recommendation with edge-case empty strings."""
        rec = TuningRecommendation(
            governor="",
            swappiness=0,
            io_scheduler="",
            thp="",
            reason="",
            workload="",
        )
        self.assertEqual(rec.governor, "")
        self.assertEqual(rec.swappiness, 0)
        self.assertEqual(rec.workload, "")


class TestDetectWorkload(unittest.TestCase):
    """Tests for AutoTuner.detect_workload."""

    @patch('utils.auto_tuner.AutoTuner._read_io_wait', return_value=1.0)
    @patch('utils.auto_tuner.AutoTuner._read_memory_percent', return_value=20.0)
    @patch('utils.auto_tuner.AutoTuner._read_cpu_percent', return_value=3.0)
    def test_detect_idle_workload(self, mock_cpu, mock_mem, mock_io):
        """Test workload classified as idle for low CPU."""
        profile = AutoTuner.detect_workload()
        self.assertEqual(profile.name, "idle")
        self.assertLessEqual(profile.cpu_percent, 10.0)

    @patch('utils.auto_tuner.AutoTuner._read_io_wait', return_value=2.0)
    @patch('utils.auto_tuner.AutoTuner._read_memory_percent', return_value=70.0)
    @patch('utils.auto_tuner.AutoTuner._read_cpu_percent', return_value=85.0)
    def test_detect_heavy_workload(self, mock_cpu, mock_mem, mock_io):
        """Test workload classified as heavy for CPU > 80%."""
        profile = AutoTuner.detect_workload()
        self.assertEqual(profile.name, "heavy")
        self.assertGreater(profile.cpu_percent, 80.0)

    @patch('utils.auto_tuner.AutoTuner._read_io_wait', return_value=0.0)
    @patch('utils.auto_tuner.AutoTuner._read_memory_percent', return_value=0.0)
    @patch('utils.auto_tuner.AutoTuner._read_cpu_percent', return_value=0.0)
    def test_detect_with_missing_proc(self, mock_cpu, mock_mem, mock_io):
        """Test detection gracefully handles zeroed-out metrics (simulating missing /proc)."""
        mock_cpu.return_value = 0.0
        profile = AutoTuner.detect_workload()
        self.assertIsInstance(profile, WorkloadProfile)
        self.assertEqual(profile.name, "idle")

    @patch('utils.auto_tuner.AutoTuner._read_io_wait', return_value=0.5)
    @patch('utils.auto_tuner.AutoTuner._read_memory_percent', return_value=40.0)
    @patch('utils.auto_tuner.AutoTuner._read_cpu_percent', return_value=15.0)
    def test_detect_returns_workload_profile(self, mock_cpu, mock_mem, mock_io):
        """Test detect_workload always returns a WorkloadProfile instance."""
        profile = AutoTuner.detect_workload()
        self.assertIsInstance(profile, WorkloadProfile)

    @patch('utils.auto_tuner.AutoTuner._read_io_wait', return_value=0.0)
    @patch('utils.auto_tuner.AutoTuner._read_memory_percent', return_value=0.0)
    @patch('utils.auto_tuner.AutoTuner._read_cpu_percent', return_value=0.0)
    def test_detect_with_empty_stat(self, mock_cpu, mock_mem, mock_io):
        """Test detect returns idle profile when all metrics are zero."""
        profile = AutoTuner.detect_workload()
        self.assertEqual(profile.name, "idle")
        self.assertEqual(profile.cpu_percent, 0.0)
        self.assertEqual(profile.memory_percent, 0.0)

    @patch('utils.auto_tuner.AutoTuner._read_io_wait', return_value=3.0)
    @patch('utils.auto_tuner.AutoTuner._read_memory_percent', return_value=75.0)
    @patch('utils.auto_tuner.AutoTuner._read_cpu_percent', return_value=65.0)
    def test_detect_compilation_workload(self, mock_cpu, mock_mem, mock_io):
        """Test workload classified as compilation (CPU>60 AND memory>60)."""
        profile = AutoTuner.detect_workload()
        self.assertEqual(profile.name, "compilation")

    @patch('utils.auto_tuner.AutoTuner._read_io_wait', return_value=1.0)
    @patch('utils.auto_tuner.AutoTuner._read_memory_percent', return_value=45.0)
    @patch('utils.auto_tuner.AutoTuner._read_cpu_percent', return_value=65.0)
    def test_detect_gaming_workload(self, mock_cpu, mock_mem, mock_io):
        """Test workload classified as gaming (CPU>60, memory<=60)."""
        profile = AutoTuner.detect_workload()
        self.assertEqual(profile.name, "gaming")

    @patch('utils.auto_tuner.AutoTuner._read_io_wait', return_value=1.0)
    @patch('utils.auto_tuner.AutoTuner._read_memory_percent', return_value=40.0)
    @patch('utils.auto_tuner.AutoTuner._read_cpu_percent', return_value=40.0)
    def test_detect_server_workload(self, mock_cpu, mock_mem, mock_io):
        """Test workload classified as server (CPU 30-60)."""
        profile = AutoTuner.detect_workload()
        self.assertEqual(profile.name, "server")

    @patch('utils.auto_tuner.AutoTuner._read_io_wait', return_value=0.5)
    @patch('utils.auto_tuner.AutoTuner._read_memory_percent', return_value=30.0)
    @patch('utils.auto_tuner.AutoTuner._read_cpu_percent', return_value=20.0)
    def test_detect_light_workload(self, mock_cpu, mock_mem, mock_io):
        """Test workload classified as light (CPU 10-30)."""
        profile = AutoTuner.detect_workload()
        self.assertEqual(profile.name, "light")


class TestGetCurrentSettings(unittest.TestCase):
    """Tests for AutoTuner.get_current_settings."""

    @patch('utils.auto_tuner.AutoTuner._read_io_scheduler', return_value="mq-deadline")
    @patch('utils.auto_tuner.os.path.exists', return_value=True)
    @patch('builtins.open', mock_open())
    def test_get_all_settings(self, mock_exists, mock_io_sched):
        """Test reading all settings with all files present."""
        gov_data = "performance\n"
        swap_data = "60\n"
        thp_data = "always [madvise] never\n"

        def open_side_effect(path, *args, **kwargs):
            if "scaling_governor" in str(path):
                return mock_open(read_data=gov_data)()
            elif "swappiness" in str(path):
                return mock_open(read_data=swap_data)()
            elif "transparent_hugepage" in str(path):
                return mock_open(read_data=thp_data)()
            return mock_open(read_data="")()

        with patch('builtins.open', side_effect=open_side_effect):
            settings = AutoTuner.get_current_settings()

        self.assertEqual(settings["governor"], "performance")
        self.assertEqual(settings["swappiness"], 60)
        self.assertEqual(settings["io_scheduler"], "mq-deadline")
        self.assertEqual(settings["thp"], "madvise")

    @patch('utils.auto_tuner.AutoTuner._read_io_scheduler', return_value="unknown")
    @patch('utils.auto_tuner.os.path.exists', return_value=False)
    def test_governor_missing(self, mock_exists, mock_io_sched):
        """Test governor reads as 'unknown' when file doesn't exist."""
        settings = AutoTuner.get_current_settings()
        self.assertEqual(settings["governor"], "unknown")

    @patch('utils.auto_tuner.AutoTuner._read_io_scheduler', return_value="unknown")
    @patch('utils.auto_tuner.os.path.exists', return_value=True)
    def test_swappiness_read(self, mock_exists, mock_io_sched):
        """Test swappiness is parsed as int."""
        with patch('builtins.open', mock_open(read_data="45\n")):
            settings = AutoTuner.get_current_settings()
        self.assertEqual(settings["swappiness"], 45)

    @patch('utils.auto_tuner.AutoTuner._read_io_scheduler', return_value="bfq")
    @patch('utils.auto_tuner.os.path.exists', return_value=False)
    def test_scheduler_read(self, mock_exists, mock_io_sched):
        """Test I/O scheduler comes from _read_io_scheduler helper."""
        settings = AutoTuner.get_current_settings()
        self.assertEqual(settings["io_scheduler"], "bfq")

    @patch('utils.auto_tuner.AutoTuner._read_io_scheduler', return_value="unknown")
    @patch('utils.auto_tuner.os.path.exists', return_value=False)
    def test_all_files_missing(self, mock_exists, mock_io_sched):
        """Test defaults when no sysfs files exist."""
        settings = AutoTuner.get_current_settings()
        self.assertEqual(settings["governor"], "unknown")
        self.assertEqual(settings["swappiness"], -1)
        self.assertEqual(settings["io_scheduler"], "unknown")
        self.assertEqual(settings["thp"], "unknown")


class TestRecommend(unittest.TestCase):
    """Tests for AutoTuner.recommend."""

    def test_recommend_for_idle(self):
        """Test recommend returns powersave governor for idle workload."""
        wp = WorkloadProfile("idle", 5.0, 20.0, 0.5, "Idle.")
        rec = AutoTuner.recommend(wp)
        self.assertEqual(rec.governor, "powersave")
        self.assertEqual(rec.swappiness, 60)

    def test_recommend_for_gaming(self):
        """Test recommend returns performance governor for gaming workload."""
        wp = WorkloadProfile("gaming", 70.0, 50.0, 1.0, "Gaming.")
        rec = AutoTuner.recommend(wp)
        self.assertEqual(rec.governor, "performance")
        self.assertEqual(rec.thp, "never")

    def test_recommend_for_compilation(self):
        """Test recommend returns performance governor for compilation."""
        wp = WorkloadProfile("compilation", 85.0, 75.0, 3.0, "Compiling.")
        rec = AutoTuner.recommend(wp)
        self.assertEqual(rec.governor, "performance")
        self.assertEqual(rec.swappiness, 10)
        self.assertEqual(rec.io_scheduler, "none")
        self.assertEqual(rec.thp, "madvise")

    @patch('utils.auto_tuner.AutoTuner.detect_workload')
    def test_recommend_auto_detect(self, mock_detect):
        """Test recommend calls detect_workload when workload is None."""
        mock_detect.return_value = WorkloadProfile("idle", 3.0, 15.0, 0.2, "Idle.")
        rec = AutoTuner.recommend(None)
        mock_detect.assert_called_once()
        self.assertEqual(rec.workload, "idle")

    def test_recommend_returns_tuning_recommendation(self):
        """Test recommend always returns a TuningRecommendation instance."""
        wp = WorkloadProfile("server", 45.0, 40.0, 2.0, "Server.")
        rec = AutoTuner.recommend(wp)
        self.assertIsInstance(rec, TuningRecommendation)
        self.assertEqual(rec.workload, "server")

    def test_recommend_unknown_workload_falls_back_to_idle(self):
        """Test recommend falls back to idle tunables for unknown workload."""
        wp = WorkloadProfile("nonexistent_workload", 0.0, 0.0, 0.0, "???")
        rec = AutoTuner.recommend(wp)
        # Falls back to idle map
        self.assertEqual(rec.governor, "powersave")


class TestApplyMethods(unittest.TestCase):
    """Tests for AutoTuner apply_* methods."""

    def test_apply_recommendation_returns_tuple(self):
        """Test apply_recommendation returns (str, list, str) 3-tuple."""
        rec = TuningRecommendation("performance", 10, "none", "never", "Gaming.", "gaming")
        result = AutoTuner.apply_recommendation(rec)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)
        self.assertIsInstance(result[0], str)
        self.assertIsInstance(result[1], list)
        self.assertIsInstance(result[2], str)

    def test_apply_swappiness_returns_tuple(self):
        """Test apply_swappiness returns (str, list, str) 3-tuple."""
        result = AutoTuner.apply_swappiness(30)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)
        self.assertIsInstance(result[0], str)
        self.assertIsInstance(result[1], list)
        self.assertIsInstance(result[2], str)

    def test_apply_recommendation_uses_pkexec(self):
        """Test apply_recommendation command starts with pkexec."""
        rec = TuningRecommendation("performance", 10, "none", "never", "Gaming.", "gaming")
        cmd, args, desc = AutoTuner.apply_recommendation(rec)
        self.assertEqual(cmd, "pkexec")
        self.assertIn("performance", " ".join(args))

    def test_apply_io_scheduler(self):
        """Test apply_io_scheduler returns proper tuple structure."""
        result = AutoTuner.apply_io_scheduler("mq-deadline", "sda")
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)
        cmd, args, desc = result
        self.assertEqual(cmd, "pkexec")
        self.assertIn("mq-deadline", " ".join(args))
        self.assertIn("sda", desc)

    def test_apply_thp(self):
        """Test apply_thp returns proper tuple structure."""
        result = AutoTuner.apply_thp("madvise")
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)
        cmd, args, desc = result
        self.assertEqual(cmd, "pkexec")
        self.assertIn("madvise", " ".join(args))

    def test_apply_thp_invalid_mode_defaults_madvise(self):
        """Test apply_thp defaults to madvise for invalid mode."""
        cmd, args, desc = AutoTuner.apply_thp("bogus")
        self.assertIn("madvise", " ".join(args))

    def test_apply_swappiness_clamps_value(self):
        """Test apply_swappiness clamps value within 0-200 range."""
        cmd, args, desc = AutoTuner.apply_swappiness(-10)
        self.assertIn("vm.swappiness=0", " ".join(args))

        cmd, args, desc = AutoTuner.apply_swappiness(999)
        self.assertIn("vm.swappiness=200", " ".join(args))

    @patch('utils.auto_tuner.AutoTuner._find_first_block_device', return_value="")
    def test_apply_io_scheduler_no_device(self, mock_find):
        """Test apply_io_scheduler with no device found returns echo fallback."""
        cmd, args, desc = AutoTuner.apply_io_scheduler("none")
        self.assertEqual(cmd, "echo")


class TestTuningHistory(unittest.TestCase):
    """Tests for AutoTuner tuning history methods."""

    @patch('utils.auto_tuner.os.path.isfile', return_value=False)
    def test_get_empty_history(self, mock_isfile):
        """Test get_tuning_history returns empty list when file doesn't exist."""
        result = AutoTuner.get_tuning_history()
        self.assertEqual(result, [])

    @patch('utils.auto_tuner.os.path.isfile', return_value=True)
    def test_get_history_with_entries(self, mock_isfile):
        """Test get_tuning_history parses existing JSON entries."""
        data = [
            {
                "timestamp": 1700000000.0,
                "workload": "gaming",
                "recommendations": {"governor": "performance"},
                "applied": True,
            },
            {
                "timestamp": 1700001000.0,
                "workload": "idle",
                "recommendations": {"governor": "powersave"},
                "applied": False,
            },
        ]
        with patch('builtins.open', mock_open(read_data=json.dumps(data))):
            result = AutoTuner.get_tuning_history()

        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], TuningHistoryEntry)
        self.assertEqual(result[0].workload, "gaming")
        self.assertTrue(result[0].applied)
        self.assertEqual(result[1].workload, "idle")
        self.assertFalse(result[1].applied)

    @patch('utils.auto_tuner.os.makedirs')
    @patch('utils.auto_tuner.os.path.isfile', return_value=False)
    def test_save_entry(self, mock_isfile, mock_makedirs):
        """Test save_tuning_entry writes JSON to disk."""
        entry = TuningHistoryEntry(
            timestamp=1700000000.0,
            workload="idle",
            recommendations={"governor": "powersave"},
            applied=True,
        )
        m = mock_open()
        with patch('builtins.open', m):
            AutoTuner.save_tuning_entry(entry)

        mock_makedirs.assert_called_once()
        m.assert_called_once()
        handle = m()
        written = "".join(c.args[0] for c in handle.write.call_args_list)
        parsed = json.loads(written)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["workload"], "idle")

    @patch('utils.auto_tuner.os.makedirs')
    @patch('utils.auto_tuner.os.path.isfile', return_value=True)
    def test_history_max_50(self, mock_isfile, mock_makedirs):
        """Test tuning history is truncated to 50 entries."""
        existing = [
            {
                "timestamp": float(i),
                "workload": "idle",
                "recommendations": {},
                "applied": False,
            }
            for i in range(55)
        ]
        new_entry = TuningHistoryEntry(
            timestamp=9999.0,
            workload="heavy",
            recommendations={"governor": "performance"},
            applied=True,
        )
        m = mock_open(read_data=json.dumps(existing))
        with patch('builtins.open', m):
            AutoTuner.save_tuning_entry(new_entry)

        handle = m()
        written = "".join(c.args[0] for c in handle.write.call_args_list)
        parsed = json.loads(written)
        self.assertLessEqual(len(parsed), 50)
        # Last entry should be our new one
        self.assertEqual(parsed[-1]["workload"], "heavy")

    @patch('utils.auto_tuner.os.path.isfile', return_value=True)
    def test_history_corrupted_json(self, mock_isfile):
        """Test get_tuning_history returns empty list on corrupted JSON."""
        with patch('builtins.open', mock_open(read_data="NOT VALID JSON{{{{")):
            result = AutoTuner.get_tuning_history()
        self.assertEqual(result, [])

    @patch('utils.auto_tuner.os.path.isfile', return_value=True)
    def test_history_non_list_json(self, mock_isfile):
        """Test get_tuning_history returns empty list when JSON is not a list."""
        with patch('builtins.open', mock_open(read_data='{"key": "value"}')):
            result = AutoTuner.get_tuning_history()
        self.assertEqual(result, [])


class TestInternalHelpers(unittest.TestCase):
    """Tests for internal helper methods."""

    @patch('utils.auto_tuner.time.sleep')
    def test_read_cpu_percent_idle(self, mock_sleep):
        """Test _read_cpu_percent returns ~0% for identical snapshots."""
        # Two identical snapshots → 0% usage
        stat_data = "cpu  100 0 100 800 10 0 0 0\n"
        with patch('builtins.open', mock_open(read_data=stat_data)):
            result = AutoTuner._read_cpu_percent()
        self.assertEqual(result, 0.0)

    @patch('utils.auto_tuner.AutoTuner._read_aggregate_cpu_times', return_value=None)
    def test_read_cpu_percent_no_data(self, mock_agg):
        """Test _read_cpu_percent returns 0 when /proc/stat unreadable."""
        result = AutoTuner._read_cpu_percent()
        self.assertEqual(result, 0.0)

    def test_read_aggregate_cpu_times_success(self):
        """Test _read_aggregate_cpu_times parses /proc/stat cpu line."""
        stat_line = "cpu  1000 20 300 4000 50 60 70 80\n"
        with patch('builtins.open', mock_open(read_data=stat_line)):
            result = AutoTuner._read_aggregate_cpu_times()
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 8)
        self.assertEqual(result[0], 1000)

    def test_read_aggregate_cpu_times_bad_format(self):
        """Test _read_aggregate_cpu_times returns None for non-cpu line."""
        with patch('builtins.open', mock_open(read_data="intr 123 456\n")):
            result = AutoTuner._read_aggregate_cpu_times()
        self.assertIsNone(result)

    def test_read_aggregate_cpu_times_oserror(self):
        """Test _read_aggregate_cpu_times returns None on OSError."""
        with patch('builtins.open', side_effect=OSError("No such file")):
            result = AutoTuner._read_aggregate_cpu_times()
        self.assertIsNone(result)

    def test_read_memory_percent_success(self):
        """Test _read_memory_percent parses /proc/meminfo."""
        meminfo = (
            "MemTotal:       16000000 kB\n"
            "MemFree:         4000000 kB\n"
            "MemAvailable:    8000000 kB\n"
        )
        with patch('builtins.open', mock_open(read_data=meminfo)):
            result = AutoTuner._read_memory_percent()
        self.assertAlmostEqual(result, 50.0, places=1)

    def test_read_memory_percent_no_total(self):
        """Test _read_memory_percent returns 0 when MemTotal is missing."""
        meminfo = "MemAvailable:    8000000 kB\n"
        with patch('builtins.open', mock_open(read_data=meminfo)):
            result = AutoTuner._read_memory_percent()
        self.assertEqual(result, 0.0)

    def test_read_memory_percent_oserror(self):
        """Test _read_memory_percent returns 0 on read failure."""
        with patch('builtins.open', side_effect=OSError("No such file")):
            result = AutoTuner._read_memory_percent()
        self.assertEqual(result, 0.0)

    @patch('utils.auto_tuner.os.listdir', return_value=["loop0", "sda", "nvme0n1"])
    @patch('utils.auto_tuner.os.path.isdir', return_value=True)
    def test_find_first_block_device(self, mock_isdir, mock_listdir):
        """Test _find_first_block_device skips loop devices."""
        result = AutoTuner._find_first_block_device()
        self.assertEqual(result, "nvme0n1")

    @patch('utils.auto_tuner.os.path.isdir', return_value=False)
    def test_find_first_block_device_no_sysblock(self, mock_isdir):
        """Test _find_first_block_device returns empty when /sys/block missing."""
        result = AutoTuner._find_first_block_device()
        self.assertEqual(result, "")

    @patch('utils.auto_tuner.os.listdir', return_value=["loop0", "loop1", "ram0"])
    @patch('utils.auto_tuner.os.path.isdir', return_value=True)
    def test_find_first_block_device_only_virtual(self, mock_isdir, mock_listdir):
        """Test _find_first_block_device returns empty when only virtual devices exist."""
        result = AutoTuner._find_first_block_device()
        self.assertEqual(result, "")

    @patch('utils.auto_tuner.AutoTuner._find_first_block_device', return_value="sda")
    @patch('utils.auto_tuner.os.path.exists', return_value=True)
    def test_read_io_scheduler_success(self, mock_exists, mock_find):
        """Test _read_io_scheduler extracts bracketed active scheduler."""
        with patch('builtins.open', mock_open(read_data="none [mq-deadline] kyber\n")):
            result = AutoTuner._read_io_scheduler()
        self.assertEqual(result, "mq-deadline")

    @patch('utils.auto_tuner.AutoTuner._find_first_block_device', return_value="")
    def test_read_io_scheduler_no_device(self, mock_find):
        """Test _read_io_scheduler returns 'unknown' with no device."""
        result = AutoTuner._read_io_scheduler()
        self.assertEqual(result, "unknown")


if __name__ == '__main__':
    unittest.main()

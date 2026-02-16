"""
Tests for utils/zram.py — ZramManager.
Covers: get_total_ram, get_current_config, set_config,
disable, get_current_usage, and validation.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

# Add source path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.zram import ZramManager, ZramConfig, ZramResult


# ---------------------------------------------------------------------------
# TestZramDataclasses — dataclass tests
# ---------------------------------------------------------------------------

class TestZramDataclasses(unittest.TestCase):
    """Tests for ZramResult and ZramConfig dataclasses."""

    def test_zram_result_creation(self):
        """ZramResult stores all fields."""
        r = ZramResult(success=True, message="OK", output="config")
        self.assertTrue(r.success)
        self.assertEqual(r.output, "config")

    def test_zram_config_creation(self):
        """ZramConfig stores all fields."""
        c = ZramConfig(enabled=True, size_mb=8192, size_percent=100,
                       algorithm="zstd", total_ram_mb=8192)
        self.assertTrue(c.enabled)
        self.assertEqual(c.algorithm, "zstd")


# ---------------------------------------------------------------------------
# TestGetTotalRam — RAM detection
# ---------------------------------------------------------------------------

class TestGetTotalRam(unittest.TestCase):
    """Tests for get_total_ram_mb with mocked /proc/meminfo."""

    @patch('builtins.open', mock_open(read_data="MemTotal:       16384000 kB\nMemFree: 8000000 kB\n"))
    def test_get_total_ram_parses_meminfo(self):
        """get_total_ram_mb parses MemTotal from /proc/meminfo."""
        ram = ZramManager.get_total_ram_mb()
        self.assertEqual(ram, 16384000 // 1024)

    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_get_total_ram_fallback(self, mock_file):
        """get_total_ram_mb returns 8192 fallback on error."""
        ram = ZramManager.get_total_ram_mb()
        self.assertEqual(ram, 8192)


# ---------------------------------------------------------------------------
# TestGetCurrentConfig — reading ZRAM configuration
# ---------------------------------------------------------------------------

class TestGetCurrentConfig(unittest.TestCase):
    """Tests for get_current_config."""

    @patch('utils.zram.subprocess.run')
    @patch.object(ZramManager, 'get_total_ram_mb', return_value=16384)
    def test_get_current_config_zram_active(self, mock_ram, mock_run):
        """get_current_config detects active ZRAM."""
        mock_run.return_value = MagicMock(returncode=0, stdout="/dev/zram0 lz4 8G 100M")

        # Mock config file not existing
        original_paths = ZramManager.CONFIG_PATHS
        ZramManager.CONFIG_PATHS = [Path("/nonexistent/zram.conf")]
        try:
            config = ZramManager.get_current_config()
            self.assertTrue(config.enabled)
            self.assertEqual(config.total_ram_mb, 16384)
        finally:
            ZramManager.CONFIG_PATHS = original_paths

    @patch('utils.zram.subprocess.run')
    @patch.object(ZramManager, 'get_total_ram_mb', return_value=8192)
    def test_get_current_config_zram_inactive(self, mock_ram, mock_run):
        """get_current_config detects inactive ZRAM."""
        mock_run.return_value = MagicMock(returncode=0, stdout="")

        original_paths = ZramManager.CONFIG_PATHS
        ZramManager.CONFIG_PATHS = [Path("/nonexistent/zram.conf")]
        try:
            config = ZramManager.get_current_config()
            self.assertFalse(config.enabled)
        finally:
            ZramManager.CONFIG_PATHS = original_paths


# ---------------------------------------------------------------------------
# TestSetConfig — setting ZRAM configuration
# ---------------------------------------------------------------------------

class TestSetConfig(unittest.TestCase):
    """Tests for set_config with mocked subprocess."""

    def test_set_config_invalid_size_low(self):
        """set_config rejects size below 10%."""
        result = ZramManager.set_config(5, "zstd")
        self.assertFalse(result.success)
        self.assertIn("between", result.message)

    def test_set_config_invalid_size_high(self):
        """set_config rejects size above 200%."""
        result = ZramManager.set_config(250, "zstd")
        self.assertFalse(result.success)

    def test_set_config_invalid_algorithm(self):
        """set_config rejects unknown algorithm."""
        result = ZramManager.set_config(50, "invalid_algo")
        self.assertFalse(result.success)
        self.assertIn("Invalid algorithm", result.message)

    @patch('utils.zram.os.unlink')
    @patch('utils.zram.subprocess.run')
    @patch.object(ZramManager, 'get_total_ram_mb', return_value=8192)
    def test_set_config_success(self, mock_ram, mock_run, mock_unlink):
        """set_config writes config successfully."""
        mock_run.return_value = MagicMock(returncode=0)

        # Create a real temp file for the method to use
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            tmp_path = f.name

        try:
            # The method creates its own temp file; we just need subprocess to succeed
            result = ZramManager.set_config(50, "zstd")
            self.assertTrue(result.success)
            self.assertIn("50%", result.message)
        finally:
            # clean up any leftover temp file
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    @patch('utils.zram.os.unlink')
    @patch('utils.zram.subprocess.run')
    @patch.object(ZramManager, 'get_total_ram_mb', return_value=8192)
    def test_set_config_100_percent(self, mock_ram, mock_run, mock_unlink):
        """set_config 100% uses 'zram-size = ram' syntax."""
        mock_run.return_value = MagicMock(returncode=0)

        result = ZramManager.set_config(100, "zstd")
        self.assertTrue(result.success)
        self.assertIn("zram-size = ram", result.output)


# ---------------------------------------------------------------------------
# TestDisable — disabling ZRAM
# ---------------------------------------------------------------------------

class TestDisable(unittest.TestCase):
    """Tests for disable with mocked subprocess."""

    @patch('utils.zram.subprocess.run')
    @patch('utils.zram.os.path.exists', return_value=True)
    def test_disable_success(self, mock_exists, mock_run):
        """disable removes config file."""
        mock_run.return_value = MagicMock(returncode=0)

        result = ZramManager.disable()
        self.assertTrue(result.success)

    @patch('utils.zram.os.path.exists', return_value=False)
    def test_disable_already_disabled(self, mock_exists):
        """disable returns success when already disabled."""
        result = ZramManager.disable()
        self.assertTrue(result.success)
        self.assertIn("already", result.message.lower())


# ---------------------------------------------------------------------------
# TestGetCurrentUsage — ZRAM usage
# ---------------------------------------------------------------------------

class TestGetCurrentUsage(unittest.TestCase):
    """Tests for get_current_usage."""

    @patch('utils.zram.subprocess.run')
    def test_get_current_usage_success(self, mock_run):
        """get_current_usage parses zramctl output."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="104857600 8589934592\n"
        )

        usage = ZramManager.get_current_usage()
        self.assertIsNotNone(usage)
        used_mb, total_mb = usage
        self.assertEqual(used_mb, 100)  # 104857600 / (1024*1024)
        self.assertEqual(total_mb, 8192)  # 8589934592 / (1024*1024)

    @patch('utils.zram.subprocess.run', side_effect=OSError("fail"))
    def test_get_current_usage_error(self, mock_run):
        """get_current_usage returns None on error."""
        usage = ZramManager.get_current_usage()
        self.assertIsNone(usage)

    @patch('utils.zram.subprocess.run')
    def test_get_current_usage_empty_output(self, mock_run):
        """get_current_usage returns None on empty output."""
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        usage = ZramManager.get_current_usage()
        self.assertIsNone(usage)


if __name__ == '__main__':
    unittest.main()

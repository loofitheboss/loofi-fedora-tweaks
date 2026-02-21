"""Tests for utils/system_info_utils.py — extracted system info queries.

v42.0.0 Sentinel: Updated to match safe alternatives (socket, platform,
subprocess.run, file reads) replacing subprocess.getoutput.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, mock_open, patch

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.system_info_utils import (
    get_hostname,
    get_kernel_version,
    get_fedora_release,
    get_cpu_model,
    get_ram_usage,
    get_disk_usage,
    get_uptime,
    get_battery_status,
)


class TestGetHostname(unittest.TestCase):

    @patch("utils.system_info_utils.socket.gethostname", return_value="fedora-desktop")
    def test_returns_hostname(self, mock_gh):
        self.assertEqual(get_hostname(), "fedora-desktop")
        mock_gh.assert_called_once()

    @patch("utils.system_info_utils.socket.gethostname", side_effect=OSError("fail"))
    def test_returns_unknown_on_error(self, mock_gh):
        self.assertEqual(get_hostname(), "Unknown")


class TestGetKernelVersion(unittest.TestCase):

    @patch("utils.system_info_utils.platform.release", return_value="6.8.11-300.fc40.x86_64")
    def test_returns_kernel(self, mock_rel):
        self.assertEqual(get_kernel_version(), "6.8.11-300.fc40.x86_64")
        mock_rel.assert_called_once()

    @patch("utils.system_info_utils.platform.release", return_value="")
    def test_returns_unknown_on_empty(self, mock_rel):
        self.assertEqual(get_kernel_version(), "Unknown")


class TestGetFedoraRelease(unittest.TestCase):

    @patch("builtins.open", mock_open(read_data="Fedora release 40 (Forty)\n"))
    def test_returns_release(self):
        self.assertEqual(get_fedora_release(), "Fedora release 40 (Forty)")

    @patch("builtins.open", side_effect=OSError("fail"))
    def test_returns_unknown_on_error(self, mock_f):
        self.assertEqual(get_fedora_release(), "Unknown")


class TestGetCpuModel(unittest.TestCase):

    @patch("utils.system_info_utils.subprocess.run")
    def test_returns_cpu(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Architecture:            x86_64\nModel name:              AMD Ryzen 7 5800X\n",
        )
        self.assertEqual(get_cpu_model(), "AMD Ryzen 7 5800X")

    @patch("utils.system_info_utils.subprocess.run")
    def test_returns_unknown_on_no_match(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="Architecture:  x86_64\n")
        self.assertEqual(get_cpu_model(), "Unknown")

    @patch("utils.system_info_utils.subprocess.run")
    def test_returns_unknown_on_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        self.assertEqual(get_cpu_model(), "Unknown")

    @patch("utils.system_info_utils.subprocess.run", side_effect=OSError("fail"))
    def test_returns_unknown_on_error(self, mock_run):
        self.assertEqual(get_cpu_model(), "Unknown")


class TestGetRamUsage(unittest.TestCase):

    @patch("utils.system_info_utils.subprocess.run")
    def test_returns_ram(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="              total        used        free\nMem:           16Gi       8.2Gi       4.0Gi\n",
        )
        self.assertEqual(get_ram_usage(), "16Gi total, 8.2Gi used")

    @patch("utils.system_info_utils.subprocess.run", side_effect=OSError("fail"))
    def test_returns_unknown_on_error(self, mock_run):
        self.assertEqual(get_ram_usage(), "Unknown")


class TestGetDiskUsage(unittest.TestCase):

    @patch("utils.system_info_utils.subprocess.run")
    def test_returns_disk(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Filesystem      Size  Used Avail Use% Mounted on\n/dev/sda1       500G  120G  380G  24% /\n",
        )
        self.assertEqual(get_disk_usage(), "120G/500G (24% used)")

    @patch("utils.system_info_utils.subprocess.run", side_effect=OSError("fail"))
    def test_returns_unknown_on_error(self, mock_run):
        self.assertEqual(get_disk_usage(), "Unknown")


class TestGetUptime(unittest.TestCase):

    @patch("utils.system_info_utils.subprocess.run")
    def test_returns_uptime(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="up 3 days, 2 hours, 15 minutes\n",
        )
        self.assertEqual(get_uptime(), "up 3 days, 2 hours, 15 minutes")

    @patch("utils.system_info_utils.subprocess.run", side_effect=OSError("fail"))
    def test_returns_unknown_on_error(self, mock_run):
        self.assertEqual(get_uptime(), "Unknown")


class TestGetBatteryStatus(unittest.TestCase):

    @patch("utils.system_info_utils.os.path.exists", return_value=True)
    @patch("builtins.open", side_effect=[
        mock_open(read_data="85\n").return_value,
        mock_open(read_data="Charging\n").return_value,
    ])
    def test_returns_battery_info(self, mock_f, mock_exists):
        result = get_battery_status()
        self.assertEqual(result, "85% (Charging)")

    @patch("utils.system_info_utils.os.path.exists", return_value=False)
    def test_returns_none_no_battery(self, mock_exists):
        result = get_battery_status()
        self.assertIsNone(result)

    @patch("utils.system_info_utils.os.path.exists", return_value=True)
    @patch("builtins.open", side_effect=OSError("fail"))
    def test_returns_none_on_error(self, mock_f, mock_exists):
        result = get_battery_status()
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()

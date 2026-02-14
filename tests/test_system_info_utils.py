"""Tests for utils/system_info_utils.py — extracted system info queries."""

import os
import sys
import unittest
from unittest.mock import patch

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

    @patch("utils.system_info_utils.subprocess.getoutput", return_value="fedora-desktop")
    def test_returns_hostname(self, mock_out):
        self.assertEqual(get_hostname(), "fedora-desktop")
        mock_out.assert_called_once_with("hostname")

    @patch("utils.system_info_utils.subprocess.getoutput", side_effect=OSError("fail"))
    def test_returns_unknown_on_error(self, mock_out):
        self.assertEqual(get_hostname(), "Unknown")


class TestGetKernelVersion(unittest.TestCase):

    @patch("utils.system_info_utils.subprocess.getoutput", return_value="6.8.11-300.fc40.x86_64")
    def test_returns_kernel(self, mock_out):
        self.assertEqual(get_kernel_version(), "6.8.11-300.fc40.x86_64")
        mock_out.assert_called_once_with("uname -r")

    @patch("utils.system_info_utils.subprocess.getoutput", side_effect=OSError("fail"))
    def test_returns_unknown_on_error(self, mock_out):
        self.assertEqual(get_kernel_version(), "Unknown")


class TestGetFedoraRelease(unittest.TestCase):

    @patch("utils.system_info_utils.subprocess.getoutput", return_value="Fedora release 40 (Forty)")
    def test_returns_release(self, mock_out):
        self.assertEqual(get_fedora_release(), "Fedora release 40 (Forty)")
        mock_out.assert_called_once_with("cat /etc/fedora-release")

    @patch("utils.system_info_utils.subprocess.getoutput", side_effect=OSError("fail"))
    def test_returns_unknown_on_error(self, mock_out):
        self.assertEqual(get_fedora_release(), "Unknown")


class TestGetCpuModel(unittest.TestCase):

    @patch("utils.system_info_utils.subprocess.getoutput", return_value="  AMD Ryzen 7 5800X")
    def test_returns_cpu(self, mock_out):
        self.assertEqual(get_cpu_model(), "AMD Ryzen 7 5800X")

    @patch("utils.system_info_utils.subprocess.getoutput", return_value="")
    def test_returns_unknown_on_empty(self, mock_out):
        self.assertEqual(get_cpu_model(), "Unknown")

    @patch("utils.system_info_utils.subprocess.getoutput", side_effect=OSError("fail"))
    def test_returns_unknown_on_error(self, mock_out):
        self.assertEqual(get_cpu_model(), "Unknown")


class TestGetRamUsage(unittest.TestCase):

    @patch("utils.system_info_utils.subprocess.getoutput", return_value="16Gi total, 8.2Gi used")
    def test_returns_ram(self, mock_out):
        self.assertEqual(get_ram_usage(), "16Gi total, 8.2Gi used")

    @patch("utils.system_info_utils.subprocess.getoutput", side_effect=OSError("fail"))
    def test_returns_unknown_on_error(self, mock_out):
        self.assertEqual(get_ram_usage(), "Unknown")


class TestGetDiskUsage(unittest.TestCase):

    @patch("utils.system_info_utils.subprocess.getoutput", return_value="120G/500G (24% used)")
    def test_returns_disk(self, mock_out):
        self.assertEqual(get_disk_usage(), "120G/500G (24% used)")

    @patch("utils.system_info_utils.subprocess.getoutput", side_effect=OSError("fail"))
    def test_returns_unknown_on_error(self, mock_out):
        self.assertEqual(get_disk_usage(), "Unknown")


class TestGetUptime(unittest.TestCase):

    @patch("utils.system_info_utils.subprocess.getoutput", return_value="up 3 days, 2 hours, 15 minutes")
    def test_returns_uptime(self, mock_out):
        self.assertEqual(get_uptime(), "up 3 days, 2 hours, 15 minutes")

    @patch("utils.system_info_utils.subprocess.getoutput", side_effect=OSError("fail"))
    def test_returns_unknown_on_error(self, mock_out):
        self.assertEqual(get_uptime(), "Unknown")


class TestGetBatteryStatus(unittest.TestCase):

    @patch("utils.system_info_utils.os.path.exists", return_value=True)
    @patch("utils.system_info_utils.subprocess.getoutput", side_effect=["85", "Charging"])
    def test_returns_battery_info(self, mock_out, mock_exists):
        result = get_battery_status()
        self.assertEqual(result, "85% (Charging)")

    @patch("utils.system_info_utils.os.path.exists", return_value=False)
    def test_returns_none_no_battery(self, mock_exists):
        result = get_battery_status()
        self.assertIsNone(result)

    @patch("utils.system_info_utils.os.path.exists", return_value=True)
    @patch("utils.system_info_utils.subprocess.getoutput", side_effect=OSError("fail"))
    def test_returns_none_on_error(self, mock_out, mock_exists):
        result = get_battery_status()
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()

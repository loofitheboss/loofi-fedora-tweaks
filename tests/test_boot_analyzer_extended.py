"""
Extended tests for BootAnalyzer - Boot performance analysis.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add source path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.boot_analyzer import BootAnalyzer, ServiceTime, BootStats


class TestServiceTimeDataclass(unittest.TestCase):
    """Tests for ServiceTime dataclass."""

    def test_service_time_creation(self):
        """ServiceTime stores all required fields."""
        service = ServiceTime(
            service="NetworkManager.service",
            time_seconds=5.5,
            is_slow=True
        )

        self.assertEqual(service.service, "NetworkManager.service")
        self.assertEqual(service.time_seconds, 5.5)
        self.assertTrue(service.is_slow)

    def test_service_time_defaults(self):
        """ServiceTime has correct defaults."""
        service = ServiceTime(service="test.service", time_seconds=1.0)
        self.assertFalse(service.is_slow)


class TestBootStatsDataclass(unittest.TestCase):
    """Tests for BootStats dataclass."""

    def test_boot_stats_creation(self):
        """BootStats stores all timing fields."""
        stats = BootStats(
            firmware_time=2.5,
            loader_time=1.2,
            kernel_time=3.1,
            userspace_time=15.2,
            total_time=22.0
        )

        self.assertEqual(stats.firmware_time, 2.5)
        self.assertEqual(stats.loader_time, 1.2)
        self.assertEqual(stats.kernel_time, 3.1)
        self.assertEqual(stats.userspace_time, 15.2)
        self.assertEqual(stats.total_time, 22.0)

    def test_boot_stats_defaults(self):
        """BootStats has None defaults for all fields."""
        stats = BootStats()

        self.assertIsNone(stats.firmware_time)
        self.assertIsNone(stats.loader_time)
        self.assertIsNone(stats.kernel_time)
        self.assertIsNone(stats.userspace_time)
        self.assertIsNone(stats.total_time)


class TestBootAnalyzerConstants(unittest.TestCase):
    """Tests for BootAnalyzer constants."""

    def test_slow_threshold_is_reasonable(self):
        """SLOW_THRESHOLD is 5 seconds."""
        self.assertEqual(BootAnalyzer.SLOW_THRESHOLD, 5.0)


class TestGetBootStats(unittest.TestCase):
    """Tests for get_boot_stats method."""

    @patch('utils.boot_analyzer.subprocess.run')
    def test_get_boot_stats_parses_full_output(self, mock_run):
        """get_boot_stats parses all timing components."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Startup finished in 2.5s (firmware) + 1.2s (loader) + 3.1s (kernel) + 15.2s (userspace) = 22.0s"
        )

        stats = BootAnalyzer.get_boot_stats()

        self.assertEqual(stats.firmware_time, 2.5)
        self.assertEqual(stats.loader_time, 1.2)
        self.assertEqual(stats.kernel_time, 3.1)
        self.assertEqual(stats.userspace_time, 15.2)
        self.assertEqual(stats.total_time, 22.0)

    @patch('utils.boot_analyzer.subprocess.run')
    def test_get_boot_stats_handles_kernel_and_userspace_only(self, mock_run):
        """get_boot_stats handles output without firmware/loader."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Startup finished in 3.1s (kernel) + 15.2s (userspace) = 18.3s"
        )

        stats = BootAnalyzer.get_boot_stats()

        self.assertIsNone(stats.firmware_time)
        self.assertIsNone(stats.loader_time)
        self.assertEqual(stats.kernel_time, 3.1)
        self.assertEqual(stats.userspace_time, 15.2)
        self.assertEqual(stats.total_time, 18.3)

    @patch('utils.boot_analyzer.subprocess.run')
    def test_get_boot_stats_handles_nonzero_exit(self, mock_run):
        """get_boot_stats returns empty BootStats on error."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")

        stats = BootAnalyzer.get_boot_stats()

        self.assertIsNone(stats.total_time)

    @patch('utils.boot_analyzer.subprocess.run')
    def test_get_boot_stats_handles_exception(self, mock_run):
        """get_boot_stats returns empty BootStats on exception."""
        mock_run.side_effect = OSError("Command failed")

        stats = BootAnalyzer.get_boot_stats()

        self.assertIsNone(stats.total_time)


class TestGetBlameData(unittest.TestCase):
    """Tests for get_blame_data method."""

    @patch('utils.boot_analyzer.subprocess.run')
    def test_get_blame_data_parses_seconds(self, mock_run):
        """get_blame_data parses service times in seconds."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="15.234s NetworkManager.service\n5.678s systemd-logind.service\n"
        )

        services = BootAnalyzer.get_blame_data()

        self.assertEqual(len(services), 2)
        self.assertEqual(services[0].service, "NetworkManager.service")
        self.assertEqual(services[0].time_seconds, 15.234)
        self.assertTrue(services[0].is_slow)

    @patch('utils.boot_analyzer.subprocess.run')
    def test_get_blame_data_parses_milliseconds(self, mock_run):
        """get_blame_data parses service times in milliseconds."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="500ms test.service\n"
        )

        services = BootAnalyzer.get_blame_data()

        self.assertEqual(len(services), 1)
        self.assertEqual(services[0].time_seconds, 0.5)
        self.assertFalse(services[0].is_slow)

    @patch('utils.boot_analyzer.subprocess.run')
    def test_get_blame_data_parses_minutes(self, mock_run):
        """get_blame_data parses service times in minutes."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="1.5min slow.service\n"
        )

        services = BootAnalyzer.get_blame_data()

        self.assertEqual(len(services), 1)
        self.assertEqual(services[0].time_seconds, 90.0)
        self.assertTrue(services[0].is_slow)

    @patch('utils.boot_analyzer.subprocess.run')
    def test_get_blame_data_respects_limit(self, mock_run):
        """get_blame_data respects the limit parameter."""
        lines = "\n".join([f"{i}s service{i}.service" for i in range(50)])
        mock_run.return_value = MagicMock(returncode=0, stdout=lines)

        services = BootAnalyzer.get_blame_data(limit=10)

        self.assertEqual(len(services), 10)

    @patch('utils.boot_analyzer.subprocess.run')
    def test_get_blame_data_handles_empty_output(self, mock_run):
        """get_blame_data returns empty list for empty output."""
        mock_run.return_value = MagicMock(returncode=0, stdout="")

        services = BootAnalyzer.get_blame_data()

        self.assertEqual(services, [])

    @patch('utils.boot_analyzer.subprocess.run')
    def test_get_blame_data_handles_nonzero_exit(self, mock_run):
        """get_blame_data returns empty list on error."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")

        services = BootAnalyzer.get_blame_data()

        self.assertEqual(services, [])

    @patch('utils.boot_analyzer.subprocess.run')
    def test_get_blame_data_handles_exception(self, mock_run):
        """get_blame_data returns empty list on exception."""
        mock_run.side_effect = OSError("Command failed")

        services = BootAnalyzer.get_blame_data()

        self.assertEqual(services, [])


class TestGetSlowServices(unittest.TestCase):
    """Tests for get_slow_services method."""

    @patch.object(BootAnalyzer, 'get_blame_data')
    def test_get_slow_services_filters_by_threshold(self, mock_blame):
        """get_slow_services returns services above threshold."""
        mock_blame.return_value = [
            ServiceTime("fast.service", 1.0, False),
            ServiceTime("slow.service", 10.0, True),
            ServiceTime("medium.service", 4.9, False),
        ]

        slow = BootAnalyzer.get_slow_services()

        self.assertEqual(len(slow), 1)
        self.assertEqual(slow[0].service, "slow.service")

    @patch.object(BootAnalyzer, 'get_blame_data')
    def test_get_slow_services_custom_threshold(self, mock_blame):
        """get_slow_services uses custom threshold."""
        mock_blame.return_value = [
            ServiceTime("service1", 2.0, False),
            ServiceTime("service2", 3.0, False),
            ServiceTime("service3", 4.0, False),
        ]

        slow = BootAnalyzer.get_slow_services(threshold=2.5)

        self.assertEqual(len(slow), 2)

    @patch.object(BootAnalyzer, 'get_blame_data')
    def test_get_slow_services_no_slow_services(self, mock_blame):
        """get_slow_services returns empty list when all fast."""
        mock_blame.return_value = [
            ServiceTime("fast1.service", 0.5, False),
            ServiceTime("fast2.service", 1.0, False),
        ]

        slow = BootAnalyzer.get_slow_services()

        self.assertEqual(slow, [])


class TestGetCriticalChain(unittest.TestCase):
    """Tests for get_critical_chain method."""

    @patch('utils.boot_analyzer.subprocess.run')
    def test_get_critical_chain_returns_output(self, mock_run):
        """get_critical_chain returns command output."""
        expected_output = "multi-user.target @18.3s\n  systemd-logind.service @5.2s +1.1s\n"
        mock_run.return_value = MagicMock(returncode=0, stdout=expected_output)

        result = BootAnalyzer.get_critical_chain()

        self.assertEqual(result, expected_output)

    @patch('utils.boot_analyzer.subprocess.run')
    def test_get_critical_chain_handles_error(self, mock_run):
        """get_critical_chain returns empty string on error."""
        mock_run.return_value = MagicMock(returncode=1, stdout="error")

        result = BootAnalyzer.get_critical_chain()

        self.assertEqual(result, "")

    @patch('utils.boot_analyzer.subprocess.run')
    def test_get_critical_chain_handles_exception(self, mock_run):
        """get_critical_chain returns empty string on exception."""
        mock_run.side_effect = OSError("Command failed")

        result = BootAnalyzer.get_critical_chain()

        self.assertEqual(result, "")


class TestGetOptimizationSuggestions(unittest.TestCase):
    """Tests for get_optimization_suggestions method."""

    @patch.object(BootAnalyzer, 'get_slow_services')
    @patch.object(BootAnalyzer, 'get_boot_stats')
    @patch.object(BootAnalyzer, 'get_blame_data')
    def test_suggestions_for_slow_boot(self, mock_blame, mock_stats, mock_slow):
        """get_optimization_suggestions suggests for slow total boot."""
        mock_stats.return_value = BootStats(total_time=45.0)
        mock_slow.return_value = []
        mock_blame.return_value = []

        suggestions = BootAnalyzer.get_optimization_suggestions()

        self.assertTrue(any("45.0s" in s for s in suggestions))

    @patch.object(BootAnalyzer, 'get_slow_services')
    @patch.object(BootAnalyzer, 'get_boot_stats')
    @patch.object(BootAnalyzer, 'get_blame_data')
    def test_suggestions_for_slow_services(self, mock_blame, mock_stats, mock_slow):
        """get_optimization_suggestions suggests for slow services."""
        mock_stats.return_value = BootStats(total_time=25.0)
        mock_slow.return_value = [
            ServiceTime("slow.service", 10.0, True),
        ]
        mock_blame.return_value = []

        suggestions = BootAnalyzer.get_optimization_suggestions()

        self.assertTrue(any("slow.service" in s for s in suggestions))

    @patch.object(BootAnalyzer, 'get_slow_services')
    @patch.object(BootAnalyzer, 'get_boot_stats')
    @patch.object(BootAnalyzer, 'get_blame_data')
    def test_suggestions_for_problematic_services(self, mock_blame, mock_stats, mock_slow):
        """get_optimization_suggestions identifies known problematic services."""
        mock_stats.return_value = BootStats(total_time=20.0)
        mock_slow.return_value = []
        mock_blame.return_value = [
            ServiceTime("NetworkManager-wait-online.service", 8.0, True),
        ]

        suggestions = BootAnalyzer.get_optimization_suggestions()

        self.assertTrue(any("NetworkManager-wait-online" in s for s in suggestions))

    @patch.object(BootAnalyzer, 'get_slow_services')
    @patch.object(BootAnalyzer, 'get_boot_stats')
    @patch.object(BootAnalyzer, 'get_blame_data')
    def test_suggestions_good_performance(self, mock_blame, mock_stats, mock_slow):
        """get_optimization_suggestions shows good message for fast boot."""
        mock_stats.return_value = BootStats(total_time=15.0)
        mock_slow.return_value = []
        mock_blame.return_value = []

        suggestions = BootAnalyzer.get_optimization_suggestions()

        self.assertTrue(any("good" in s.lower() for s in suggestions))

    @patch.object(BootAnalyzer, 'get_slow_services')
    @patch.object(BootAnalyzer, 'get_boot_stats')
    @patch.object(BootAnalyzer, 'get_blame_data')
    def test_suggestions_unavailable(self, mock_blame, mock_stats, mock_slow):
        """get_optimization_suggestions handles unavailable analyze."""
        mock_stats.return_value = BootStats()  # All None
        mock_slow.return_value = []
        mock_blame.return_value = []

        suggestions = BootAnalyzer.get_optimization_suggestions()

        self.assertTrue(any("Unable to analyze" in s for s in suggestions))

    @patch.object(BootAnalyzer, 'get_slow_services')
    @patch.object(BootAnalyzer, 'get_boot_stats')
    @patch.object(BootAnalyzer, 'get_blame_data')
    def test_suggestions_limit_slow_services(self, mock_blame, mock_stats, mock_slow):
        """get_optimization_suggestions limits to top 5 slow services."""
        mock_stats.return_value = BootStats(total_time=60.0)
        mock_slow.return_value = [
            ServiceTime(f"slow{i}.service", 10.0 + i, True)
            for i in range(10)
        ]
        mock_blame.return_value = []

        suggestions = BootAnalyzer.get_optimization_suggestions()

        # Count slow service suggestions
        slow_suggestions = [s for s in suggestions if "takes" in s and "s." in s]
        self.assertLessEqual(len(slow_suggestions), 5)


class TestServiceTimeSlowFlag(unittest.TestCase):
    """Tests for is_slow flag behavior."""

    @patch('utils.boot_analyzer.subprocess.run')
    def test_is_slow_true_for_services_above_threshold(self, mock_run):
        """is_slow is True for services >= 5 seconds."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="5.0s exactly-threshold.service\n"
        )

        services = BootAnalyzer.get_blame_data()

        self.assertEqual(len(services), 1)
        self.assertTrue(services[0].is_slow)

    @patch('utils.boot_analyzer.subprocess.run')
    def test_is_slow_false_for_services_below_threshold(self, mock_run):
        """is_slow is False for services < 5 seconds."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="4.9s below-threshold.service\n"
        )

        services = BootAnalyzer.get_blame_data()

        self.assertEqual(len(services), 1)
        self.assertFalse(services[0].is_slow)


if __name__ == '__main__':
    unittest.main()

"""
Tests for v9.3.0 "Clarity Update" changes.
Covers: centralized version, logging module, command_runner rename,
AI stop_service, and backward-compat shim.
"""
import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import logging
import importlib
import warnings

# Add source path to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))


class TestVersionModule(unittest.TestCase):
    """Test centralized version management."""

    def test_version_exists(self):
        from version import __version__
        self.assertIsNotNone(__version__)

    def test_version_is_current(self):
        from version import __version__
        self.assertEqual(__version__, "26.0.2")

    def test_version_codename(self):
        from version import __version_codename__
        self.assertEqual(__version_codename__, "Status Bar UI Hotfix")

    def test_app_name(self):
        from version import __app_name__
        self.assertEqual(__app_name__, "Loofi Fedora Tweaks")

    def test_version_format(self):
        """Version should follow semver format."""
        from version import __version__
        parts = __version__.split(".")
        self.assertEqual(len(parts), 3)
        for part in parts:
            self.assertTrue(part.isdigit(), f"Version part '{part}' is not a digit")


class TestLoggingModule(unittest.TestCase):
    """Test centralized logging configuration."""

    def test_get_logger_returns_logger(self):
        from utils.log import get_logger
        logger = get_logger("test_module")
        self.assertIsInstance(logger, logging.Logger)

    def test_logger_name_prefix(self):
        from utils.log import get_logger
        logger = get_logger("mymodule")
        self.assertTrue(logger.name.startswith("loofi"))

    def test_logger_already_prefixed(self):
        from utils.log import get_logger
        logger = get_logger("loofi.existing")
        self.assertEqual(logger.name, "loofi.existing")

    def test_different_loggers_distinct(self):
        from utils.log import get_logger
        logger_a = get_logger("module_a")
        logger_b = get_logger("module_b")
        self.assertNotEqual(logger_a.name, logger_b.name)

    def test_logger_can_log(self):
        from utils.log import get_logger
        logger = get_logger("test_can_log")
        # Should not raise
        logger.info("Test message")
        logger.debug("Debug message")
        logger.warning("Warning message")
        logger.error("Error message")


class TestCommandRunnerRename(unittest.TestCase):
    """Test that command_runner module works and old process shim still works."""

    def test_command_runner_importable(self):
        """New module should be importable."""
        from utils.command_runner import CommandRunner
        self.assertTrue(hasattr(CommandRunner, 'output_received'))

    def test_command_runner_has_signals(self):
        from utils.command_runner import CommandRunner
        self.assertTrue(hasattr(CommandRunner, 'finished'))
        self.assertTrue(hasattr(CommandRunner, 'error_occurred'))
        self.assertTrue(hasattr(CommandRunner, 'progress_update'))

    def test_backward_compat_shim(self):
        """Old import path should still work but emit deprecation warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            # Force reimport
            if 'utils.process' in sys.modules:
                del sys.modules['utils.process']
            from utils.process import CommandRunner
            self.assertTrue(len(w) >= 1)
            self.assertTrue(any(issubclass(warning.category, DeprecationWarning) for warning in w))


class TestOllamaStopService(unittest.TestCase):
    """Test the new stop_service method for Ollama."""

    @patch('utils.ai.OllamaManager.is_installed', return_value=False)
    def test_stop_when_not_installed(self, mock_installed):
        from utils.ai import OllamaManager
        result = OllamaManager.stop_service()
        self.assertFalse(result.success)
        self.assertIn("not installed", result.message)

    @patch('utils.ai.OllamaManager.is_running', return_value=False)
    @patch('utils.ai.OllamaManager.is_installed', return_value=True)
    def test_stop_when_already_stopped(self, mock_installed, mock_running):
        from utils.ai import OllamaManager
        result = OllamaManager.stop_service()
        self.assertTrue(result.success)
        self.assertIn("already stopped", result.message)

    @patch('subprocess.run')
    @patch('utils.ai.OllamaManager.is_running', return_value=True)
    @patch('utils.ai.OllamaManager.is_installed', return_value=True)
    def test_stop_via_systemctl(self, mock_installed, mock_running, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        from utils.ai import OllamaManager
        result = OllamaManager.stop_service()
        self.assertTrue(result.success)

    @patch('subprocess.run')
    @patch('utils.ai.OllamaManager.is_running', return_value=True)
    @patch('utils.ai.OllamaManager.is_installed', return_value=True)
    def test_stop_fallback_to_pkill(self, mock_installed, mock_running, mock_run):
        # systemctl fails, pkill succeeds
        mock_run.side_effect = [
            MagicMock(returncode=1),  # systemctl fails
            MagicMock(returncode=0),  # pkill succeeds
        ]
        from utils.ai import OllamaManager
        result = OllamaManager.stop_service()
        self.assertTrue(result.success)

    @patch('subprocess.run', side_effect=Exception("test error"))
    @patch('utils.ai.OllamaManager.is_running', return_value=True)
    @patch('utils.ai.OllamaManager.is_installed', return_value=True)
    def test_stop_handles_exception(self, mock_installed, mock_running, mock_run):
        from utils.ai import OllamaManager
        result = OllamaManager.stop_service()
        self.assertFalse(result.success)
        self.assertIn("Failed to stop", result.message)


if __name__ == "__main__":
    unittest.main()

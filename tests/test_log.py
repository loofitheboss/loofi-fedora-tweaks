"""Tests for utils/log.py — centralized logging configuration."""

import logging
import logging.handlers
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(
    __file__), '..', 'loofi-fedora-tweaks'))


class TestGetLogDir(unittest.TestCase):
    """Tests for _get_log_dir()."""

    @patch.dict(os.environ, {"XDG_STATE_HOME": ""}, clear=False)
    @patch("utils.log.Path.mkdir")
    @patch("utils.log.os.path.expanduser", return_value="/home/testuser/.local/state")
    def test_default_xdg_path(self, _mock_expand, mock_mkdir):
        from utils.log import _get_log_dir
        result = _get_log_dir()
        self.assertIn("loofi-fedora-tweaks", str(result))
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch.dict(os.environ, {"XDG_STATE_HOME": "/custom/state"}, clear=False)
    @patch("utils.log.Path.mkdir")
    def test_custom_xdg_path(self, mock_mkdir):
        from utils.log import _get_log_dir
        result = _get_log_dir()
        self.assertEqual(result, Path("/custom/state/loofi-fedora-tweaks"))
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)


class TestSetupRootLogger(unittest.TestCase):
    """Tests for _setup_root_logger()."""

    def setUp(self):
        import utils.log as log_module
        self._orig_initialized = log_module._initialized
        log_module._initialized = False

    def tearDown(self):
        import utils.log as log_module
        log_module._initialized = self._orig_initialized

    @patch("utils.log._get_log_dir")
    def test_setup_creates_handlers(self, mock_log_dir):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            mock_log_dir.return_value = Path(tmpdir)
            import utils.log as log_module
            log_module._initialized = False

            log_module._setup_root_logger()

            root = logging.getLogger("loofi")
            handler_types = [type(h) for h in root.handlers]
            self.assertIn(logging.StreamHandler, handler_types)
            self.assertTrue(log_module._initialized)

            for h in root.handlers[:]:
                if isinstance(h, logging.handlers.RotatingFileHandler):
                    root.removeHandler(h)
                    h.close()

    @patch("utils.log._get_log_dir")
    def test_setup_idempotent(self, mock_log_dir):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            mock_log_dir.return_value = Path(tmpdir)
            import utils.log as log_module
            log_module._initialized = False

            log_module._setup_root_logger()
            handler_count_first = len(logging.getLogger("loofi").handlers)

            log_module._setup_root_logger()
            handler_count_second = len(logging.getLogger("loofi").handlers)
            self.assertEqual(handler_count_first, handler_count_second)

            root = logging.getLogger("loofi")
            for h in root.handlers[:]:
                if isinstance(h, logging.handlers.RotatingFileHandler):
                    root.removeHandler(h)
                    h.close()

    @patch("utils.log.logging.handlers.RotatingFileHandler",
           side_effect=OSError("permission denied"))
    @patch("utils.log._get_log_dir", return_value=Path("/nonexistent"))
    def test_setup_continues_without_file_handler(self, _mock_dir, _mock_handler):
        import utils.log as log_module
        log_module._initialized = False

        log_module._setup_root_logger()
        self.assertTrue(log_module._initialized)


class TestGetLogger(unittest.TestCase):
    """Tests for get_logger()."""

    @patch("utils.log._setup_root_logger")
    def test_get_logger_returns_logger(self, _mock_setup):
        from utils.log import get_logger
        result = get_logger("test_module")
        self.assertIsInstance(result, logging.Logger)

    @patch("utils.log._setup_root_logger")
    def test_get_logger_prefixes_name(self, _mock_setup):
        from utils.log import get_logger
        result = get_logger("mymodule")
        self.assertEqual(result.name, "loofi.mymodule")

    @patch("utils.log._setup_root_logger")
    def test_get_logger_preserves_loofi_prefix(self, _mock_setup):
        from utils.log import get_logger
        result = get_logger("loofi.existing")
        self.assertEqual(result.name, "loofi.existing")

    @patch("utils.log._setup_root_logger")
    def test_get_logger_calls_setup(self, mock_setup):
        from utils.log import get_logger
        get_logger("any_module")
        mock_setup.assert_called_once()


if __name__ == "__main__":
    unittest.main()

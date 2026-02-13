"""
Shared pytest fixtures for Loofi Fedora Tweaks test suite.
Compatible with both pytest-style and unittest-style tests.

Provides reusable mocks for subprocess, filesystem, and tool detection
so that tests never touch the real system.
"""

import os
import sys
import tempfile
import shutil

# Force offscreen Qt rendering in CI (must be set before any PyQt6 import)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from unittest.mock import patch, MagicMock

# Ensure the app source is on the path for all test modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))


# ── Session-scoped QApplication singleton ──────────────────────────────
# Prevents multiple QApplication instances across test files, which causes
# Qt assertion crashes (IOT/abort) in PyQt6 offscreen mode.
_qapp_instance = None


@pytest.fixture(scope="session", autouse=True)
def qapp():
    """Ensure exactly one QApplication exists for the entire test session."""
    global _qapp_instance
    try:
        from PyQt6.QtWidgets import QApplication
        _qapp_instance = QApplication.instance()
        if _qapp_instance is None:
            _qapp_instance = QApplication([])
        yield _qapp_instance
    except ImportError:
        yield None


@pytest.fixture
def mock_subprocess():
    """Patch subprocess.run and subprocess.check_output with MagicMock.

    Returns a dict with keys 'run' and 'check_output' pointing to their
    respective MagicMock instances.  By default both return a successful
    CompletedProcess-like object.

    Usage (pytest-style):
        def test_something(mock_subprocess):
            mock_subprocess['run'].return_value.stdout = 'hello'
            ...

    Usage (unittest-style via request.getfixturevalue):
        result = self._mock_subprocess['run']
    """
    mock_run_obj = MagicMock()
    mock_run_obj.return_value = MagicMock(
        returncode=0, stdout="", stderr=""
    )

    mock_check_output_obj = MagicMock()
    mock_check_output_obj.return_value = ""

    with patch('subprocess.run', mock_run_obj), \
         patch('subprocess.check_output', mock_check_output_obj):
        yield {
            'run': mock_run_obj,
            'check_output': mock_check_output_obj,
        }


@pytest.fixture
def temp_config_dir():
    """Create a temporary directory simulating ~/.config/loofi-fedora-tweaks/.

    Yields the path to the temporary directory.  The directory and all its
    contents are removed after the test completes.
    """
    tmpdir = tempfile.mkdtemp(prefix="loofi-test-config-")
    config_dir = os.path.join(tmpdir, ".config", "loofi-fedora-tweaks")
    os.makedirs(config_dir, exist_ok=True)
    yield config_dir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def mock_which():
    """Patch shutil.which to control which tools appear installed.

    Yields a MagicMock whose return_value or side_effect can be set by
    the test.  The default is to return None (tool not found).

    Usage:
        def test_foo(mock_which):
            mock_which.return_value = '/usr/bin/flatpak'
            ...

        def test_bar(mock_which):
            mock_which.side_effect = lambda cmd: '/usr/bin/dnf' if cmd == 'dnf' else None
    """
    with patch('shutil.which') as mocked:
        mocked.return_value = None
        yield mocked


@pytest.fixture
def mock_file_exists():
    """Patch os.path.exists to control filesystem path checks.

    Yields a MagicMock whose side_effect can be set to a function that
    returns True/False for specific paths.  The default returns False
    for all paths.

    Usage:
        def test_atomic(mock_file_exists):
            mock_file_exists.side_effect = lambda p: p == '/run/ostree-booted'
            assert SystemManager.is_atomic()
    """
    with patch('os.path.exists') as mocked:
        mocked.return_value = False
        yield mocked

"""Tests for scripts/check_fedora_review.py."""

import importlib.util
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None, f"Failed to load spec from {path}"
    assert spec.loader is not None, f"Spec has no loader for {path}"
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@patch("subprocess.run")
@patch("shutil.which", return_value="/usr/bin/fedora-review")
def test_check_fedora_review_success(mock_which, mock_run):
    module = _load_module("check_fedora_review_success", Path("scripts/check_fedora_review.py"))
    mock_run.side_effect = [
        subprocess.CompletedProcess(
            args=["fedora-review", "-V"],
            returncode=0,
            stdout="fedora-review 0.9.0",
            stderr="",
        ),
        subprocess.CompletedProcess(
            args=["fedora-review", "-d"],
            returncode=0,
            stdout="Available checks",
            stderr="",
        ),
    ]

    ok, errors = module.check_fedora_review(timeout=15)

    assert mock_which.called
    assert ok
    assert errors == []
    assert mock_run.call_count == 2
    for call in mock_run.call_args_list:
        assert call.kwargs["timeout"] == 15
        assert call.kwargs["check"] is False
        assert call.kwargs["capture_output"] is True
        assert call.kwargs["text"] is True


@patch("subprocess.run")
@patch("shutil.which", return_value=None)
def test_check_fedora_review_binary_missing(mock_which, mock_run):
    module = _load_module("check_fedora_review_missing", Path("scripts/check_fedora_review.py"))

    ok, errors = module.check_fedora_review()

    assert mock_which.called
    assert not ok
    assert any("not found in PATH" in error for error in errors)
    assert any("dnf install -y fedora-review" in error for error in errors)
    mock_run.assert_not_called()


@patch("subprocess.run")
@patch("shutil.which", return_value="/usr/bin/fedora-review")
def test_check_fedora_review_command_failure(mock_which, mock_run):
    module = _load_module("check_fedora_review_failure", Path("scripts/check_fedora_review.py"))
    mock_run.side_effect = [
        subprocess.CompletedProcess(
            args=["fedora-review", "-V"],
            returncode=0,
            stdout="fedora-review 0.9.0",
            stderr="",
        ),
        subprocess.CompletedProcess(
            args=["fedora-review", "-d"],
            returncode=2,
            stdout="",
            stderr="probe failed",
        ),
    ]

    ok, errors = module.check_fedora_review()

    assert mock_which.called
    assert not ok
    assert any("check registry probe" in error for error in errors)
    assert any("probe failed" in error for error in errors)


@patch("subprocess.run")
@patch("shutil.which", return_value="/usr/bin/fedora-review")
def test_check_fedora_review_timeout(mock_which, mock_run):
    module = _load_module("check_fedora_review_timeout", Path("scripts/check_fedora_review.py"))
    mock_run.side_effect = [
        subprocess.CompletedProcess(
            args=["fedora-review", "-V"],
            returncode=0,
            stdout="fedora-review 0.9.0",
            stderr="",
        ),
        subprocess.TimeoutExpired(
            cmd=["fedora-review", "-d"],
            timeout=module.DEFAULT_TIMEOUT_SECONDS,
        ),
    ]

    ok, errors = module.check_fedora_review()

    assert mock_which.called
    assert not ok
    assert any("timed out" in error for error in errors)

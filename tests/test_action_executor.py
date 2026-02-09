"""
Tests for v19.0 Foundation — ActionResult + ActionExecutor.
"""

import json
import os
import tempfile
import time
import pytest
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))


class TestActionResult:
    """Test unified ActionResult schema."""

    def test_ok_convenience(self):
        from utils.action_result import ActionResult
        r = ActionResult.ok("All good", exit_code=0)
        assert r.success is True
        assert r.message == "All good"
        assert r.exit_code == 0

    def test_fail_convenience(self):
        from utils.action_result import ActionResult
        r = ActionResult.fail("Broke", exit_code=1)
        assert r.success is False
        assert r.exit_code == 1

    def test_previewed_convenience(self):
        from utils.action_result import ActionResult
        r = ActionResult.previewed("dnf", ["check-update"])
        assert r.preview is True
        assert r.success is True
        assert "[PREVIEW]" in r.message
        assert r.data["command"] == "dnf"
        assert r.data["args"] == ["check-update"]

    def test_auto_timestamp(self):
        from utils.action_result import ActionResult
        before = time.time()
        r = ActionResult.ok("test")
        assert r.timestamp >= before

    def test_to_dict_roundtrip(self):
        from utils.action_result import ActionResult
        r = ActionResult(
            success=True,
            message="hello",
            exit_code=0,
            stdout="out",
            stderr="err",
            data={"key": "val"},
            preview=False,
            needs_reboot=True,
            timestamp=1000.0,
            action_id="a1",
        )
        d = r.to_dict()
        r2 = ActionResult.from_dict(d)
        assert r2.success == r.success
        assert r2.message == r.message
        assert r2.exit_code == r.exit_code
        assert r2.stdout == r.stdout
        assert r2.stderr == r.stderr
        assert r2.data == r.data
        assert r2.preview == r.preview
        assert r2.needs_reboot == r.needs_reboot
        assert r2.timestamp == r.timestamp
        assert r2.action_id == r.action_id

    def test_truncation_in_to_dict(self):
        from utils.action_result import ActionResult
        r = ActionResult.ok("test", stdout="x" * 10000)
        d = r.to_dict()
        assert len(d["stdout"]) == ActionResult._MAX_OUTPUT

    def test_from_dict_defaults(self):
        from utils.action_result import ActionResult
        r = ActionResult.from_dict({})
        assert r.success is False
        assert r.message == ""
        assert r.preview is False


class TestActionExecutor:
    """Test centralized executor."""

    def test_preview_mode(self):
        from utils.action_executor import ActionExecutor
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("core.executor.action_executor._LOG_DIR", tmpdir), \
                 patch("core.executor.action_executor._ACTION_LOG_FILE", os.path.join(tmpdir, "log.jsonl")):
                result = ActionExecutor.run("echo", ["hello"], preview=True)
                assert result.preview is True
                assert result.success is True
                assert "echo" in result.message
                assert "hello" in result.message

    def test_global_dry_run(self):
        from utils.action_executor import ActionExecutor
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("core.executor.action_executor._LOG_DIR", tmpdir), \
                 patch("core.executor.action_executor._ACTION_LOG_FILE", os.path.join(tmpdir, "log.jsonl")):
                ActionExecutor.set_global_dry_run(True)
                try:
                    result = ActionExecutor.run("echo", ["test"])
                    assert result.preview is True
                    assert result.success is True
                finally:
                    ActionExecutor.set_global_dry_run(False)

    def test_successful_execution(self):
        from utils.action_executor import ActionExecutor
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("core.executor.action_executor._LOG_DIR", tmpdir), \
                 patch("core.executor.action_executor._ACTION_LOG_FILE", os.path.join(tmpdir, "log.jsonl")):
                result = ActionExecutor.run("echo", ["hello world"])
                assert result.success is True
                assert result.exit_code == 0
                assert "hello world" in result.stdout

    def test_failed_execution(self):
        from utils.action_executor import ActionExecutor
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("core.executor.action_executor._LOG_DIR", tmpdir), \
                 patch("core.executor.action_executor._ACTION_LOG_FILE", os.path.join(tmpdir, "log.jsonl")):
                result = ActionExecutor.run("false")
                assert result.success is False
                assert result.exit_code != 0

    def test_command_not_found(self):
        from utils.action_executor import ActionExecutor
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("core.executor.action_executor._LOG_DIR", tmpdir), \
                 patch("core.executor.action_executor._ACTION_LOG_FILE", os.path.join(tmpdir, "log.jsonl")):
                result = ActionExecutor.run("nonexistent_cmd_xyz_12345")
                assert result.success is False
                assert result.exit_code == 127
                assert "not found" in result.message.lower()

    def test_timeout(self):
        from utils.action_executor import ActionExecutor
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("core.executor.action_executor._LOG_DIR", tmpdir), \
                 patch("core.executor.action_executor._ACTION_LOG_FILE", os.path.join(tmpdir, "log.jsonl")):
                result = ActionExecutor.run("sleep", ["10"], timeout=1)
                assert result.success is False
                assert "timed out" in result.message.lower()

    def test_pkexec_prepend(self):
        from utils.action_executor import ActionExecutor
        cmd = ActionExecutor._build_command("dnf", ["clean", "all"], pkexec=True)
        assert cmd[0] == "pkexec"
        assert cmd[1] == "dnf"
        assert cmd[2:] == ["clean", "all"]

    def test_flatpak_wrapping(self):
        from utils.action_executor import ActionExecutor
        with patch("os.path.exists", return_value=True):
            cmd = ActionExecutor._build_command("dnf", ["check-update"])
            assert cmd[0] == "flatpak-spawn"
            assert cmd[1] == "--host"

    def test_flatpak_no_double_wrap(self):
        from utils.action_executor import ActionExecutor
        with patch("os.path.exists", return_value=True):
            cmd = ActionExecutor._build_command("flatpak-spawn", ["--host", "echo"])
            assert cmd[0] == "flatpak-spawn"
            # Should not double-wrap
            assert cmd.count("flatpak-spawn") == 1

    def test_action_id_propagation(self):
        from utils.action_executor import ActionExecutor
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("core.executor.action_executor._LOG_DIR", tmpdir), \
                 patch("core.executor.action_executor._ACTION_LOG_FILE", os.path.join(tmpdir, "log.jsonl")):
                result = ActionExecutor.run("echo", ["test"], action_id="op-123")
                assert result.action_id == "op-123"


class TestActionLog:
    """Test structured action logging."""

    def test_log_written(self):
        from utils.action_executor import ActionExecutor
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "log.jsonl")
            with patch("core.executor.action_executor._LOG_DIR", tmpdir), \
                 patch("core.executor.action_executor._ACTION_LOG_FILE", log_path):
                ActionExecutor.run("echo", ["logged"], preview=True)
                assert os.path.exists(log_path)
                with open(log_path) as fh:
                    entry = json.loads(fh.readline())
                assert entry["success"] is True
                assert entry["preview"] is True
                assert "echo" in entry["cmd"]

    def test_get_action_log(self):
        from utils.action_executor import ActionExecutor
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "log.jsonl")
            with patch("core.executor.action_executor._LOG_DIR", tmpdir), \
                 patch("core.executor.action_executor._ACTION_LOG_FILE", log_path):
                ActionExecutor.run("echo", ["one"], preview=True)
                ActionExecutor.run("echo", ["two"], preview=True)
                entries = ActionExecutor.get_action_log(limit=10)
                assert len(entries) == 2

    def test_log_trimming(self):
        from utils.action_executor import ActionExecutor, MAX_LOG_ENTRIES
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "log.jsonl")
            with patch("core.executor.action_executor._LOG_DIR", tmpdir), \
                 patch("core.executor.action_executor._ACTION_LOG_FILE", log_path):
                # Write more than MAX_LOG_ENTRIES
                with open(log_path, "w") as fh:
                    for i in range(MAX_LOG_ENTRIES + 100):
                        fh.write(json.dumps({"ts": i, "cmd": ["test"], "success": True}) + "\n")
                ActionExecutor._trim_log()
                with open(log_path) as fh:
                    lines = fh.readlines()
                assert len(lines) == MAX_LOG_ENTRIES

    def test_export_diagnostics(self):
        from utils.action_executor import ActionExecutor
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "log.jsonl")
            with patch("core.executor.action_executor._LOG_DIR", tmpdir), \
                 patch("core.executor.action_executor._ACTION_LOG_FILE", log_path):
                ActionExecutor.run("echo", ["diag"], preview=True)
                diag = ActionExecutor.export_diagnostics()
                assert diag["version"] == "19.0.0"
                assert "exported_at" in diag
                assert len(diag["action_log"]) >= 1

    def test_log_failure_does_not_crash(self):
        from utils.action_executor import ActionExecutor
        with patch("core.executor.action_executor._LOG_DIR", "/nonexistent/path"), \
             patch("core.executor.action_executor._ACTION_LOG_FILE", "/nonexistent/path/log.jsonl"):
            # Should not raise — logging failure is non-critical
            result = ActionExecutor.run("echo", ["safe"], preview=True)
            assert result.success is True


class TestOperationBridge:
    """Test operations.py execute_operation bridge."""

    def test_preview_operation(self):
        from utils.operations import execute_operation, CleanupOps
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("core.executor.action_executor._LOG_DIR", tmpdir), \
                 patch("core.executor.action_executor._ACTION_LOG_FILE", os.path.join(tmpdir, "log.jsonl")):
                result = execute_operation(CleanupOps.trim_ssd(), preview=True)
                assert result.preview is True
                assert result.success is True
                assert "fstrim" in result.message

    def test_pkexec_extraction(self):
        from utils.operations import execute_operation, CleanupOps
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("core.executor.action_executor._LOG_DIR", tmpdir), \
                 patch("core.executor.action_executor._ACTION_LOG_FILE", os.path.join(tmpdir, "log.jsonl")):
                result = execute_operation(CleanupOps.clean_dnf_cache(), preview=True)
                assert result.preview is True
                # Should have extracted pkexec and the real command
                assert "dnf" in result.message or "rpm-ostree" in result.message

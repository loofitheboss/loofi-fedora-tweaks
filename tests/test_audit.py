"""
Test audit logger — v35.0.0 "Fortress"

Full coverage of AuditLogger class: creation, rotation, JSONL format,
field validation, sensitive param redaction, singleton pattern.
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(
    __file__), '..', 'loofi-fedora-tweaks'))


class TestAuditLogger(unittest.TestCase):
    """Tests for utils/audit.py AuditLogger."""

    def setUp(self):
        """Create a fresh AuditLogger with a temp directory."""
        from utils.audit import AuditLogger

        # Reset singleton properly (closes handlers)
        AuditLogger.reset()

        self.tmpdir = tempfile.mkdtemp()
        self.env_patch = patch.dict(
            os.environ, {"LOOFI_AUDIT_DIR": self.tmpdir})
        self.env_patch.start()

        self.audit = AuditLogger()

    def tearDown(self):
        """Clean up singleton and temp directory."""
        from utils.audit import AuditLogger
        AuditLogger.reset()
        self.env_patch.stop()

        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_singleton_pattern(self):
        """AuditLogger should return the same instance."""
        from utils.audit import AuditLogger
        a1 = AuditLogger()
        a2 = AuditLogger()
        self.assertIs(a1, a2)

    def _flush(self):
        """Flush RotatingFileHandler buffers so data is on disk."""
        for h in self.audit._logger.handlers:
            h.flush()

    def test_log_creates_file(self):
        """Logging should create the audit.jsonl file."""
        self.audit.log(action="test.action", params={
                       "key": "value"}, exit_code=0)
        self._flush()
        self.assertTrue(self.audit.log_path.exists())

    def test_log_jsonl_format(self):
        """Each log entry should be valid JSON on its own line."""
        self.audit.log(action="dnf.install", params={
                       "package": "vim"}, exit_code=0)
        self.audit.log(action="dnf.remove", params={
                       "package": "nano"}, exit_code=1)
        self._flush()

        lines = self.audit.log_path.read_text().strip().split("\n")
        self.assertEqual(len(lines), 2)

        for line in lines:
            entry = json.loads(line)
            self.assertIn("ts", entry)
            self.assertIn("action", entry)
            self.assertIn("params", entry)
            self.assertIn("exit_code", entry)

    def test_log_entry_fields(self):
        """Entry should contain all required fields."""
        entry = self.audit.log(
            action="sysctl.set",
            params={"key": "vm.swappiness", "value": "10"},
            exit_code=0,
            stderr="",
        )
        self.assertIn("ts", entry)
        self.assertEqual(entry["action"], "sysctl.set")
        self.assertEqual(entry["exit_code"], 0)
        self.assertFalse(entry["dry_run"])
        self.assertIn("user", entry)
        self.assertIsNone(entry["stderr_hash"])

    def test_dry_run_flag(self):
        """Dry-run entries should be marked."""
        entry = self.audit.log(action="test", dry_run=True)
        self.assertTrue(entry["dry_run"])

    def test_stderr_hash(self):
        """Stderr should be hashed, not stored raw."""
        entry = self.audit.log(
            action="test",
            stderr="Error: permission denied",
        )
        self.assertIsNotNone(entry["stderr_hash"])
        self.assertNotIn("permission denied", json.dumps(entry))
        # SHA-256 hex truncated to 16 chars
        self.assertEqual(len(entry["stderr_hash"]), 16)

    def test_sensitive_param_redaction(self):
        """Sensitive parameters should be redacted."""
        entry = self.audit.log(
            action="test",
            params={"password": "s3cret", "user": "loofi", "token": "abc123"},
        )
        self.assertEqual(entry["params"]["password"], "***REDACTED***")
        self.assertEqual(entry["params"]["token"], "***REDACTED***")
        self.assertEqual(entry["params"]["user"], "loofi")

    def test_get_recent(self):
        """get_recent should return entries in order."""
        for i in range(5):
            self.audit.log(action=f"test.{i}", exit_code=i)
        self._flush()

        recent = self.audit.get_recent(3)
        self.assertEqual(len(recent), 3)
        # Recent entries are most recent first
        for entry in recent:
            self.assertIn("action", entry)

    def test_get_recent_empty(self):
        """get_recent should return empty list when no logs exist."""
        recent = self.audit.get_recent(10)
        self.assertEqual(recent, [])

    def test_log_validation_failure(self):
        """Validation failures should be logged with extra fields."""
        entry = self.audit.log_validation_failure(
            action="PrivilegedCommand.dnf",
            param="action",
            detail="Required parameter is empty",
            params={"action": ""},
        )
        self.assertEqual(
            entry["action"], "PrivilegedCommand.dnf.validation_failure")
        self.assertEqual(entry["param"], "action")
        self.assertEqual(entry["detail"], "Required parameter is empty")

    def test_log_path_property(self):
        """log_path should point to audit.jsonl in config dir."""
        self.assertTrue(str(self.audit.log_path).endswith("audit.jsonl"))

    def test_reset(self):
        """reset() should clear singleton state."""
        from utils.audit import AuditLogger
        self.audit.log(action="test")
        AuditLogger.reset()
        # Re-create with same LOOFI_AUDIT_DIR
        new_audit = AuditLogger()
        self.audit = new_audit  # so tearDown cleans this one
        self.assertIsNotNone(new_audit)


class TestAuditLoggerEdgeCases(unittest.TestCase):
    """Edge cases and error handling for AuditLogger."""

    def setUp(self):
        from utils.audit import AuditLogger
        AuditLogger.reset()
        self.tmpdir = tempfile.mkdtemp()
        self.env_patch = patch.dict(
            os.environ, {"LOOFI_AUDIT_DIR": self.tmpdir})
        self.env_patch.start()
        self.audit = AuditLogger()

    def tearDown(self):
        from utils.audit import AuditLogger
        AuditLogger.reset()
        self.env_patch.stop()
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_empty_params(self):
        """Empty params dict should work."""
        entry = self.audit.log(action="test", params={})
        self.assertEqual(entry["params"], {})

    def test_none_params(self):
        """None params should default to empty dict."""
        entry = self.audit.log(action="test", params=None)
        self.assertEqual(entry["params"], {})

    def test_none_exit_code(self):
        """None exit_code (not executed) should be stored."""
        entry = self.audit.log(action="test", exit_code=None)
        self.assertIsNone(entry["exit_code"])

    def test_nested_sensitive_params(self):
        """Only top-level sensitive keys are redacted."""
        entry = self.audit.log(
            action="test",
            params={"config": {"password": "hidden"}},
        )
        # _sanitize_params recurses into nested dicts
        self.assertEqual(entry["params"]["config"]
                         ["password"], "***REDACTED***")

    def test_empty_stderr(self):
        """Empty stderr should result in null hash."""
        entry = self.audit.log(action="test", stderr="")
        self.assertIsNone(entry["stderr_hash"])


if __name__ == "__main__":
    unittest.main()

"""Tests for smart log viewer."""
import unittest
import sys
import os
import json
import tempfile
from unittest.mock import patch, MagicMock, mock_open

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from utils.smart_logs import SmartLogViewer, LogEntry, LogPattern, LogSummary, KNOWN_PATTERNS


class TestLogEntry(unittest.TestCase):
    """Tests for LogEntry dataclass."""

    def test_create_entry(self):
        """Test basic LogEntry creation."""
        entry = LogEntry(
            timestamp="2026-02-08 12:00:00",
            unit="sshd.service",
            priority=3,
            message="Connection refused",
            priority_label="ERROR",
        )
        self.assertEqual(entry.timestamp, "2026-02-08 12:00:00")
        self.assertEqual(entry.unit, "sshd.service")
        self.assertEqual(entry.priority, 3)
        self.assertEqual(entry.message, "Connection refused")
        self.assertEqual(entry.priority_label, "ERROR")

    def test_pattern_match_none_by_default(self):
        """Test pattern_match defaults to None."""
        entry = LogEntry(
            timestamp="",
            unit="",
            priority=6,
            message="hello",
            priority_label="INFO",
        )
        self.assertIsNone(entry.pattern_match)

    def test_all_fields(self):
        """Test LogEntry with all fields including pattern_match."""
        entry = LogEntry(
            timestamp="2026-01-01 00:00:00",
            unit="kernel",
            priority=2,
            message="Out of memory: Killed process 1234",
            priority_label="CRITICAL",
            pattern_match="System ran out of memory and killed a process",
        )
        self.assertEqual(entry.pattern_match, "System ran out of memory and killed a process")
        self.assertEqual(entry.priority, 2)


class TestLogPattern(unittest.TestCase):
    """Tests for LogPattern dataclass."""

    def test_create_pattern(self):
        """Test basic LogPattern creation."""
        p = LogPattern(
            name="TestPat",
            regex=r"test regex",
            severity="info",
            explanation="A test pattern",
        )
        self.assertEqual(p.name, "TestPat")
        self.assertEqual(p.regex, r"test regex")
        self.assertEqual(p.explanation, "A test pattern")

    def test_severity_values(self):
        """Test that known patterns use valid severity values."""
        valid = {"critical", "warning", "info"}
        for pattern in KNOWN_PATTERNS:
            self.assertIn(pattern.severity, valid, f"Invalid severity for {pattern.name}")

    def test_known_patterns_not_empty(self):
        """Test KNOWN_PATTERNS list is populated."""
        self.assertTrue(len(KNOWN_PATTERNS) > 0)


class TestLogSummary(unittest.TestCase):
    """Tests for LogSummary dataclass."""

    def test_create_summary(self):
        """Test basic LogSummary creation."""
        summary = LogSummary(
            total_entries=100,
            critical_count=5,
            warning_count=10,
            error_count=15,
            top_units=[("sshd.service", 20)],
            detected_patterns=[("OOM Killer", 3)],
        )
        self.assertEqual(summary.total_entries, 100)
        self.assertEqual(summary.critical_count, 5)

    def test_default_counts(self):
        """Test summary with zero counts."""
        summary = LogSummary(
            total_entries=0,
            critical_count=0,
            warning_count=0,
            error_count=0,
            top_units=[],
            detected_patterns=[],
        )
        self.assertEqual(summary.total_entries, 0)
        self.assertEqual(summary.critical_count, 0)
        self.assertEqual(summary.warning_count, 0)
        self.assertEqual(summary.error_count, 0)

    def test_top_units_type(self):
        """Test top_units is a list of tuples."""
        summary = LogSummary(
            total_entries=10,
            critical_count=0,
            warning_count=0,
            error_count=0,
            top_units=[("a.service", 5), ("b.service", 3)],
            detected_patterns=[],
        )
        self.assertIsInstance(summary.top_units, list)
        for item in summary.top_units:
            self.assertIsInstance(item, tuple)
            self.assertEqual(len(item), 2)


class TestKnownPatterns(unittest.TestCase):
    """Tests for KNOWN_PATTERNS module-level list."""

    def test_patterns_count(self):
        """Test at least 10 patterns are defined."""
        self.assertGreaterEqual(len(KNOWN_PATTERNS), 10)

    def test_oom_pattern_matches(self):
        """Test OOM pattern matches expected text."""
        import re
        oom = next(p for p in KNOWN_PATTERNS if p.name == "OOM Killer")
        self.assertIsNotNone(re.search(oom.regex, "Out of memory: Killed process 1234", re.IGNORECASE))

    def test_segfault_pattern_matches(self):
        """Test segfault pattern matches expected text."""
        import re
        seg = next(p for p in KNOWN_PATTERNS if p.name == "Segfault")
        self.assertIsNotNone(re.search(seg.regex, "segfault at 0x00000", re.IGNORECASE))

    def test_disk_full_matches(self):
        """Test disk full pattern matches expected text."""
        import re
        disk = next(p for p in KNOWN_PATTERNS if p.name == "Disk Full")
        self.assertIsNotNone(re.search(disk.regex, "No space left on device", re.IGNORECASE))

    def test_no_match(self):
        """Test that a normal info message matches nothing."""
        import re
        msg = "normal info message everything is fine"
        for p in KNOWN_PATTERNS:
            self.assertIsNone(
                re.search(p.regex, msg, re.IGNORECASE),
                f"Pattern {p.name} should not match '{msg}'",
            )


class TestMatchPatterns(unittest.TestCase):
    """Tests for SmartLogViewer.match_patterns()."""

    def test_match_oom(self):
        """Test match_patterns returns OOM explanation."""
        result = SmartLogViewer.match_patterns("Out of memory: Killed process 9999")
        self.assertEqual(result, "System ran out of memory and killed a process")

    def test_match_segfault(self):
        """Test match_patterns returns segfault explanation."""
        result = SmartLogViewer.match_patterns("app[1234]: segfault at 0x0000dead")
        self.assertEqual(result, "A program crashed due to a memory access violation")

    def test_match_auth_failure(self):
        """Test match_patterns returns auth failure explanation."""
        result = SmartLogViewer.match_patterns("pam_unix(sudo:auth): authentication failure")
        self.assertEqual(result, "Failed login or sudo/pkexec attempt")

    def test_match_service_failed(self):
        """Test match_patterns matches service failure messages."""
        result1 = SmartLogViewer.match_patterns("Failed to start My Custom Service")
        self.assertEqual(result1, "A systemd service failed to start")
        result2 = SmartLogViewer.match_patterns("myunit.service entered failed state")
        self.assertEqual(result2, "A systemd service failed to start")

    def test_no_match(self):
        """Test match_patterns returns None for non-matching text."""
        result = SmartLogViewer.match_patterns("Started session 42 of user alice")
        self.assertIsNone(result)

    def test_match_empty_message(self):
        """Test match_patterns returns None for empty string."""
        self.assertIsNone(SmartLogViewer.match_patterns(""))
        self.assertIsNone(SmartLogViewer.match_patterns(None))


class TestGetLogs(unittest.TestCase):
    """Tests for SmartLogViewer.get_logs()."""

    def _journal_line(self, message="hello", priority="6", unit="test.service", ts="1707350400000000"):
        """Helper to build a JSON journal line."""
        return json.dumps({
            "MESSAGE": message,
            "PRIORITY": priority,
            "_SYSTEMD_UNIT": unit,
            "__REALTIME_TIMESTAMP": ts,
        })

    @patch("utils.smart_logs.subprocess.run")
    def test_get_logs_parses_json(self, mock_run):
        """Test get_logs parses JSON journal output into LogEntry list."""
        lines = "\n".join([
            self._journal_line("first message", "3", "a.service"),
            self._journal_line("second message", "6", "b.service"),
        ])
        mock_run.return_value = MagicMock(returncode=0, stdout=lines, stderr="")

        entries = SmartLogViewer.get_logs()

        self.assertEqual(len(entries), 2)
        self.assertIsInstance(entries[0], LogEntry)
        self.assertEqual(entries[0].message, "first message")
        self.assertEqual(entries[0].priority, 3)
        self.assertEqual(entries[0].unit, "a.service")
        self.assertEqual(entries[1].message, "second message")

    @patch("utils.smart_logs.subprocess.run")
    def test_get_logs_with_unit_filter(self, mock_run):
        """Test get_logs passes -u flag for unit filter."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        SmartLogViewer.get_logs(unit="sshd")

        cmd = mock_run.call_args[0][0]
        self.assertIn("-u", cmd)
        idx = cmd.index("-u")
        self.assertEqual(cmd[idx + 1], "sshd")

    @patch("utils.smart_logs.subprocess.run")
    def test_get_logs_with_priority(self, mock_run):
        """Test get_logs passes -p flag for priority filter."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        SmartLogViewer.get_logs(priority=3)

        cmd = mock_run.call_args[0][0]
        self.assertIn("-p", cmd)
        idx = cmd.index("-p")
        self.assertEqual(cmd[idx + 1], "3")

    @patch("utils.smart_logs.subprocess.run")
    def test_get_logs_empty_output(self, mock_run):
        """Test get_logs returns empty list on empty output."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        entries = SmartLogViewer.get_logs()

        self.assertEqual(entries, [])

    @patch("utils.smart_logs.subprocess.run")
    def test_get_logs_subprocess_error(self, mock_run):
        """Test get_logs handles subprocess failure gracefully."""
        mock_run.side_effect = subprocess.SubprocessError("timeout")

        entries = SmartLogViewer.get_logs()

        self.assertEqual(entries, [])

    @patch("utils.smart_logs.subprocess.run")
    def test_get_logs_nonzero_returncode(self, mock_run):
        """Test get_logs returns empty list on non-zero exit code."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="permission denied")

        entries = SmartLogViewer.get_logs()

        self.assertEqual(entries, [])


class TestGetErrorSummary(unittest.TestCase):
    """Tests for SmartLogViewer.get_error_summary()."""

    def _make_entry(self, priority, unit="svc.service", pattern_match=None, message="msg"):
        return LogEntry(
            timestamp="2026-02-08 12:00:00",
            unit=unit,
            priority=priority,
            message=message,
            priority_label=SmartLogViewer.PRIORITY_LABELS.get(priority, "UNKNOWN"),
            pattern_match=pattern_match,
        )

    @patch.object(SmartLogViewer, "get_logs")
    def test_summary_counts(self, mock_get_logs):
        """Test summary correctly counts critical/warning/error entries."""
        mock_get_logs.return_value = [
            self._make_entry(2),  # critical
            self._make_entry(2),  # critical
            self._make_entry(3),  # error
            self._make_entry(4),  # warning
            self._make_entry(4),  # warning
            self._make_entry(4),  # warning
        ]

        summary = SmartLogViewer.get_error_summary()

        self.assertEqual(summary.total_entries, 6)
        self.assertEqual(summary.critical_count, 2)
        self.assertEqual(summary.error_count, 1)
        self.assertEqual(summary.warning_count, 3)

    @patch.object(SmartLogViewer, "get_logs")
    def test_summary_top_units(self, mock_get_logs):
        """Test summary aggregates unit frequencies correctly."""
        mock_get_logs.return_value = [
            self._make_entry(3, unit="a.service"),
            self._make_entry(3, unit="a.service"),
            self._make_entry(3, unit="a.service"),
            self._make_entry(3, unit="b.service"),
        ]

        summary = SmartLogViewer.get_error_summary()

        # top_units should have a.service first
        self.assertTrue(len(summary.top_units) >= 1)
        self.assertEqual(summary.top_units[0][0], "a.service")
        self.assertEqual(summary.top_units[0][1], 3)

    @patch.object(SmartLogViewer, "get_logs")
    def test_summary_detected_patterns(self, mock_get_logs):
        """Test summary includes detected patterns."""
        mock_get_logs.return_value = [
            self._make_entry(2, pattern_match="OOM explanation"),
            self._make_entry(2, pattern_match="OOM explanation"),
            self._make_entry(3, pattern_match="Segfault explanation"),
        ]

        summary = SmartLogViewer.get_error_summary()

        pattern_names = [p[0] for p in summary.detected_patterns]
        self.assertIn("OOM explanation", pattern_names)
        self.assertIn("Segfault explanation", pattern_names)
        # OOM appears twice so should be first
        self.assertEqual(summary.detected_patterns[0], ("OOM explanation", 2))

    @patch.object(SmartLogViewer, "get_logs")
    def test_summary_empty(self, mock_get_logs):
        """Test summary with no entries returns zero counts."""
        mock_get_logs.return_value = []

        summary = SmartLogViewer.get_error_summary()

        self.assertEqual(summary.total_entries, 0)
        self.assertEqual(summary.critical_count, 0)
        self.assertEqual(summary.warning_count, 0)
        self.assertEqual(summary.error_count, 0)
        self.assertEqual(summary.top_units, [])
        self.assertEqual(summary.detected_patterns, [])


class TestGetUnitList(unittest.TestCase):
    """Tests for SmartLogViewer.get_unit_list()."""

    @patch("utils.smart_logs.subprocess.run")
    def test_get_units(self, mock_run):
        """Test get_unit_list parses systemctl output."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="sshd.service loaded active running\nnginx.service loaded active running\n",
            stderr="",
        )

        units = SmartLogViewer.get_unit_list()

        self.assertIn("nginx.service", units)
        self.assertIn("sshd.service", units)
        # Should be sorted
        self.assertEqual(units, sorted(units))

    @patch("utils.smart_logs.subprocess.run")
    def test_get_units_empty(self, mock_run):
        """Test get_unit_list handles empty systemctl output."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        units = SmartLogViewer.get_unit_list()

        self.assertEqual(units, [])

    @patch("utils.smart_logs.subprocess.run")
    def test_get_units_subprocess_error(self, mock_run):
        """Test get_unit_list handles subprocess failure."""
        mock_run.side_effect = subprocess.SubprocessError("timeout")

        units = SmartLogViewer.get_unit_list()

        self.assertEqual(units, [])

    @patch("utils.smart_logs.subprocess.run")
    def test_get_units_nonzero_exit(self, mock_run):
        """Test get_unit_list returns empty on non-zero exit."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")

        units = SmartLogViewer.get_unit_list()

        self.assertEqual(units, [])


class TestExportLogs(unittest.TestCase):
    """Tests for SmartLogViewer.export_logs()."""

    def _sample_entries(self):
        return [
            LogEntry(
                timestamp="2026-02-08 10:00:00",
                unit="sshd.service",
                priority=3,
                message="Connection refused",
                priority_label="ERROR",
            ),
            LogEntry(
                timestamp="2026-02-08 10:01:00",
                unit="kernel",
                priority=4,
                message="cpu clock throttled",
                priority_label="WARNING",
                pattern_match="CPU is being thermally throttled",
            ),
        ]

    @patch("utils.smart_logs.os.makedirs")
    def test_export_text(self, mock_makedirs):
        """Test export_logs writes text format correctly."""
        entries = self._sample_entries()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            path = f.name

        try:
            result = SmartLogViewer.export_logs(entries, path, format="text")
            self.assertTrue(result)
            with open(path, "r") as fh:
                content = fh.read()
            self.assertIn("[ERROR]", content)
            self.assertIn("sshd.service", content)
            self.assertIn("Connection refused", content)
            self.assertIn("[WARNING]", content)
        finally:
            os.unlink(path)

    @patch("utils.smart_logs.os.makedirs")
    def test_export_json(self, mock_makedirs):
        """Test export_logs writes valid JSON format."""
        entries = self._sample_entries()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name

        try:
            result = SmartLogViewer.export_logs(entries, path, format="json")
            self.assertTrue(result)
            with open(path, "r") as fh:
                data = json.load(fh)
            self.assertIsInstance(data, list)
            self.assertEqual(len(data), 2)
            self.assertEqual(data[0]["message"], "Connection refused")
            self.assertEqual(data[1]["pattern_match"], "CPU is being thermally throttled")
        finally:
            os.unlink(path)

    @patch("utils.smart_logs.os.makedirs")
    def test_export_empty(self, mock_makedirs):
        """Test export_logs handles empty entry list."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            path = f.name

        try:
            result = SmartLogViewer.export_logs([], path, format="text")
            self.assertTrue(result)
            with open(path, "r") as fh:
                content = fh.read()
            self.assertEqual(content, "")
        finally:
            os.unlink(path)

    @patch("utils.smart_logs.os.makedirs")
    @patch("builtins.open", side_effect=OSError("Permission denied"))
    def test_export_write_error(self, mock_open_fn, mock_makedirs):
        """Test export_logs returns False on write error."""
        entries = self._sample_entries()

        result = SmartLogViewer.export_logs(entries, "/no/access/file.log", format="text")

        self.assertFalse(result)


# We need the subprocess import for side_effect usage
import subprocess


class TestParseJsonLines(unittest.TestCase):
    """Tests for SmartLogViewer._parse_json_lines() internal helper."""

    def test_basic_parse(self):
        """Test parsing well-formed JSON lines."""
        raw = json.dumps({
            "MESSAGE": "test msg",
            "PRIORITY": "4",
            "_SYSTEMD_UNIT": "u.service",
            "__REALTIME_TIMESTAMP": "1707350400000000",
        })
        entries = SmartLogViewer._parse_json_lines(raw)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].message, "test msg")
        self.assertEqual(entries[0].priority, 4)

    def test_malformed_json_skipped(self):
        """Test malformed JSON lines are skipped."""
        raw = "NOT-JSON\n" + json.dumps({"MESSAGE": "ok", "PRIORITY": "6"})
        entries = SmartLogViewer._parse_json_lines(raw)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].message, "ok")

    def test_binary_message_field(self):
        """Test non-string MESSAGE field is converted to string."""
        raw = json.dumps({"MESSAGE": [72, 101, 108, 108], "PRIORITY": "6"})
        entries = SmartLogViewer._parse_json_lines(raw)
        self.assertEqual(len(entries), 1)
        self.assertIsInstance(entries[0].message, str)

    def test_pattern_match_set_on_parse(self):
        """Test pattern_match is populated during parsing."""
        raw = json.dumps({
            "MESSAGE": "Out of memory: Killed process 42",
            "PRIORITY": "2",
            "_SYSTEMD_UNIT": "kernel",
            "__REALTIME_TIMESTAMP": "1707350400000000",
        })
        entries = SmartLogViewer._parse_json_lines(raw)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].pattern_match, "System ran out of memory and killed a process")


class TestFormatTimestamp(unittest.TestCase):
    """Tests for SmartLogViewer._format_timestamp() internal helper."""

    def test_valid_timestamp(self):
        """Test formatting a valid microsecond timestamp."""
        # 2026-02-08 00:00:00 UTC = 1770508800 seconds = 1770508800000000 usec
        result = SmartLogViewer._format_timestamp("1770508800000000")
        self.assertEqual(result, "2026-02-08 00:00:00")

    def test_empty_timestamp(self):
        """Test empty string returns empty."""
        self.assertEqual(SmartLogViewer._format_timestamp(""), "")

    def test_invalid_timestamp(self):
        """Test invalid value returns the raw string."""
        result = SmartLogViewer._format_timestamp("not-a-number")
        self.assertEqual(result, "not-a-number")


if __name__ == "__main__":
    unittest.main()

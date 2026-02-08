"""
Smart Log Viewer utilities.
Part of v15.0 "Nebula" update.

Provides structured journalctl access with pattern detection,
error summarization, and export capabilities. Builds on the
journal.py foundation with JSON parsing and known-issue matching.
"""

import json
import logging
import os
import re
import subprocess
from collections import Counter
from dataclasses import dataclass, asdict
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class LogEntry:
    """A single parsed journal log entry."""
    timestamp: str
    unit: str
    priority: int
    message: str
    priority_label: str
    pattern_match: Optional[str] = None


@dataclass
class LogPattern:
    """A known log pattern with explanation."""
    name: str
    regex: str
    severity: str          # "critical" | "warning" | "info"
    explanation: str


@dataclass
class LogSummary:
    """Aggregate summary of log entries."""
    total_entries: int
    critical_count: int
    warning_count: int
    error_count: int
    top_units: List[Tuple[str, int]]
    detected_patterns: List[Tuple[str, int]]


# ---------------------------------------------------------------------------
# Known patterns — compiled once at module level
# ---------------------------------------------------------------------------

KNOWN_PATTERNS: List[LogPattern] = [
    LogPattern(
        name="OOM Killer",
        regex=r"Out of memory: Killed process",
        severity="critical",
        explanation="System ran out of memory and killed a process",
    ),
    LogPattern(
        name="Segfault",
        regex=r"segfault at",
        severity="critical",
        explanation="A program crashed due to a memory access violation",
    ),
    LogPattern(
        name="Disk Full",
        regex=r"No space left on device",
        severity="critical",
        explanation="A disk partition is full",
    ),
    LogPattern(
        name="Auth Failure",
        regex=r"authentication failure",
        severity="warning",
        explanation="Failed login or sudo/pkexec attempt",
    ),
    LogPattern(
        name="Service Failed",
        regex=r"Failed to start|entered failed state",
        severity="warning",
        explanation="A systemd service failed to start",
    ),
    LogPattern(
        name="USB Disconnect",
        regex=r"USB disconnect",
        severity="info",
        explanation="A USB device was disconnected",
    ),
    LogPattern(
        name="Kernel Panic",
        regex=r"Kernel panic",
        severity="critical",
        explanation="System experienced a kernel panic",
    ),
    LogPattern(
        name="NetworkManager Down",
        regex=r"NetworkManager.*deactivating",
        severity="warning",
        explanation="Network connection was deactivated",
    ),
    LogPattern(
        name="Thermal Throttle",
        regex=r"cpu clock throttled",
        severity="warning",
        explanation="CPU is being thermally throttled",
    ),
    LogPattern(
        name="Firmware Error",
        regex=r"firmware bug",
        severity="warning",
        explanation="Firmware reported an error",
    ),
]

# Pre-compile all pattern regexes for efficient reuse
_COMPILED_PATTERNS: List[Tuple[LogPattern, re.Pattern]] = [
    (p, re.compile(p.regex, re.IGNORECASE)) for p in KNOWN_PATTERNS
]


# ---------------------------------------------------------------------------
# SmartLogViewer
# ---------------------------------------------------------------------------

class SmartLogViewer:
    """
    Structured journalctl wrapper with pattern detection and export.

    All methods are static — no instance state required.  Every subprocess
    call uses an argument list (never ``shell=True``) and handles errors
    gracefully.
    """

    PRIORITY_LABELS = {
        0: "EMERG",
        1: "ALERT",
        2: "CRITICAL",
        3: "ERROR",
        4: "WARNING",
        5: "NOTICE",
        6: "INFO",
        7: "DEBUG",
    }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def get_logs(
        unit: Optional[str] = None,
        priority: Optional[int] = None,
        since: Optional[str] = None,
        lines: int = 100,
        grep: Optional[str] = None,
    ) -> List[LogEntry]:
        """
        Retrieve journal log entries as structured :class:`LogEntry` objects.

        Args:
            unit: Restrict to a specific systemd unit (e.g. ``"sshd"``).
            priority: Maximum priority level (0 = emerg … 7 = debug).
            since: Time specification passed to ``--since`` (e.g.
                ``"1 hour ago"``, ``"today"``).
            lines: Maximum number of journal lines to fetch.
            grep: Optional message grep filter (``--grep``).

        Returns:
            List of :class:`LogEntry`.  Empty list on any error.
        """
        cmd = ["journalctl", "--output=json", "--no-pager", "-n", str(lines)]

        if unit:
            cmd.extend(["-u", unit])
        if priority is not None:
            cmd.extend(["-p", str(priority)])
        if since:
            cmd.extend(["--since", since])
        if grep:
            cmd.extend(["--grep", grep])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                logger.debug(
                    "journalctl returned %d: %s", result.returncode, result.stderr
                )
                return []

            return SmartLogViewer._parse_json_lines(result.stdout)

        except subprocess.SubprocessError as e:
            logger.debug("Failed to run journalctl: %s", e)
            return []
        except OSError as e:
            logger.debug("OS error running journalctl: %s", e)
            return []

    @staticmethod
    def get_error_summary(since: str = "24h ago") -> LogSummary:
        """
        Produce an error summary for the given time window.

        Fetches log entries with priority <= 4 (warning and above) and
        aggregates them into a :class:`LogSummary`.

        Args:
            since: Time specification (default ``"24h ago"``).

        Returns:
            A :class:`LogSummary` instance.  Counts will be zero on error.
        """
        entries = SmartLogViewer.get_logs(priority=4, since=since, lines=5000)

        critical_count = 0
        warning_count = 0
        error_count = 0
        unit_counter: Counter = Counter()
        pattern_counter: Counter = Counter()

        for entry in entries:
            if entry.priority <= 2:
                critical_count += 1
            elif entry.priority == 3:
                error_count += 1
            elif entry.priority == 4:
                warning_count += 1

            if entry.unit:
                unit_counter[entry.unit] += 1

            if entry.pattern_match:
                pattern_counter[entry.pattern_match] += 1

        return LogSummary(
            total_entries=len(entries),
            critical_count=critical_count,
            warning_count=warning_count,
            error_count=error_count,
            top_units=unit_counter.most_common(5),
            detected_patterns=pattern_counter.most_common(),
        )

    @staticmethod
    def match_patterns(message: str) -> Optional[str]:
        """
        Match a log message against :data:`KNOWN_PATTERNS`.

        Args:
            message: The log message text.

        Returns:
            The pattern's *explanation* string if matched, otherwise ``None``.
        """
        if not message:
            return None
        for pattern, compiled in _COMPILED_PATTERNS:
            if compiled.search(message):
                return pattern.explanation
        return None

    @staticmethod
    def get_unit_list() -> List[str]:
        """
        Return a sorted list of active systemd unit names.

        Uses ``systemctl list-units`` with plain output.

        Returns:
            Sorted list of unit name strings.  Empty on error.
        """
        try:
            result = subprocess.run(
                [
                    "systemctl",
                    "list-units",
                    "--no-pager",
                    "--plain",
                    "--no-legend",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                logger.debug(
                    "systemctl list-units failed: %s", result.stderr
                )
                return []

            units: List[str] = []
            for line in result.stdout.strip().splitlines():
                parts = line.split()
                if parts:
                    units.append(parts[0])

            return sorted(units)

        except subprocess.SubprocessError as e:
            logger.debug("Failed to list units: %s", e)
            return []
        except OSError as e:
            logger.debug("OS error listing units: %s", e)
            return []

    @staticmethod
    def export_logs(
        entries: List[LogEntry],
        filepath: str,
        format: str = "text",
    ) -> bool:
        """
        Export log entries to a file.

        Args:
            entries: The log entries to export.
            filepath: Destination file path.
            format: ``"text"`` (one line per entry) or ``"json"`` (list of
                dicts).

        Returns:
            ``True`` on success, ``False`` on failure.
        """
        try:
            # Ensure parent directory exists
            parent = os.path.dirname(filepath)
            if parent:
                os.makedirs(parent, exist_ok=True)

            if format == "json":
                data = [asdict(e) for e in entries]
                with open(filepath, "w", encoding="utf-8") as fh:
                    json.dump(data, fh, indent=2, ensure_ascii=False)
            else:
                with open(filepath, "w", encoding="utf-8") as fh:
                    for entry in entries:
                        fh.write(
                            f"{entry.timestamp} [{entry.priority_label}] "
                            f"{entry.unit}: {entry.message}\n"
                        )

            logger.debug("Exported %d entries to %s", len(entries), filepath)
            return True

        except OSError as e:
            logger.debug("Failed to export logs to %s: %s", filepath, e)
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_json_lines(raw: str) -> List[LogEntry]:
        """Parse newline-delimited JSON journal output into LogEntry list."""
        entries: List[LogEntry] = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                logger.debug("Skipping malformed JSON line: %.80s", line)
                continue

            # Defensive field extraction — journalctl JSON keys are
            # upper-case (e.g. MESSAGE, _SYSTEMD_UNIT, PRIORITY,
            # __REALTIME_TIMESTAMP).
            message = obj.get("MESSAGE", "")
            if not isinstance(message, str):
                # MESSAGE can sometimes be a list of ints (binary blob)
                message = str(message)

            priority_raw = obj.get("PRIORITY", "6")
            try:
                priority = int(priority_raw)
            except (ValueError, TypeError):
                priority = 6

            unit = obj.get("_SYSTEMD_UNIT", obj.get("SYSLOG_IDENTIFIER", ""))

            # Timestamp: __REALTIME_TIMESTAMP is microseconds since epoch
            ts_raw = obj.get("__REALTIME_TIMESTAMP", "")
            timestamp = SmartLogViewer._format_timestamp(ts_raw)

            priority_label = SmartLogViewer.PRIORITY_LABELS.get(priority, "UNKNOWN")
            pattern_match = SmartLogViewer.match_patterns(message)

            entries.append(
                LogEntry(
                    timestamp=timestamp,
                    unit=unit,
                    priority=priority,
                    message=message,
                    priority_label=priority_label,
                    pattern_match=pattern_match,
                )
            )

        return entries

    @staticmethod
    def _format_timestamp(ts_raw: str) -> str:
        """Convert journalctl microsecond timestamp to human-readable form."""
        if not ts_raw:
            return ""
        try:
            from datetime import datetime, timezone
            usec = int(ts_raw)
            dt = datetime.fromtimestamp(usec / 1_000_000, tz=timezone.utc)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError, OSError):
            return str(ts_raw)

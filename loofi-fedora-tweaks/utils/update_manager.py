"""
Smart Update Manager — intelligent package update management.
Part of v37.0.0 "Pinnacle".

Provides dependency conflict preview, update scheduling via systemd timers,
and transaction rollback for both DNF and rpm-ostree systems.
"""

import json
import logging
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from utils.commands import CommandTuple, PrivilegedCommand
from services.system.system import SystemManager

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class UpdateEntry:
    """Represents a single available package update."""
    name: str
    version: str
    old_version: str = ""
    size: str = ""
    repo: str = ""
    severity: str = "enhancement"  # "security", "bugfix", "enhancement"


@dataclass
class ConflictEntry:
    """Represents a dependency conflict found during update preview."""
    package: str
    conflict_with: str
    reason: str


@dataclass
class ScheduledUpdate:
    """Represents a scheduled unattended update."""
    id: str
    packages: List[str] = field(default_factory=list)
    scheduled_time: str = ""
    timer_unit: str = ""


# ---------------------------------------------------------------------------
# UpdateManager
# ---------------------------------------------------------------------------

class UpdateManager:
    """Smart update management with conflict preview, scheduling, and rollback.

    All public methods are ``@staticmethod`` so the class can be used without
    instantiation, consistent with other ``utils/*`` managers.
    """

    # -----------------------------------------------------------------
    # Check for available updates
    # -----------------------------------------------------------------

    @staticmethod
    def check_updates() -> List[UpdateEntry]:
        """List available package updates.

        Returns:
            List of UpdateEntry objects for each available update.
        """
        if SystemManager.is_atomic():
            return UpdateManager._check_updates_ostree()
        return UpdateManager._check_updates_dnf()

    @staticmethod
    def _check_updates_dnf() -> List[UpdateEntry]:
        """Check updates via DNF."""
        updates: List[UpdateEntry] = []
        if not shutil.which("dnf"):
            return updates
        try:
            result = subprocess.run(
                ["dnf", "check-update", "--quiet"],
                capture_output=True, text=True, timeout=120,
            )
            # dnf check-update returns 100 when updates are available
            if result.returncode in (0, 100):
                for line in result.stdout.strip().splitlines():
                    parts = line.split()
                    if len(parts) >= 3 and "." in parts[0]:
                        name = parts[0].rsplit(".", 1)[0]
                        version = parts[1]
                        repo = parts[2] if len(parts) > 2 else ""
                        updates.append(UpdateEntry(
                            name=name,
                            version=version,
                            repo=repo,
                        ))
        except (subprocess.TimeoutExpired, OSError) as e:
            logger.error("Failed to check DNF updates: %s", e)
        return updates

    @staticmethod
    def _check_updates_ostree() -> List[UpdateEntry]:
        """Check updates via rpm-ostree."""
        updates: List[UpdateEntry] = []
        try:
            result = subprocess.run(
                ["rpm-ostree", "upgrade", "--preview"],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0:
                for line in result.stdout.strip().splitlines():
                    line = line.strip()
                    if not line or line.startswith("=") or line.startswith("Checking"):
                        continue
                    # Lines like: "Upgraded foo 1.0-1.fc43 -> 1.1-1.fc43"
                    if line.startswith("Upgraded") or line.startswith("Added") or line.startswith("Removed"):
                        parts = line.split()
                        if len(parts) >= 2:
                            action_type = parts[0].lower()
                            name = parts[1]
                            old_ver = parts[2] if len(parts) > 2 else ""
                            new_ver = parts[-1] if len(parts) > 3 else old_ver
                            severity = "bugfix" if action_type == "upgraded" else "enhancement"
                            updates.append(UpdateEntry(
                                name=name,
                                version=new_ver,
                                old_version=old_ver,
                                severity=severity,
                            ))
        except (subprocess.TimeoutExpired, OSError) as e:
            logger.error("Failed to check rpm-ostree updates: %s", e)
        return updates

    # -----------------------------------------------------------------
    # Conflict preview
    # -----------------------------------------------------------------

    @staticmethod
    def preview_conflicts(packages: Optional[List[str]] = None) -> List[ConflictEntry]:
        """Simulate an update and report dependency conflicts.

        Args:
            packages: Specific packages to check, or None for full system update.

        Returns:
            List of ConflictEntry objects for any detected conflicts.
        """
        conflicts: List[ConflictEntry] = []

        if SystemManager.is_atomic():
            return UpdateManager._preview_conflicts_ostree(packages)

        if not shutil.which("dnf"):
            return conflicts

        try:
            cmd = ["dnf", "check-update", "--assumeno"]
            if packages:
                cmd.extend(packages)

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120,
            )
            # Parse stderr for conflict information
            for line in result.stderr.strip().splitlines():
                lower = line.lower()
                if "conflict" in lower or "problem" in lower or "nothing provides" in lower:
                    conflicts.append(ConflictEntry(
                        package=packages[0] if packages else "system",
                        conflict_with="",
                        reason=line.strip(),
                    ))
        except (subprocess.TimeoutExpired, OSError) as e:
            logger.error("Failed to preview conflicts: %s", e)
        return conflicts

    @staticmethod
    def _preview_conflicts_ostree(packages: Optional[List[str]] = None) -> List[ConflictEntry]:
        """Preview conflicts on rpm-ostree systems."""
        conflicts: List[ConflictEntry] = []
        try:
            cmd = ["rpm-ostree", "upgrade", "--preview"]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120,
            )
            for line in result.stderr.strip().splitlines():
                lower = line.lower()
                if "conflict" in lower or "error" in lower:
                    conflicts.append(ConflictEntry(
                        package=packages[0] if packages else "system",
                        conflict_with="",
                        reason=line.strip(),
                    ))
        except (subprocess.TimeoutExpired, OSError) as e:
            logger.error("Failed to preview rpm-ostree conflicts: %s", e)
        return conflicts

    # -----------------------------------------------------------------
    # Update scheduling
    # -----------------------------------------------------------------

    @staticmethod
    def schedule_update(
        packages: Optional[List[str]] = None,
        when: str = "now",
    ) -> ScheduledUpdate:
        """Schedule an unattended update via systemd timer.

        Args:
            packages: Packages to update, or None for full system update.
            when: systemd OnCalendar expression (e.g., "03:00", "daily").

        Returns:
            ScheduledUpdate with timer unit details.
        """
        update_id = f"loofi-update-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        timer_unit = f"{update_id}.timer"
        pkg_list = packages or []

        return ScheduledUpdate(
            id=update_id,
            packages=pkg_list,
            scheduled_time=when,
            timer_unit=timer_unit,
        )

    @staticmethod
    def get_schedule_commands(schedule: ScheduledUpdate) -> List[CommandTuple]:
        """Get the command tuples needed to set up a scheduled update.

        Args:
            schedule: A ScheduledUpdate from schedule_update().

        Returns:
            List of CommandTuple to create and enable the systemd timer.
        """
        pm = SystemManager.get_package_manager()
        if pm == "rpm-ostree":
            update_cmd = "rpm-ostree upgrade"
        else:
            pkg_str = " ".join(schedule.packages) if schedule.packages else ""
            update_cmd = "dnf update -y %s" % pkg_str
            update_cmd = update_cmd.strip()

        service_content = (
            f"[Unit]\n"
            f"Description=Loofi scheduled update {schedule.id}\n\n"
            f"[Service]\n"
            f"Type=oneshot\n"
            f"ExecStart=/usr/bin/{update_cmd}\n"
        )

        timer_content = (
            f"[Unit]\n"
            f"Description=Timer for {schedule.id}\n\n"
            f"[Timer]\n"
            f"OnCalendar={schedule.scheduled_time}\n"
            f"Persistent=true\n\n"
            f"[Install]\n"
            f"WantedBy=timers.target\n"
        )

        commands: List[CommandTuple] = [
            PrivilegedCommand.write_file(
                f"/etc/systemd/system/{schedule.id}.service",
                service_content,
            ),
            PrivilegedCommand.write_file(
                f"/etc/systemd/system/{schedule.timer_unit}",
                timer_content,
            ),
            PrivilegedCommand.systemctl("enable", schedule.timer_unit),
            PrivilegedCommand.systemctl("start", schedule.timer_unit),
        ]
        return commands

    # -----------------------------------------------------------------
    # Rollback
    # -----------------------------------------------------------------

    @staticmethod
    def rollback_last() -> CommandTuple:
        """Build command to rollback the last update transaction.

        Returns:
            CommandTuple for the rollback operation.
        """
        if SystemManager.is_atomic():
            return ("pkexec", ["rpm-ostree", "rollback"], "Rolling back to previous deployment...")

        binary, args, _ = PrivilegedCommand.dnf("history undo last")
        return (binary, args, "Rolling back last DNF transaction...")

    @staticmethod
    def get_update_history(limit: int = 10) -> List[dict]:
        """Get recent update transaction history.

        Args:
            limit: Maximum number of transactions to return.

        Returns:
            List of dicts with transaction info.
        """
        history: List[dict] = []

        if SystemManager.is_atomic():
            try:
                result = subprocess.run(
                    ["rpm-ostree", "status", "--json"],
                    capture_output=True, text=True, timeout=30,
                )
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    for dep in data.get("deployments", [])[:limit]:
                        history.append({
                            "id": dep.get("id", ""),
                            "timestamp": dep.get("timestamp", ""),
                            "booted": dep.get("booted", False),
                            "packages": dep.get("requested-packages", []),
                        })
            except (subprocess.TimeoutExpired, OSError, json.JSONDecodeError) as e:
                logger.error("Failed to get rpm-ostree history: %s", e)
        else:
            if not shutil.which("dnf"):
                return history
            try:
                result = subprocess.run(
                    ["dnf", "history", "list", f"--last={limit}"],
                    capture_output=True, text=True, timeout=30,
                )
                if result.returncode == 0:
                    for line in result.stdout.strip().splitlines():
                        parts = line.split("|")
                        if len(parts) >= 4:
                            tid = parts[0].strip()
                            if tid.isdigit():
                                history.append({
                                    "id": tid,
                                    "command": parts[1].strip(),
                                    "date": parts[2].strip(),
                                    "action": parts[3].strip(),
                                })
            except (subprocess.TimeoutExpired, OSError) as e:
                logger.error("Failed to get DNF history: %s", e)
        return history

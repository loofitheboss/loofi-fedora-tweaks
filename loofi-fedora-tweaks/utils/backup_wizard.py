"""
System Backup Wizard — guided snapshot management.
Part of v37.0.0 "Pinnacle" — T6.

Wraps Timeshift and Snapper for guided backup creation, listing,
and restoration. Complements the lower-level SnapshotManager with
a wizard-friendly API.
"""

import logging
import shutil
import subprocess
from dataclasses import dataclass
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

CommandTuple = Tuple[str, List[str], str]


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class SnapshotEntry:
    """A single snapshot entry."""
    id: str
    date: str
    description: str
    tool: str  # "timeshift" | "snapper"
    size: str = ""
    snapshot_type: str = ""  # "single" | "pre-post" | "ondemand"


@dataclass
class SnapshotResult:
    """Result of a snapshot operation."""
    success: bool
    snapshot_id: str = ""
    message: str = ""
    tool: str = ""


# ---------------------------------------------------------------------------
# BackupWizard
# ---------------------------------------------------------------------------

class BackupWizard:
    """Guided system backup wizard wrapping Timeshift and Snapper.

    All methods are ``@staticmethod``.
    Detects available tools, creates/lists/restores snapshots.
    """

    SUPPORTED_TOOLS = ["timeshift", "snapper"]

    # -----------------------------------------------------------------
    # Tool detection
    # -----------------------------------------------------------------

    @staticmethod
    def detect_backup_tool() -> str:
        """Detect which backup tool is available.

        Checks for ``timeshift`` and ``snapper`` on ``$PATH``.
        Prefers timeshift if both are available.

        Returns:
            Tool name: ``"timeshift"``, ``"snapper"``, or ``"none"``.
        """
        for tool in BackupWizard.SUPPORTED_TOOLS:
            if shutil.which(tool):
                return tool
        return "none"

    @staticmethod
    def get_available_tools() -> List[str]:
        """Return list of available backup tools.

        Returns:
            List of tool names that are installed.
        """
        return [t for t in BackupWizard.SUPPORTED_TOOLS if shutil.which(t)]

    @staticmethod
    def is_available() -> bool:
        """Return True if any backup tool is installed."""
        return BackupWizard.detect_backup_tool() != "none"

    # -----------------------------------------------------------------
    # Snapshot creation
    # -----------------------------------------------------------------

    @staticmethod
    def create_snapshot(
        tool: Optional[str] = None,
        description: str = "Loofi backup",
    ) -> CommandTuple:
        """Return command tuple to create a system snapshot.

        Args:
            tool: Backup tool to use. Auto-detected if None.
            description: Human-readable snapshot description.

        Returns:
            Command tuple (binary, args, desc).
        """
        if tool is None:
            tool = BackupWizard.detect_backup_tool()

        # Sanitize description
        safe_desc = description.replace('"', '').replace("'", "").replace(";", "")[:80]

        if tool == "timeshift":
            return (
                "pkexec",
                ["timeshift", "--create", "--comments", safe_desc],
                f"Creating Timeshift snapshot: {safe_desc}",
            )
        elif tool == "snapper":
            return (
                "pkexec",
                ["snapper", "create", "--description", safe_desc, "--type", "single"],
                f"Creating Snapper snapshot: {safe_desc}",
            )
        return (
            "echo",
            ["No backup tool available. Install timeshift or snapper."],
            "No backup tool found",
        )

    # -----------------------------------------------------------------
    # List snapshots
    # -----------------------------------------------------------------

    @staticmethod
    def list_snapshots(tool: Optional[str] = None) -> List[SnapshotEntry]:
        """List existing system snapshots.

        Args:
            tool: Backup tool to query. Auto-detected if None.

        Returns:
            List of :class:`SnapshotEntry`.
        """
        if tool is None:
            tool = BackupWizard.detect_backup_tool()

        if tool == "timeshift":
            return BackupWizard._list_timeshift_snapshots()
        elif tool == "snapper":
            return BackupWizard._list_snapper_snapshots()
        return []

    @staticmethod
    def _list_timeshift_snapshots() -> List[SnapshotEntry]:
        """Parse timeshift --list output."""
        entries: List[SnapshotEntry] = []
        try:
            result = subprocess.run(
                ["timeshift", "--list"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                return entries

            # Timeshift --list output format:
            # Num  Name                             Tags  Description
            #  1   2026-02-14_12-00-00              O     Loofi backup
            parsing = False
            for line in result.stdout.splitlines():
                stripped = line.strip()
                if stripped.startswith("---"):
                    parsing = True
                    continue
                if not parsing or not stripped:
                    continue
                parts = stripped.split(None, 3)
                if len(parts) >= 2:
                    snap_id = parts[0]
                    date = parts[1]
                    desc = parts[3] if len(parts) > 3 else ""
                    tag = parts[2] if len(parts) > 2 else ""
                    entries.append(SnapshotEntry(
                        id=snap_id,
                        date=date,
                        description=desc,
                        tool="timeshift",
                        snapshot_type=tag,
                    ))
        except subprocess.TimeoutExpired:
            logger.warning("Timeout listing Timeshift snapshots")
        except FileNotFoundError:
            logger.debug("timeshift not found")
        return entries

    @staticmethod
    def _list_snapper_snapshots() -> List[SnapshotEntry]:
        """Parse snapper list output."""
        entries: List[SnapshotEntry] = []
        try:
            result = subprocess.run(
                ["snapper", "list"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                return entries

            # Snapper list output:
            # # | Type   | Pre # | Date                     | User | Cleanup | Description
            # --+--------+-------+--------------------------+------+---------+-----------
            # 0 | single |       |                          | root |         | current
            # 1 | single |       | 2026-02-14 12:00:00      | root | number  | Loofi backup
            parsing = False
            for line in result.stdout.splitlines():
                stripped = line.strip()
                if stripped.startswith("--"):
                    parsing = True
                    continue
                if not parsing or not stripped:
                    continue
                parts = [p.strip() for p in stripped.split("|")]
                if len(parts) >= 7:
                    snap_id = parts[0]
                    snap_type = parts[1]
                    date = parts[3]
                    desc = parts[6] if len(parts) > 6 else ""
                    entries.append(SnapshotEntry(
                        id=snap_id,
                        date=date,
                        description=desc,
                        tool="snapper",
                        snapshot_type=snap_type,
                    ))
        except subprocess.TimeoutExpired:
            logger.warning("Timeout listing Snapper snapshots")
        except FileNotFoundError:
            logger.debug("snapper not found")
        return entries

    # -----------------------------------------------------------------
    # Restore
    # -----------------------------------------------------------------

    @staticmethod
    def restore_snapshot(
        snapshot_id: str,
        tool: Optional[str] = None,
    ) -> CommandTuple:
        """Return command tuple to restore a system snapshot.

        Args:
            snapshot_id: ID of the snapshot to restore.
            tool: Backup tool to use. Auto-detected if None.

        Returns:
            Command tuple (binary, args, desc).
        """
        if tool is None:
            tool = BackupWizard.detect_backup_tool()

        if tool == "timeshift":
            return (
                "pkexec",
                ["timeshift", "--restore", "--snapshot", snapshot_id, "--yes"],
                f"Restoring Timeshift snapshot {snapshot_id}",
            )
        elif tool == "snapper":
            return (
                "pkexec",
                ["snapper", "undochange", f"{snapshot_id}..0"],
                f"Restoring Snapper snapshot {snapshot_id}",
            )
        return (
            "echo",
            ["No backup tool available"],
            "Cannot restore — no backup tool found",
        )

    # -----------------------------------------------------------------
    # Delete
    # -----------------------------------------------------------------

    @staticmethod
    def delete_snapshot(
        snapshot_id: str,
        tool: Optional[str] = None,
    ) -> CommandTuple:
        """Return command tuple to delete a system snapshot.

        Args:
            snapshot_id: ID of the snapshot to delete.
            tool: Backup tool to use. Auto-detected if None.

        Returns:
            Command tuple (binary, args, desc).
        """
        if tool is None:
            tool = BackupWizard.detect_backup_tool()

        if tool == "timeshift":
            return (
                "pkexec",
                ["timeshift", "--delete", "--snapshot", snapshot_id],
                f"Deleting Timeshift snapshot {snapshot_id}",
            )
        elif tool == "snapper":
            return (
                "pkexec",
                ["snapper", "delete", snapshot_id],
                f"Deleting Snapper snapshot {snapshot_id}",
            )
        return (
            "echo",
            ["No backup tool available"],
            "Cannot delete — no backup tool found",
        )

    # -----------------------------------------------------------------
    # Status
    # -----------------------------------------------------------------

    @staticmethod
    def get_backup_status() -> dict:
        """Return summary of backup system state.

        Returns:
            Dict with: tool, available, snapshot_count, last_snapshot.
        """
        tool = BackupWizard.detect_backup_tool()
        status = {
            "tool": tool,
            "available": tool != "none",
            "snapshot_count": 0,
            "last_snapshot": None,
        }

        if tool == "none":
            return status

        snapshots = BackupWizard.list_snapshots(tool)
        status["snapshot_count"] = len(snapshots)
        if snapshots:
            status["last_snapshot"] = {
                "id": snapshots[-1].id,
                "date": snapshots[-1].date,
                "description": snapshots[-1].description,
            }
        return status

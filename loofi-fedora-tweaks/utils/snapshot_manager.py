"""
System Snapshot Timeline — unified snapshot management across backends.
Part of v15.0 "Nebula".

Provides a consistent interface for creating, listing, and managing system
snapshots via Timeshift, Snapper, or raw Btrfs subvolumes.
"""

import logging
import shutil
import subprocess
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

from utils.commands import PrivilegedCommand  # noqa: F401 — keep for pattern consistency

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class SnapshotInfo:
    """Represents a single system snapshot."""
    id: str
    label: str
    backend: str  # "timeshift" | "snapper" | "btrfs"
    timestamp: float
    size_str: str
    description: str


@dataclass
class SnapshotBackend:
    """Describes a snapshot backend available on the system."""
    name: str
    available: bool
    command: str
    version: str


# ---------------------------------------------------------------------------
# Preferred backend ordering
# ---------------------------------------------------------------------------

_BACKEND_PRIORITY = ["snapper", "timeshift", "btrfs"]


# ---------------------------------------------------------------------------
# SnapshotManager
# ---------------------------------------------------------------------------

class SnapshotManager:
    """Unified manager for system snapshot operations.

    All public methods are ``@staticmethod`` so the class can be used without
    instantiation, consistent with other ``utils/*`` managers.
    """

    # -----------------------------------------------------------------
    # Backend detection
    # -----------------------------------------------------------------

    @staticmethod
    def detect_backends() -> List[SnapshotBackend]:
        """Detect which snapshot backends are installed.

        Checks for ``timeshift``, ``snapper``, and ``btrfs`` commands on
        ``$PATH`` and queries each for its version string.

        Returns:
            A list of :class:`SnapshotBackend` for every known backend.
        """
        backends: List[SnapshotBackend] = []

        for name in _BACKEND_PRIORITY:
            cmd_path = shutil.which(name)
            available = cmd_path is not None
            version = ""

            if available:
                try:
                    result = subprocess.run(
                        [name, "--version"],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    # Take the first non-empty line as the version string
                    for line in result.stdout.strip().splitlines():
                        stripped = line.strip()
                        if stripped:
                            version = stripped
                            break
                    # Some tools print version info on stderr
                    if not version:
                        for line in result.stderr.strip().splitlines():
                            stripped = line.strip()
                            if stripped:
                                version = stripped
                                break
                except (OSError, subprocess.SubprocessError, FileNotFoundError) as exc:
                    logger.warning("Could not query version for %s: %s", name, exc)
                    version = "unknown"

            backends.append(SnapshotBackend(
                name=name,
                available=available,
                command=cmd_path or name,
                version=version,
            ))

        return backends

    @staticmethod
    def get_preferred_backend() -> Optional[str]:
        """Return the best available backend name, or ``None``.

        Priority order: snapper → timeshift → btrfs.
        """
        for name in _BACKEND_PRIORITY:
            if shutil.which(name) is not None:
                return name
        return None

    # -----------------------------------------------------------------
    # Listing
    # -----------------------------------------------------------------

    @staticmethod
    def list_snapshots(backend: str = None) -> List[SnapshotInfo]:
        """List existing snapshots for the given (or auto-detected) backend.

        Args:
            backend: One of ``"timeshift"``, ``"snapper"``, ``"btrfs"``.
                     If *None*, the preferred backend is auto-detected.

        Returns:
            A list of :class:`SnapshotInfo` sorted by *timestamp* descending
            (newest first).
        """
        if backend is None:
            backend = SnapshotManager.get_preferred_backend()
        if backend is None:
            logger.info("No snapshot backend available")
            return []

        parsers = {
            "timeshift": SnapshotManager._list_timeshift,
            "snapper": SnapshotManager._list_snapper,
            "btrfs": SnapshotManager._list_btrfs,
        }

        parser = parsers.get(backend)
        if parser is None:
            logger.error("Unknown snapshot backend: %s", backend)
            return []

        try:
            snapshots = parser()
        except (OSError, subprocess.SubprocessError, FileNotFoundError) as exc:
            logger.error("Failed to list %s snapshots: %s", backend, exc)
            return []

        # Sort newest-first
        snapshots.sort(key=lambda s: s.timestamp, reverse=True)
        return snapshots

    # -- Timeshift -------------------------------------------------------

    @staticmethod
    def _list_timeshift() -> List[SnapshotInfo]:
        result = subprocess.run(
            ["pkexec", "timeshift", "--list"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        snapshots: List[SnapshotInfo] = []
        in_table = False

        for line in result.stdout.splitlines():
            stripped = line.strip()

            # Detect the table body after dashes separator
            if stripped.startswith("---"):
                in_table = True
                continue

            if not in_table or not stripped:
                continue

            # Typical timeshift --list row:
            #   0  >  2024-01-15_10-00-01  D  1.2 GB  Pre-update snapshot
            parts = stripped.split()
            if len(parts) < 3:
                continue

            try:
                snap_id = parts[0]
                # Find the timestamp token (format: YYYY-MM-DD_HH-MM-SS)
                ts_str = ""
                ts_index = -1
                for idx, token in enumerate(parts):
                    if len(token) == 19 and token[4] == "-" and token[10] == "_":
                        ts_str = token
                        ts_index = idx
                        break

                if not ts_str:
                    # Fallback: use current time
                    timestamp = time.time()
                else:
                    try:
                        timestamp = time.mktime(
                            time.strptime(ts_str, "%Y-%m-%d_%H-%M-%S")
                        )
                    except ValueError:
                        timestamp = time.time()

                # Size is usually 2 tokens after ts (tag + size like "1.2 GB")
                size_str = ""
                desc_tokens: List[str] = []
                if ts_index >= 0 and ts_index + 2 < len(parts):
                    # tag letter right after timestamp
                    remaining = parts[ts_index + 1:]
                    # Try to pick up size (number + unit)
                    if len(remaining) >= 2:
                        try:
                            float(remaining[1])
                            size_str = f"{remaining[1]} {remaining[2]}" if len(remaining) > 2 else remaining[1]
                            desc_tokens = remaining[3:] if len(remaining) > 3 else []
                        except (ValueError, IndexError):
                            # Couldn't parse size; treat rest as description
                            desc_tokens = remaining[1:]
                    else:
                        desc_tokens = remaining
                else:
                    desc_tokens = parts[1:]

                description = " ".join(desc_tokens)
                label = description or f"timeshift-{snap_id}"

                snapshots.append(SnapshotInfo(
                    id=snap_id,
                    label=label,
                    backend="timeshift",
                    timestamp=timestamp,
                    size_str=size_str,
                    description=description,
                ))
            except (IndexError, ValueError) as exc:
                logger.debug("Skipping unparseable timeshift line: %s (%s)", stripped, exc)
                continue

        return snapshots

    # -- Snapper ---------------------------------------------------------

    @staticmethod
    def _list_snapper() -> List[SnapshotInfo]:
        result = subprocess.run(
            ["pkexec", "snapper", "list", "--columns", "number,date,description"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        snapshots: List[SnapshotInfo] = []
        lines = result.stdout.splitlines()

        for line in lines:
            stripped = line.strip()
            # Skip header / separator lines
            if not stripped or stripped.startswith("---") or stripped.startswith("#") or stripped.lower().startswith("number"):
                continue

            # Columns are separated by " | "
            if "|" in stripped:
                parts = [p.strip() for p in stripped.split("|")]
            else:
                parts = stripped.split(None, 2)

            if len(parts) < 2:
                continue

            try:
                snap_id = parts[0].strip()
                if not snap_id or not snap_id[0].isdigit():
                    continue

                date_str = parts[1].strip() if len(parts) > 1 else ""
                description = parts[2].strip() if len(parts) > 2 else ""

                # Parse date — snapper uses locale-dependent formats
                timestamp = 0.0
                date_formats = [
                    "%a %b %d %H:%M:%S %Y",
                    "%Y-%m-%d %H:%M:%S",
                    "%a %d %b %Y %I:%M:%S %p %Z",
                    "%c",
                ]
                for fmt in date_formats:
                    try:
                        timestamp = time.mktime(time.strptime(date_str, fmt))
                        break
                    except ValueError:
                        continue

                if timestamp == 0.0 and date_str:
                    # Last-resort: try the C-library parser
                    try:
                        timestamp = time.mktime(time.strptime(date_str))
                    except ValueError:
                        timestamp = 0.0

                label = description or f"snapper-{snap_id}"

                snapshots.append(SnapshotInfo(
                    id=snap_id,
                    label=label,
                    backend="snapper",
                    timestamp=timestamp,
                    size_str="",
                    description=description,
                ))
            except (IndexError, ValueError) as exc:
                logger.debug("Skipping unparseable snapper line: %s (%s)", stripped, exc)
                continue

        return snapshots

    # -- Btrfs -----------------------------------------------------------

    @staticmethod
    def _list_btrfs() -> List[SnapshotInfo]:
        result = subprocess.run(
            ["pkexec", "btrfs", "subvolume", "list", "/"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        snapshots: List[SnapshotInfo] = []

        for line in result.stdout.splitlines():
            stripped = line.strip()
            if not stripped:
                continue

            # Typical line:
            # ID 258 gen 123 top level 5 path .snapshots/my-label
            parts = stripped.split()
            if len(parts) < 9:
                continue

            try:
                snap_id = parts[1] if len(parts) > 1 else ""
                # "path" is the last token
                path_index = None
                for idx, token in enumerate(parts):
                    if token == "path":
                        path_index = idx
                        break

                if path_index is None or path_index + 1 >= len(parts):
                    continue

                path_value = " ".join(parts[path_index + 1:])

                # Only include entries that look like snapshots
                if ".snapshots" not in path_value and "snapshot" not in path_value.lower():
                    continue

                label = path_value.rsplit("/", 1)[-1] if "/" in path_value else path_value

                # Btrfs subvolume list doesn't expose timestamps directly;
                # fall back to 0 (caller can stat the path if needed).
                timestamp = 0.0

                snapshots.append(SnapshotInfo(
                    id=snap_id,
                    label=label,
                    backend="btrfs",
                    timestamp=timestamp,
                    size_str="",
                    description=path_value,
                ))
            except (IndexError, ValueError) as exc:
                logger.debug("Skipping unparseable btrfs line: %s (%s)", stripped, exc)
                continue

        return snapshots

    # -----------------------------------------------------------------
    # Creation
    # -----------------------------------------------------------------

    @staticmethod
    def create_snapshot(label: str, backend: str = None) -> Tuple[str, List[str], str]:
        """Return an operation tuple to create a snapshot.

        Args:
            label: Human-readable label or comment for the snapshot.
            backend: Backend to use (auto-detected when *None*).

        Returns:
            ``(command, args_list, description)`` — the standard Loofi
            operation tuple ready for :class:`CommandRunner`.
        """
        if backend is None:
            backend = SnapshotManager.get_preferred_backend()
        if backend is None:
            logger.error("No snapshot backend available for create")
            return ("echo", ["No snapshot backend available"], "Error: no backend")

        if backend == "timeshift":
            return (
                "pkexec",
                ["timeshift", "--create", "--comments", label],
                f"Creating Timeshift snapshot '{label}'...",
            )

        if backend == "snapper":
            return (
                "pkexec",
                ["snapper", "create", "--description", label],
                f"Creating Snapper snapshot '{label}'...",
            )

        if backend == "btrfs":
            # Sanitise label for use as a path component
            safe_label = label.replace("/", "_").replace(" ", "_")
            return (
                "pkexec",
                ["btrfs", "subvolume", "snapshot", "/", f"/.snapshots/{safe_label}"],
                f"Creating Btrfs snapshot '{safe_label}'...",
            )

        logger.error("Unknown backend for create: %s", backend)
        return ("echo", [f"Unknown backend: {backend}"], f"Error: unknown backend {backend}")

    # -----------------------------------------------------------------
    # Deletion
    # -----------------------------------------------------------------

    @staticmethod
    def delete_snapshot(snapshot_id: str, backend: str = None) -> Tuple[str, List[str], str]:
        """Return an operation tuple to delete a snapshot.

        Args:
            snapshot_id: The snapshot identifier (number for timeshift/snapper,
                         subvolume ID or path for btrfs).
            backend: Backend to use (auto-detected when *None*).

        Returns:
            Standard operation tuple.
        """
        if backend is None:
            backend = SnapshotManager.get_preferred_backend()
        if backend is None:
            logger.error("No snapshot backend available for delete")
            return ("echo", ["No snapshot backend available"], "Error: no backend")

        if backend == "timeshift":
            return (
                "pkexec",
                ["timeshift", "--delete", "--snapshot-id", snapshot_id],
                f"Deleting Timeshift snapshot {snapshot_id}...",
            )

        if backend == "snapper":
            return (
                "pkexec",
                ["snapper", "delete", snapshot_id],
                f"Deleting Snapper snapshot {snapshot_id}...",
            )

        if backend == "btrfs":
            # snapshot_id is expected to be the subvolume path
            return (
                "pkexec",
                ["btrfs", "subvolume", "delete", snapshot_id],
                f"Deleting Btrfs subvolume {snapshot_id}...",
            )

        logger.error("Unknown backend for delete: %s", backend)
        return ("echo", [f"Unknown backend: {backend}"], f"Error: unknown backend {backend}")

    # -----------------------------------------------------------------
    # Count
    # -----------------------------------------------------------------

    @staticmethod
    def get_snapshot_count(backend: str = None) -> int:
        """Return the number of snapshots for the given backend.

        This is a convenience wrapper around :meth:`list_snapshots`.
        """
        return len(SnapshotManager.list_snapshots(backend=backend))

    # -----------------------------------------------------------------
    # Retention
    # -----------------------------------------------------------------

    @staticmethod
    def apply_retention(
        max_snapshots: int = 10,
        backend: str = None,
    ) -> List[Tuple[str, List[str], str]]:
        """Generate delete operations for snapshots exceeding *max_snapshots*.

        The oldest snapshots beyond *max_snapshots* are selected for removal.

        Args:
            max_snapshots: Maximum number of snapshots to keep.
            backend: Backend to use (auto-detected when *None*).

        Returns:
            A list of operation tuples (may be empty if within limits).
        """
        if backend is None:
            backend = SnapshotManager.get_preferred_backend()
        if backend is None:
            logger.info("No backend available — nothing to prune")
            return []

        snapshots = SnapshotManager.list_snapshots(backend=backend)

        if len(snapshots) <= max_snapshots:
            return []

        # Snapshots are already sorted newest-first; keep the first N
        to_delete = snapshots[max_snapshots:]

        operations: List[Tuple[str, List[str], str]] = []
        for snap in to_delete:
            op = SnapshotManager.delete_snapshot(snap.id, backend=backend)
            operations.append(op)

        logger.info(
            "Retention policy: keeping %d, deleting %d snapshots (%s)",
            max_snapshots,
            len(to_delete),
            backend,
        )
        return operations

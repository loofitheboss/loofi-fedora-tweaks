"""
Disposable VM Manager - snapshot-based throwaway virtual machines.
Part of v11.5 "Hypervisor Update".

Creates QCOW2 overlay images backed by a reusable base image so that
each session starts clean.  On shutdown the overlay is deleted and the
session is gone, making it ideal for malware analysis, testing, or
one-off browsing.
"""

import logging
import os
import re
import shutil
import subprocess
import uuid

from utils.containers import Result

logger = logging.getLogger(__name__)


# Name validation: alphanumeric, dash, underscore only
_VM_NAME_RE = re.compile(r'^[a-zA-Z0-9_-]+$')


class DisposableVMManager:
    """Manages snapshot-backed disposable VMs."""

    DISPOSABLE_BASE_NAME = "loofi-disposable"

    # ==================== PATHS ====================

    @classmethod
    def _get_storage_dir(cls) -> str:
        """Return (and ensure exists) the disposable VM storage directory."""
        user_dir = os.path.expanduser("~/.local/share/loofi-vms/disposable")
        os.makedirs(user_dir, exist_ok=True)
        return user_dir

    @classmethod
    def get_base_image_path(cls) -> str:
        """Return the path to the base QCOW2 image."""
        return os.path.join(cls._get_storage_dir(), f"{cls.DISPOSABLE_BASE_NAME}-base.qcow2")

    # ==================== BASE IMAGE ====================

    @classmethod
    def is_base_image_available(cls) -> bool:
        """Check whether the base QCOW2 image exists."""
        return os.path.isfile(cls.get_base_image_path())

    @classmethod
    def create_base_image(cls, iso_path: str, size_gb: int = 20) -> Result:
        """Create the base QCOW2 image using ``qemu-img``.

        Args:
            iso_path: Path to the installation ISO (used later by the user
                      to install into the base image).
            size_gb: Disk size in GiB.

        Returns:
            Result with success/failure and message.
        """
        if not shutil.which("qemu-img"):
            return Result(False, "qemu-img is not installed. Install qemu-img first.")

        if not iso_path or not os.path.isfile(iso_path):
            return Result(False, f"ISO file not found: {iso_path}")

        base_path = cls.get_base_image_path()

        try:
            result = subprocess.run(
                [
                    "qemu-img", "create",
                    "-f", "qcow2",
                    base_path,
                    f"{size_gb}G",
                ],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                return Result(
                    True,
                    f"Base image created at {base_path} ({size_gb} GiB).",
                    {"path": base_path, "iso": iso_path},
                )
            else:
                error = result.stderr.strip() or result.stdout.strip()
                return Result(False, f"Failed to create base image: {error}")

        except subprocess.TimeoutExpired:
            return Result(False, "Base image creation timed out.")
        except (subprocess.SubprocessError, OSError) as e:
            logger.debug("Error creating base image: %s", e)
            return Result(False, f"Error creating base image: {e}")

    # ==================== OVERLAY / SNAPSHOT ====================

    @classmethod
    def create_snapshot_overlay(cls, base_path: str) -> str:
        """Create a QCOW2 overlay backed by *base_path*.

        Returns:
            Path to the newly created overlay file, or empty string on failure.
        """
        if not shutil.which("qemu-img"):
            return ""

        storage_dir = cls._get_storage_dir()
        overlay_name = f"disposable-{uuid.uuid4().hex[:8]}.qcow2"
        overlay_path = os.path.join(storage_dir, overlay_name)

        try:
            result = subprocess.run(
                [
                    "qemu-img", "create",
                    "-f", "qcow2",
                    "-b", base_path,
                    "-F", "qcow2",
                    overlay_path,
                ],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode == 0:
                return overlay_path
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to create snapshot overlay: %s", e)
        return ""

    # ==================== LAUNCH ====================

    @classmethod
    def launch_disposable(cls, name: str = None, snapshot: bool = True) -> Result:
        """Launch a disposable VM.

        If *snapshot* is True, a QCOW2 overlay is created on top of the base
        image; on shutdown the overlay is deleted and the session is lost.

        Args:
            name: Optional VM name.  Auto-generated when ``None``.
            snapshot: Whether to use an overlay (True) or boot the base directly.

        Returns:
            Result with success/failure and message.
        """
        if not cls.is_base_image_available():
            return Result(
                False,
                "No base image found. Create one first with create_base_image().",
            )

        if not shutil.which("virsh"):
            return Result(False, "virsh is not installed.")

        if name is None:
            name = f"disposable-{uuid.uuid4().hex[:8]}"

        if not _VM_NAME_RE.match(name):
            return Result(
                False,
                "Invalid VM name. Use only letters, numbers, dashes, and underscores.",
            )

        base_path = cls.get_base_image_path()

        if snapshot:
            disk_path = cls.create_snapshot_overlay(base_path)
            if not disk_path:
                return Result(False, "Failed to create snapshot overlay.")
        else:
            disk_path = base_path

        if not shutil.which("virt-install"):
            return Result(False, "virt-install is not installed.")

        cmd = [
            "virt-install",
            "--name", name,
            "--ram", "2048",
            "--vcpus", "2",
            "--disk", f"path={disk_path},format=qcow2",
            "--os-variant", "generic",
            "--network", "default",
            "--graphics", "spice",
            "--import",
            "--noautoconsole",
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode == 0:
                return Result(
                    True,
                    f"Disposable VM '{name}' launched.",
                    {"name": name, "overlay": disk_path if snapshot else "", "snapshot": snapshot},
                )
            else:
                error = result.stderr.strip() or result.stdout.strip()
                # Clean up overlay on failure
                if snapshot and disk_path and os.path.isfile(disk_path):
                    cls.cleanup_disposable(disk_path)
                return Result(False, f"Failed to launch disposable VM: {error}")

        except subprocess.TimeoutExpired:
            return Result(False, "Disposable VM launch timed out.")
        except (subprocess.SubprocessError, OSError) as e:
            logger.debug("Error launching disposable VM: %s", e)
            return Result(False, f"Error launching disposable VM: {e}")

    # ==================== CLEANUP ====================

    @classmethod
    def cleanup_disposable(cls, overlay_path: str) -> Result:
        """Delete a disposable VM overlay file.

        Args:
            overlay_path: Absolute path to the overlay QCOW2 to remove.

        Returns:
            Result with success/failure and message.
        """
        if not overlay_path:
            return Result(False, "No overlay path provided.")

        if not os.path.isfile(overlay_path):
            return Result(False, f"Overlay file not found: {overlay_path}")

        try:
            os.remove(overlay_path)
            return Result(True, f"Overlay deleted: {overlay_path}")
        except OSError as e:
            return Result(False, f"Failed to delete overlay: {e}")

    # ==================== LIST ACTIVE ====================

    @classmethod
    def list_active_disposables(cls) -> list:
        """Return names of currently defined disposable VMs.

        Scans ``virsh list --all`` for VMs whose names start with
        ``disposable-``.
        """
        if not shutil.which("virsh"):
            return []

        try:
            result = subprocess.run(
                ["virsh", "list", "--all", "--name"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0:
                return []

            names = []
            for line in result.stdout.strip().split("\n"):
                line = line.strip()
                if line.startswith("disposable-"):
                    names.append(line)
            return names

        except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to list active disposables: %s", e)
            return []

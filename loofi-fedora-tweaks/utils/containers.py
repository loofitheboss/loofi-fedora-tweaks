"""
Container management utilities for Distrobox.
Part of v7.1 "Developer" update.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from utils.install_hints import build_install_hint

logger = logging.getLogger(__name__)


class ContainerStatus(Enum):
    """Container runtime status."""

    RUNNING = "running"
    STOPPED = "stopped"
    CREATED = "created"
    UNKNOWN = "unknown"


@dataclass
class Container:
    """Represents a Distrobox container."""

    name: str
    status: ContainerStatus
    image: str
    id: str = ""


@dataclass
class Result:
    """Operation result with message."""

    success: bool
    message: str
    data: Optional[dict] = None


class ContainerManager:
    """
    Manages Distrobox containers.

    Distrobox is the primary target as it's more feature-rich than Toolbx
    and supports more base images (Ubuntu, Arch, Alpine, etc.).
    """

    # Common container images for the Create wizard
    AVAILABLE_IMAGES = {
        "fedora": "registry.fedoraproject.org/fedora-toolbox:latest",
        "ubuntu": "docker.io/library/ubuntu:22.04",
        "arch": "docker.io/archlinux/archlinux:latest",
        "alpine": "docker.io/library/alpine:latest",
        "debian": "docker.io/library/debian:stable",
        "opensuse": "registry.opensuse.org/opensuse/tumbleweed:latest",
    }

    @classmethod
    def is_available(cls) -> bool:
        """Check if distrobox is installed."""
        return shutil.which("distrobox") is not None

    @classmethod
    def list_containers(cls) -> list[Container]:
        """
        List all Distrobox containers.

        Returns:
            List of Container objects.
        """
        if not cls.is_available():
            return []

        try:
            result = subprocess.run(
                ["distrobox", "list", "--no-color"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return []

            containers = []
            lines = result.stdout.strip().split("\n")

            # Skip header line (ID | NAME | STATUS | IMAGE)
            for line in lines[1:]:
                if not line.strip():
                    continue

                # Parse pipe-separated output
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 4:
                    container_id = parts[0]
                    name = parts[1]
                    status_str = parts[2].lower()
                    image = parts[3]

                    # Parse status
                    if "running" in status_str or "up" in status_str:
                        status = ContainerStatus.RUNNING
                    elif "created" in status_str:
                        status = ContainerStatus.CREATED
                    elif "exited" in status_str or "stopped" in status_str:
                        status = ContainerStatus.STOPPED
                    else:
                        status = ContainerStatus.UNKNOWN

                    containers.append(
                        Container(
                            name=name, status=status, image=image, id=container_id
                        )
                    )

            return containers

        except subprocess.TimeoutExpired:
            return []
        except (subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to list distrobox containers: %s", e)
            return []

    @classmethod
    def create_container(
        cls,
        name: str,
        image: str = "fedora",
        home_sharing: bool = True,
        additional_packages: Optional[list[str]] = None,
    ) -> Result:
        """
        Create a new Distrobox container.

        Args:
            name: Container name (alphanumeric, dashes, underscores)
            image: Image key from AVAILABLE_IMAGES or full image URL
            home_sharing: Whether to share home directory with host
            additional_packages: Extra packages to install during creation

        Returns:
            Result object with success status and message.
        """
        if not cls.is_available():
            return Result(
                False,
                f"Distrobox is not installed. {build_install_hint('distrobox')}",
            )

        # Validate name
        if not re.match(r"^[a-zA-Z0-9_-]+$", name):
            return Result(
                False,
                "Invalid container name. Use only letters, numbers, dashes, and underscores.",
            )

        # Resolve image URL
        image_url = cls.AVAILABLE_IMAGES.get(image.lower(), image)

        cmd = ["distrobox", "create", "--name", name, "--image", image_url]

        if not home_sharing:
            cmd.append("--no-entry")

        if additional_packages:
            cmd.extend(["--additional-packages", " ".join(additional_packages)])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # Container creation can take time
            )

            if result.returncode == 0:
                return Result(
                    True, f"Container '{name}' created successfully.", {"name": name}
                )
            else:
                error = result.stderr.strip() or result.stdout.strip()
                return Result(False, f"Failed to create container: {error}")

        except subprocess.TimeoutExpired:
            return Result(False, "Container creation timed out after 5 minutes.")
        except (subprocess.SubprocessError, OSError) as e:
            return Result(False, f"Error creating container: {e}")

    @classmethod
    def enter_container(cls, name: str) -> subprocess.Popen | None:
        """
        Start an interactive shell in a container.

        This returns a Popen object that can be used to interact with
        the container. For GUI use, this should be wrapped in a terminal.

        Args:
            name: Container name to enter.

        Returns:
            Popen object for the container session, or None on error.
        """
        if not cls.is_available():
            return None

        try:
            # Return the process so the caller can manage it
            return subprocess.Popen(  # noqa: timeout — interactive session, caller manages
                ["distrobox", "enter", name],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except (subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to enter container: %s", e)
            return None

    @classmethod
    def get_enter_command(cls, name: str) -> str:
        """
        Get the command string to enter a container.

        Useful for spawning in an external terminal emulator.

        Args:
            name: Container name.

        Returns:
            Command string to execute in a terminal.
        """
        return f"distrobox enter {name}"

    @classmethod
    def delete_container(cls, name: str, force: bool = False) -> Result:
        """
        Delete a Distrobox container.

        Args:
            name: Container name to delete.
            force: Force removal even if running.

        Returns:
            Result object with success status and message.
        """
        if not cls.is_available():
            return Result(False, "Distrobox is not installed.")

        cmd = ["distrobox", "rm", name]
        if force:
            cmd.append("--force")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode == 0:
                return Result(True, f"Container '{name}' deleted.")
            else:
                error = result.stderr.strip() or result.stdout.strip()
                return Result(False, f"Failed to delete container: {error}")

        except subprocess.TimeoutExpired:
            return Result(False, "Delete operation timed out.")
        except (subprocess.SubprocessError, OSError) as e:
            return Result(False, f"Error deleting container: {e}")

    @classmethod
    def stop_container(cls, name: str) -> Result:
        """
        Stop a running container.

        Args:
            name: Container name to stop.

        Returns:
            Result object with success status and message.
        """
        if not cls.is_available():
            return Result(False, "Distrobox is not installed.")

        try:
            result = subprocess.run(
                ["distrobox", "stop", name], capture_output=True, text=True, timeout=30
            )

            if result.returncode == 0:
                return Result(True, f"Container '{name}' stopped.")
            else:
                error = result.stderr.strip() or result.stdout.strip()
                return Result(False, f"Failed to stop container: {error}")

        except (subprocess.SubprocessError, OSError) as e:
            return Result(False, f"Error stopping container: {e}")

    @classmethod
    def get_available_images(cls) -> dict[str, str]:
        """
        Get the dictionary of available base images.

        Returns:
            Dict mapping friendly names to full image URLs.
        """
        return cls.AVAILABLE_IMAGES.copy()

    @classmethod
    def export_app_from_container(cls, container_name: str, app_name: str) -> Result:
        """
        Export an application from a container to the host.

        This creates a desktop entry on the host that runs the app inside the container.

        Args:
            container_name: Container to export from.
            app_name: Application binary name to export.

        Returns:
            Result object with success status and message.
        """
        if not cls.is_available():
            return Result(False, "Distrobox is not installed.")

        try:
            result = subprocess.run(
                [
                    "distrobox",
                    "enter",
                    container_name,
                    "--",
                    "distrobox-export",
                    "--app",
                    app_name,
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                return Result(
                    True, f"Application '{app_name}' exported from '{container_name}'."
                )
            else:
                error = result.stderr.strip() or result.stdout.strip()
                return Result(False, f"Failed to export app: {error}")

        except (subprocess.SubprocessError, OSError) as e:
            return Result(False, f"Error exporting app: {e}")

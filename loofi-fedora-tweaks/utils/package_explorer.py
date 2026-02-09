"""
Package Explorer — Unified package search/install/remove.
Part of v16.0 "Horizon".

Supports DNF (traditional), rpm-ostree (atomic), and Flatpak.
"""

import subprocess
import logging
import json
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime, timedelta

from utils.system import SystemManager
from utils.commands import PrivilegedCommand

logger = logging.getLogger(__name__)


@dataclass
class PackageInfo:
    """Information about a package."""
    name: str
    version: str = ""
    repo: str = ""
    size: str = ""
    summary: str = ""
    installed: bool = False
    source: str = ""       # "dnf", "rpm-ostree", "flatpak"
    arch: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "repo": self.repo,
            "size": self.size,
            "summary": self.summary,
            "installed": self.installed,
            "source": self.source,
            "arch": self.arch,
        }


@dataclass
class PackageResult:
    """Result of a package operation."""
    success: bool
    message: str


class PackageExplorer:
    """Unified package search and management across DNF, rpm-ostree, and Flatpak.

    All methods are classmethods. Install/remove use PrivilegedCommand.
    """

    # ---------------------------------------------------------------- search
    @classmethod
    def search(cls, query: str, include_flatpak: bool = True) -> List[PackageInfo]:
        """Search for packages across DNF/rpm-ostree and Flatpak.

        Args:
            query: Search term (name or keyword).
            include_flatpak: Also search Flatpak remotes.

        Returns:
            Combined list of PackageInfo results, sorted by name.
        """
        results: List[PackageInfo] = []
        results.extend(cls._search_dnf(query))
        if include_flatpak:
            results.extend(cls._search_flatpak(query))
        return sorted(results, key=lambda p: (not p.installed, p.name.lower()))

    @classmethod
    def _search_dnf(cls, query: str) -> List[PackageInfo]:
        """Search packages via DNF/rpm-ostree."""
        try:
            # Use dnf even on Atomic — it can still search
            cmd = ["dnf", "search", "--quiet", query]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                return []

            packages: List[PackageInfo] = []
            current_section = ""
            for line in result.stdout.strip().splitlines():
                if not line.strip():
                    continue
                # DNF outputs section headers like "Name Matched: ..." or "Summary Matched: ..."
                if line.startswith("=") or "Matched" in line:
                    current_section = line.strip()
                    continue

                # Lines look like: name.arch : summary
                if " : " in line:
                    name_arch, _, summary = line.partition(" : ")
                    name_arch = name_arch.strip()
                    summary = summary.strip()

                    if "." in name_arch:
                        name, _, arch = name_arch.rpartition(".")
                    else:
                        name = name_arch
                        arch = ""

                    source = "dnf"
                    if SystemManager.is_atomic():
                        source = "rpm-ostree"

                    packages.append(PackageInfo(
                        name=name,
                        summary=summary,
                        arch=arch,
                        source=source,
                        installed=cls._is_rpm_installed(name),
                    ))

            return packages

        except (subprocess.TimeoutExpired, OSError) as exc:
            logger.error("DNF search error: %s", exc)
            return []

    @classmethod
    def _search_flatpak(cls, query: str) -> List[PackageInfo]:
        """Search Flatpak remotes."""
        try:
            cmd = ["flatpak", "search", "--columns=application,version,remotes,description", query]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                return []

            packages: List[PackageInfo] = []
            for line in result.stdout.strip().splitlines():
                if not line.strip():
                    continue
                parts = line.split("\t")
                if len(parts) < 2:
                    continue

                app_id = parts[0].strip()
                version = parts[1].strip() if len(parts) > 1 else ""
                remote = parts[2].strip() if len(parts) > 2 else ""
                desc = parts[3].strip() if len(parts) > 3 else ""

                packages.append(PackageInfo(
                    name=app_id,
                    version=version,
                    repo=remote,
                    summary=desc,
                    source="flatpak",
                    installed=cls._is_flatpak_installed(app_id),
                ))

            return packages

        except (subprocess.TimeoutExpired, OSError) as exc:
            logger.error("Flatpak search error: %s", exc)
            return []

    # -------------------------------------------------------------- install
    @classmethod
    def install(cls, name: str, source: str = "auto") -> PackageResult:
        """Install a package.

        Args:
            name: Package name (or Flatpak app ID).
            source: "dnf", "rpm-ostree", "flatpak", or "auto" (detect).
        """
        if source == "auto":
            source = cls._detect_source(name)

        try:
            if source == "flatpak":
                cmd = ["flatpak", "install", "-y", "--noninteractive", name]
            elif source == "rpm-ostree":
                cmd = ["pkexec", "rpm-ostree", "install", name]
            else:
                binary, args, _ = PrivilegedCommand.dnf("install", name)
                cmd = [binary] + args

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300
            )
            if result.returncode == 0:
                return PackageResult(True, f"Installed {name}")
            else:
                return PackageResult(
                    False, f"Failed to install {name}: {result.stderr.strip()}"
                )
        except subprocess.TimeoutExpired:
            return PackageResult(False, f"Timed out installing {name}")
        except OSError as exc:
            return PackageResult(False, f"Error: {exc}")

    # -------------------------------------------------------------- remove
    @classmethod
    def remove(cls, name: str, source: str = "auto") -> PackageResult:
        """Remove a package.

        Args:
            name: Package name (or Flatpak app ID).
            source: "dnf", "rpm-ostree", "flatpak", or "auto".
        """
        if source == "auto":
            source = cls._detect_source_installed(name)

        try:
            if source == "flatpak":
                cmd = ["flatpak", "uninstall", "-y", "--noninteractive", name]
            elif source == "rpm-ostree":
                cmd = ["pkexec", "rpm-ostree", "uninstall", name]
            else:
                binary, args, _ = PrivilegedCommand.dnf("remove", name)
                cmd = [binary] + args

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300
            )
            if result.returncode == 0:
                return PackageResult(True, f"Removed {name}")
            else:
                return PackageResult(
                    False, f"Failed to remove {name}: {result.stderr.strip()}"
                )
        except subprocess.TimeoutExpired:
            return PackageResult(False, f"Timed out removing {name}")
        except OSError as exc:
            return PackageResult(False, f"Error: {exc}")

    # -------------------------------------------------------- list installed
    @classmethod
    def list_installed(cls, source: str = "all",
                       search: str = "") -> List[PackageInfo]:
        """List installed packages.

        Args:
            source: "dnf", "flatpak", or "all".
            search: Optional substring filter.
        """
        results: List[PackageInfo] = []
        if source in ("dnf", "all"):
            results.extend(cls._list_rpm_installed(search))
        if source in ("flatpak", "all"):
            results.extend(cls._list_flatpak_installed(search))
        return sorted(results, key=lambda p: p.name.lower())

    @classmethod
    def _list_rpm_installed(cls, search: str = "") -> List[PackageInfo]:
        """List installed RPM packages."""
        try:
            cmd = ["rpm", "-qa", "--queryformat",
                   "%{NAME}\t%{VERSION}-%{RELEASE}\t%{ARCH}\t%{SUMMARY}\n"]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                return []

            packages: List[PackageInfo] = []
            src = "rpm-ostree" if SystemManager.is_atomic() else "dnf"
            for line in result.stdout.strip().splitlines():
                parts = line.split("\t")
                if len(parts) < 3:
                    continue
                name = parts[0]
                version = parts[1]
                arch = parts[2]
                summary = parts[3] if len(parts) > 3 else ""

                if search and search.lower() not in name.lower() and search.lower() not in summary.lower():
                    continue

                packages.append(PackageInfo(
                    name=name,
                    version=version,
                    arch=arch,
                    summary=summary,
                    installed=True,
                    source=src,
                ))
            return packages

        except (subprocess.TimeoutExpired, OSError):
            return []

    @classmethod
    def _list_flatpak_installed(cls, search: str = "") -> List[PackageInfo]:
        """List installed Flatpak applications."""
        try:
            cmd = ["flatpak", "list", "--app",
                   "--columns=application,version,origin,description"]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=15
            )
            if result.returncode != 0:
                return []

            packages: List[PackageInfo] = []
            for line in result.stdout.strip().splitlines():
                parts = line.split("\t")
                if len(parts) < 1:
                    continue
                app_id = parts[0].strip()
                version = parts[1].strip() if len(parts) > 1 else ""
                origin = parts[2].strip() if len(parts) > 2 else ""
                desc = parts[3].strip() if len(parts) > 3 else ""

                if search and search.lower() not in app_id.lower() and search.lower() not in desc.lower():
                    continue

                packages.append(PackageInfo(
                    name=app_id,
                    version=version,
                    repo=origin,
                    summary=desc,
                    installed=True,
                    source="flatpak",
                ))
            return packages

        except (subprocess.TimeoutExpired, OSError):
            return []

    # --------------------------------------------------- recently installed
    @classmethod
    def recently_installed(cls, days: int = 30) -> List[PackageInfo]:
        """Get packages installed in the last N days via DNF history."""
        try:
            cmd = ["dnf", "history", "list", "--reverse"]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                return []

            # Parse DNF history for Install actions
            packages: List[PackageInfo] = []
            for line in result.stdout.strip().splitlines():
                if "Install" not in line:
                    continue
                parts = line.split("|")
                if len(parts) < 4:
                    continue
                date_str = parts[2].strip()
                # Try to filter by date
                try:
                    dt = datetime.strptime(date_str.split()[0], "%Y-%m-%d")
                    if datetime.now() - dt > timedelta(days=days):
                        continue
                except (ValueError, IndexError):
                    continue

                action_part = parts[3].strip() if len(parts) > 3 else ""
                packages.append(PackageInfo(
                    name=action_part,
                    summary=f"Installed on {date_str}",
                    installed=True,
                    source="dnf",
                ))

            return packages

        except (subprocess.TimeoutExpired, OSError):
            return []

    # -------------------------------------------------------- package info
    @classmethod
    def get_package_info(cls, name: str) -> Optional[PackageInfo]:
        """Get detailed info for a specific package."""
        try:
            cmd = ["dnf", "info", "--quiet", name]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=15
            )
            if result.returncode != 0:
                return None

            info = PackageInfo(name=name)
            src = "rpm-ostree" if SystemManager.is_atomic() else "dnf"
            info.source = src

            for line in result.stdout.strip().splitlines():
                if ":" not in line:
                    continue
                key, _, val = line.partition(":")
                key = key.strip().lower()
                val = val.strip()

                if key == "name":
                    info.name = val
                elif key == "version":
                    info.version = val
                elif key == "release":
                    info.version += f"-{val}"
                elif key == "architecture" or key == "arch":
                    info.arch = val
                elif key == "size":
                    info.size = val
                elif key in ("summary", "description"):
                    if not info.summary:
                        info.summary = val
                elif key == "repository" or key == "repo":
                    info.repo = val
                    if val.startswith("@"):
                        info.installed = True

            return info

        except (subprocess.TimeoutExpired, OSError):
            return None

    # --------------------------------------------------------- helpers
    @classmethod
    def _is_rpm_installed(cls, name: str) -> bool:
        """Check if an RPM package is installed."""
        try:
            result = subprocess.run(
                ["rpm", "-q", name],
                capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, OSError):
            return False

    @classmethod
    def _is_flatpak_installed(cls, app_id: str) -> bool:
        """Check if a Flatpak app is installed."""
        try:
            result = subprocess.run(
                ["flatpak", "info", app_id],
                capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, OSError):
            return False

    @classmethod
    def _detect_source(cls, name: str) -> str:
        """Auto-detect the best source for installing a package."""
        # If name looks like a Flatpak app ID (e.g. org.gnome.Calculator)
        if "." in name and name.count(".") >= 2:
            return "flatpak"
        if SystemManager.is_atomic():
            return "rpm-ostree"
        return "dnf"

    @classmethod
    def _detect_source_installed(cls, name: str) -> str:
        """Detect which source an installed package came from."""
        if cls._is_flatpak_installed(name):
            return "flatpak"
        if SystemManager.is_atomic():
            return "rpm-ostree"
        return "dnf"

    # --------------------------------------------------------- summary
    @classmethod
    def get_counts(cls) -> dict:
        """Get a quick summary of installed package counts."""
        rpm_count = 0
        flatpak_count = 0
        try:
            result = subprocess.run(
                ["rpm", "-qa"], capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0:
                rpm_count = len(result.stdout.strip().splitlines())
        except (subprocess.TimeoutExpired, OSError):
            pass

        try:
            result = subprocess.run(
                ["flatpak", "list", "--app"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                flatpak_count = len(result.stdout.strip().splitlines())
        except (subprocess.TimeoutExpired, OSError):
            pass

        return {
            "rpm": rpm_count,
            "flatpak": flatpak_count,
            "total": rpm_count + flatpak_count,
        }

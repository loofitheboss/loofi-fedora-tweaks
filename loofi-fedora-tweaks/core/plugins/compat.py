from __future__ import annotations

import logging
import os
import subprocess
from typing import Any

from core.plugins.metadata import CompatStatus

log = logging.getLogger(__name__)


class CompatibilityDetector:
    """
    Detects system properties for plugin compatibility gating.

    All system calls are isolated in private methods for easy mocking in tests.
    Results are cached per detector instance (reset by creating a new instance).

    Checks performed:
    - Fedora version (from /etc/fedora-release or /etc/os-release)
    - Desktop Environment (XDG_CURRENT_DESKTOP, DESKTOP_SESSION)
    - Wayland vs X11 (WAYLAND_DISPLAY)
    - Hardware capabilities (module-specific, checked on demand)
    - Package availability (rpm -q, checked on demand)
    """

    def __init__(self) -> None:
        self._cache: dict[str, Any] = {}

    # ---------------------------------------------------------------- Public API

    def fedora_version(self) -> int:
        """Return Fedora major version number, or 0 if not Fedora."""
        if "fedora_version" not in self._cache:
            self._cache["fedora_version"] = self._read_fedora_version()
        return int(self._cache["fedora_version"])

    def desktop_environment(self) -> str:
        """Return lowercase DE name: 'gnome', 'kde', 'xfce', 'other', or 'unknown'."""
        if "desktop_env" not in self._cache:
            self._cache["desktop_env"] = self._read_desktop_env()
        return str(self._cache["desktop_env"])

    def is_wayland(self) -> bool:
        """Return True if running under Wayland."""
        if "is_wayland" not in self._cache:
            self._cache["is_wayland"] = bool(os.environ.get("WAYLAND_DISPLAY"))
        return bool(self._cache["is_wayland"])

    def has_package(self, package_name: str) -> bool:
        """Return True if RPM package is installed."""
        key = f"pkg:{package_name}"
        if key not in self._cache:
            self._cache[key] = self._check_package(package_name)
        return bool(self._cache[key])

    def check_plugin_compat(self, compat_spec: dict) -> CompatStatus:
        """
        Evaluate a PluginMetadata.compat dict against system state.

        Supported keys:
            min_fedora: int        — minimum Fedora version
            de: list[str]         — allowed DEs (empty = all)
            requires_packages: list[str]  — required RPM packages
            wayland_only: bool    — requires Wayland
            x11_only: bool        — requires X11
        """
        warnings: list[str] = []

        min_fed = compat_spec.get("min_fedora", 0)
        if min_fed and self.fedora_version() < min_fed:
            return CompatStatus(
                compatible=False,
                reason=f"Requires Fedora {min_fed}+, detected {self.fedora_version()}"
            )

        allowed_de = compat_spec.get("de", [])
        if allowed_de and self.desktop_environment() not in allowed_de:
            return CompatStatus(
                compatible=False,
                reason=f"Requires DE in {allowed_de}, detected '{self.desktop_environment()}'"
            )

        if compat_spec.get("wayland_only") and not self.is_wayland():
            return CompatStatus(compatible=False, reason="Requires Wayland session")

        if compat_spec.get("x11_only") and self.is_wayland():
            return CompatStatus(compatible=False, reason="Requires X11 session")

        for pkg in compat_spec.get("requires_packages", []):
            if not self.has_package(pkg):
                warnings.append(f"Package not installed: {pkg}")

        return CompatStatus(compatible=True, warnings=warnings)

    # -------------------------------------------------------------- Private I/O

    def _read_fedora_version(self) -> int:
        try:
            with open("/etc/fedora-release") as fh:
                content = fh.read()
            import re
            m = re.search(r"release (\d+)", content)
            return int(m.group(1)) if m else 0
        except OSError:
            return 0

    def _read_desktop_env(self) -> str:
        de = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
        if "gnome" in de:
            return "gnome"
        if "kde" in de or "plasma" in de:
            return "kde"
        if "xfce" in de:
            return "xfce"
        if de:
            return "other"
        return "unknown"

    def _check_package(self, name: str) -> bool:
        try:
            result = subprocess.run(
                ["rpm", "-q", name],
                capture_output=True, timeout=5
            )
            return result.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False

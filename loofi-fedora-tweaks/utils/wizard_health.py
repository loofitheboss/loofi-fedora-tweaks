"""Wizard health checks extracted from UI.

Provides reusable health-check helpers for first-run onboarding without
running subprocess calls in UI modules.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import Dict, List, Tuple

from services.system.system import SystemManager

from utils.log import get_logger

logger = get_logger(__name__)

HealthCheckTuple = Tuple[str, str, str]


class WizardHealth:
    """Collect system health results for first-run wizard recommendations."""

    @staticmethod
    def run_health_checks() -> Tuple[List[HealthCheckTuple], Dict[str, object]]:
        """Run all health checks.

        Returns:
            Tuple containing a display-oriented check list and a machine-readable
            results dictionary consumed by recommendation logic.
        """
        checks: List[HealthCheckTuple] = []
        results: Dict[str, object] = {}

        WizardHealth._check_disk_space(checks, results)
        WizardHealth._check_package_state(checks, results)
        WizardHealth._check_firewall(checks, results)
        WizardHealth._check_backup_tool(checks, results)
        WizardHealth._check_selinux(checks, results)

        return checks, results

    @staticmethod
    def _check_disk_space(
        checks: List[HealthCheckTuple], results: Dict[str, object]
    ) -> None:
        try:
            stat = os.statvfs("/")
            free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
            total_gb = (stat.f_blocks * stat.f_frsize) / (1024**3)
            pct_used = ((total_gb - free_gb) / total_gb * 100) if total_gb else 0
            if free_gb < 5:
                checks.append(
                    (
                        "⚠️",
                        f"Low disk space: {free_gb:.1f} GB free ({pct_used:.0f}% used)",
                        "warning",
                    )
                )
            else:
                checks.append(
                    (
                        "✅",
                        f"Disk space OK: {free_gb:.1f} GB free ({pct_used:.0f}% used)",
                        "ok",
                    )
                )
            results["disk_free_gb"] = round(free_gb, 1)
        except OSError:
            checks.append(("❓", "Could not check disk space", "unknown"))

    @staticmethod
    def _check_package_state(
        checks: List[HealthCheckTuple], results: Dict[str, object]
    ) -> None:
        package_manager = SystemManager.get_package_manager()
        if package_manager == "dnf":
            WizardHealth._check_dnf_state(checks, results, package_manager)
            return
        WizardHealth._check_ostree_state(checks, results)

    @staticmethod
    def _check_dnf_state(
        checks: List[HealthCheckTuple],
        results: Dict[str, object],
        package_manager: str,
    ) -> None:
        if not shutil.which(package_manager):
            checks.append(("ℹ️", "DNF not found (atomic system?)", "info"))
            return

        try:
            result = subprocess.run(
                [package_manager, "check", "--duplicates"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                checks.append(("✅", "Package state healthy (no duplicates)", "ok"))
            else:
                checks.append(("⚠️", "Package issues detected (duplicates found)", "warning"))
            results["pkg_healthy"] = result.returncode == 0
        except (subprocess.TimeoutExpired, OSError) as exc:
            logger.debug("Failed to check dnf package state: %s", exc)
            checks.append(("❓", "Could not check package state", "unknown"))

    @staticmethod
    def _check_ostree_state(
        checks: List[HealthCheckTuple], results: Dict[str, object]
    ) -> None:
        try:
            result = subprocess.run(
                ["rpm-ostree", "status"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                checks.append(("✅", "Package state healthy (rpm-ostree status)", "ok"))
                results["pkg_healthy"] = True
            else:
                checks.append(("⚠️", "Package issues detected (rpm-ostree status failed)", "warning"))
                results["pkg_healthy"] = False
        except (subprocess.TimeoutExpired, OSError) as exc:
            logger.debug("Failed to check rpm-ostree package state: %s", exc)
            checks.append(("❓", "Could not check package state", "unknown"))

    @staticmethod
    def _check_firewall(
        checks: List[HealthCheckTuple], results: Dict[str, object]
    ) -> None:
        if shutil.which("firewall-cmd"):
            try:
                result = subprocess.run(
                    ["firewall-cmd", "--state"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                running = "running" in result.stdout.lower()
                if running:
                    checks.append(("✅", "Firewall is running", "ok"))
                else:
                    checks.append(("⚠️", "Firewall is NOT running", "warning"))
                results["firewall_running"] = running
            except (subprocess.TimeoutExpired, OSError) as exc:
                logger.debug("Failed to check firewall status: %s", exc)
                checks.append(("❓", "Could not check firewall status", "unknown"))
        else:
            checks.append(("❓", "firewall-cmd not found", "unknown"))

    @staticmethod
    def _check_backup_tool(
        checks: List[HealthCheckTuple], results: Dict[str, object]
    ) -> None:
        if shutil.which("timeshift") or shutil.which("snapper"):
            tool = "timeshift" if shutil.which("timeshift") else "snapper"
            checks.append(("✅", f"Backup tool available: {tool}", "ok"))
            results["backup_tool"] = tool
        else:
            checks.append(("⚠️", "No backup tool installed (timeshift/snapper)", "warning"))
            results["backup_tool"] = None

    @staticmethod
    def _check_selinux(
        checks: List[HealthCheckTuple], results: Dict[str, object]
    ) -> None:
        try:
            result = subprocess.run(
                ["getenforce"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            mode = result.stdout.strip()
            if mode == "Enforcing":
                checks.append(("✅", f"SELinux: {mode}", "ok"))
            else:
                checks.append(("ℹ️", f"SELinux: {mode}", "info"))
            results["selinux"] = mode
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.debug("Failed to check SELinux: %s", exc)
            checks.append(("❓", "Could not check SELinux", "unknown"))

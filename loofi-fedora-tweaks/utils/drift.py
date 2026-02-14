"""
Configuration Drift Detection - Monitor for unexpected system changes.
Tracks system state and alerts when it deviates from applied presets.
"""

import json
import hashlib
import logging
import subprocess
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class DriftItem:
    """A single configuration item that has drifted."""
    category: str  # kernel, packages, services, etc.
    setting: str
    expected: str
    actual: str
    severity: str  # info, warning, critical


@dataclass
class DriftReport:
    """Full drift detection report."""
    preset_name: str
    applied_at: str
    checked_at: str
    is_drifted: bool
    drift_count: int
    items: List[DriftItem]


@dataclass
class SystemSnapshot:
    """A snapshot of system configuration state."""
    timestamp: str
    preset_name: str
    preset_hash: str

    # State hashes
    kernel_params_hash: str
    installed_packages_hash: str
    enabled_services_hash: str
    dnf_config_hash: str
    sysctl_hash: str

    # Actual values for comparison
    kernel_params: List[str]
    layered_packages: List[str]
    user_services: List[str]


class DriftDetector:
    """
    Detects configuration drift from applied presets.

    Workflow:
    1. When preset is applied, save a SystemSnapshot
    2. Periodically compare current state to snapshot
    3. Alert user if significant drift is detected
    """

    SNAPSHOTS_DIR = Path.home() / ".local/share/loofi-fedora-tweaks/snapshots"
    CURRENT_SNAPSHOT = SNAPSHOTS_DIR / "current.json"

    def __init__(self):
        self.SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    def capture_snapshot(self, preset_name: str = "manual") -> SystemSnapshot:
        """
        Capture current system state as a snapshot.

        Args:
            preset_name: Name of the preset being applied.

        Returns:
            SystemSnapshot of current system state.
        """
        timestamp = datetime.now().isoformat()

        # Gather system state
        kernel_params = self._get_kernel_params()
        layered_packages = self._get_layered_packages()
        user_services = self._get_user_services()
        dnf_config = self._get_dnf_config()
        sysctl_values = self._get_sysctl_values()

        snapshot = SystemSnapshot(
            timestamp=timestamp,
            preset_name=preset_name,
            preset_hash=self._hash_string(preset_name + timestamp),
            kernel_params_hash=self._hash_list(kernel_params),
            installed_packages_hash=self._hash_list(layered_packages),
            enabled_services_hash=self._hash_list(user_services),
            dnf_config_hash=self._hash_string(dnf_config),
            sysctl_hash=self._hash_string(sysctl_values),
            kernel_params=kernel_params,
            layered_packages=layered_packages,
            user_services=user_services
        )

        return snapshot

    def save_snapshot(self, snapshot: SystemSnapshot) -> bool:
        """Save a snapshot as the current baseline."""
        try:
            with open(self.CURRENT_SNAPSHOT, "w") as f:
                json.dump(asdict(snapshot), f, indent=2)
            return True
        except (OSError, json.JSONDecodeError) as e:
            logger.debug("Failed to save snapshot: %s", e)
            return False

    def load_snapshot(self) -> Optional[SystemSnapshot]:
        """Load the current baseline snapshot."""
        if not self.CURRENT_SNAPSHOT.exists():
            return None

        try:
            with open(self.CURRENT_SNAPSHOT, "r") as f:
                data = json.load(f)
            return SystemSnapshot(**data)
        except (OSError, json.JSONDecodeError, TypeError) as e:
            logger.debug("Failed to load snapshot: %s", e)
            return None

    def check_drift(self) -> Optional[DriftReport]:
        """
        Check for configuration drift from the saved snapshot.

        Returns:
            DriftReport if there's a baseline, None otherwise.
        """
        baseline = self.load_snapshot()
        if not baseline:
            return None

        # Capture current state
        current = self.capture_snapshot(baseline.preset_name)

        # Compare states
        drift_items = []

        # Check kernel parameters
        if current.kernel_params_hash != baseline.kernel_params_hash:
            added = set(current.kernel_params) - set(baseline.kernel_params)
            removed = set(baseline.kernel_params) - set(current.kernel_params)

            for param in added:
                drift_items.append(DriftItem(
                    category="kernel",
                    setting=param,
                    expected="not set",
                    actual="set",
                    severity="warning"
                ))

            for param in removed:
                drift_items.append(DriftItem(
                    category="kernel",
                    setting=param,
                    expected="set",
                    actual="not set",
                    severity="warning"
                ))

        # Check packages
        if current.installed_packages_hash != baseline.installed_packages_hash:
            added = set(current.layered_packages) - set(baseline.layered_packages)
            removed = set(baseline.layered_packages) - set(current.layered_packages)

            for pkg in added:
                drift_items.append(DriftItem(
                    category="packages",
                    setting=pkg,
                    expected="not installed",
                    actual="installed",
                    severity="info"
                ))

            for pkg in removed:
                drift_items.append(DriftItem(
                    category="packages",
                    setting=pkg,
                    expected="installed",
                    actual="not installed",
                    severity="warning"
                ))

        # Check services
        if current.enabled_services_hash != baseline.enabled_services_hash:
            added = set(current.user_services) - set(baseline.user_services)
            removed = set(baseline.user_services) - set(current.user_services)

            for svc in added:
                drift_items.append(DriftItem(
                    category="services",
                    setting=svc,
                    expected="disabled",
                    actual="enabled",
                    severity="info"
                ))

            for svc in removed:
                drift_items.append(DriftItem(
                    category="services",
                    setting=svc,
                    expected="enabled",
                    actual="disabled",
                    severity="warning"
                ))

        return DriftReport(
            preset_name=baseline.preset_name,
            applied_at=baseline.timestamp,
            checked_at=datetime.now().isoformat(),
            is_drifted=len(drift_items) > 0,
            drift_count=len(drift_items),
            items=drift_items
        )

    def clear_baseline(self) -> bool:
        """Clear the current baseline snapshot."""
        try:
            if self.CURRENT_SNAPSHOT.exists():
                self.CURRENT_SNAPSHOT.unlink()
            return True
        except OSError as e:
            logger.debug("Failed to clear baseline: %s", e)
            return False

    # System state gathering methods

    def _get_kernel_params(self) -> List[str]:
        """Get current kernel command line parameters."""
        try:
            with open("/proc/cmdline", "r") as f:
                return f.read().strip().split()
        except Exception as e:
            logger.debug("Failed to read kernel params: %s", e)
            return []

    def _get_layered_packages(self) -> List[str]:
        """Get list of layered packages (rpm-ostree or manual installs)."""
        try:
            # Try rpm-ostree first
            result = subprocess.run(
                ["rpm-ostree", "status", "--json"],
                capture_output=True, text=True, check=False,
                timeout=600,
            )
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                deployments = data.get("deployments", [])
                if deployments:
                    return list(deployments[0].get("requested-packages", []))

            # Fallback: get manually installed packages
            result = subprocess.run(
                ["dnf", "repoquery", "--userinstalled", "--qf", "%{name}"],
                capture_output=True, text=True, check=False,
                timeout=600,
            )
            if result.returncode == 0:
                return result.stdout.strip().split("\n")[:100]  # Limit

        except (subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to get layered packages: %s", e)
        return []

    def _get_user_services(self) -> List[str]:
        """Get list of user-enabled systemd services."""
        try:
            result = subprocess.run(
                ["systemctl", "--user", "list-unit-files", "--state=enabled", "--no-legend"],
                capture_output=True, text=True, check=False,
                timeout=60,
            )
            if result.returncode == 0:
                services = []
                for line in result.stdout.strip().split("\n"):
                    if line.strip():
                        services.append(line.split()[0])
                return services
        except (subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to get user services: %s", e)
        return []

    def _get_dnf_config(self) -> str:
        """Get DNF configuration content."""
        try:
            with open("/etc/dnf/dnf.conf", "r") as f:
                return f.read()
        except OSError as e:
            logger.debug("Failed to read dnf config: %s", e)
            return ""

    def _get_sysctl_values(self) -> str:
        """Get relevant sysctl values."""
        keys = [
            "vm.swappiness",
            "net.ipv4.tcp_congestion_control",
            "net.core.default_qdisc"
        ]

        values = []
        for key in keys:
            try:
                result = subprocess.run(
                    ["sysctl", "-n", key],
                    capture_output=True, text=True, check=False,
                    timeout=15,
                )
                if result.returncode == 0:
                    values.append(f"{key}={result.stdout.strip()}")
            except (subprocess.SubprocessError, OSError) as e:
                logger.debug("Failed to read sysctl %s: %s", key, e)

        return "\n".join(values)

    def _hash_string(self, s: str) -> str:
        """Create SHA256 hash of a string."""
        return hashlib.sha256(s.encode()).hexdigest()[:16]

    def _hash_list(self, lst: List[str]) -> str:
        """Create SHA256 hash of a sorted list."""
        return self._hash_string("\n".join(sorted(lst)))

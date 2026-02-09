"""
Service Explorer — Full systemd service browser.
Part of v16.0 "Horizon".

Goes beyond the gaming-focused ServiceManager to provide full systemd
service browsing, control, and inspection for both system and user scopes.
"""

import subprocess
import logging
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum

from utils.commands import PrivilegedCommand

logger = logging.getLogger(__name__)


class ServiceScope(Enum):
    """Systemd unit scope."""
    SYSTEM = "system"
    USER = "user"


class ServiceState(Enum):
    """Active state of a service."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"
    ACTIVATING = "activating"
    DEACTIVATING = "deactivating"
    UNKNOWN = "unknown"


@dataclass
class ServiceInfo:
    """Rich service information."""
    name: str
    description: str = ""
    state: ServiceState = ServiceState.UNKNOWN
    sub_state: str = ""
    enabled: str = ""          # enabled, disabled, static, masked, alias
    scope: ServiceScope = ServiceScope.SYSTEM
    memory_bytes: int = 0
    main_pid: int = 0
    active_enter: str = ""     # timestamp when last activated
    fragment_path: str = ""    # path to unit file

    @property
    def is_running(self) -> bool:
        return self.state == ServiceState.ACTIVE

    @property
    def is_failed(self) -> bool:
        return self.state == ServiceState.FAILED

    @property
    def is_enabled(self) -> bool:
        return self.enabled in ("enabled", "enabled-runtime")

    @property
    def is_masked(self) -> bool:
        return self.enabled == "masked"

    @property
    def memory_human(self) -> str:
        """Human-readable memory string."""
        if self.memory_bytes <= 0:
            return "—"
        if self.memory_bytes < 1024:
            return f"{self.memory_bytes} B"
        elif self.memory_bytes < 1024 ** 2:
            return f"{self.memory_bytes / 1024:.1f} KB"
        elif self.memory_bytes < 1024 ** 3:
            return f"{self.memory_bytes / (1024 ** 2):.1f} MB"
        else:
            return f"{self.memory_bytes / (1024 ** 3):.2f} GB"

    def to_dict(self) -> dict:
        """Serialize for JSON output."""
        return {
            "name": self.name,
            "description": self.description,
            "state": self.state.value,
            "sub_state": self.sub_state,
            "enabled": self.enabled,
            "scope": self.scope.value,
            "memory": self.memory_human,
            "memory_bytes": self.memory_bytes,
            "main_pid": self.main_pid,
            "active_enter": self.active_enter,
            "fragment_path": self.fragment_path,
        }


@dataclass
class ServiceResult:
    """Result of a service operation."""
    success: bool
    message: str


class ServiceExplorer:
    """Full systemd service browser and controller.

    All methods are classmethods for consistency with the project pattern.
    System-scope operations that mutate state use pkexec via PrivilegedCommand.
    """

    # ------------------------------------------------------------------ list
    @classmethod
    def list_services(cls, scope: ServiceScope = ServiceScope.SYSTEM,
                      filter_state: Optional[str] = None,
                      search: str = "") -> List[ServiceInfo]:
        """List systemd service units.

        Args:
            scope: SYSTEM or USER.
            filter_state: "active", "inactive", "failed", or None for all.
            search: Substring filter on name or description.

        Returns:
            List of ServiceInfo objects sorted by name.
        """
        try:
            cmd = ["systemctl"]
            if scope == ServiceScope.USER:
                cmd.append("--user")
            cmd.extend([
                "list-units", "--type=service", "--all",
                "--no-pager", "--plain", "--no-legend",
            ])

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                logger.warning("systemctl list-units failed: %s", result.stderr)
                return []

            services: List[ServiceInfo] = []
            for line in result.stdout.strip().splitlines():
                if not line.strip():
                    continue
                parts = line.split()
                if len(parts) < 4:
                    continue

                name = parts[0].replace(".service", "")
                active = parts[2].lower()
                sub = parts[3].lower()
                desc = " ".join(parts[4:]) if len(parts) > 4 else ""

                state_map = {
                    "active": ServiceState.ACTIVE,
                    "inactive": ServiceState.INACTIVE,
                    "failed": ServiceState.FAILED,
                    "activating": ServiceState.ACTIVATING,
                    "deactivating": ServiceState.DEACTIVATING,
                }
                state = state_map.get(active, ServiceState.UNKNOWN)

                if filter_state and state.value != filter_state:
                    continue

                if search and search.lower() not in name.lower() and search.lower() not in desc.lower():
                    continue

                services.append(ServiceInfo(
                    name=name,
                    description=desc,
                    state=state,
                    sub_state=sub,
                    scope=scope,
                ))

            # Enrich with enabled status in bulk
            cls._enrich_enabled(services, scope)

            return sorted(services, key=lambda s: s.name)

        except subprocess.TimeoutExpired:
            logger.error("Timed out listing services")
            return []
        except OSError as exc:
            logger.error("OS error listing services: %s", exc)
            return []

    @classmethod
    def _enrich_enabled(cls, services: List[ServiceInfo],
                        scope: ServiceScope) -> None:
        """Batch-query the enabled state for a list of services."""
        if not services:
            return
        try:
            cmd = ["systemctl"]
            if scope == ServiceScope.USER:
                cmd.append("--user")
            cmd.append("is-enabled")
            cmd.extend(f"{s.name}.service" for s in services)

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )
            lines = result.stdout.strip().splitlines()
            for i, svc in enumerate(services):
                if i < len(lines):
                    svc.enabled = lines[i].strip()
        except (subprocess.TimeoutExpired, OSError):
            pass

    # ------------------------------------------------------------ details
    @classmethod
    def get_service_details(cls, name: str,
                            scope: ServiceScope = ServiceScope.SYSTEM) -> ServiceInfo:
        """Get rich details for a single service using systemctl show."""
        info = ServiceInfo(name=name, scope=scope)
        try:
            cmd = ["systemctl"]
            if scope == ServiceScope.USER:
                cmd.append("--user")
            cmd.extend([
                "show", f"{name}.service", "--no-pager",
                "--property=Description,ActiveState,SubState,UnitFileState,"
                "MemoryCurrent,MainPID,ActiveEnterTimestamp,FragmentPath",
            ])
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                return info

            props = {}
            for line in result.stdout.strip().splitlines():
                if "=" in line:
                    key, _, val = line.partition("=")
                    props[key.strip()] = val.strip()

            info.description = props.get("Description", "")
            active = props.get("ActiveState", "unknown").lower()
            state_map = {
                "active": ServiceState.ACTIVE,
                "inactive": ServiceState.INACTIVE,
                "failed": ServiceState.FAILED,
                "activating": ServiceState.ACTIVATING,
                "deactivating": ServiceState.DEACTIVATING,
            }
            info.state = state_map.get(active, ServiceState.UNKNOWN)
            info.sub_state = props.get("SubState", "")
            info.enabled = props.get("UnitFileState", "")
            info.active_enter = props.get("ActiveEnterTimestamp", "")
            info.fragment_path = props.get("FragmentPath", "")

            mem = props.get("MemoryCurrent", "")
            if mem and mem != "[not set]":
                try:
                    info.memory_bytes = int(mem)
                except ValueError:
                    pass

            pid = props.get("MainPID", "0")
            try:
                info.main_pid = int(pid)
            except ValueError:
                pass

        except (subprocess.TimeoutExpired, OSError) as exc:
            logger.error("Error getting details for %s: %s", name, exc)
        return info

    # --------------------------------------------------------- journal logs
    @classmethod
    def get_service_logs(cls, name: str,
                         scope: ServiceScope = ServiceScope.SYSTEM,
                         lines: int = 50) -> str:
        """Get recent journal logs for a service."""
        try:
            cmd = ["journalctl"]
            if scope == ServiceScope.USER:
                cmd.append("--user")
            cmd.extend([
                "-u", f"{name}.service",
                "--no-pager", "-n", str(lines),
                "--output=short-iso",
            ])
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=15
            )
            return result.stdout if result.returncode == 0 else result.stderr
        except (subprocess.TimeoutExpired, OSError) as exc:
            return f"Error reading logs: {exc}"

    # --------------------------------------------------------- actions
    @classmethod
    def start_service(cls, name: str,
                      scope: ServiceScope = ServiceScope.SYSTEM) -> ServiceResult:
        """Start a service."""
        return cls._run_action("start", name, scope)

    @classmethod
    def stop_service(cls, name: str,
                     scope: ServiceScope = ServiceScope.SYSTEM) -> ServiceResult:
        """Stop a service."""
        return cls._run_action("stop", name, scope)

    @classmethod
    def restart_service(cls, name: str,
                        scope: ServiceScope = ServiceScope.SYSTEM) -> ServiceResult:
        """Restart a service."""
        return cls._run_action("restart", name, scope)

    @classmethod
    def enable_service(cls, name: str,
                       scope: ServiceScope = ServiceScope.SYSTEM) -> ServiceResult:
        """Enable a service (start on boot)."""
        return cls._run_action("enable", name, scope)

    @classmethod
    def disable_service(cls, name: str,
                        scope: ServiceScope = ServiceScope.SYSTEM) -> ServiceResult:
        """Disable a service."""
        return cls._run_action("disable", name, scope)

    @classmethod
    def mask_service(cls, name: str,
                     scope: ServiceScope = ServiceScope.SYSTEM) -> ServiceResult:
        """Mask a service (prevent starting)."""
        return cls._run_action("mask", name, scope)

    @classmethod
    def unmask_service(cls, name: str,
                       scope: ServiceScope = ServiceScope.SYSTEM) -> ServiceResult:
        """Unmask a service."""
        return cls._run_action("unmask", name, scope)

    # --------------------------------------------------------- internal
    @classmethod
    def _run_action(cls, action: str, name: str,
                    scope: ServiceScope) -> ServiceResult:
        """Execute a systemctl action on a service."""
        try:
            cmd: list[str] = []
            if scope == ServiceScope.SYSTEM:
                binary, args, _ = PrivilegedCommand.systemctl(action, f"{name}.service")
                cmd = [binary] + args
            else:
                cmd = ["systemctl", "--user", action, f"{name}.service"]

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                verb = action.capitalize()
                past = {"Start": "Started", "Stop": "Stopped",
                        "Restart": "Restarted", "Enable": "Enabled",
                        "Disable": "Disabled", "Mask": "Masked",
                        "Unmask": "Unmasked"}.get(verb, verb)
                return ServiceResult(True, f"{past} {name}")
            else:
                return ServiceResult(
                    False,
                    f"Failed to {action} {name}: {result.stderr.strip()}"
                )
        except subprocess.TimeoutExpired:
            return ServiceResult(False, f"Timed out trying to {action} {name}")
        except OSError as exc:
            return ServiceResult(False, f"Error: {exc}")

    # --------------------------------------------------------- summary
    @classmethod
    def get_summary(cls, scope: ServiceScope = ServiceScope.SYSTEM) -> dict:
        """Get a quick summary: total, active, failed, inactive counts."""
        services = cls.list_services(scope)
        total = len(services)
        active = sum(1 for s in services if s.state == ServiceState.ACTIVE)
        failed = sum(1 for s in services if s.state == ServiceState.FAILED)
        inactive = sum(1 for s in services if s.state == ServiceState.INACTIVE)
        return {
            "total": total,
            "active": active,
            "failed": failed,
            "inactive": inactive,
            "scope": scope.value,
        }

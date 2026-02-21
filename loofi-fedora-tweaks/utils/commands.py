"""
Centralized command builder for privileged operations.
Part of v11.0 "Aurora Update", hardened in v35.0.0 "Fortress".

Replaces inconsistent pkexec command construction across multiple files.
Ensures all privileged commands use argument arrays (never shell strings)
to prevent command injection.

v35.0.0: Auto-audit logging via execute_and_log(), POLKIT_MAP.
"""

import functools
import re
import subprocess
from typing import Any, Callable, Dict, List, Optional, Tuple

from services.system import SystemManager

from utils.audit import AuditLogger

CommandTuple = Tuple[str, List[str], str]

# --- Polkit Action ID Mapping ---

POLKIT_MAP: Dict[str, str] = {
    "dnf": "org.loofi.fedora-tweaks.package-manage",
    "rpm-ostree": "org.loofi.fedora-tweaks.ostree-manage",
    "systemctl": "org.loofi.fedora-tweaks.service-manage",
    "sysctl": "org.loofi.fedora-tweaks.kernel",
    "fwupdmgr": "org.loofi.fedora-tweaks.hardware-settings",
    "journalctl": "org.loofi.fedora-tweaks.system-cleanup",
    "fstrim": "org.loofi.fedora-tweaks.storage",
    "rpm": "org.loofi.fedora-tweaks.package-manage",
    "firewall-cmd": "org.loofi.fedora-tweaks.firewall",
    "nmcli": "org.loofi.fedora-tweaks.network",
    "tee": "org.loofi.fedora-tweaks.security",
    "flatpak": "org.loofi.fedora-tweaks.package-manage",
}

# --- Parameter Validation ---

# Path traversal patterns to detect
_PATH_TRAVERSAL_RE = re.compile(r"(^|/)\.\.(/|$)")


def _check_path_traversal(value: str) -> bool:
    """Return True if value contains path traversal sequences."""
    return bool(_PATH_TRAVERSAL_RE.search(value))


def validated_action(schema: Dict[str, Dict[str, Any]]) -> Callable:
    """Decorator to validate PrivilegedCommand method parameters.

    Schema format:
        { "param_name": {"type": str, "required": bool, "min_len": int, "pattern": re} }

    Validates:
    - Required parameters are present and non-empty
    - Type matches the declared type
    - No path traversal in string values
    - Custom constraints (min_len, pattern, choices)

    On failure: raises ValidationError and logs to audit.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Build param map from positional + keyword args
            import inspect

            from utils.errors import ValidationError

            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            param_map = dict(bound.arguments)

            audit = AuditLogger()
            action_name = f"PrivilegedCommand.{func.__name__}"

            for pname, constraints in schema.items():
                value = param_map.get(pname)

                # Required check
                if constraints.get("required", False):
                    if value is None or (
                        isinstance(value, str) and value.strip() == ""
                    ):
                        audit.log_validation_failure(
                            action=action_name,
                            param=pname,
                            detail="Required parameter is empty or missing",
                            params=param_map,
                        )
                        raise ValidationError(
                            param=pname,
                            detail="Required parameter is empty or missing",
                        )

                if value is None:
                    continue

                # Type check
                expected_type = constraints.get("type")
                if expected_type and not isinstance(value, expected_type):
                    audit.log_validation_failure(
                        action=action_name,
                        param=pname,
                        detail=f"Expected {expected_type.__name__}, got {type(value).__name__}",
                        params=param_map,
                    )
                    raise ValidationError(
                        param=pname,
                        detail=f"Expected {expected_type.__name__}, got {type(value).__name__}",
                    )

                # Path traversal check for strings
                if isinstance(value, str) and _check_path_traversal(value):
                    audit.log_validation_failure(
                        action=action_name,
                        param=pname,
                        detail="Path traversal detected",
                        params=param_map,
                    )
                    raise ValidationError(
                        param=pname,
                        detail="Path traversal detected",
                    )

                # Min length
                min_len = constraints.get("min_len")
                if min_len and isinstance(value, str) and len(value) < min_len:
                    audit.log_validation_failure(
                        action=action_name,
                        param=pname,
                        detail=f"Value too short (min {min_len})",
                        params=param_map,
                    )
                    raise ValidationError(
                        param=pname,
                        detail=f"Value too short (min {min_len})",
                    )

                # Choices check
                choices = constraints.get("choices")
                if choices and value not in choices:
                    audit.log_validation_failure(
                        action=action_name,
                        param=pname,
                        detail=f"Invalid choice '{value}', expected one of {choices}",
                        params=param_map,
                    )
                    raise ValidationError(
                        param=pname,
                        detail=f"Invalid choice '{value}', expected one of {choices}",
                    )

            return func(*args, **kwargs)

        return wrapper

    return decorator


class PrivilegedCommand:
    """Safe builder for pkexec-wrapped system commands."""

    @staticmethod
    def execute_and_log(
        cmd_tuple: CommandTuple,
        timeout: int = 60,
        dry_run: bool = False,
        action_name: Optional[str] = None,
    ) -> subprocess.CompletedProcess:
        """Execute a CommandTuple and auto-log to audit.

        Args:
            cmd_tuple: (binary, args, description) from any builder method.
            timeout: Subprocess timeout in seconds.
            dry_run: If True, log but do not execute.
            action_name: Override action name for audit (auto-derived if None).

        Returns:
            CompletedProcess result (or a stub with returncode=-1 for dry_run).
        """
        binary, args, desc = cmd_tuple
        cmd = [binary] + args

        # Derive action name from command if not provided
        if action_name is None:
            action_name = PrivilegedCommand._derive_action_name(binary, args)

        audit = AuditLogger()
        params = {"cmd": cmd, "description": desc}

        if dry_run:
            audit.log(action=action_name, params=params, exit_code=None, dry_run=True)
            return subprocess.CompletedProcess(
                args=cmd, returncode=-1, stdout="", stderr=""
            )

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )
            audit.log(
                action=action_name,
                params=params,
                exit_code=result.returncode,
                stderr=result.stderr,
            )
            return result
        except subprocess.TimeoutExpired:
            from utils.errors import CommandTimeoutError

            audit.log(
                action=action_name,
                params=params,
                exit_code=-1,
                stderr=f"TIMEOUT after {timeout}s",
            )
            raise CommandTimeoutError(cmd=" ".join(cmd), timeout=timeout)

    @staticmethod
    def _derive_action_name(binary: str, args: List[str]) -> str:
        """Derive a human-readable action name from command components."""
        if not args:
            return binary
        # For pkexec, use the wrapped command
        if binary == "pkexec" and len(args) >= 2:
            return f"{args[0]}.{args[1]}"
        if binary == "pkexec" and len(args) == 1:
            return args[0]
        return f"{binary}.{args[0]}"

    @staticmethod
    def get_polkit_action_id(cmd_tuple: CommandTuple) -> Optional[str]:
        """Resolve the Polkit action ID for a command tuple.

        Returns the matching policy ID from POLKIT_MAP, or None if unmapped.
        """
        binary, args, _ = cmd_tuple
        # For pkexec-wrapped commands, check the actual tool
        if binary == "pkexec" and args:
            return POLKIT_MAP.get(args[0])
        return POLKIT_MAP.get(binary)

    @staticmethod
    @validated_action(
        {
            "action": {
                "type": str,
                "required": True,
                "choices": (
                    "install",
                    "remove",
                    "update",
                    "clean",
                    "autoremove",
                    "upgrade",
                    "downgrade",
                    "reinstall",
                    "info",
                    "search",
                ),
            },
        }
    )
    def dnf(action: str, *packages: str, flags: list | None = None) -> CommandTuple:
        """Build a DNF command tuple (cmd, args, description).

        On Atomic systems, automatically uses rpm-ostree instead.
        """
        pm = SystemManager.get_package_manager()
        flag_list = flags or []

        if pm == "rpm-ostree":
            if action == "install":
                return (
                    "pkexec",
                    ["rpm-ostree", "install"] + list(packages),
                    f"Installing {', '.join(packages)} via rpm-ostree...",
                )
            elif action == "remove":
                return (
                    "pkexec",
                    ["rpm-ostree", "uninstall"] + list(packages),
                    f"Removing {', '.join(packages)} via rpm-ostree...",
                )
            elif action == "update":
                return (
                    "pkexec",
                    ["rpm-ostree", "upgrade"],
                    "Upgrading system via rpm-ostree...",
                )
            elif action == "clean":
                return (
                    "pkexec",
                    ["rpm-ostree", "cleanup", "--base"],
                    "Cleaning rpm-ostree base...",
                )
            else:
                return (
                    "pkexec",
                    ["rpm-ostree"] + action.split() + list(packages),
                    f"rpm-ostree {action}...",
                )
        else:
            action_parts = action.split()
            args = ["dnf"] + action_parts + ["-y"] + flag_list + list(packages)
            desc_map = {
                "install": f"Installing {', '.join(packages)}...",
                "remove": f"Removing {', '.join(packages)}...",
                "update": "Updating system packages...",
                "clean": "Cleaning DNF cache...",
                "autoremove": "Removing unused packages...",
            }
            desc = desc_map.get(action, f"DNF {action}...")
            return ("pkexec", args, desc)

    @staticmethod
    @validated_action(
        {
            "action": {"type": str, "required": True},
            "service": {"type": str, "required": True, "min_len": 1},
        }
    )
    def systemctl(action: str, service: str, user: bool = False) -> CommandTuple:
        """Build a systemctl command tuple."""
        if user:
            return (
                "systemctl",
                ["--user", action, service],
                f"{action.title()} user service {service}...",
            )
        return (
            "pkexec",
            ["systemctl", action, service],
            f"{action.title()} system service {service}...",
        )

    @staticmethod
    @validated_action(
        {
            "key": {"type": str, "required": True, "min_len": 1},
            "value": {"type": str, "required": True},
        }
    )
    def sysctl(key: str, value: str) -> CommandTuple:
        """Build a sysctl set command tuple."""
        return (
            "pkexec",
            ["sysctl", "-w", f"{key}={value}"],
            f"Setting {key} = {value}...",
        )

    @staticmethod
    @validated_action(
        {
            "path": {"type": str, "required": True, "min_len": 1},
            "content": {"type": str, "required": True},
        }
    )
    def write_file(path: str, content: str) -> CommandTuple:
        """Write content to a file via pkexec tee."""
        return ("pkexec", ["tee", path], f"Writing to {path}...")

    @staticmethod
    @validated_action(
        {
            "action": {"type": str, "required": True},
        }
    )
    def flatpak(action: str, *args: str) -> CommandTuple:
        """Build a flatpak command tuple."""
        return ("flatpak", [action] + list(args), f"Flatpak {action}...")

    @staticmethod
    @validated_action(
        {
            "action": {
                "type": str,
                "required": True,
                "choices": ("update", "get-updates", "refresh", "get-devices"),
            },
        }
    )
    def fwupd(action: str = "update") -> CommandTuple:
        """Build a fwupdmgr command tuple."""
        return ("pkexec", ["fwupdmgr", action, "-y"], f"Firmware {action}...")

    @staticmethod
    def journal_vacuum(time: str = "2weeks") -> CommandTuple:
        """Build a journal vacuum command tuple."""
        return (
            "pkexec",
            ["journalctl", f"--vacuum-time={time}"],
            f"Vacuuming journal ({time})...",
        )

    @staticmethod
    def fstrim() -> CommandTuple:
        """Build an SSD trim command tuple."""
        return ("pkexec", ["fstrim", "-av"], "Trimming SSD volumes...")

    @staticmethod
    def rpm_rebuild() -> CommandTuple:
        """Build an RPM database rebuild command tuple."""
        return ("pkexec", ["rpm", "--rebuilddb"], "Rebuilding RPM database...")

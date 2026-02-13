"""
Plugin Sandbox - Runtime permission enforcement for external plugins.
Part of v26.0 "Unity".

ADVISORY SANDBOX: This is NOT a security boundary. Python can escape any
pure-Python sandbox. This is defense-in-depth to catch accidental violations
and provide clear error messages for plugin developers.

For high-risk plugins, consider process isolation (bubblewrap, firejail).
"""

import logging
import sys
import functools
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Optional, Protocol, Set
from importlib.abc import MetaPathFinder
from importlib.machinery import ModuleSpec

logger = logging.getLogger(__name__)

# Valid permissions (must match utils/plugin_base.py)
VALID_PERMISSIONS = {
    "network",       # Socket access, HTTP requests
    "filesystem",    # File read/write (restricted paths)
    "subprocess",    # Run external commands (non-privileged)
    "sudo",          # Privileged operations (pkexec)
    "clipboard",     # System clipboard access
    "notifications"  # Desktop notifications
}

# Module blocklists by permission
NETWORK_MODULES = {
    "socket", "urllib", "urllib.request", "urllib.parse", "urllib.error",
    "http", "http.client", "http.server", "ftplib", "smtplib",
    "requests", "aiohttp", "httpx"
}

SUBPROCESS_MODULES = {"subprocess", "os.system", "commands", "popen2"}

# Dangerous builtins to monitor
RESTRICTED_BUILTINS = {"open", "compile", "exec", "eval", "__import__"}


class IsolationMode(str, Enum):
    """OS-level isolation policy mode for plugin execution."""

    ADVISORY = "advisory"
    PROCESS = "process"
    OS = "os"


@dataclass(frozen=True)
class PluginIsolationPolicy:
    """Contract for v27 plugin isolation policy."""
    plugin_id: str
    mode: IsolationMode = IsolationMode.ADVISORY
    allow_network: bool = False
    allow_filesystem: bool = False
    allow_subprocess: bool = False
    allow_privileged: bool = False


class IsolationProvider(Protocol):
    """Interface for policy application by concrete isolation backends."""

    def apply_policy(self, policy: PluginIsolationPolicy) -> bool:
        """Apply isolation policy and return True if enforced."""


class RestrictedImporter(MetaPathFinder):
    """
    Custom import hook to block dangerous modules based on permissions.
    Installed via sys.meta_path.
    """

    def __init__(self, plugin_id: str, permissions: Set[str]):
        self.plugin_id = plugin_id
        self.permissions = permissions
        self.blocked_modules: Set[str] = set()

        # Build blocklist
        if "network" not in permissions:
            self.blocked_modules.update(NETWORK_MODULES)
        if "subprocess" not in permissions:
            self.blocked_modules.update(SUBPROCESS_MODULES)

    def find_spec(
        self,
        fullname: str,
        path: Optional[Any] = None,
        target: Optional[ModuleType] = None
    ) -> Optional[ModuleSpec]:
        """Check if module is blocked before import."""
        # Check both full name and base module
        base_module = fullname.split(".")[0]

        if fullname in self.blocked_modules or base_module in self.blocked_modules:
            msg = (
                f"Plugin '{self.plugin_id}' attempted to import '{fullname}' "
                f"but required permission not granted. "
            )
            if fullname in NETWORK_MODULES or base_module in NETWORK_MODULES:
                msg += "Add 'network' permission to plugin manifest."
            elif fullname in SUBPROCESS_MODULES or base_module in SUBPROCESS_MODULES:
                msg += "Add 'subprocess' permission to plugin manifest."

            logger.warning(msg)
            raise PermissionError(msg)

        # Let other importers handle it
        return None


class PluginSandbox:
    """
    Permission enforcement layer for plugins.

    Wraps plugin instances to intercept operations and enforce declared
    permissions. Uses custom import hooks and function wrapping.

    Example:
        sandbox = PluginSandbox(
            plugin_id="my-plugin",
            permissions=["network", "filesystem"]
        )
        wrapped = sandbox.wrap_plugin(original_plugin)
    """

    def __init__(
        self,
        plugin_id: str,
        permissions: list[str],
        isolation_mode: Optional[IsolationMode] = None,
    ):
        """
        Initialize sandbox with plugin ID and granted permissions.

        Args:
            plugin_id: Unique plugin identifier
            permissions: List of granted permission names
        """
        self.plugin_id = plugin_id
        self.permissions = set(permissions)
        self.importer: Optional[RestrictedImporter] = None

        # Validate permissions
        invalid = self.permissions - VALID_PERMISSIONS
        if invalid:
            logger.warning(
                "Plugin '%s' requested invalid permissions: %s",
                plugin_id, invalid
            )
            self.permissions -= invalid

        self.policy = PluginIsolationPolicy(
            plugin_id=plugin_id,
            mode=isolation_mode or self._derive_isolation_mode(),
            allow_network="network" in self.permissions,
            allow_filesystem="filesystem" in self.permissions,
            allow_subprocess="subprocess" in self.permissions,
            allow_privileged="sudo" in self.permissions,
        )

        # Define allowed paths for filesystem access
        config_base = Path.home() / ".config" / "loofi-fedora-tweaks"
        self.allowed_paths = {
            config_base / "plugins" / plugin_id,
            config_base / "plugin-data" / plugin_id,
        }

        logger.debug(
            "PluginSandbox initialized for '%s' with permissions: %s",
            plugin_id, sorted(self.permissions)
        )

    def _derive_isolation_mode(self) -> IsolationMode:
        """
        Determine minimum required isolation mode from requested permissions.

        - `sudo`/`subprocess` => OS mode required
        - `network`/`filesystem` => process mode required
        - otherwise advisory
        """
        if "sudo" in self.permissions or "subprocess" in self.permissions:
            return IsolationMode.OS
        if "network" in self.permissions or "filesystem" in self.permissions:
            return IsolationMode.PROCESS
        return IsolationMode.ADVISORY

    def enforce_isolation(
        self,
        provider: Optional[IsolationProvider] = None,
        policy: Optional[PluginIsolationPolicy] = None,
    ) -> bool:
        """
        Enforce isolation policy for this plugin.

        Returns:
            True when selected policy mode is enforceable on current system.
        """
        enforced_policy = policy or self.policy
        isolation_provider = provider or _DefaultIsolationProvider()
        enforced = isolation_provider.apply_policy(enforced_policy)
        if not enforced:
            logger.warning(
                "Isolation policy for plugin '%s' could not be enforced (mode=%s)",
                self.plugin_id,
                enforced_policy.mode,
            )
        return enforced

    def install(self):
        """Install import hook in sys.meta_path."""
        if self.importer is None:
            self.importer = RestrictedImporter(self.plugin_id, self.permissions)
            sys.meta_path.insert(0, self.importer)
            logger.debug("Import hook installed for plugin '%s'", self.plugin_id)

    def uninstall(self):
        """Remove import hook from sys.meta_path."""
        if self.importer and self.importer in sys.meta_path:
            sys.meta_path.remove(self.importer)
            logger.debug("Import hook removed for plugin '%s'", self.plugin_id)

    def wrap(self, plugin: Any) -> Any:
        """Wrap plugin instance with sandbox enforcement (modifies in-place).

        Args:
            plugin: Plugin instance to wrap

        Returns:
            The same plugin instance (for chaining)
        """
        # Install import hook
        if not hasattr(self, "_importer"):
            self._importer = RestrictedImporter(self.plugin_id, self.permissions)
            sys.meta_path.insert(0, self._importer)

        # Create restricted builtins
        if not hasattr(self, "_restricted_builtins"):
            original_builtins = __builtins__ if isinstance(__builtins__, dict) else __builtins__.__dict__
            self._restricted_builtins = original_builtins.copy()

            if "filesystem" not in self.permissions:
                # Wrap open() to restrict file access
                original_open = self._restricted_builtins.get("open", open)
                self._restricted_builtins["open"] = self.wrap_open(original_open)

        logger.debug("Sandbox wrapped plugin '%s'", self.plugin_id)
        return plugin

    def unwrap(self, plugin: Any = None) -> None:
        """Remove sandbox hooks from plugin (cleanup).

        Args:
            plugin: Plugin instance (optional, for API consistency)
        """
        # Remove import hook
        if hasattr(self, "_importer") and self._importer in sys.meta_path:
            sys.meta_path.remove(self._importer)
            delattr(self, "_importer")

        # Clear restricted builtins
        if hasattr(self, "_restricted_builtins"):
            delattr(self, "_restricted_builtins")

        logger.debug("Sandbox unwrapped for plugin '%s'", self.plugin_id)

    def check_permission(self, permission: str) -> bool:
        """Check if plugin has specific permission."""
        return permission in self.permissions

    def validate_path(self, path: Path) -> bool:
        """
        Check if file path is within allowed directories.

        Args:
            path: Path to validate

        Returns:
            True if path is allowed, False otherwise
        """
        if "filesystem" not in self.permissions:
            return False

        try:
            resolved = path.resolve()
            return any(
                resolved == allowed or resolved.is_relative_to(allowed)
                for allowed in self.allowed_paths
            )
        except (OSError, ValueError):
            return False

    def wrap_open(self, original_open: Callable) -> Callable:
        """
        Wrap builtin open() to enforce filesystem permissions.

        Args:
            original_open: Original open() builtin

        Returns:
            Wrapped open function
        """
        @functools.wraps(original_open)
        def _wrapped_open(file, mode='r', *args, **kwargs):
            # Allow read-only access to system files
            if 'w' not in mode and 'a' not in mode and 'x' not in mode:
                return original_open(file, mode, *args, **kwargs)

            # Check write permissions
            path = Path(file)
            if not self.validate_path(path):
                msg = (
                    f"Plugin '{self.plugin_id}' attempted to write to '{file}' "
                    f"outside allowed directories. Allowed paths: "
                    f"{[str(p) for p in self.allowed_paths]}"
                )
                logger.warning(msg)
                raise PermissionError(msg)

            return original_open(file, mode, *args, **kwargs)

        return _wrapped_open

    def wrap_subprocess(self, subprocess_module: ModuleType) -> ModuleType:
        """
        Wrap subprocess module to enforce subprocess/sudo permissions.

        Args:
            subprocess_module: Imported subprocess module

        Returns:
            Wrapped module (modifies in place, returns for convenience)
        """
        if not self.check_permission("subprocess"):
            # Block all subprocess operations
            def _blocked(*args, **kwargs):
                msg = (
                    f"Plugin '{self.plugin_id}' attempted subprocess call "
                    f"but 'subprocess' permission not granted."
                )
                logger.warning(msg)
                raise PermissionError(msg)

            for func_name in ["run", "call", "check_call", "check_output", "Popen"]:
                if hasattr(subprocess_module, func_name):
                    setattr(subprocess_module, func_name, _blocked)

            return subprocess_module

        # Subprocess allowed, but check for sudo/pkexec
        if not self.check_permission("sudo"):
            original_run = subprocess_module.run
            original_popen = subprocess_module.Popen

            def _check_privileged_command(cmd, *args, **kwargs):
                """Check for privileged escalation commands."""
                if isinstance(cmd, (list, tuple)) and len(cmd) > 0:
                    binary = cmd[0]
                elif isinstance(cmd, str):
                    binary = cmd.split()[0] if cmd else ""
                else:
                    binary = ""

                blocked = {"sudo", "pkexec", "su", "doas"}
                if any(binary.endswith(b) for b in blocked):
                    msg = (
                        f"Plugin '{self.plugin_id}' attempted privileged command "
                        f"'{binary}' but 'sudo' permission not granted."
                    )
                    logger.warning(msg)
                    raise PermissionError(msg)

            @functools.wraps(original_run)
            def _wrapped_run(cmd, *args, **kwargs):
                _check_privileged_command(cmd, *args, **kwargs)
                return original_run(cmd, *args, **kwargs)

            @functools.wraps(original_popen)
            def _wrapped_popen(cmd, *args, **kwargs):
                _check_privileged_command(cmd, *args, **kwargs)
                return original_popen(cmd, *args, **kwargs)

            subprocess_module.run = _wrapped_run  # type: ignore[attr-defined]
            subprocess_module.Popen = _wrapped_popen  # type: ignore[attr-defined]

            # Wrap other convenience functions
            if hasattr(subprocess_module, "check_call"):
                original_check_call = subprocess_module.check_call

                @functools.wraps(original_check_call)
                def _wrapped_check_call(cmd, *args, **kwargs):
                    _check_privileged_command(cmd, *args, **kwargs)
                    return original_check_call(cmd, *args, **kwargs)
                subprocess_module.check_call = _wrapped_check_call  # type: ignore[attr-defined]

            if hasattr(subprocess_module, "check_output"):
                original_check_output = subprocess_module.check_output

                @functools.wraps(original_check_output)
                def _wrapped_check_output(cmd, *args, **kwargs):
                    _check_privileged_command(cmd, *args, **kwargs)
                    return original_check_output(cmd, *args, **kwargs)
                subprocess_module.check_output = _wrapped_check_output  # type: ignore[attr-defined]

        return subprocess_module

    def wrap_plugin(self, plugin: Any) -> Any:
        """
        Wrap plugin instance to enforce permissions.

        Installs import hook and patches builtins in plugin's namespace.
        Returns original plugin (modifications are in-place and environmental).

        Args:
            plugin: LoofiPlugin instance to wrap

        Returns:
            Same plugin instance (for convenience)
        """
        try:
            # Install import hook
            self.install()

            # Wrap open() in plugin's module namespace if possible
            if hasattr(plugin, "__module__"):
                plugin_module = sys.modules.get(plugin.__module__)
                if plugin_module:
                    # Store original open
                    if not hasattr(plugin_module, "_sandbox_original_open"):
                        plugin_module._sandbox_original_open = open  # type: ignore[attr-defined]

                    # Install wrapped open
                    setattr(
                        plugin_module,
                        "open",
                        self.wrap_open(plugin_module._sandbox_original_open)  # type: ignore[attr-defined]
                    )

            # Note: subprocess wrapping happens at import time via RestrictedImporter
            # and when plugin actually imports subprocess

            logger.info("Plugin '%s' sandboxed successfully", self.plugin_id)

        except Exception as exc:
            # Fail-safe: log but don't crash
            logger.warning(
                "Failed to sandbox plugin '%s': %s. Allowing plugin execution.",
                self.plugin_id, exc, exc_info=True
            )

        return plugin

    def unwrap_plugin(self, plugin: Any):
        """
        Remove sandbox restrictions from plugin.

        Args:
            plugin: Previously wrapped plugin instance
        """
        try:
            # Uninstall import hook
            self.uninstall()

            # Restore original open if we patched it
            if hasattr(plugin, "__module__"):
                plugin_module = sys.modules.get(plugin.__module__)
                if plugin_module and hasattr(plugin_module, "_sandbox_original_open"):
                    setattr(
                        plugin_module,
                        "open",
                        plugin_module._sandbox_original_open
                    )
                    delattr(plugin_module, "_sandbox_original_open")

            logger.debug("Plugin '%s' unsandboxed", self.plugin_id)

        except Exception as exc:
            logger.warning(
                "Failed to unwrap plugin '%s': %s",
                self.plugin_id, exc
            )

    def __enter__(self):
        """Context manager entry - install sandbox."""
        self.install()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - uninstall sandbox."""
        self.uninstall()
        return False


def create_sandbox(plugin_id: str, permissions: list[str]) -> PluginSandbox:
    """
    Factory function to create a PluginSandbox instance.

    Args:
        plugin_id: Unique plugin identifier
        permissions: List of granted permission names

    Returns:
        Configured PluginSandbox instance

    Example:
        >>> sandbox = create_sandbox("my-plugin", ["network", "filesystem"])
        >>> with sandbox:
        ...     # Plugin code runs with restrictions
        ...     pass
    """
    return PluginSandbox(plugin_id, permissions)


class _DefaultIsolationProvider:
    """Default isolation provider backed by utils.sandbox runtime checks."""

    def apply_policy(self, policy: PluginIsolationPolicy) -> bool:
        from utils.sandbox import PluginIsolationManager

        result = PluginIsolationManager.enforce_policy(policy)
        return result.success

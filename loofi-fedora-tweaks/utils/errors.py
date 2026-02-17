"""
Centralized error hierarchy for Loofi Fedora Tweaks.
Part of v11.0 "Aurora Update".

All custom exceptions derive from LoofiError which includes:
- error code (machine-readable)
- hint (user-facing recovery suggestion)
- recoverable flag
"""


class LoofiError(Exception):
    """Base exception with error code and recovery hint."""

    def __init__(self, message, code="UNKNOWN", hint="", recoverable=True):
        super().__init__(message)
        self.code = code
        self.hint = hint
        self.recoverable = recoverable


class DnfLockedError(LoofiError):
    """Another package manager is currently running."""

    def __init__(self):
        super().__init__(
            "Another package manager is currently running.",
            code="DNF_LOCKED",
            hint="Wait for the other package manager to finish. If the lock appears stale, reboot or inspect running package-manager processes.",
            recoverable=True,
        )


class PrivilegeError(LoofiError):
    """Operation requires elevated privileges."""

    def __init__(self, operation=""):
        msg = f"Elevated privileges required for: {operation}" if operation else "Elevated privileges required."
        super().__init__(
            msg,
            code="PERMISSION_DENIED",
            hint="This operation requires authentication via Polkit (pkexec).",
            recoverable=True,
        )


class CommandFailedError(LoofiError):
    """A system command returned non-zero exit code."""

    def __init__(self, cmd, exit_code, stderr=""):
        msg = f"Command failed: {cmd} (exit code {exit_code})"
        if stderr:
            msg += f"\n{stderr}"
        super().__init__(
            msg,
            code="COMMAND_FAILED",
            hint="Check the output log for details.",
            recoverable=True,
        )


class HardwareNotFoundError(LoofiError):
    """Expected hardware component not detected."""

    def __init__(self, component=""):
        super().__init__(
            f"Hardware not found: {component}" if component else "Required hardware not found.",
            code="HARDWARE_NOT_FOUND",
            hint="This feature requires specific hardware that was not detected on your system.",
            recoverable=False,
        )


class NetworkError(LoofiError):
    """Network operation failed."""

    def __init__(self, message="Network operation failed."):
        super().__init__(
            message,
            code="NETWORK_ERROR",
            hint="Check your internet connection and try again.",
            recoverable=True,
        )


class ConfigError(LoofiError):
    """Configuration file is invalid or corrupted."""

    def __init__(self, path="", detail=""):
        msg = f"Invalid configuration: {path}" if path else "Invalid configuration."
        if detail:
            msg += f" ({detail})"
        super().__init__(
            msg,
            code="CONFIG_ERROR",
            hint="Delete the configuration file and restart to regenerate defaults.",
            recoverable=True,
        )


class CommandTimeoutError(LoofiError):
    """A system command exceeded its time limit."""

    def __init__(self, cmd="", timeout=0):
        msg = f"Command timed out after {timeout}s: {cmd}" if cmd else "Command timed out."
        super().__init__(
            msg,
            code="COMMAND_TIMEOUT",
            hint="The operation took too long. Try again or increase the timeout.",
            recoverable=True,
        )
        self.timeout = timeout


class ValidationError(LoofiError):
    """Parameter validation failed for a privileged action."""

    def __init__(self, param="", detail=""):
        msg = f"Invalid parameter: {param}" if param else "Parameter validation failed."
        if detail:
            msg += f" ({detail})"
        super().__init__(
            msg,
            code="VALIDATION_ERROR",
            hint="Check the parameter values and try again.",
            recoverable=True,
        )

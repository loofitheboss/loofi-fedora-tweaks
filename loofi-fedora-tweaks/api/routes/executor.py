"""Executor API routes for ActionExecutor operations."""

from typing import List, Tuple

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from utils.action_executor import ActionExecutor
from utils.action_result import ActionResult
from utils.auth import AuthManager

router = APIRouter()

# Allowlist of permitted commands for API execution
# Maps logical command names to their absolute paths
# Security: Only these commands can be executed via the API endpoint
ALLOWED_COMMANDS = {
    "dnf": "/usr/bin/dnf",
    "rpm-ostree": "/usr/bin/rpm-ostree",
    "flatpak": "/usr/bin/flatpak",
    "systemctl": "/usr/bin/systemctl",
    "journalctl": "/usr/bin/journalctl",
    "fwupdmgr": "/usr/bin/fwupdmgr",
    "cpupower": "/usr/sbin/cpupower",
    "grubby": "/usr/sbin/grubby",
    "sysctl": "/usr/sbin/sysctl",
    "firewall-cmd": "/usr/bin/firewall-cmd",
    "bluetoothctl": "/usr/bin/bluetoothctl",
    "virsh": "/usr/bin/virsh",
    "distrobox": "/usr/bin/distrobox",
    "ollama": "/usr/bin/ollama",
    "zramctl": "/usr/sbin/zramctl",
    "lspci": "/usr/sbin/lspci",
    "nvidia-smi": "/usr/bin/nvidia-smi",
    "fstrim": "/usr/sbin/fstrim",
    "btrfs": "/usr/sbin/btrfs",
    "timeshift": "/usr/bin/timeshift",
    "snapper": "/usr/bin/snapper",
    "firejail": "/usr/bin/firejail",
    "resolvectl": "/usr/bin/resolvectl",
    "nmcli": "/usr/bin/nmcli",
}

# Shell metacharacters that could enable command injection
SHELL_METACHARACTERS = {';', '|', '&', '$', '`', '(', ')', '{', '}', '>', '<', '\n', '\r'}


def _validate_command(command: str, args: List[str]) -> Tuple[bool, str, str]:
    """
    Validate command against allowlist and check args for shell metacharacters.
    
    Args:
        command: The command name to validate
        args: List of command arguments
        
    Returns:
        Tuple of (is_valid, resolved_command, error_message)
        If valid: (True, resolved_path, "")
        If invalid: (False, "", error_description)
    """
    # Check if command is in allowlist
    if command not in ALLOWED_COMMANDS:
        return (False, "", f"Command not allowed: {command}")
    
    # Check args for shell metacharacters
    for arg in args:
        if any(char in arg for char in SHELL_METACHARACTERS):
            return (False, "", f"Argument contains shell metacharacters: {arg}")
    
    # Return resolved path
    return (True, ALLOWED_COMMANDS[command], "")


class ActionPayload(BaseModel):
    """Payload for executing a system action."""

    command: str = Field(..., description="Executable or command name")
    args: List[str] = Field(default_factory=list, description="Command arguments")
    pkexec: bool = Field(False, description="Require privilege escalation")
    preview: bool = Field(True, description="Run in preview mode first")
    action_id: str = Field("", description="Optional action identifier")


class ActionResponse(BaseModel):
    """Serialized ActionResult response."""

    result: dict
    preview: dict


@router.post(
    "/execute",
    response_model=ActionResponse,
    status_code=status.HTTP_200_OK,
)
def execute_action(
    payload: ActionPayload,
    _auth: str = Depends(AuthManager.verify_bearer_token),
):
    """Execute an action via ActionExecutor with mandatory preview."""
    # Security: Validate command against allowlist before execution
    is_valid, resolved_command, error_msg = _validate_command(payload.command, payload.args)
    
    if not is_valid:
        # Return failed result for invalid command without executing
        failed_result = ActionResult.fail(error_msg, action_id=payload.action_id)
        return ActionResponse(
            result=failed_result.to_dict(),
            preview=failed_result.to_dict()
        )
    
    # Use resolved command path from allowlist
    preview_result = ActionExecutor.run(
        resolved_command,
        payload.args,
        preview=True,
        pkexec=payload.pkexec,
        action_id=payload.action_id,
    )

    if not payload.preview:
        result = ActionExecutor.run(
            resolved_command,
            payload.args,
            preview=False,
            pkexec=payload.pkexec,
            action_id=payload.action_id,
        )
    else:
        result = ActionResult.previewed(
            resolved_command,
            payload.args,
            action_id=payload.action_id,
        )

    return ActionResponse(result=result.to_dict(), preview=preview_result.to_dict())

"""Executor API routes for ActionExecutor operations.

Security:
- Command allowlist enforced — only known-safe executables accepted.
- All executions audit-logged via AuditLogger.
- Bearer JWT required on all endpoints.
"""

import logging
from typing import FrozenSet, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from utils.action_executor import ActionExecutor
from utils.action_result import ActionResult
from utils.audit import AuditLogger
from utils.auth import AuthManager

logger = logging.getLogger(__name__)

router = APIRouter()

# Allowlist of executables the API may invoke.
# Matches the commands exposed by PrivilegedCommand builders and common
# read-only diagnostic tools.  Anything not listed is rejected with 403.
COMMAND_ALLOWLIST: FrozenSet[str] = frozenset({
    # Package management (via PrivilegedCommand)
    "dnf", "rpm-ostree",
    # Service management
    "systemctl",
    # Kernel tuning
    "sysctl",
    # Flatpak
    "flatpak",
    # Firmware
    "fwupdmgr",
    # Maintenance
    "journalctl", "fstrim", "rpm",
    # Read-only diagnostics
    "hostnamectl", "uname", "lsblk", "df", "free", "uptime",
    "sensors", "lspci", "lsusb", "ip", "ss", "nmcli",
    "firewall-cmd", "timedatectl", "localectl",
})


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


def _validate_command(command: str, args: List[str]) -> None:
    """Reject commands not on the allowlist.

    Raises:
        HTTPException: 403 if command is not allowed.
    """
    if command not in COMMAND_ALLOWLIST:
        audit = AuditLogger()
        audit.log(
            "api.execute.rejected",
            params={"command": command, "args": args, "reason": "not_in_allowlist"},
            exit_code=None,
        )
        logger.warning("API rejected disallowed command: %s", command)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Command '{command}' is not in the API allowlist",
        )


@router.post(
    "/execute",
    response_model=ActionResponse,
    status_code=status.HTTP_200_OK,
)
def execute_action(
    payload: ActionPayload,
    _auth: str = Depends(AuthManager.verify_bearer_token),
):
    """Execute an action via ActionExecutor with mandatory preview.

    Security: command must be in COMMAND_ALLOWLIST. All invocations are
    audit-logged with timestamp, params, and exit code.
    """
    _validate_command(payload.command, payload.args)

    audit = AuditLogger()

    preview_result = ActionExecutor.run(
        payload.command,
        payload.args,
        preview=True,
        pkexec=payload.pkexec,
        action_id=payload.action_id,
    )

    if not payload.preview:
        result = ActionExecutor.run(
            payload.command,
            payload.args,
            preview=False,
            pkexec=payload.pkexec,
            action_id=payload.action_id,
        )
        audit.log(
            "api.execute",
            params={
                "command": payload.command,
                "args": payload.args,
                "pkexec": payload.pkexec,
                "action_id": payload.action_id,
            },
            exit_code=result.exit_code if hasattr(result, "exit_code") else None,
        )
    else:
        result = ActionResult.previewed(
            payload.command,
            payload.args,
            action_id=payload.action_id,
        )
        audit.log(
            "api.execute.preview",
            params={
                "command": payload.command,
                "args": payload.args,
                "pkexec": payload.pkexec,
                "action_id": payload.action_id,
            },
            exit_code=None,
        )

    return ActionResponse(result=result.to_dict(), preview=preview_result.to_dict())

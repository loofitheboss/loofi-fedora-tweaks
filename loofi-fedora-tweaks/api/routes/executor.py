"""Executor API routes for ActionExecutor operations."""

from typing import List

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from utils.action_executor import ActionExecutor
from utils.action_result import ActionResult
from utils.auth import AuthManager

router = APIRouter()


class ActionPayload(BaseModel):
    """Payload for executing a system action."""

    command: str = Field(..., description="Logical command name")
    args: List[str] = Field(default_factory=list, description="Command arguments")
    pkexec: bool = Field(False, description="Require privilege escalation")
    preview: bool = Field(True, description="Run in preview mode first")
    action_id: str = Field("", description="Optional action identifier")


class ActionResponse(BaseModel):
"""Serialized ActionResult response."""

    result: dict
    preview: dict


# Allowlist of permitted commands exposed via this API.
# The key is a logical command name provided by the client.
# The value is the executable that will actually be invoked.
ALLOWED_COMMANDS = {
    # Example logical-to-executable mapping:
    # "dnf": "dnf",
    # Add additional allowed commands here as needed.
}


@router.post(
    "/execute",
    response_model=ActionResponse,
    status_code=status.HTTP_200_OK,
)
    # Resolve the logical command name to an allowed executable.
    resolved_command = ALLOWED_COMMANDS.get(payload.command)
    if resolved_command is None:
        # Command is not in the allowlist; do not execute it.
        error_result = ActionResult.fail(
            f"Command not allowed: {payload.command}",
            action_id=payload.action_id,
        )
        # For symmetry with the normal response, return the same error in both fields.
        return ActionResponse(
            result=error_result.to_dict(),
            preview=error_result.to_dict(),
        )

def execute_action(
    payload: ActionPayload,
    _auth: str = Depends(AuthManager.verify_bearer_token),
):
    """Execute an action via ActionExecutor with mandatory preview."""
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

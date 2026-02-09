"""
Unified Action Result — v19.0 Foundation.

Single structured result type for all system actions.
Replaces ad-hoc OperationResult / AgentResult for centralized execution.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ActionResult:
    """
    Structured result from any system action.

    Attributes:
        success: Whether the action completed successfully.
        message: Human-readable summary.
        exit_code: Process exit code (None if not a subprocess).
        stdout: Captured standard output (truncated).
        stderr: Captured standard error (truncated).
        data: Arbitrary structured payload for callers.
        preview: True if this was a preview/dry-run (nothing executed).
        needs_reboot: True if a reboot is required to apply changes.
        timestamp: Unix timestamp of result creation.
        action_id: Optional identifier linking to the action definition.
    """

    success: bool
    message: str
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    data: Optional[Dict[str, Any]] = None
    preview: bool = False
    needs_reboot: bool = False
    timestamp: float = field(default_factory=time.time)
    action_id: str = ""

    # Truncation limits for serialization safety
    _MAX_OUTPUT = 4000

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for logging / export."""
        return {
            "success": self.success,
            "message": self.message,
            "exit_code": self.exit_code,
            "stdout": self.stdout[: self._MAX_OUTPUT],
            "stderr": self.stderr[: self._MAX_OUTPUT],
            "data": self.data,
            "preview": self.preview,
            "needs_reboot": self.needs_reboot,
            "timestamp": self.timestamp,
            "action_id": self.action_id,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ActionResult":
        return cls(
            success=d.get("success", False),
            message=d.get("message", ""),
            exit_code=d.get("exit_code"),
            stdout=d.get("stdout", ""),
            stderr=d.get("stderr", ""),
            data=d.get("data"),
            preview=d.get("preview", False),
            needs_reboot=d.get("needs_reboot", False),
            timestamp=d.get("timestamp", 0.0),
            action_id=d.get("action_id", ""),
        )

    @classmethod
    def ok(cls, message: str, **kwargs) -> "ActionResult":
        """Convenience: successful result."""
        return cls(success=True, message=message, **kwargs)

    @classmethod
    def fail(cls, message: str, **kwargs) -> "ActionResult":
        """Convenience: failed result."""
        return cls(success=False, message=message, **kwargs)

    @classmethod
    def previewed(cls, command: str, args: List[str], **kwargs) -> "ActionResult":
        """Convenience: preview-only result (nothing was executed)."""
        cmd_str = " ".join([command] + args)
        return cls(
            success=True,
            message=f"[PREVIEW] Would execute: {cmd_str}",
            preview=True,
            data={"command": command, "args": args},
            **kwargs,
        )

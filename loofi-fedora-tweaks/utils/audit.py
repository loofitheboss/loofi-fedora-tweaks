"""
Structured audit logger for privileged actions.
Part of v35.0.0 "Fortress" — Security & Privilege Hardening.

Logs all privileged operations to ~/.config/loofi-fedora-tweaks/audit.jsonl
in JSON Lines format with automatic rotation (10 MB, 5 backups).

Each entry contains:
- ts: ISO 8601 timestamp
- action: action name (e.g., "dnf.install")
- params: sanitized parameter dict
- exit_code: process exit code (or null if not executed)
- stderr_hash: SHA-256 hash of stderr output (for deduplication)
- user: current system user
- dry_run: whether this was a dry-run invocation
"""

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


class AuditLogger:
    """Structured JSON Lines audit logger for privileged actions."""

    _instance: Optional["AuditLogger"] = None
    _initialized: bool = False

    # Rotation config
    MAX_BYTES = 10 * 1024 * 1024  # 10 MB
    BACKUP_COUNT = 5

    # Sensitive parameter names to redact
    SENSITIVE_KEYS = frozenset({
        "password", "token", "secret", "key", "credential",
        "auth", "passphrase", "private_key",
    })

    def __new__(cls) -> "AuditLogger":
        """Singleton pattern — one audit logger per process."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if AuditLogger._initialized:
            return
        AuditLogger._initialized = True

        self._log_dir = Path(
            os.environ.get(
                "LOOFI_AUDIT_DIR",
                os.path.expanduser("~/.config/loofi-fedora-tweaks"),
            )
        )
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._log_path = self._log_dir / "audit.jsonl"

        # Set up rotating file handler
        self._logger = logging.getLogger("loofi.audit")
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False

        # Only add handler once
        if not self._logger.handlers:
            handler = RotatingFileHandler(
                str(self._log_path),
                maxBytes=self.MAX_BYTES,
                backupCount=self.BACKUP_COUNT,
                encoding="utf-8",
            )
            handler.setFormatter(logging.Formatter("%(message)s"))
            self._logger.addHandler(handler)

        self._user = os.environ.get(
            "USER", os.environ.get("LOGNAME", "unknown"))

    @property
    def log_path(self) -> Path:
        """Return the path to the audit log file."""
        return self._log_path

    def log(
        self,
        action: str,
        params: Optional[dict] = None,
        exit_code: Optional[int] = None,
        stderr: str = "",
        dry_run: bool = False,
    ) -> dict:
        """
        Log a privileged action.

        Args:
            action: Action identifier (e.g., "dnf.install", "systemctl.restart")
            params: Parameter dict (sensitive values auto-redacted)
            exit_code: Process exit code, or None if not executed
            stderr: Stderr output (hashed, not stored raw)
            dry_run: Whether this was a dry-run invocation

        Returns:
            The logged entry dict (for testing/chaining)
        """
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "params": self._sanitize_params(params or {}),
            "exit_code": exit_code,
            "stderr_hash": self._hash_stderr(stderr) if stderr else None,
            "user": self._user,
            "dry_run": dry_run,
        }

        self._logger.info(json.dumps(entry, separators=(",", ":")))
        return entry

    def log_validation_failure(
        self,
        action: str,
        param: str,
        detail: str,
        params: Optional[dict] = None,
    ) -> dict:
        """
        Log a parameter validation failure.

        Args:
            action: Action that was attempted
            param: Parameter name that failed validation
            detail: Description of the validation failure
            params: Full parameter dict (sanitized)

        Returns:
            The logged entry dict
        """
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "action": f"{action}.validation_failure",
            "param": param,
            "detail": detail,
            "params": self._sanitize_params(params or {}),
            "exit_code": None,
            "stderr_hash": None,
            "user": self._user,
            "dry_run": False,
        }

        self._logger.info(json.dumps(entry, separators=(",", ":")))
        return entry

    def get_recent(self, count: int = 50) -> list[dict]:
        """
        Read the most recent audit entries.

        Args:
            count: Maximum number of entries to return

        Returns:
            List of entry dicts, newest first
        """
        entries: list[dict] = []
        if not self._log_path.exists():
            return entries

        try:
            with open(self._log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        except OSError:
            return entries

        # Return newest first, limited to count
        return entries[-count:][::-1]

    def _sanitize_params(self, params: dict) -> dict:
        """Redact sensitive parameter values."""
        sanitized: dict[str, object] = {}
        for key, value in params.items():
            if any(s in key.lower() for s in self.SENSITIVE_KEYS):
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_params(value)
            else:
                sanitized[key] = value
        return sanitized

    @staticmethod
    def _hash_stderr(stderr: str) -> str:
        """SHA-256 hash of stderr for deduplication without storing raw output."""
        return hashlib.sha256(stderr.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def reset(cls) -> None:
        """Reset singleton (for testing only)."""
        if cls._instance is not None:
            for handler in cls._instance._logger.handlers[:]:
                handler.close()
                cls._instance._logger.removeHandler(handler)
        cls._instance = None
        cls._initialized = False

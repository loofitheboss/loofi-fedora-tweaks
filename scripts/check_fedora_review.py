#!/usr/bin/env python3
"""Validate Fedora review tooling availability for packaging and release gates."""

from __future__ import annotations

import shutil
import subprocess
import sys
from typing import Sequence


DEFAULT_TIMEOUT_SECONDS = 20
CHECK_COMMANDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("version probe", ("-V",)),
    ("check registry probe", ("-d",)),
)


def _extract_output(result: subprocess.CompletedProcess[str]) -> str:
    """Return a compact output snippet from a command result."""
    stdout = result.stdout.strip()
    if stdout:
        return stdout
    stderr = result.stderr.strip()
    if stderr:
        return stderr
    return ""


def _run_probe(
    binary: str,
    args: Sequence[str],
    description: str,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> str | None:
    """Run one fedora-review probe and return an error message if it fails."""
    command = [binary, *args]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return (
            f"{description} timed out after {timeout}s: {' '.join(command)}"
        )
    except (subprocess.SubprocessError, OSError) as exc:
        return f"{description} failed to execute: {exc}"

    if result.returncode != 0:
        snippet = _extract_output(result)
        details = f" Output: {snippet}" if snippet else ""
        return (
            f"{description} failed with exit code {result.returncode}: "
            f"{' '.join(command)}.{details}"
        )
    return None


def check_fedora_review(timeout: int = DEFAULT_TIMEOUT_SECONDS) -> tuple[bool, list[str]]:
    """Check that fedora-review exists and responds to lightweight probes."""
    binary = shutil.which("fedora-review")
    if not binary:
        return (
            False,
            [
                "fedora-review was not found in PATH.",
                "Install it with: dnf install -y fedora-review",
            ],
        )

    errors: list[str] = []
    for description, args in CHECK_COMMANDS:
        error = _run_probe(binary, args, description, timeout=timeout)
        if error:
            errors.append(error)

    if errors:
        errors.append("Install or repair Fedora review tooling: dnf install -y fedora-review")
    return not errors, errors


def main() -> int:
    """Entry point for workflow gates."""
    ok, errors = check_fedora_review()
    if not ok:
        print("[fedora-review-check] FAILED")
        for error in errors:
            print(f"- {error}")
        return 1

    print("[fedora-review-check] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

---
description: "Security and OWASP guidelines adapted for Loofi Fedora Tweaks (Python, PyQt6, pkexec privilege model)"
applyTo: "**"
---

# Secure Coding and OWASP Guidelines — Loofi Fedora Tweaks

## Instructions

Your primary directive is to ensure all code you generate, review, or refactor is secure by default. Follow a security-first mindset. When in doubt, choose the more secure option and explain the reasoning.

## Project-Specific Security Rules

### Privilege Escalation
- **NEVER use `sudo`** — only `pkexec` via `PrivilegedCommand`
- **Always unpack** the PrivilegedCommand tuple: `binary, args, desc = PrivilegedCommand.dnf(...)`
- **Audit log** all privileged actions (timestamp, action, params, exit code)
- **Never expand root-level capability** without: validation, audit log, rollback strategy

### Subprocess Security
- **NEVER use `shell=True`** in `subprocess.run()`, `subprocess.Popen()`, or `subprocess.check_output()`
- **Always set `timeout=N`** on every subprocess call to prevent hangs
- **Sanitize all user-provided arguments** before passing to subprocess commands
- **Use list arguments** (not string commands) for subprocess calls

### Secret Management
- Never hardcode secrets, API keys, or tokens in source code
- Use environment variables or `~/.config/loofi-fedora-tweaks/` for sensitive configuration
- Never log sensitive data — use `%s` formatting with redacted values

## A01: Broken Access Control

- Enforce Principle of Least Privilege — default to the most restrictive permissions
- Deny by default — access should only be granted with explicit rules
- Prevent path traversal when handling file operations based on user input
- Validate all file paths against allowed directories

```python
# ✅ Safe path handling
import os
safe_base = os.path.expanduser("~/.config/loofi-fedora-tweaks/")
user_path = os.path.normpath(os.path.join(safe_base, user_input))
if not user_path.startswith(safe_base):
    raise ValueError("Path traversal detected")
```

## A03: Injection

- **No shell injection** — always use list-based subprocess calls
- **Sanitize command-line input** — validate arguments before passing to PrivilegedCommand

```python
# ❌ BAD: Shell injection risk
subprocess.run(f"dnf install {package}", shell=True)

# ✅ GOOD: List-based, via PrivilegedCommand
from utils.commands import PrivilegedCommand
binary, args, desc = PrivilegedCommand.dnf("install", package)
cmd = [binary] + args
subprocess.run(cmd, capture_output=True, text=True, timeout=120)
```

## A06: Vulnerable Components

- Use up-to-date dependencies — check with `pip-audit` or `safety`
- CI runs `bandit` security scanner (skips B103,B104,B108,B310,B404,B603,B602)
- When adding new libraries, verify they are actively maintained

## A08: Software and Data Integrity

- Never use `pickle` for deserializing untrusted data — use JSON
- Validate all configuration files before loading
- Use typed dataclasses for structured data to enforce schemas

## Error Handling Security

```python
# ✅ Correct: Don't expose internal details in user-facing errors
from utils.errors import LoofiError, CommandFailedError
try:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
except (subprocess.SubprocessError, OSError) as e:
    logger.debug("Command failed: %s", e)  # Internal log only
    raise CommandFailedError(hint="Operation failed. Check system logs.")
```

## General Guidelines

- Be explicit about security mitigations in code comments
- When identifying vulnerabilities in code review, explain the risk AND provide corrected code
- All dangerous operations require `ConfirmActionDialog.confirm()` + `SafetyManager` snapshot prompt
- Follow the stabilization guide: `.github/instructions/system_hardening_and_stabilization_guide.md`

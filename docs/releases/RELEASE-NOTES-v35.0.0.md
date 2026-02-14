# v35.0.0 "Fortress" — Release Notes

**Release date**: 2025-07-19
**Codename**: Fortress
**Focus**: Security & Privilege Hardening

---

## What's New

v35.0.0 "Fortress" is a security hardening release — subprocess timeout enforcement, structured audit logging, granular Polkit policies, parameter validation, and dry-run mode.

### Subprocess Timeout Enforcement

Every `subprocess.run()` and `subprocess.check_output()` call in the codebase now includes a mandatory `timeout` parameter. An AST-based script scanned and patched 56+ source files with category-specific defaults:

| Category | Timeout | Examples |
|----------|---------|----------|
| Package operations | 600s | dnf install, rpm-ostree |
| Network operations | 30s | nmcli, ping, curl |
| System info | 15s | uname, lsblk, hostname |
| Service management | 60s | systemctl, journalctl |
| File operations | 120s | tee, cp, rsync |
| Container/VM | 300s | podman, docker, virsh |
| Default | 60s | Everything else |

`CommandTimeoutError` exception added to `utils/errors.py` for consistent timeout handling.

### Structured Audit Logging

New `AuditLogger` singleton (`utils/audit.py`) logs all privileged actions to `~/.config/loofi-fedora-tweaks/audit.jsonl` in JSON Lines format:

- **Fields**: timestamp (ISO 8601), action name, sanitized parameters, exit code, stderr SHA-256 hash, user, dry_run flag
- **Rotation**: 10 MB max, 5 backups
- **Redaction**: Sensitive parameter names (`password`, `token`, `secret`, `key`, `credential`, `auth`, `passphrase`, `private_key`) are automatically redacted
- **CLI**: `loofi-fedora-tweaks --cli audit-log --count 20` to view recent entries

### Granular Polkit Policies

Split the monolithic Polkit policy into 7 purpose-scoped policy files:

| Policy File | Action ID | Scope |
|------------|-----------|-------|
| `org.loofi.fedora-tweaks.policy` | package-manage | DNF/rpm-ostree package ops |
| `org.loofi.fedora-tweaks.firewall.policy` | firewall-manage | Firewall rules |
| `org.loofi.fedora-tweaks.network.policy` | network-manage | Network settings |
| `org.loofi.fedora-tweaks.storage.policy` | storage-manage | Storage/disk ops |
| `org.loofi.fedora-tweaks.service-manage.policy` | service-manage | Systemd service mgmt |
| `org.loofi.fedora-tweaks.kernel.policy` | kernel-manage | Kernel parameters |
| `org.loofi.fedora-tweaks.security.policy` | security-manage | Security operations |

`POLKIT_MAP` in `utils/commands.py` maps tool names to action IDs. `PrivilegedCommand.get_polkit_action_id()` resolves the correct policy for any command tuple.

### Parameter Schema Validation

New `@validated_action` decorator on `PrivilegedCommand` builder methods enforces:

- **Type checking**: Parameters must match expected types
- **Required parameters**: Cannot be empty or missing
- **Path traversal detection**: Blocks `../`, `..\\`, `%2e%2e` patterns
- **Choices validation**: `dnf()` action must be one of `install`, `remove`, `update`, `clean`, `search`, `info`, `list`, `upgrade`, `downgrade`, `reinstall`, `autoremove`
- **Minimum length**: Enforced where applicable

Validation failures are audit-logged via `AuditLogger.log_validation_failure()` and raise `ValidationError`.

### CLI Dry-Run Mode

`--dry-run` flag on CLI shows what commands would execute without running them:

- Prints the full command that would be executed
- Audit-logs the action with `dry_run=True`
- Supports `--json` output format

### GUI Command Preview

`ConfirmActionDialog` now accepts an optional `command_preview` parameter:

- Collapsible preview area (hidden by default)
- "🔍 Preview" toggle button shows the exact command before execution
- Used for dangerous operations that require user confirmation

### PrivilegedCommand.execute_and_log()

New method that combines command execution with audit logging:

- Runs the command with `subprocess.run()` and specified timeout
- Automatically audit-logs the action with exit code and stderr hash
- Supports dry-run mode (audit-logs without executing)
- Raises `CommandTimeoutError` on timeout with audit entry

### CLI --timeout Flag

Global `--timeout` flag (default: 300s) sets operation timeout for all CLI commands.

### Notification Panel Fix

`NotificationPanel` improved with:

- Class constants for consistent sizing (MIN_HEIGHT=150, MAX_HEIGHT=500, PANEL_WIDTH=350)
- Edge-clipping prevention in `_toggle_notification_panel()`
- Drop shadow styling

### Security & Documentation

- **SECURITY.md**: Vulnerability disclosure policy, supported versions (v34+), 90-day response timeline
- **install.sh deprecated**: Deprecation banner with `--i-know-what-i-am-doing` override — RPM is the supported install method

---

## Test Coverage

3 new test files with 54 tests:

| File | Tests | Coverage |
|------|-------|----------|
| `test_timeout_enforcement.py` | 4 | AST-based scanner verifying no untimed subprocess calls |
| `test_audit.py` | 17 | Full AuditLogger coverage (singleton, JSONL format, redaction, rotation) |
| `test_commands.py` | 33 | PrivilegedCommand builders, validation, Polkit map, execute_and_log |

---

## Upgrade Notes

- **RPM spec updated**: 6 new Polkit policy files added to package
- **install.sh deprecated**: Use RPM packaging (`build_rpm.sh`) instead
- Existing audit log path: `~/.config/loofi-fedora-tweaks/audit.jsonl`
- All subprocess calls now have timeouts — long-running operations may need `--timeout` adjustment

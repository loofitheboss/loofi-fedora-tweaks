# Security Model

Security architecture and privilege management in Loofi Fedora Tweaks.

---

## Core Principles

1. **pkexec-only**: All privileged operations use `pkexec` (Polkit), never `sudo`
2. **Subprocess safety**: All subprocess calls have timeouts, no shell injection, no `shell=True`
3. **Audit logging**: All privileged actions logged to structured JSONL audit trail
4. **Parameter validation**: All inputs validated before execution
5. **Minimal privileges**: Request only necessary permissions, scope operations narrowly

---

## Polkit Policies

### Purpose-Scoped Policy Files (v35.0+)

Split into **7 granular policy files** for better security:

| File | Purpose | Actions |
|------|---------|---------|
| `org.loofi.fedora-tweaks.package.policy` | Package management | Install, remove, update, clean cache |
| `org.loofi.fedora-tweaks.firewall.policy` | Firewall configuration | Add/remove rules, zones, services |
| `org.loofi.fedora-tweaks.network.policy` | Network settings | DNS, interfaces, VPN |
| `org.loofi.fedora-tweaks.storage.policy` | Storage operations | Mount, unmount, disk management |
| `org.loofi.fedora-tweaks.service-manage.policy` | Service control | Start, stop, restart, enable, disable services |
| `org.loofi.fedora-tweaks.kernel.policy` | Kernel management | Boot config, kernel params, modules |
| `org.loofi.fedora-tweaks.security.policy` | Security hardening | SELinux, AppArmor, auditing |

### Policy Location

**System-wide**: `/usr/share/polkit-1/actions/`

Each policy file follows Polkit XML schema:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE policyconfig PUBLIC
 "-//freedesktop//DTD PolicyKit Policy Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/PolicyKit/1.0/policyconfig.dtd">
<policyconfig>
  <action id="org.loofi.fedora-tweaks.package.install">
    <description>Install packages</description>
    <message>Authentication is required to install packages</message>
    <defaults>
      <allow_any>auth_admin</allow_any>
      <allow_inactive>auth_admin</allow_inactive>
      <allow_active>auth_admin_keep</allow_active>
    </defaults>
  </action>
</policyconfig>
```

### POLKIT_MAP

The `POLKIT_MAP` in `utils/commands.py` maps operation types to action IDs:

```python
POLKIT_MAP = {
    "package": "org.loofi.fedora-tweaks.package.install",
    "firewall": "org.loofi.fedora-tweaks.firewall.modify",
    "network": "org.loofi.fedora-tweaks.network.configure",
    "storage": "org.loofi.fedora-tweaks.storage.manage",
    "service": "org.loofi.fedora-tweaks.service-manage.control",
    "kernel": "org.loofi.fedora-tweaks.kernel.modify",
    "security": "org.loofi.fedora-tweaks.security.modify",
}
```

---

## Subprocess Safety

### Timeout Enforcement (v35.0+)

**All subprocess calls MUST have timeouts**:

```python
# ✅ Correct
subprocess.run(cmd, timeout=60, capture_output=True, text=True)

# ❌ Wrong — missing timeout
subprocess.run(cmd, capture_output=True, text=True)
```

**Category-specific defaults**:
- Package operations: 600s (10 minutes)
- Network operations: 30s
- System info queries: 15s
- Service control: 60s
- File operations: 120s
- Containers/VMs: 300s
- Default: 60s

### No Shell Injection

**Never use `shell=True`**:

```python
# ✅ Correct — list of args
subprocess.run(["pkexec", "dnf", "install", "-y", "firefox"], timeout=600)

# ❌ Wrong — shell injection risk
subprocess.run("pkexec dnf install -y " + package_name, shell=True, timeout=600)
```

**Never use `sh -c`** for privilege escalation:

```python
# ✅ Correct
["pkexec", "systemctl", "restart", "sshd"]

# ❌ Wrong — shell command string
["pkexec", "sh", "-c", "systemctl restart sshd"]
```

### Command Validation

All privileged commands go through `PrivilegedCommand` builder with validation:

```python
from utils.commands import PrivilegedCommand

# Validated, safe command construction
binary, args, desc = PrivilegedCommand.dnf("install", "firefox")
subprocess.run([binary] + args, timeout=600)
```

---

## Audit Logging (v35.0+)

### Structured Audit Trail

All privileged actions logged to `~/.config/loofi-fedora-tweaks/audit.jsonl` in JSON Lines format.

**Log entry structure**:

```json
{
  "timestamp": "2026-02-14T23:45:12.123456",
  "action": "package.install",
  "params": {
    "packages": ["firefox"],
    "package_manager": "dnf"
  },
  "exit_code": 0,
  "stderr_hash": "sha256:abc123...",
  "dry_run": false
}
```

### Features

- **Auto-rotation**: 10 MB max size, 5 backup files
- **Sensitive parameter redaction**: Passwords, tokens, keys automatically redacted
- **stderr hashing**: SHA-256 hash of stderr output for privacy
- **Dry-run logging**: Preview mode actions logged with `dry_run: true`

### Audit Logger API

```python
from utils.audit import AuditLogger

# Log privileged action
AuditLogger().log(
    action="package.install",
    params={"packages": ["firefox"]},
    exit_code=0
)

# Log validation failure
AuditLogger().log_validation_failure(
    action="firewall.add_port",
    params={"port": "not-a-number"},
    reason="Invalid port number"
)

# Retrieve recent entries
recent = AuditLogger().get_recent(count=20)
```

### CLI Access

```bash
# View last 20 audit entries
loofi-fedora-tweaks --cli audit-log --count 20

# View all entries
loofi-fedora-tweaks --cli audit-log --count 0

# JSON output
loofi-fedora-tweaks --cli --json audit-log --count 50
```

---

## Parameter Validation (v35.0+)

### @validated_action Decorator

All `PrivilegedCommand` builder methods use `@validated_action` decorator:

```python
@validated_action(
    required=["action"],
    types={"action": str},
    choices={"action": ["install", "remove", "update"]},
    paths=[]
)
def dnf(action: str, *packages: str) -> Tuple[str, List[str], str]:
    # Validated before execution
    pass
```

### Validation Features

- **Type checking**: Ensure parameters are correct type
- **Required parameters**: Fail if missing required params
- **Path traversal detection**: Reject paths with `..` or absolute paths where relative expected
- **Choices validation**: Ensure parameter value is in allowed set
- **Audit logging**: All validation failures logged

### ValidationError

```python
from utils.errors import ValidationError

try:
    PrivilegedCommand.dnf("invalid-action", "package")
except ValidationError as e:
    print(e.code)  # "VALIDATION_FAILED"
    print(e.hint)  # "action must be one of: install, remove, update"
```

---

## Safety Guards

### SafetyManager

Prompts for snapshots before risky operations:

```python
from utils.safety import SafetyManager

# Confirm action with optional snapshot
SafetyManager.confirm_action(
    action_name="delete_logs",
    requires_snapshot=True
)
```

**Features:**
- Detects available snapshot tools (Timeshift, Snapper)
- Prompts user to create snapshot before proceeding
- Can be disabled per-action via "Don't ask again" checkbox

### ConfirmActionDialog

User confirmation dialog for dangerous operations:

```python
from ui.confirm_dialog import ConfirmActionDialog

if ConfirmActionDialog.confirm(
    parent=self,
    title="Delete All Snapshots",
    message="This action cannot be undone. All snapshots will be permanently deleted.",
    risk_level="HIGH"
):
    # User confirmed, proceed
```

**Features:**
- Risk badges: LOW (green), MEDIUM (yellow), HIGH (red)
- Command preview section (collapsible)
- Per-action "Don't ask again" option
- Undo command display

### HistoryManager

Action logging with undo support:

```python
from utils.history import HistoryManager

# Log action with undo command
HistoryManager.log_change(
    action="delete_snapshots",
    description="Deleted 3 snapshots",
    undo_commands=[
        ("restore_snapshot", ["--id", "123"], "Restore snapshot 123")
    ]
)

# Undo last action
HistoryManager.undo_last()

# Get recent history
history = HistoryManager.get_history(limit=50)
```

**Features:**
- Max 50 actions stored
- Persistent storage in `~/.config/loofi-fedora-tweaks/history.json`
- Status bar undo button in GUI

---

## Risk Registry (v37.0+)

Centralized risk assessment for all privileged actions.

### RiskLevel Enum

```python
from utils.risk import RiskLevel

class RiskLevel(Enum):
    LOW = "low"        # Safe, reversible operations
    MEDIUM = "medium"  # Caution needed, mostly reversible
    HIGH = "high"      # Dangerous, irreversible operations
```

### RiskEntry

```python
from utils.risk import RiskEntry

entry = RiskEntry(
    action="delete_snapshots",
    level=RiskLevel.HIGH,
    description="Permanently delete system snapshots",
    revert_instructions="Cannot be reverted. Create new snapshots."
)
```

### RiskRegistry

```python
from utils.risk import RiskRegistry

# Get risk level for action
risk = RiskRegistry.get_risk("delete_snapshots")
print(risk.level)  # RiskLevel.HIGH

# List all high-risk actions
high_risk = RiskRegistry.list_by_level(RiskLevel.HIGH)
```

---

## Dry-Run Mode (v35.0+)

Preview commands without executing:

```bash
# CLI dry-run
loofi-fedora-tweaks --cli --dry-run cleanup all

# Output:
# 🔍 [DRY-RUN] Would execute: pkexec dnf clean all
#    Description: Cleaning DNF cache...
# 🔍 [DRY-RUN] Would execute: pkexec journalctl --vacuum-time=7d
#    Description: Cleaning journal logs...
```

**Features:**
- Shows exact command that would run
- Logs to audit trail with `dry_run: true`
- Supports `--json` output
- Works with all CLI commands

---

## Best Practices

### For Developers

1. **Always unpack PrivilegedCommand tuples** before passing to subprocess
2. **Never hardcode `dnf`** — use `SystemManager.get_package_manager()`
3. **Add timeouts to ALL subprocess calls** — use category-specific defaults
4. **Use @validated_action** for all privileged command builders
5. **Log all privileged actions** via `AuditLogger`
6. **Test both Traditional and Atomic Fedora** paths
7. **Never use `shell=True` or `sh -c`** patterns

### For Users

1. **Review audit logs regularly**: `loofi-fedora-tweaks --cli audit-log`
2. **Enable snapshot creation** before risky operations
3. **Use dry-run mode** to preview commands: `--dry-run`
4. **Keep polkit policies updated** when upgrading
5. **Review plugin permissions** before installing from marketplace
6. **Report security issues** to maintainers privately (see SECURITY.md)

---

## Security Disclosure

For security vulnerabilities, see [SECURITY.md](https://github.com/loofitheboss/loofi-fedora-tweaks/blob/master/SECURITY.md):

- **Supported versions**: v34.0.0+
- **Response timeline**: 90 days
- **Disclosure**: Private disclosure via GitHub Security Advisories

---

## Next Steps

- [Architecture](Architecture) — Understand PrivilegedCommand pattern
- [Atomic Fedora Support](Atomic-Fedora-Support) — Package manager detection
- [Plugin Development](Plugin-Development) — Plugin permissions model
- [Troubleshooting](Troubleshooting) — Privilege escalation issues

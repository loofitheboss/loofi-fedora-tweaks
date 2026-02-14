# v35.0.0 "Fortress" — Architecture Spec

## Theme

Security & privilege hardening. Complete stabilization guide Phase 1–2.
No new user-facing features. Hardening-only release.

## Design Decisions

### Subprocess Timeout Enforcement

- Add `timeout=` parameter to all 263 `subprocess.run/check_output/Popen/call` calls
- Default timeouts by category:
  - Package operations (dnf, rpm-ostree): `timeout=600` (10 min)
  - Network queries (ping, curl, nmcli): `timeout=30`
  - System info queries (lsblk, uname, hostnamectl): `timeout=15`
  - Service operations (systemctl): `timeout=60`
  - File operations (cp, mv, rm): `timeout=120`
  - Container operations (podman, docker): `timeout=300`
  - VM operations (virsh, qemu): `timeout=300`
  - Default fallback: `timeout=60`
- Wrap `subprocess.TimeoutExpired` with `CommandTimeoutError` from `utils/errors.py`
- CLI `run_operation()` gets configurable `--timeout` flag (default 300s)

### Structured Audit Logging

- New module: `utils/audit.py`
- `AuditLogger` class with structured JSON output
- Log file: `~/.config/loofi-fedora-tweaks/audit.jsonl` (JSON Lines format)
- Each entry: `{"ts": ISO8601, "action": str, "params": dict, "exit_code": int, "stderr_hash": str, "user": str}`
- Rotation: 10 MB, 5 backups (via RotatingFileHandler)
- Integration: `PrivilegedCommand` auto-logs via decorator
- CLI `--audit-log` flag to dump recent entries

### Parameter Schema Validation

- Add `@validated_action` decorator to `PrivilegedCommand` methods
- Schema: dict mapping param names → allowed types + value constraints
- Reject unknown parameters, empty strings, path traversal attempts
- Log validation failures to audit log

### Polkit Policy Separation

- Split single `org.loofi.fedora-tweaks.policy` into granular files:
  - `org.loofi.fedora-tweaks.package-manage.policy`
  - `org.loofi.fedora-tweaks.system-update.policy`
  - `org.loofi.fedora-tweaks.hardware-settings.policy`
  - `org.loofi.fedora-tweaks.system-cleanup.policy`
  - `org.loofi.fedora-tweaks.ostree-manage.policy`
  - `org.loofi.fedora-tweaks.firewall.policy` (NEW)
  - `org.loofi.fedora-tweaks.network.policy` (NEW)
  - `org.loofi.fedora-tweaks.storage.policy` (NEW)
  - `org.loofi.fedora-tweaks.service-manage.policy` (NEW)
  - `org.loofi.fedora-tweaks.kernel.policy` (NEW)
  - `org.loofi.fedora-tweaks.security.policy` (NEW)
- Keep combined policy as fallback; installer deploys granular set
- `PrivilegedCommand` maps actions to policy IDs

### Dry-Run Mode

- Add `--dry-run` flag to CLI
- GUI: preview mode in `ConfirmActionDialog` shows command without executing
- `PrivilegedCommand.execute()` accepts `dry_run=bool` parameter
- Dry-run logs to audit log with `"dry_run": true`

### Notification Panel Fix

- `NotificationPanel.__init__()` calls `self.hide()` at end
- Set `setMaximumHeight(500)` and proper background styling
- Bell button added before badge in layout (bell → badge order)
- Panel positioning: clamp X/Y to window bounds, dynamic height cap
- `setFixedHeight(16)` on badge for consistency

### SECURITY.md

- Vulnerability disclosure via GitHub Security Advisories
- Supported versions table (v34+)
- Security contact email
- Responsible disclosure timeline (90 days)

### install.sh Deprecation

- Add prominent warning banner: "This method is not recommended"
- Add `--i-know-what-i-am-doing` flag required to proceed
- Update README to recommend RPM/Copr as primary install method
- Keep script functional but discourage usage

## File Impact

### New Files
- `utils/audit.py` — Structured audit logger
- `SECURITY.md` — Vulnerability disclosure process
- `config/org.loofi.fedora-tweaks.firewall.policy` — Firewall Polkit
- `config/org.loofi.fedora-tweaks.network.policy` — Network Polkit
- `config/org.loofi.fedora-tweaks.storage.policy` — Storage Polkit
- `config/org.loofi.fedora-tweaks.service-manage.policy` — Service Polkit
- `config/org.loofi.fedora-tweaks.kernel.policy` — Kernel Polkit
- `config/org.loofi.fedora-tweaks.security.policy` — Security Polkit
- `tests/test_audit.py` — Audit logger tests
- `tests/test_timeout_enforcement.py` — Timeout validation tests

### Modified Files (56 utils + CLI for timeouts)
- All 56 files listed in timeout audit (see tasks spec)
- `utils/commands.py` — Parameter validation, audit integration
- `utils/errors.py` — `CommandTimeoutError` exception
- `cli/main.py` — `run_operation()` timeout, `--dry-run`, `--audit-log`
- `ui/notification_panel.py` — Start hidden, proper styling
- `ui/main_window.py` — Bell/badge ordering, panel positioning
- `install.sh` — Deprecation warning
- `README.md` — Install method update
- `CHANGELOG.md` — v35.0.0 entries

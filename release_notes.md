# Release Notes — v19.0.0 "Vanguard"

## Safe Centralized Execution

v19.0 "Vanguard" establishes a **centralized action executor** — a single auditable path for all system commands with preview mode, structured logging, and resource-aware agent arbitration. This is the foundation for preview-before-apply, undo/restore, and diagnostics export in future releases.

---

### Headline Features

#### Centralized ActionExecutor
- **Preview mode**: See exactly what any action will do before it runs
- **Global dry-run**: Disable all real execution with a single toggle for testing
- **Structured JSONL logging**: Every action is logged with timestamp, command, result, and exit code
- **Flatpak-aware**: Auto-wraps commands with `flatpak-spawn --host` inside sandboxed environments
- **pkexec support**: Privilege escalation via `pkexec=True` parameter

#### Unified ActionResult
- Single structured result type replacing ad-hoc `OperationResult` and `AgentResult`
- Fields: `success`, `message`, `exit_code`, `stdout`, `stderr`, `data`, `preview`, `needs_reboot`, `timestamp`, `action_id`
- Convenience constructors: `ActionResult.ok()`, `ActionResult.fail()`, `ActionResult.previewed()`
- Full serialization with output truncation safety

#### Agent Arbitrator
- Blocks background agents when CPU temperature exceeds thermal limit
- Blocks background work on battery power
- Critical actions bypass thermal/power constraints for safety-first response

#### Diagnostics Export
- `ActionExecutor.export_diagnostics()` returns structured action log + system info
- `ActionExecutor.get_action_log(limit=50)` reads recent action history
- JSONL action log auto-trimmed at 500 entries

#### Operations Bridge
- `execute_operation()` bridges existing operation tuples to ActionExecutor
- Enables CLI and headless execution paths without touching GUI code

---

### Safety Model

| Feature | Description |
|---------|-------------|
| Preview mode | Inspect what would execute without running |
| Global dry-run | Single toggle disables all real execution |
| Structured results | Every action returns exit code, stdout, stderr |
| Action logging | JSONL audit trail with auto-trimming |
| Arbitrator | Thermal and battery-aware agent gating |
| Non-critical logging | Log failures never crash actions |

---

### Tests

- **24 new tests** covering ActionResult, ActionExecutor, logging, and bridge
- **4 new arbitrator tests** for thermal blocking, battery blocking, and critical bypass
- **79 tests passing** across the new modules (1598 total project-wide)

---

### New Files

| File | Purpose |
|------|---------|
| `utils/action_result.py` | Unified ActionResult schema |
| `utils/action_executor.py` | Centralized executor with preview, dry-run, logging |
| `utils/arbitrator.py` | Agent resource arbitrator |
| `tests/test_action_executor.py` | ActionExecutor + ActionResult test suite |

---

### What's Next (v19.x — Phase 2 & 3)

- Search + Categories + Recommended/Advanced labels in UI
- Diagnostics export UI with download button
- Preview UI integration in GUI tabs
- Undo/restore for reversible tweaks
- First-run onboarding with safety disclaimers
- RPM/Flatpak build validation alignment
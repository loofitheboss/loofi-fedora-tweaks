---
description: "Code review guidelines adapted for Loofi Fedora Tweaks (Python 3.12+, PyQt6, Fedora Linux)"
applyTo: "**"
excludeAgent: ["coding-agent"]
---

# Code Review Instructions — Loofi Fedora Tweaks

## Review Language

Respond in **English**.

## Review Priorities

### 🔴 CRITICAL (Block merge)
- **Security**: `sudo` usage, `shell=True`, missing `timeout`, exposed secrets, missing audit logging
- **Correctness**: Logic errors, hardcoded `dnf` (must use `SystemManager.get_package_manager()`), unpacked PrivilegedCommand violations
- **Layer Violations**: subprocess calls in `ui/`, PyQt6 imports in `utils/`, business logic in UI tabs
- **Breaking Changes**: API contract changes, CLI output format changes

### 🟡 IMPORTANT (Requires discussion)
- **Test Coverage**: Missing tests for new code, missing atomic/traditional Fedora paths
- **Performance**: Blocking GUI thread, missing caching for `shutil.which()`, O(n²) algorithms
- **Architecture**: Deviation from `ARCHITECTURE.md` patterns
- **Error Handling**: Silent failures, missing typed exceptions from `utils/errors.py`

### 🟢 SUGGESTION (Non-blocking improvements)
- **Readability**: Poor naming, complex logic that could be simplified
- **Optimization**: Performance improvements without functional impact
- **Documentation**: Missing docstrings, outdated comments

## Project-Specific Checks

### Privilege & Command Patterns
```python
# ✅ Verify PrivilegedCommand is always unpacked
binary, args, desc = PrivilegedCommand.dnf("install", "package")
cmd = [binary] + args

# ❌ Never pass raw tuple to subprocess
subprocess.run(PrivilegedCommand.dnf("install", "package"))  # WRONG
```

### Layer Boundaries
- `ui/*_tab.py` — NO `subprocess`, NO business logic, must inherit `BaseTab`
- `utils/*.py` — NO `import PyQt6`, all `@staticmethod`, return ops tuples
- `cli/main.py` — NO `import ui`, calls `utils/` only

### Atomic Fedora Support
- All package operations must branch on `SystemManager.is_atomic()`
- Tests must cover both `dnf` and `rpm-ostree` paths

### Testing Standards
- `@patch` decorators only — never context managers
- Patch module-under-test namespace: `'utils.module.subprocess.run'`
- Test both success AND failure paths
- Never hardcode versions in assertions

## Comment Format

```markdown
**[🔴/🟡/🟢] Category: Brief title**

Description of the issue.

**Why this matters:** Impact explanation.

**Suggested fix:**
```python
# corrected code
```
```

## Checklist

### Code Quality
- [ ] Follows naming conventions (`*Manager`/`*Ops` for utils, `*Tab` for UI)
- [ ] Functions are small and focused
- [ ] No code duplication
- [ ] Error handling uses typed exceptions from `utils/errors.py`
- [ ] `%s` logging (never f-strings in log calls)

### Security
- [ ] No `sudo` — only `pkexec` via PrivilegedCommand
- [ ] No `shell=True` in subprocess
- [ ] All subprocess calls have `timeout=N`
- [ ] Privileged actions are audit-logged

### Testing
- [ ] New code has test coverage
- [ ] Tests cover atomic and traditional Fedora
- [ ] All system calls mocked with `@patch`
- [ ] Both success and failure paths tested

### Architecture
- [ ] Layer boundaries respected (no subprocess in UI, no PyQt6 in utils)
- [ ] Follows patterns in `ARCHITECTURE.md`
- [ ] Uses `self.tr("...")` for user-visible strings

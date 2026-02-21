# Architecture Spec — v1.0.0 "Foundation"

## Design Rationale

v1.0.0 "Foundation" is a version renormalization release. The project graduates from
experimental rapid-increment versioning (v50.0.0) to proper semantic versioning (v1.0.0),
marking the first stable production baseline.

No architectural changes — this release establishes the canonical stable reference point
for all future SemVer-compliant development.

## Scope

### 1. Version Renormalization

| Component | Before | After |
|-----------|--------|-------|
| `version.py` | 50.0.0 "Forge" | 1.0.0 "Foundation" |
| `pyproject.toml` | 50.0.0, Beta | 1.0.0, Production/Stable |
| `.spec` | 50.0.0 | 1.0.0 |
| README badges | v50.0.0 | v1.0.0 |

### 2. Test Expansion

Two new test suites added:
- `test_log.py` — Logging subsystem (XDG paths, root logger, configuration)
- `test_monitor.py` — SystemMonitor (memory, CPU, health checks, byte formatting)

### 3. Test Fix

- `test_plugins_v2.py` — Decoupled version compatibility test from runtime version using `@patch`

### 4. Bug Fix

- `generate_workflow_reports.py` — Fixed Unicode encoding crash on Windows (cp1252 console)

## Architecture Unchanged

The v1.0.0 architecture is identical to v50.0.0:
- 29 feature tabs (GUI mode)
- CLI, Daemon, WebAPI entry modes
- Plugin-based architecture with SDK
- Hardware-aware defaults
- Atomic Fedora (rpm-ostree) support
- RPM/Flatpak/AppImage packaging

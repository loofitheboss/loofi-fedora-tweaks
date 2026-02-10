# Architecture Advisor Memory

## Project Structure Overview

Current package: `loofi-fedora-tweaks/` (hyphenated name, common in Python projects)

### Key Architectural Patterns Identified

1. **Centralized Action Executor Pattern** (`utils/action_executor.py`)
   - All system-modifying commands must route through ActionExecutor
   - Returns structured ActionResult objects
   - Supports preview mode, dry-run, and rollback
   - Maintains action log at `~/.local/share/loofi-fedora-tweaks/action_log.jsonl`
   - v19.0 Foundation requirement: safety-first operations

2. **Module Boundaries** (current state)
   - `ui/` — 40+ tab files, dialogs, widgets (PyQt6)
   - `utils/` — 130+ modules, ~27K lines (MASSIVE catch-all)
   - `api/` — REST API routes (executor, system endpoints)
   - `plugins/` — Plugin system with ai_lab, hello_world, virtualization examples
   - `agents/` — Agent configuration JSON files (cleanup, security, thermal)
   - `cli/` — CLI interface entry point
   - `web/` — Web interface components
   - `main.py` — Entry point with mode detection (GUI/CLI/daemon/web)
   - `version.py` — Version string

3. **Utils Problem**
   - 130+ files in single flat directory
   - Mixes: system services, business logic, UI helpers, agents, AI, execution layer
   - No clear separation of concerns
   - Examples of misplaced code:
     - `action_executor.py` — core execution layer, not a "util"
     - `agents.py`, `agent_*.py` — agent logic in utils
     - `api_server.py` — server infrastructure in utils
     - `daemon.py` — background service in utils
     - System services: `services.py`, `systemd.py`, `package_manager.py`

4. **Entry Point Pattern**
   - `main.py` dispatches to: GUI, CLI, daemon, or web server
   - No root required for GUI, most operations use pkexec escalation
   - Tests must mock ActionExecutor, no system access

## v23.0 Refactor Target

CLAUDE.md specifies:
- `ui/` — UI layer
- `core/` — core business logic
- `services/` — service abstraction
- `utils/` — utilities only

## Design Constraints

- Backward compatibility: imports must remain stable or aliased
- Packaging: RPM/Flatpak/AppImage/sdist all reference current paths
- Testing: no root required, all system calls mocked
- Minimal disruption: incremental migration preferred

## v23.0 Decisions

**CommandRunner vs CommandWorker (Feb 2026):**
- Decision: **Adapter pattern** (Option A)
- CommandWorker wraps CommandRunner for BaseWorker compatibility
- Preserve existing CommandRunner usage in 25+ tabs
- No breaking changes to BaseTab API
- Gradual migration path: new code uses CommandWorker, old code unchanged
- Rationale: Minimize disruption, maintain backward compat, incremental refactor

**Service Layer Strategy (Feb 2026):**
- Decision: **New abstractions** (Option A)
- Service layer provides clean interfaces, delegates to existing utils
- SystemManager remains unchanged (no rename, no breaking imports)
- PackageService wraps existing package_manager.py logic
- SystemService uses SystemManager for detection/info, adds async operations
- Rationale: Backward compatible, incremental architecture improvement, no migration disruption

## Related Files

- [refactor-plan.md](refactor-plan.md) — v23.0 structure design

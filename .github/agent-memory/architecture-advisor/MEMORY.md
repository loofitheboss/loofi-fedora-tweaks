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

## v25.0 Plugin Architecture Decisions (Feb 2026)

**Package root**: `loofi-fedora-tweaks/loofi-fedora-tweaks/` (inner package, NOT project root)

**MainWindow facts** (`loofi-fedora-tweaks/loofi-fedora-tweaks/ui/main_window.py`):

- 26 hardcoded `add_page()` calls in `__init__`
- `_lazy_tab()` dict with 22 entries (lambda importlib loaders)
- `_TAB_META` dict with 26 entries: name -> (description, badge)
- `DashboardTab` and `SystemInfoTab` are eager (not lazy)
- `SettingsTab` passed `self` (MainWindow) in `_lazy_tab("settings")` lambda
- Categories: Dashboard, Automation, System, Hardware, Software, Network, Security, Desktop, Tools, Settings

**BaseTab facts** (`ui/base_tab.py`):

- Extends `QWidget` only (not ABC/Protocol)
- Has CommandRunner wiring, output_area, run_command, append_output
- Zero-arg `__init__`
- Does NOT currently implement any plugin interface

**SettingsTab** (`ui/settings_tab.py`):

- `__init__(self, main_window=None)` — takes optional MainWindow ref
- Cannot be zero-arg instantiated without refactor
- DI solution: add `set_context(context: dict)`, defer `_init_ui()` until then

**v25.0 Key Decisions:**

- PluginInterface: ABC (not Protocol) — fail-fast enforcement
- External plugins: DEFERRED to v26.0
- Compat checks: RUNTIME disabled state (not load-time skip)
- Metadata: CLASS ATTRIBUTE `_METADATA` + `metadata()` method (not decorator)
- LazyWidget: pass `plugin.create_widget` as zero-arg callable — NO changes to LazyWidget
- Import isolation: `core/plugins/loader.py` uses `importlib.import_module()` for UI tabs — no static imports

**Circular import rule**: `core/plugins/` MUST NOT statically import `ui/`. Loader uses importlib at runtime.

**MRO pattern for dual-parent tabs**: `class SomeTab(QWidget, PluginInterface)` — QWidget first.

**Spec files produced:**

- `.workflow/specs/arch-v25.0.md` — full blueprint with signatures, migration strategy, risk mitigations
- `.workflow/specs/release-notes-draft-v25.0.md` — user-facing notes + plugin dev guide

## Related Files

- [refactor-plan.md](refactor-plan.md) — v23.0 structure design

# Project Coordinator Memory

## Workflow System (v23.0+)

### Automated Pipeline

- 7-phase pipeline: PLAN, DESIGN, IMPLEMENT, TEST, DOCUMENT, PACKAGE, RELEASE
- Prompts at `.claude/workflow/prompts/`
- Task files at `.claude/workflow/tasks-v{VERSION}.md`
- Model routing: `.claude/workflow/model-router.md`
- CLI runner: `scripts/workflow-runner.sh <version> [phase]`

### Version Status

- v21.0: DONE (UX Stabilization)
- v22.0: SKIPPED (Usability)
- v23.0: DONE (Architecture Hardening)
- v24.0: DONE (Power Features)
- v25.0: NEXT (Plugin Architecture + UI Redesign)
  -- P1 PLAN complete 2026-02-11
- Source of truth: `ROADMAP.md`

## Architecture

- **Main window**: `ui/main_window.py`
  HBox: sidebar (240px) | right (breadcrumb + stack + status)
- **Themes**: 3 QSS in `assets/`: modern (dark), light, style (legacy)
- **Tab pattern**: 14 tabs use `configure_top_tabs()`;
  lazy-loaded via `lazy_widget.py`
- **Base tab**: `base_tab.py` provides CommandRunner wiring;
  not all tabs extend it
- **Main entry**: `main.py` loads `modern.qss` by default

## v23.0 Architecture Hardening (2026-02-09)

### Completed

- Dir skeleton: `core/` (6 subdirs), `services/` (8 subdirs)
- `core/executor/`: ActionExecutor + ActionResult + Operations
- Backward-compat shims in `utils/`
- Tests: `test_action_executor.py` (18 tests)
- CI: `ci.yml` + `release.yml` + `auto-release.yml`

### Stub Only (init comment, no logic)

- `core/`: agents, ai, diagnostics, export, profiles
- `services/`: all 8 subdirs

### Not Started

- Service abstraction: 0 of 90 utils files migrated
- Subprocess centralization: 292 calls in 55 files
- QThread/QRunnable: ad-hoc in 8 files

### Key Numbers

- 90 Python files in utils/, 40+ in ui/, 3 in core/executor/
- 2 subprocess wrappers: CommandRunner (QProcess/GUI)
  and ActionExecutor (subprocess/core)
- CommandRunner imported by 11 files

## Task Decomposition Rules

- Max 15 tasks per version
- Order: utils, core, services, ui, cli, tests, docs
- Each task: 1 agent, 1 layer, acceptance criteria
- Pair implementation tasks with test tasks

## Layout Constants (main_window.py)

- Sidebar: `setFixedWidth(240)`, search: 36px, footer: 28px
- Breadcrumb: 44px, status bar: 28px

## Key Patterns

- See [patterns.md](patterns.md) for QSS and layout patterns

## v25.0 Plugin Architecture -- Plan (2026-02-11)

### Key Findings

- 26 tabs via hardcoded `add_page()` + `_lazy_tab()` dict
- 11 tabs extend `BaseTab`, 15 extend plain `QWidget`
- `_TAB_META` dict holds desc+badge -- moves to PluginMetadata
- `SettingsTab` takes MainWindow ref -- needs DI hook
- LazyWidget pattern preserved in PluginLoader
- Task spec: `.workflow/specs/tasks-v25.0.md` (15 tasks)

### New Files (planned)

- `core/plugins/interface.py` -- PluginInterface ABC
- `core/plugins/metadata.py` -- PluginMetadata dataclass
- `core/plugins/registry.py` -- PluginRegistry
- `core/plugins/loader.py` -- PluginLoader
- `core/plugins/compat.py` -- CompatibilityDetector

### Critical Risks

- Circular import: `core/plugins/` must not import `ui/`
- Tab ordering regression: need PluginMetadata.order field
- 15 QWidget-only tabs need migration to PluginInterface

## General Risks

- Inline `setStyleSheet()` in ~30 files: hardcoded dark colors
- 292 direct subprocess calls: massive migration surface

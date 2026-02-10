# Project Coordinator Memory

## Workflow System (v23.0+)

### Automated Pipeline
- 7-phase pipeline: PLAN → DESIGN → IMPLEMENT → TEST → DOCUMENT → PACKAGE → RELEASE
- Prompts at `.claude/workflow/prompts/`
- Task files at `.claude/workflow/tasks-v{VERSION}.md`
- Model routing: `.claude/workflow/model-router.md`
- CLI runner: `scripts/workflow-runner.sh <version> [phase]`

### Version Status
- v21.0: DONE (UX Stabilization)
- v23.0: ACTIVE (Architecture Hardening)
- v22.0: NEXT (Usability)
- v24.0-v25.0: PLANNED
- Source of truth: `ROADMAP.md`

## Architecture

- **Main window**: `loofi-fedora-tweaks/ui/main_window.py` -- HBox layout: sidebar (240px fixed) | right (breadcrumb + stacked content + status bar)
- **Themes**: 3 QSS files in `assets/`: `style.qss` (legacy), `modern.qss` (dark/Catppuccin Mocha), `light.qss` (Catppuccin Latte)
- **Tab pattern**: 14 tabs use `configure_top_tabs()` from `tab_utils.py`; tabs are lazy-loaded via `lazy_widget.py`
- **Base tab**: `base_tab.py` provides command runner wiring; not all tabs extend it
- **Main entry**: `main.py` loads `modern.qss` by default

## v23.0 Architecture Hardening -- Status (2026-02-09)

### Completed
- Directory skeleton: `core/` (6 subdirs), `services/` (8 subdirs), `ui/` (pre-existing)
- `core/executor/`: ActionExecutor + ActionResult + Operations -- full implementations
- Backward-compat shims in `utils/` (action_executor, action_result, operations, __init__)
- Tests: `test_action_executor.py` -- 18 tests for preview/dry-run/exec/timeout/flatpak/logging
- GitHub Actions: `ci.yml` (lint+typecheck+security+test+RPM) + `release.yml` (tag-triggered)
- Auto-release pipeline: `.github/workflows/auto-release.yml`

### Stub Only (init comment, no logic)
- `core/`: agents, ai, diagnostics, export, profiles
- `services/`: all 8 subdirs (desktop, hardware, network, security, software, storage, system, virtualization)

### Not Started
- Service abstraction: 0 of 90 utils files migrated to services/
- Subprocess centralization: 292 `subprocess.*` calls in 55 utils files
- QThread/QRunnable pattern: ad-hoc in 8 files, no centralized worker

### Key Numbers
- 90 Python files in utils/, 40+ in ui/, 3 in core/executor/
- 2 subprocess wrappers coexist: CommandRunner (QProcess/GUI) + ActionExecutor (subprocess/core)
- CommandRunner imported by 11 files, PrivilegedCommand by 5 files

## Task Decomposition Rules
- Max 15 tasks per version
- Order: utils → core → services → ui → cli → tests → docs
- Each task: 1 agent, 1 layer, acceptance criteria
- Pair implementation tasks with test tasks

## Layout Constants (main_window.py)
- Sidebar: `setFixedWidth(240)`, search: `setFixedHeight(36)`, footer: 28px
- Breadcrumb: `setFixedHeight(44)`, status bar: `setFixedHeight(28)`

## Key Patterns
- See [patterns.md](patterns.md) for QSS and layout patterns

## Risks
- Inline `setStyleSheet()` in ~30 files uses hardcoded dark theme colors
- 292 direct subprocess calls -- massive migration surface

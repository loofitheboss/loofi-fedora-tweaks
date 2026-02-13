# Architecture Spec — v33.0.0 "Testing & CI Hardening"

## Design Rationale

v33.0 introduces a self-maintaining AI workflow system. The core problem: project stats
(tab count, test count, coverage, version) were hardcoded in 19+ files with no
synchronization mechanism, causing massive drift.

## Architecture Decisions

### 1. Stats Introspection Engine (`scripts/project_stats.py`)

- Reads live data from codebase: version.py, ui/*_tab.py, tests/test_*.py, utils/*.py
- Outputs `.project-stats.json` (gitignored — regenerated on demand)
- `--check` mode for CI gates
- Foundation for template rendering and drift detection

### 2. Template Variable System

Agent/instruction files use `{{variable}}` placeholders (e.g., `{{tab_count}}`, `{{version}}`).
`sync_ai_adapters.py --render` substitutes these with values from `.project-stats.json`.

### 3. Single Canonical Source (ARCHITECTURE.md)

All agent and instruction files reference `ARCHITECTURE.md` instead of duplicating
layer rules, tab layout, and critical patterns. Reduces maintenance surface from 19 files to 1.

### 4. Strict Phase Ordering

`workflow_runner.py` enforces `Plan → Design → Build → Test → Doc → Package → Release`.
Each phase checks the run manifest for prior phase completion. `--force-phase` escapes.

### 5. Claude CLI Support

`build_agent_command()` now handles `--assistant claude` with proper model mapping
and tool allowlisting (`Edit,Write,Bash,Read,MultiEdit` for write, `Read,Bash` for review).

### 6. CI Hardening

- Remove `continue-on-error: true` from `test` and `typecheck` jobs
- Add `stats_check` job using `project_stats.py --check`
- Build gate now requires test + typecheck to pass

### 7. Version Bump Cascade (`scripts/bump_version.py`)

Single command updates: version.py → .spec → stats → templates → race-lock.
Ensures version changes propagate everywhere automatically.

## File Changes

| File | Change |
|------|--------|
| `scripts/project_stats.py` | NEW — stats introspection engine |
| `scripts/bump_version.py` | NEW — version bump cascade |
| `ARCHITECTURE.md` | NEW — canonical architecture reference |
| `scripts/sync_ai_adapters.py` | ADD `--render` mode for template substitution |
| `scripts/workflow_runner.py` | ADD Claude CLI, phase ordering enforcement |
| `.github/agents/*.agent.md` | REWRITE — reference ARCHITECTURE.md, correct stats |
| `.github/instructions/*.md` | UPDATE — correct stats, Python 3.12+ |
| `.github/copilot-instructions.md` | UPDATE — reference ARCHITECTURE.md |
| `AGENTS.md`, `CLAUDE.md` | UPDATE — correct stats |
| `.github/workflows/ci.yml` | HARDEN — remove soft gates, add stats_check |
| `.codex/skills/` | ADD design, doc, package skills |
| `.github/workflow/model-router.*` | ALIGN .toml and .md |
| `.vscode/tasks.json` | UPDATE defaults to v33.0 |

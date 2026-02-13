# Plan: Self-Maintaining AI Workflow Automation (v33.0)

**TL;DR**: The project's AI infrastructure has no mechanism to stay current — version numbers, tab counts, test counts, and coverage stats are hardcoded in 19+ files and manually maintained (they aren't). This plan adds a **project stats introspection engine** that auto-generates accurate data from the codebase, a **template system** for agent/instruction files so they never go stale, **strict CI gates** that block releases when stats drift, and a **custom MCP server** so AI agents can query live workflow state. Every change is designed to be self-maintaining: version bumps flow automatically, stats refresh on every CI run, and agent files regenerate from templates.

---

**Steps**

### Phase 1: Stats Engine — Single Source of Dynamic Truth

1. **Create [scripts/project_stats.py](scripts/project_stats.py)** — introspects the actual codebase and outputs a JSON stats file:
   - Reads `version.py` → `version`, `codename`, `app_name`
   - Counts `ui/*_tab.py` → `tab_count` (currently 27, not 25)
   - Counts `tests/test_*.py` → `test_file_count`
   - Counts `utils/*.py` → `utils_module_count` (currently 101, not 52)
   - Reads latest pytest coverage from `.workflow/reports/` → `coverage_percent`
   - Reads latest test count from pytest output → `test_count`
   - Reads `ROADMAP.md` → `active_version`, `next_version`, `roadmap_status`
   - Reads `.race-lock.json` → `pipeline_version`, `pipeline_status`
   - Lists actual tab names from `MainWindow` tab registration → `tab_names[]`
   - Outputs to **`.project-stats.json`** (gitignored, regenerated on every run)
   - Also outputs human-readable **`.project-stats.md`** for embedding in docs
   - Has `--check` mode: compares stats against what's in instruction/agent files, exits non-zero on drift
   - Has `--format template` mode: outputs stats as `{{variable}}` substitution map

2. **Add `.project-stats.json` to `.gitignore`** — this is a build artifact, not committed. CI and local dev regenerate it.

3. **Add `stats_check` job to [.github/workflows/ci.yml](.github/workflows/ci.yml)** — runs `project_stats.py --check` on every push/PR. **Hard gate** (no `continue-on-error`). This catches any hardcoded stat that drifts from reality.

### Phase 2: Template System — Agent/Instruction Files Never Go Stale

4. **Convert `sync_ai_adapters.py` from pure copier to template engine**:
   - Add `--render` mode: reads `.project-stats.json`, substitutes `{{version}}`, `{{tab_count}}`, `{{test_count}}`, `{{coverage}}`, `{{utils_count}}`, `{{active_version}}`, `{{codename}}` in all agent/instruction files
   - Template variables use `{{double_brace}}` syntax (won't conflict with markdown or code)
   - Falls back to `project_stats.py` if `.project-stats.json` doesn't exist
   - The existing `--check` drift detection now also validates template variables are current
   - Existing pure-copy behavior preserved for non-templated files

5. **Convert all 8 VS Code agent files to use template variables**:
   - Replace every instance of hardcoded version: `v13.0`, `v13.5.0`, `v15.0`, `v19.0` → `{{version}}`
   - Replace `20 tabs` / `25 tabs` → `{{tab_count}} tabs`
   - Replace `839+ tests` / `3846+ tests` → `{{test_count}}+ tests`
   - Replace `151 test files` → `{{test_file_count}} test files`
   - Replace `52+ utils modules` → `{{utils_module_count}} utils modules`
   - Replace `76.8%` coverage → `{{coverage}}% coverage`
   - Fix `Python 3.11+` → `Python 3.12+` in `primary.instructions.md` to match `pyproject.toml` (`requires-python = ">=3.12"`)
   - Remove hardcoded CI runner paths from [CodeGen.agent.md](.github/agents/CodeGen.agent.md)
   - Fix GTK references → PyQt6 (fix, not template)
   - Add `@import ARCHITECTURE.md` reference instruction in each agent

6. **Convert instruction files to use template variables**:
   - [primary.instructions.md](.github/instructions/primary.instructions.md): `current: v29.0.0` → `current: v{{version}}`; `25 UI tabs, 151 test files (3846+ tests, 76.8% coverage), 52+ utils modules` → `{{tab_count}} UI tabs, {{test_file_count}} test files ({{test_count}}+ tests, {{coverage}}% coverage), {{utils_module_count}} utils modules`
   - [workflow.instructions.md](.github/instructions/workflow.instructions.md): `Active: v29.0.0` → `Active: v{{active_version}}`; coverage targets → `{{coverage}}%`
   - [AGENTS.md](AGENTS.md): same stat substitutions
   - [CLAUDE.md](CLAUDE.md): same
   - [.github/copilot-instructions.md](.github/copilot-instructions.md): same

7. **Add template rendering to CI** — after `stats_check` passes, the `adapter_drift` job runs `sync_ai_adapters.py --render --check` to verify all templates are rendered with current stats. If a file still contains `{{variable}}` in committed content, CI fails.

8. **Create rendering workflow**: the sync script renders templates → writes output files → these are the files AI tools actually read. Two approaches (recommend A):
   - **A. Render in-place**: Templates use `{{var}}` in source, `sync_ai_adapters.py --render` replaces them in the actual files. CI `--check` verifies values match reality. When stats change, re-run render and commit.
   - **B. Source/output split**: Keep `.tmpl` files as source, generate output files. More complex, more files.
   - With approach A: `sync_ai_adapters.py --render` becomes part of the version bump workflow — run once, commit results.

### Phase 3: Single Architecture Reference

9. **Create [ARCHITECTURE.md](ARCHITECTURE.md)** at project root — the ONE canonical reference. Uses template variables for all stats. Contains:
   - Project identity: `v{{version}} "{{codename}}"`, PyQt6, `{{tab_count}}` tabs, `{{test_count}}+` tests
   - Layer structure (UI → Utils → CLI → Core → Services → Plugins)
   - All critical patterns (PrivilegedCommand, BaseTab, CommandRunner, operations tuples, Atomic Fedora, error framework)
   - Tab layout table (dynamic from `{{tab_names}}`)
   - Testing conventions
   - Build/run commands

10. **Refactor all instruction/agent files** to reference `ARCHITECTURE.md` for shared patterns instead of duplicating them. Each file keeps only its role-specific delta:
    - Agent files: role, tools, scope, workflow — no architecture duplication
    - Instruction files: rules, conventions, output format — no pattern duplication
    - `AGENTS.md`: agent system quick reference only
    - `CLAUDE.md`: Claude-specific config only

### Phase 4: Agent Definitions Update + Auto-generation

11. **Rewrite all 8 VS Code agent files** with template variables + current architecture:
    - All reference `ARCHITECTURE.md` as required context
    - All use `{{version}}`, `{{tab_count}}`, `{{test_count}}` etc.
    - Fix specific errors: GTK→PyQt6, wrong Python version, wrong paths
    - Add Guardian ↔ security scope for v33 quality targets
    - Make Manager aware of workflow pipeline phases and MCP server

12. **Update `sync_ai_adapters.py`** to generate Claude agents from VS Code canonical source with template rendering. Fix memory paths from `/workspaces/` → relative `./`

13. **Add auto-regeneration to version bump workflow**: when `scripts/bump_version.py` (step 29) runs, it automatically:
    - Updates `version.py`
    - Runs `project_stats.py` to refresh stats
    - Runs `sync_ai_adapters.py --render` to update all files
    - Commits the changes

### Phase 5: Workflow Pipeline — Strict Phase Enforcement

14. **Add strict phase ordering to [scripts/workflow_runner.py](scripts/workflow_runner.py)**:
    - `design` → requires `tasks-{ver}.md` exists
    - `build` → requires `arch-{ver}.md` exists
    - `test` → requires build phase logged in manifest
    - `doc` → requires test results with 0 failures
    - `package` → requires doc phase logged
    - `release` → requires package artifacts exist
    - New `--force` flag bypasses ordering for recovery
    - New `--status` flag prints current phase state for the active version

15. **Add Claude Code CLI command builder** to `workflow_runner.py`:
    - Detect `claude` binary availability
    - Build `claude --model {model} --prompt {prompt}` commands
    - Add proper model mapping: `.toml` model names → Claude CLI model names
    - Add to `VALID_ASSISTANTS` with documentation

16. **Create v33 workflow specs** with full contract markers:
    - [.workflow/specs/tasks-v33.0.0.md](.workflow/specs/tasks-v33.0.0.md) — every step in this plan as a task with ID, Files, Dep, Agent, Description, Acceptance, Docs, Tests
    - [.workflow/specs/arch-v33.0.0.md](.workflow/specs/arch-v33.0.0.md) — architecture decisions for stats engine, template system, MCP server
    - Update [.race-lock.json](.workflow/specs/.race-lock.json) → `v33.0.0 active`
    - Create retroactive v32 specs from ROADMAP

### Phase 6: CI/CD Hardening

17. **Remove `continue-on-error: true`** from `test` and `typecheck` jobs in:
    - [.github/workflows/ci.yml](.github/workflows/ci.yml)
    - [.github/workflows/auto-release.yml](.github/workflows/auto-release.yml)
    - Add `needs.test.result == 'success'` and `needs.typecheck.result == 'success'` to auto-release build gate

18. **Add workflow pipeline gate to auto-release** — new job `pipeline_gate`:
    - Validates `tasks-{ver}.md` and `arch-{ver}.md` exist
    - Validates all tasks are marked complete
    - Validates race-lock version matches releasing version

19. **Add stats consistency gate to CI** — `project_stats.py --check` as hard gate, catches any hardcoded stat drift on every PR

20. **Add pytest annotations** — `pytest-github-actions-annotate-failures` for inline PR error annotations

### Phase 7: Codex Skills — Full Phase Coverage

21. **Create [.codex/skills/design/SKILL.md](.codex/skills/design/SKILL.md)** — reads `tasks-{ver}.md`, produces `arch-{ver}.md` with module boundaries and API contracts

22. **Create [.codex/skills/doc/SKILL.md](.codex/skills/doc/SKILL.md)** — updates CHANGELOG, README, release notes; validates `self.tr()` wrapping

23. **Create [.codex/skills/package/SKILL.md](.codex/skills/package/SKILL.md)** — verifies version sync, builds RPM, validates packaging artifacts

24. **Update existing skills** ([test](/.codex/skills/test/SKILL.md), [release](/.codex/skills/release/SKILL.md), [implement](/.codex/skills/implement/SKILL.md)) to:
    - Reference `ARCHITECTURE.md` instead of inlining patterns
    - Use `project_stats.py` for dynamic data
    - Include race-lock state transitions in release skill

### Phase 8: Custom MCP Workflow Server

25. **Create [scripts/mcp_workflow_server.py](scripts/mcp_workflow_server.py)** — stdio MCP server:
    - **Tools**: `workflow_status`, `workflow_tasks`, `workflow_run_phase`, `workflow_validate`, `project_stats`
    - **Resources**: `workflow://race-lock`, `workflow://tasks/{version}`, `workflow://arch/{version}`, `workflow://stats`
    - The `project_stats` tool runs `project_stats.py` and returns live stats — agents always have current data
    - `workflow_status` returns phase state, active version, next version, blockers

26. **Register in MCP configs** — [.vscode/mcp.json](.vscode/mcp.json) and [.copilot/mcp-config.json](.copilot/mcp-config.json)

### Phase 9: Model Router + VS Code Alignment

27. **Align model router** — single three-tier system in `.toml` (brain/work/light), regenerate `.md` from `.toml` via script. Remove conflicting `CLAUDE.md` model section.

28. **Update [.vscode/tasks.json](.vscode/tasks.json)** — fix defaults to `v33.0`, add local test/lint tasks, remove legacy validate task

29. **Create [scripts/bump_version.py](scripts/bump_version.py)** — the cascade script:
    - Updates `version.py` and `.spec`
    - Runs `project_stats.py` to generate fresh stats
    - Runs `sync_ai_adapters.py --render` to refresh all template variables
    - Creates new `tasks-{ver}.md` and `arch-{ver}.md` stubs
    - Updates race-lock
    - Updates `tasks.json` defaults
    - Has `--check` mode for CI (validates everything is in sync without modifying)
    - Single command: `python3 scripts/bump_version.py v34.0.0 "Codename"`

### Phase 10: Cleanup

30. **Delete orphaned files**: `.github/workflow/tasks-v23.0.md`, fix MEMORY.md paths
31. **Add `stats_freshness` CI check** — weekly cron job that runs `project_stats.py --check` against committed files, opens an issue if any stat is stale (catches drift between releases)

---

## Self-Maintenance Guarantees

| What drifts today | Prevention mechanism | Enforcement |
|---|---|---|
| Version in instruction/agent files | `{{version}}` template variable from `version.py` | `stats_check` CI gate (hard fail) |
| Tab count (25 vs 27 vs actual) | `{{tab_count}}` counted from `ui/*_tab.py` | `stats_check` CI gate |
| Test count (839 vs 3846 vs actual) | `{{test_count}}` from pytest output | `stats_check` CI gate |
| Coverage percent | `{{coverage}}` from last pytest-cov run | `stats_check` CI gate |
| Utils module count (52 vs 101) | `{{utils_module_count}}` counted from `utils/*.py` | `stats_check` CI gate |
| Agent files frozen at old version | Template rendering + adapter sync CI check | `adapter_drift` CI gate |
| Race lock stale | `bump_version.py` auto-updates lock | `pipeline_gate` in auto-release |
| Workflow specs missing | `bump_version.py` creates stubs | `pipeline_gate` in auto-release |
| Model router conflicts | Single `.toml` source, `.md` auto-generated | Part of render pipeline |
| VS Code task defaults | `bump_version.py` updates defaults | `stats_check` CI gate |

**Key principle**: No human should ever manually update a project stat. `project_stats.py` introspects reality, `sync_ai_adapters.py --render` propagates it, `bump_version.py` orchestrates it, and CI enforces it.

---

## Verification

- `python3 scripts/project_stats.py` — outputs accurate `.project-stats.json`
- `python3 scripts/project_stats.py --check` — exits 0 (all files match reality)
- `python3 scripts/sync_ai_adapters.py --render --check` — exits 0 (all templates rendered, no drift)
- `python3 scripts/bump_version.py --check` — exits 0 (version consistent everywhere)
- Push a PR that changes a stat — `stats_check` CI gate catches it
- Push a PR with failing tests — CI fails (no `continue-on-error`)
- Run `workflow_runner.py --phase build --target-version v33.0.0` without arch spec — rejected with clear error
- MCP server responds to `workflow_status` with live race-lock + stats

---

## Decisions

- **Self-maintenance**: Template variable system (`{{var}}`) + stats introspection engine — no more hardcoded stats
- **Canonical source**: VS Code `.github/agents/` with template variables → auto-rendered + synced to Claude adapters
- **CI enforcement**: 3 hard gates — `stats_check` (stat drift), `adapter_drift` (agent sync), `pipeline_gate` (workflow specs exist)
- **Version cascade**: Single `bump_version.py` command updates everything — version.py, .spec, stats, agents, instructions, race-lock, task stubs, VS Code defaults
- **Weekly freshness cron**: Auto-opens GitHub issue if stats drift between releases
- **Phase ordering**: Strict with `--force` escape hatch
- **Full Codex skills**: All 7 phases covered (add design, doc, package)
- **MCP server**: Custom workflow server with live stats tool
- **Model router**: Single `.toml` truth, `.md` auto-generated

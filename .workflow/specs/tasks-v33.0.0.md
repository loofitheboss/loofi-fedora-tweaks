# Tasks — v33.0.0 "Testing & CI Hardening"

## Scope

Self-maintaining AI workflow automation, CI hardening, and testing improvements.

---

## Tasks

- [ ] T1: ID: T1 | Files: scripts/project_stats.py | Dep: none | Agent: backend-builder | Description: Project stats introspection engine
  Acceptance: Generates .project-stats.json with version, tab count, test count, coverage, utils count
  Docs: README.md (mention stats command)
  Tests: tests/test_project_stats.py

- [ ] T2: ID: T2 | Files: ARCHITECTURE.md | Dep: none | Agent: architecture-advisor | Description: Canonical architecture reference document
  Acceptance: Single source of truth for architecture, layer rules, tab layout, patterns
  Docs: ARCHITECTURE.md
  Tests: N/A (documentation)

- [ ] T3: ID: T3 | Files: scripts/sync_ai_adapters.py | Dep: T1 | Agent: backend-builder | Description: Add --render mode for template variable substitution
  Acceptance: --render substitutes {{variable}} templates using .project-stats.json
  Docs: README.md (sync command docs)
  Tests: tests/test_sync_ai_adapters.py

- [ ] T4: ID: T4 | Files: .github/agents/*.agent.md | Dep: T2 | Agent: code-implementer | Description: Rewrite 8 VS Code agent files with ARCHITECTURE.md references
  Acceptance: All agents reference ARCHITECTURE.md, correct stats, no duplication
  Docs: AGENTS.md
  Tests: CI adapter_drift check

- [ ] T5: ID: T5 | Files: .github/instructions/*.md, .github/copilot-instructions.md | Dep: T2 | Agent: code-implementer | Description: Update instruction files with correct stats and references
  Acceptance: All instruction files reference ARCHITECTURE.md, Python 3.12+
  Docs: N/A
  Tests: CI adapter_drift check

- [ ] T6: ID: T6 | Files: scripts/workflow_runner.py | Dep: none | Agent: backend-builder | Description: Add Claude CLI support and phase ordering enforcement
  Acceptance: --assistant claude works, phases enforce ordering with --force-phase escape
  Docs: docs/CONTRIBUTING.md (workflow section)
  Tests: tests/test_workflow_runner.py

- [ ] T7: ID: T7 | Files: .github/workflows/ci.yml | Dep: T1 | Agent: code-implementer | Description: Harden CI gates (remove continue-on-error, add stats_check)
  Acceptance: test and typecheck are hard gates, stats_check job validates consistency
  Docs: N/A
  Tests: CI pipeline validates itself

- [ ] T8: ID: T8 | Files: .codex/skills/ | Dep: none | Agent: code-implementer | Description: Create missing Codex skills (design, doc, package)
  Acceptance: All 7 pipeline phases have matching Codex skills
  Docs: README.md
  Tests: N/A (configuration)

- [ ] T9: ID: T9 | Files: scripts/bump_version.py | Dep: T1, T3 | Agent: backend-builder | Description: Version bump cascade script
  Acceptance: Updates version.py, .spec, re-generates stats, re-renders templates
  Docs: docs/RELEASE_CHECKLIST.md
  Tests: tests/test_bump_version.py

- [ ] T10: ID: T10 | Files: .github/workflow/model-router.toml, model-router.md | Dep: none | Agent: code-implementer | Description: Align model router files
  Acceptance: .toml and .md are consistent, three-tier system (brain/labor/labor-light)
  Docs: model-router.md
  Tests: N/A (configuration)

- [ ] T11: ID: T11 | Files: .vscode/tasks.json | Dep: none | Agent: code-implementer | Description: Update VS Code tasks with current defaults
  Acceptance: Default version is v33.0, local test/lint tasks added
  Docs: N/A
  Tests: N/A (configuration)

- [ ] T12: ID: T12 | Files: .github/workflows/stats-freshness.yml | Dep: T1 | Agent: code-implementer | Description: Weekly stats freshness cron
  Acceptance: Weekly CI job regenerates stats and checks for drift
  Docs: N/A
  Tests: CI validates itself

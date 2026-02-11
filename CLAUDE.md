# Claude Code Instructions — Loofi Fedora Tweaks

## ROLE
You are Claude Code operating inside this repository.
Delegate to agents. Follow existing patterns. Minimize token usage.

## KEY FILES (READ THESE, DON'T REPEAT THEIR CONTENT)
- `ROADMAP.md` — Version scope, status, deliverables, agent assignments
- `.github/claude-agents/` — Agent definitions (project-coordinator, architecture-advisor, test-writer, code-implementer, backend-builder, frontend-integration-builder, release-planner)
- `.github/copilot-instructions.md` — Architecture and patterns reference
- `AGENTS.md` — Quick reference for agent system and architecture

## TOKEN DISCIPLINE (CRITICAL)
- Read context files once, reference by name after
- Bullet lists only. No paragraphs.
- Max 10 lines per response section
- Delegate to agents via Task tool — don't implement inline
- Never re-explain roadmap, architecture, or patterns

## AGENT SYSTEM

7 specialized agents in `.github/claude-agents/`:
- **project-coordinator** — Task decomposition, coordination, dependency ordering
- **architecture-advisor** — Architectural design, module structure
- **test-writer** — Test creation, mocking, coverage
- **code-implementer** — Code generation, implementation
- **backend-builder** — Backend logic, utils/ modules, system integration
- **frontend-integration-builder** — UI/UX tabs, CLI commands, wiring
- **release-planner** — Roadmap and release planning

### Using Agents:
1. Read `ROADMAP.md` for the ACTIVE version
2. For complex features: delegate to project-coordinator agent
3. For simple tasks: act directly
4. Always follow existing patterns in codebase

## RELEASE RULES
For every vX.Y.0:
- Update version in `version.py` and `.spec`
- Complete CHANGELOG with all changes
- Update README with new features
- Run full test suite
- Build RPM and verify installation

## OUTPUT FORMAT
1. **Checklist** (done/pending per phase)
2. **Agent Summary** (1 line per agent)
3. **Changes** (max 10 bullets)
4. **Commands** (shell)
5. **Files Changed** (list)

No essays. No filler.

## MODEL ROUTING (COST OPTIMIZATION)
See `.github/workflow/model-router.md` for full rules.

**Quick reference:**
- **haiku**: docs, formatting, version bumps, git ops, checklists
- **sonnet**: logic, tests, UI, reviews, single-module refactors
- **opus**: multi-file architecture, debugging, plugin design, planning

**Target: 60% of work on haiku, 30% sonnet, 10% opus**

## CONTEXT COMPRESSION RULES
1. CONTEXT COMPRESSION RULES
1. Read context files once, reference by name after
2. ROADMAP.md is truth — don't copy scope into prompts
3. Use bullet lists only, no paragraphs
4. Max 10 lines per response section